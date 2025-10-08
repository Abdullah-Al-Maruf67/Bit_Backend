import base64
import zlib
import hashlib

class Blob:
    @classmethod
    def create_from_data(cls, data: dict) -> 'Blob':
        """
        Create a blob from client-compressed data
        """
        file_path = data.get('path') or data.get('file_path')
        if not file_path:
            raise ValueError("File path not provided in blob data")
        file_path = '/'.join(filter(None, file_path.split('/')))
        
        try:
            # Decode base64 compressed data from client
            try:
                compressed_content = base64.b64decode(data['compressed_data'])
            except Exception as e:
                raise ValueError(f"Invalid base64 data: {str(e)}")
            if len(compressed_content) < 2:
                raise ValueError("Compressed data too short")
            
            original_content = None
            last_error = None
            # Try multiple decompression methods in sequence
            for method in (
                lambda: zlib.decompress(compressed_content),
                lambda: zlib.decompress(compressed_content, wbits=-15),
                lambda: zlib.decompress(compressed_content, wbits=32 + 15)
            ):
                try:
                    original_content = method()
                    if original_content:
                        break
                except zlib.error as e:
                    last_error = e
            if not original_content:
                raise ValueError(
                    f"All decompression methods failed. Last error: {str(last_error)}. "
                    f"Compressed data size: {len(compressed_content)} bytes, first few bytes: {compressed_content[:10].hex()}"
                )
            
            # Compute SHA1 hash from original content
            hash_val = hashlib.sha1(original_content).hexdigest()
            
            # Use get_or_create to avoid duplicate blob creation
            blob, created = cls.objects.get_or_create(
                sha1_hash=hash_val,
                defaults={
                    'file_size': len(original_content),
                    'compressed_size': len(compressed_content),
                    'file_path': file_path,
                    'compressed_data': compressed_content,
                    'content': original_content,
                }
            )
            return blob
        
        except Exception as e:
            raise ValueError(f"Error processing blob data: {str(e)}") 