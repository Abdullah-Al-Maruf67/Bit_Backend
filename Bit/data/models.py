from django.db import models
import zlib
import base64
from typing import Any
from django.utils import timezone
from datetime import datetime, timezone as dt_timezone
from django.contrib.auth import get_user_model
from django.conf import settings
import hashlib
import uuid
import json
import binascii


def get_default_user():
    User = get_user_model()
    # Get or create a default user
    user, created = User.objects.get_or_create(
        username='default_user',
        defaults={'email': 'default@example.com'}
    )
    return user.id

class Blob(models.Model):
    """
    Represents a file blob with compression functionality.
    
    Stores file content in a compressed format along with metadata
    like hash, size, and path information.
    """
    sha1_hash = models.CharField(
        max_length=40,
        help_text="SHA1 hash of the file content"
    )
    file_path = models.CharField(
        max_length=1024,
        help_text="Original file path"
    )
    file_size = models.PositiveIntegerField(
        help_text="Original file size in bytes"
    )
    compressed_data = models.BinaryField(
        help_text="zlib compressed file content"
    )
    compressed_size = models.PositiveIntegerField(
        help_text="Size of compressed data in bytes"
    )
    content = models.BinaryField(
        help_text="Base64 encoded content of the file",
        null=True  # Allow null for backward compatibility
    )
    
    @property
    def folder_path(self) -> str:
        """
        Get the folder path component of the file_path.
        Example: for 'foo/bar/file.txt' returns 'foo/bar'
        """
        if '/' not in self.file_path:
            return ''
        return '/'.join(self.file_path.split('/')[:-1])

    @property
    def filename(self) -> str:
        """
        Get the filename component of the file_path.
        Examele: for 'foo/bar/file.txt' returns 'file.txt'
        """
        return self.file_path.split('/')[-1]

    @classmethod
    def get_folder_structure(cls, repository_id: int) -> dict:
        """
        Returns a nested dictionary representing the folder structure
        for all blobs in a repository, including file metadata like SHA1.
        """
        # Change the query to get blobs directly from repository
        blobs = cls.objects.filter(repositories__id=repository_id)
        structure = {'files': []}

        for blob in blobs:
            if not blob.file_path:
                continue

            parts = blob.file_path.split('/')
            current = structure

            # Handle nested folders
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {'files': []}
                current = current[part]

            # Add file to current folder with metadata
            filename = parts[-1]
            file_info = {
                'name': filename,
                'sha1': blob.sha1_hash,
                'size': blob.file_size,
                'path': blob.file_path
            }
            
            # Check if file already exists (prevent duplicates)
            existing_files = [f for f in current['files'] if isinstance(f, dict) and f.get('name') == filename]
            if not existing_files:
                current['files'].append(file_info)

        return structure

    @classmethod
    def create_from_data(cls, data: dict) -> 'Blob':
        """
        Create a blob from client-compressed data.
        Expects data['compressed_data'] to be base64-encoded zlib-compressed content.
        """
        try:
            compressed_data = data['compressed_data']
            file_path = data.get('path') or data.get('file_path')
            if file_path is None:
                raise KeyError('path')
        except KeyError as e:
            raise ValueError(f"Missing required field in blob data: {str(e)}")
        
        try:
            decoded_data = base64.b64decode(compressed_data)
            try:
                decompressed_data = zlib.decompress(decoded_data)
            except zlib.error:
                decompressed_data = decoded_data
            
        except (TypeError, binascii.Error) as e:
            raise ValueError(f"Invalid base64 data: {str(e)}")
        
        # Compute SHA1 hash from the final content
        sha1_hash = hashlib.sha1(decompressed_data).hexdigest()
        
        # Create or get blob with this hash and path
        blob, created = cls.objects.get_or_create(
            sha1_hash=sha1_hash,
            file_path=file_path,
            defaults={
                'file_size': len(decompressed_data),
                'compressed_size': len(decoded_data),
                'compressed_data': decoded_data,
                'content': decompressed_data,
            }
        )
        
        return blob
    
    def get_original_data(self) -> bytes:
        """
        Decompress the stored data and return the original file content.
        
        Returns:
            bytes: Original uncompressed file content
        """
        return zlib.decompress(self.compressed_data)
    
    def get_content_base64(self) -> str:
        """
        Return the content as base64 encoded string.
        """
        return base64.b64encode(self.content).decode() if self.content else None
    
    def __str__(self) -> str:
        return f"Blob {self.sha1_hash[:8]}"  # Show only first 8 chars of hash
    
    class Meta:
        ordering = ['-file_size']
        verbose_name = 'File Blob'
        verbose_name_plural = 'File Blobs'
        unique_together = ['sha1_hash', 'file_path']


