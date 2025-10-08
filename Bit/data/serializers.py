from rest_framework import serializers
from .models import Repository, ShareableLink, Commit, Blob
from django.utils import timezone
from datetime import timedelta, datetime, timezone as dt_timezone
import uuid
from django.contrib.auth import get_user_model
import base64
import hashlib
import binascii

User = get_user_model()

class ShareableLinkSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShareableLink
        fields = ['token', 'expiration', 'is_active', 'created_at']
        read_only_fields = ['token', 'expiration', 'created_at']

class RepositorySerializer(serializers.ModelSerializer):
    share_links = ShareableLinkSerializer(many=True, read_only=True)
    author_username = serializers.CharField(source='author.username', read_only=True)
    
    class Meta:
        model = Repository
        fields = ['id', 'name', 'description', 'share_links', 'author_username', 'created_at']
        read_only_fields = ['id', 'author_username', 'created_at']

    def create(self, validated_data):
        # Get the user from the request context
        user = self.context['request'].user
        repository = Repository.objects.create(
            **validated_data,
            author=user
        )
        # Automatically create first share link
        ShareableLink.objects.create(
            repository=repository,
            token=uuid.uuid4(),
            expiration=timezone.now() + timedelta(days=10)
        )
        return repository 

class BlobSerializer(serializers.ModelSerializer):
    compressed_data = serializers.CharField(write_only=True)
    path = serializers.CharField(source='file_path', required=True)
    
    class Meta:
        model = Blob
        fields = ['sha1_hash', 'file_size', 'compressed_size', 'path', 'compressed_data']
        read_only_fields = ['sha1_hash', 'file_size', 'compressed_size']

    def validate(self, attrs):
        # Explicitly check for file_path presence after source mapping
        if 'file_path' not in attrs:
            raise serializers.ValidationError("'path' field is required for blobs")
        return attrs

    def create(self, validated_data):
        try:
            compressed_data = validated_data.pop('compressed_data')
            file_path = validated_data.pop('file_path')
        except KeyError as e:
            raise serializers.ValidationError(f"Missing required field: {e}")
        
        # Validate file_path is not empty
        if not file_path:
            raise serializers.ValidationError("File path cannot be empty")
        
        # Pass the raw base64 string to create_from_data
        return Blob.create_from_data({
            'path': file_path,
            'compressed_data': compressed_data,  # Pass the raw base64 string
        })

class CommitSerializer(serializers.ModelSerializer):
    blobs = serializers.SerializerMethodField()
    
    class Meta:
        model = Commit
        fields = [
            'commit_hash', 'author', 'email', 'timestamp', 
            'message', 'parent_hash', 'blobs'
        ]

    def get_blobs(self, obj):
        """Serialize all blobs associated with this commit"""
        return [{
            'sha1_hash': blob.sha1_hash,
            'file_size': blob.file_size,
            'compressed_size': blob.compressed_size,
            'path': blob.file_path  # Use file_path instead of path
        } for blob in obj.blobs.all()]

    def create(self, validated_data):
        # Extract blobs data before creating commit
        blobs_data = validated_data.pop('blobs', [])
        
        # Create commit
        commit = Commit.objects.create(**validated_data)
        
        # Process and add blobs
        for blob_data in blobs_data:
            blob = Blob.create_from_data(blob_data)
            commit.blobs.add(blob)
        
        return commit 