from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from .models import Repository, ShareableLink, Blob, Commit
from .serializers import (
    RepositorySerializer, 
    ShareableLinkSerializer,
    CommitSerializer
)
from django.utils import timezone
from datetime import timedelta
import uuid

# Create your views here.

class RepositoryViewSet(viewsets.ModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        # DEBUG: Print incoming repository creation request
        print("=" * 50)
        print("🏗️ INCOMING REPOSITORY CREATION REQUEST:")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"📦 Data: {request.data}")
        print(f"👤 User: {request.user.username}")
        print("=" * 50)
        
        return super().create(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        """Override retrieve to include repository contents"""
        repository = self.get_object()
        serializer = self.get_serializer(repository)
        data = serializer.data
        
        # Add the repository structure/contents
        data['contents'] = Blob.get_folder_structure(repository.id)
        
        return Response(data)

    def list(self, request, *args, **kwargs):
        """Override list to include repository contents for each repository"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data
        
        # Add contents for each repository
        for repo in data:
            repo['contents'] = Blob.get_folder_structure(repo['id'])
            
        return Response(data)

    @action(detail=True, methods=['get'], url_path='file')
    def get_file(self, request, pk=None):
        """Return file content using either unique `sha1` or `path`.

        - Prefer `sha1` when provided: GET /repositories/{id}/file?sha1=...
          If multiple files share the same content, also pass `path` to disambiguate.
        - Otherwise, use full `path`.
        """
        repository = self.get_object()
        file_path = request.query_params.get('path')
        sha1 = request.query_params.get('sha1')

        if not sha1 and not file_path:
            return Response({'error': 'Provide either `sha1` or `path`'}, status=status.HTTP_400_BAD_REQUEST)

        blob = None
        if sha1:
            qs = Blob.objects.filter(repositories__id=repository.id, sha1_hash=sha1)
            if file_path:
                qs = qs.filter(file_path=file_path)
            matches = list(qs[:2])
            if len(matches) == 0:
                return Response({'error': 'File not found for given sha1/path'}, status=status.HTTP_404_NOT_FOUND)
            if len(matches) > 1 and not file_path:
                return Response({
                    'error': 'Multiple files share this content. Provide `path` to disambiguate.',
                    'candidates': list(Blob.objects.filter(repositories__id=repository.id, sha1_hash=sha1).values_list('file_path', flat=True))
                }, status=status.HTTP_409_CONFLICT)
            blob = matches[0]
        else:
            try:
                blob = Blob.objects.get(repositories__id=repository.id, file_path=file_path)
            except Blob.DoesNotExist:
                return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
        raw_bytes = None
        if blob.content:
            raw_bytes = bytes(blob.content)
        else:
            try:
                raw_bytes = blob.get_original_data()
            except Exception:
                return Response({'error': 'Failed to read file content'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        try:
            text = raw_bytes.decode('utf-8')
            return Response({'path': blob.file_path, 'sha1': blob.sha1_hash, 'encoding': 'utf-8', 'text': text})
        except UnicodeDecodeError:
            import base64
            b64 = base64.b64encode(raw_bytes).decode('ascii')
            return Response({'path': blob.file_path, 'sha1': blob.sha1_hash, 'encoding': 'base64', 'content': b64})

    @action(detail=True, methods=['post'])
    def generate_link(self, request, pk=None):
        print("=" * 50)
        print("🔗 INCOMING SHARE TOKEN GENERATION REQUEST:")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"📦 Data: {request.data}")
        print(f"🏗️ Repository ID: {pk}")
        print(f"👤 User: {request.user.username}")
        print("=" * 50)
        
        repository = self.get_object()
        
        # Check if user is the repository owner
        if repository.author != request.user:
            return Response(
                {'error': 'Only the repository owner can generate share links'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        ShareableLink.objects.filter(
            repository=repository,
            is_active=True
        ).update(is_active=False)
        
        new_link = ShareableLink.objects.create(
            repository=repository,
            token=uuid.uuid4(),
            expiration=timezone.now() + timedelta(days=10)
        )
        
        return Response({
            'token': new_link.token,
            'expiration': new_link.expiration
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def structure(self, request, pk=None):
        """Get the folder structure of the repository"""
        repository = self.get_object()
        structure = Blob.get_folder_structure(repository.id)
        return Response(structure)

    def destroy(self, request, *args, **kwargs):
        """Delete a repository and clean up associated data"""
        repository = self.get_object()
        
        # Check if user has permission to delete (only author can delete)
        if repository.author != request.user:
            return Response(
                {'error': 'You can only delete your own repositories'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Clean up associated data
        # Remove repository from all blobs (but don't delete blobs - they might be used by other repos)
        repository.blobs.clear()
        
        # Remove repository from commits (but don't delete commits - they might be used by other repos)
        repository.commits.clear()
        
        # Delete shareable links
        repository.share_links.all().delete()
        
        # Delete the repository itself
        repository.delete()
        
        return Response(
            {'message': f'Repository "{repository.name}" deleted successfully'}, 
            status=status.HTTP_204_NO_CONTENT
        )

    @action(detail=False, methods=['get'], url_path='author/(?P<username>[^/.]+)')
    def by_author(self, request, username=None):
        """Get all repositories by a specific author username"""
        from django.contrib.auth import get_user_model
        
        User = get_user_model()
        try:
            user = User.objects.get(username=username)
            repositories = Repository.objects.filter(author=user)
            serializer = self.get_serializer(repositories, many=True)
            
            # Add contents for each repository
            data = serializer.data
            for repo in data:
                repo['contents'] = Blob.get_folder_structure(repo['id'])
            
            return Response(data)
        except User.DoesNotExist:
            return Response(
                {'error': f'User with username "{username}" not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class ShareableLinkViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]
    
    @action(detail=False, methods=['get'], url_path='(?P<token>.+)/check')
    def check_validity(self, request, token=None):
        # DEBUG: Print incoming token validation request
        print("=" * 50)
        print("✅ INCOMING TOKEN VALIDATION REQUEST:")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"🔑 Token: {token}")
        print("=" * 50)
        
        try:
            link = ShareableLink.objects.get(token=token)
            is_valid = link.is_valid()
            return Response({
                'valid': is_valid,
                'expiration': link.expiration,
                'repository': link.repository.name
            })
        except ShareableLink.DoesNotExist:
            return Response({'valid': False}, status=404)
    
    @action(detail=False, methods=['get'], url_path='(?P<token>.+)/repository')
    def get_repository_by_token(self, request, token=None):
        """
        Get repository data using a share link token.
        Returns repository information and contents without requiring authentication.
        """
        # DEBUG: Print incoming repository access request
        print("=" * 50)
        print("📦 INCOMING SHARE TOKEN REPOSITORY ACCESS REQUEST:")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"🔑 Token: {token}")
        print("=" * 50)
        
        try:
            link = ShareableLink.objects.get(token=token)
            
            # Check if link is valid
            if not link.is_valid():
                return Response(
                    {'error': 'Share link has expired or is invalid'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            repository = link.repository
            
            # Serialize repository data
            serializer = RepositorySerializer(repository)
            data = serializer.data
            
            # Add repository contents/structure
            data['contents'] = Blob.get_folder_structure(repository.id)
            
            # Add share link info
            data['share_info'] = {
                'expiration': link.expiration,
                'created_at': link.created_at
            }
            
            return Response(data)
            
        except ShareableLink.DoesNotExist:
            return Response(
                {'error': 'Invalid share token'}, 
                status=status.HTTP_404_NOT_FOUND
            )

class CommitViewSet(viewsets.ModelViewSet):
    queryset = Commit.objects.all()
    serializer_class = CommitSerializer
    permission_classes = [permissions.AllowAny]

    def dispatch(self, request, *args, **kwargs):
        # DEBUG: Catch ALL requests to this viewset
        print("=" * 50)
        print("🚨 DISPATCH - ALL COMMIT REQUESTS:")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"📦 Raw Data: {getattr(request, 'data', 'No data')}")
        print(f"📋 Content Type: {getattr(request, 'content_type', 'No content type')}")
        print(f"📏 Content Length: {getattr(request, 'content_length', 'No content length')}")
        print(f"🔑 Headers: {dict(request.headers)}")
        
        # Try to read the raw body
        try:
            body = request.body.decode('utf-8')
            print(f"📄 Raw Body: {body}")
            print(f"📄 Body Length: {len(body)}")
        except UnicodeDecodeError as e:
            print(f"❌ UTF-8 decode error: {e}")
            print(f"📄 Raw Bytes: {request.body}")
            print(f"📄 Bytes Length: {len(request.body)}")
            print(f"📄 First 50 bytes: {request.body[:50]}")
            # Try to decode as latin-1 to see what's there
            try:
                body_latin1 = request.body.decode('latin-1')
                print(f"📄 Latin-1 decoded: {body_latin1}")
            except Exception as e2:
                print(f"❌ Latin-1 decode also failed: {e2}")
        except Exception as e:
            print(f"❌ Error reading body: {e}")
        
        print("=" * 50)
        
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            print(f"❌ ERROR in dispatch: {e}")
            print(f"❌ Error type: {type(e)}")
            import traceback
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response_data = serializer.data
        
        # Get the original blob paths from the database
        original_blobs = instance.blobs.all()
        for blob in response_data.get('blobs', []):
            # Find the matching original blob
            original_blob = original_blobs.get(sha1_hash=blob['sha1_hash'])
            if original_blob:
                # Try to get the original path from the blob's metadata or attributes
                original_path = getattr(original_blob, 'original_path', None)
                if original_path:
                    blob['path'] = original_path
                elif hasattr(original_blob, 'metadata') and original_blob.metadata.get('path'):
                    blob['path'] = original_blob.metadata['path']
                # If we can't find the original path, keep the path from the blob
                
        return Response(response_data)

    def create(self, request, *args, **kwargs):
        # DEBUG: Print incoming request IMMEDIATELY
        print("=" * 50)
        print("🔍 INCOMING COMMIT REQUEST (RAW):")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"📦 Raw Data: {request.data}")
        print(f"📋 Content Type: {request.content_type}")
        print(f"🔑 Headers: {dict(request.headers)}")
        print("=" * 50)
        
        # DEBUG: Print incoming request
        print("=" * 50)
        print("🔍 INCOMING COMMIT REQUEST:")
        print(f"📝 Method: {request.method}")
        print(f"🌐 URL: {request.path}")
        print(f"📦 Data: {request.data}")
        print("=" * 50)
        
        # Validate share token and get repository
        share_token = request.data.get('share_token')
        try:
            share_link = ShareableLink.objects.get(token=share_token, is_active=True)
            if not share_link.is_valid():
                return Response(
                    {"error": "Share link has expired"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except ShareableLink.DoesNotExist:
            return Response(
                {"error": "Invalid share token"}, 
                status=status.HTTP_403_FORBIDDEN
            )

        repository = share_link.repository
        
        # Prepare commit data
        commit_data = {
            'author': request.data.get('author'),
            'email': request.data.get('email'),
            'message': request.data.get('message'),
            'parent_hash': request.data.get('parent_hash'),
            'timestamp': timezone.now()  # Use current time
        }
        
        # Process operations into blobs
        operations = request.data.get('operations', [])
        blobs_data = []
        deleted_files = []
        
        for op in operations:
            if op.get('type') == 'DELETE':
                deleted_files.append(op.get('path'))
                continue
                
            if op.get('type') == 'UPDATE':
                blobs_data.append({
                    'compressed_data': op['content'],
                    'path': op['path']
                })
        
        # Create commit using model method
        commit = Commit.create_from_data({
            **commit_data,
            'blobs': blobs_data
        })
        
        # Associate with repository and update contents
        repository.commits.add(commit)
        repository.update_contents()
        
        # Prepare response
        response_data = CommitSerializer(commit).data
        response_data.update({
            'id': commit.id,
            'contents': Blob.get_folder_structure(repository.id),
            'operations_summary': {
                'updated': [op['path'] for op in operations if op['type'] == 'UPDATE'],
                'deleted': deleted_files,
                'unchanged': []
            }
        })
        
        return Response(response_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'])
    def by_hash(self, request):
        commit_hash = request.query_params.get('hash')
        if not commit_hash:
            return Response(
                {'error': 'Commit hash is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            commit = Commit.objects.get(commit_hash=commit_hash)
            return Response({
                'id': commit.id,
                'commit_hash': commit.commit_hash,
                # ... other commit details ...
            })
        except Commit.DoesNotExist:
            return Response(
                {'error': 'Commit not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )

@api_view(['POST'])
def merge_commit(request, repository_id, commit_id):
    try:
        repository = Repository.objects.get(id=repository_id)
        commit = Commit.objects.get(id=commit_id)
        
        # First add the commit to the repository if it's not already there
        repository.commits.add(commit)
        
        # Perform the merge operation
        repository.update_contents()
        
        # Get the updated repository contents
        contents = Blob.get_folder_structure(repository.id)
        
        return Response({
            "message": "Commit merged successfully",
            "repository": {
                "id": repository.id,
                "name": repository.name,
                "contents": contents
            }
        })
        
    except Repository.DoesNotExist:
        return Response(
            {"error": "Repository not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Commit.DoesNotExist:
        return Response(
            {"error": "Commit not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