class Commit(models.Model):
    """
    Represents a version control commit with associated metadata and relationships.
    """
    commit_hash = models.CharField(
        max_length=40,
        unique=True,
        help_text="Unique commit hash identifier"
    )
    author = models.CharField(
        max_length=200,
        help_text="Name of the commit author"
    )
    email = models.EmailField(
        help_text="Email of the commit author"
    )
    timestamp = models.DateTimeField(
        help_text="When the commit was created"
    )
    message = models.TextField(
        help_text="Commit message"
    )
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Previous commit in history"
    )
    parent_hash = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        help_text="Hash of the parent commit"
    )
    blobs = models.ManyToManyField(
        Blob,
        related_name='commits',
        help_text="Files included in this commit"
    )
    deleted_files = models.JSONField(
        default=list,
        blank=True,
        help_text="List of file paths that were deleted in this commit"
    )
    
    @classmethod
    def create_from_data(cls, data: dict) -> 'Commit':
        blobs_data = data.pop('blobs', [])
        deleted_files = data.pop('deleted_files', [])
        
        # Convert timestamp to integer if it's a datetime object
        timestamp = data.get('timestamp')
        if isinstance(timestamp, datetime):
            timestamp = int(timestamp.timestamp())
        
        # Include timestamp in commit hash calculation to make it unique
        commit_data = {
            'author': data.get('author'),
            'email': data.get('email'),
            'timestamp': str(timestamp),  # Convert timestamp to string for hash
            'message': data.get('message'),
            'parent_hash': data.get('parent_hash', ''),
            'deleted_files': deleted_files  # Include deleted files in hash
        }
        
        # Add a unique component to ensure unique commits
        commit_data['unique'] = str(uuid.uuid4())
        
        commit_hash = hashlib.sha1(
            json.dumps(commit_data, sort_keys=True).encode()
        ).hexdigest()

        # Create the datetime object for the database
        commit_timestamp = datetime.fromtimestamp(timestamp, tz=dt_timezone.utc)

        # Always create a new commit
        commit = cls.objects.create(
            commit_hash=commit_hash,
            author=data['author'],
            email=data['email'],
            timestamp=commit_timestamp,
            message=data['message'],
            parent_hash=data.get('parent_hash'),
            deleted_files=deleted_files,  # Store deleted files
        )

        # Process blobs
        processed_paths = set()
        for blob_item in blobs_data:
            if isinstance(blob_item, Blob):
                blob = blob_item
            elif isinstance(blob_item, dict):
                path = blob_item.get('path')
                if path in processed_paths:
                    continue
                processed_paths.add(path)
                blob = Blob.create_from_data(blob_item)
            else:
                raise ValueError("Invalid blob data provided")
            commit.blobs.add(blob)
        
        return commit
    
    def __str__(self) -> str:
        return f"Commit {self.commit_hash[:8]} by {self.author}"
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Commit'
        verbose_name_plural = 'Commits'


class Repository(models.Model):
    """
    Represents a code repository containing commits and their history.
    """
    name = models.CharField(
        max_length=255,
        help_text="Repository name"
    )
    description = models.TextField(
        blank=True,
        help_text="Repository description"
    )
    commits = models.ManyToManyField(
        Commit,
        related_name='repositories',
        help_text="Commits in this repository"
    )
    blobs = models.ManyToManyField(
        Blob,
        related_name='repositories',
        help_text="Current files in the repository"
    )
    author = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='repositories',
        help_text="Repository creator"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the repository was created"
    )
    
    def __str__(self) -> str:
        return self.name
    
    def update_contents(self):
        """
        Update repository contents by applying changes from the latest commit.
        This properly merges changes instead of replacing all content.
        """
        if not self.commits.exists():
            return
            
        # Get the latest commit (by timestamp)
        latest_commit = self.commits.latest('timestamp')
        
        # Add/update blobs from the latest commit
        # ManyToMany will handle duplicates automatically
        blobs_to_add = list(latest_commit.blobs.all())
        if blobs_to_add:
            self.blobs.add(*blobs_to_add)
        
        # Remove blobs that were deleted in the latest commit
        for deleted_path in latest_commit.deleted_files:
            # Remove blobs with matching file_path
            self.blobs.filter(file_path=deleted_path).delete()
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Repository'
        verbose_name_plural = 'Repositories'


class ShareableLink(models.Model):
    """
    Represents a temporary shareable link for a repository with expiration.
    """
    token = models.CharField(
        max_length=36, 
        unique=True,
        help_text="Unique access token for the link"
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='share_links'
    )
    expiration = models.DateTimeField(
        help_text="When the link becomes invalid"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the link is currently valid"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def is_valid(self):
        return self.is_active and timezone.now() < self.expiration

    class Meta:
        ordering = ['-created_at']


class GitBlob(models.Model):
    """
    Represents just the file content, like Git's blob object
    """
    sha1_hash = models.CharField(
        max_length=40,
        unique=True,  # Now can be unique since it's just content
        help_text="SHA1 hash of the file content"
    )
    compressed_data = models.BinaryField(
        help_text="zlib compressed file content"
    )
    size = models.PositiveIntegerField(
        help_text="Original file size in bytes"
    )


class GitTree(models.Model):
    """
    Represents a directory structure, like Git's tree object
    """
    sha1_hash = models.CharField(max_length=40, unique=True)
    entries = models.JSONField(help_text="Dictionary of name->sha1_hash mappings")
    parent = models.ForeignKey(
        'self', 
        null=True, 
        on_delete=models.CASCADE
    )


class GitCommit(models.Model):
    """
    Points to a tree and contains metadata, like Git's commit object
    """
    commit_hash = models.CharField(max_length=40, unique=True)
    tree = models.ForeignKey(GitTree, on_delete=models.CASCADE)
    parent = models.ForeignKey(
        'self',
        null=True,
        on_delete=models.SET_NULL
    )
    author = models.CharField(max_length=100)
    timestamp = models.DateTimeField()
    message = models.TextField()
