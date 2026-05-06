import cloudinary
import cloudinary.uploader
import cloudinary.utils
from cloudinary import api as cloudinary_api
from django.core.files.storage import FileSystemStorage
import os
from urllib.parse import urlparse

def parse_cloudinary_url(url):
    parsed = urlparse(url)
    cloud_name = parsed.hostname
    api_key = parsed.username
    api_secret = parsed.password
    return cloud_name, api_key, api_secret

class CloudinaryStorage(FileSystemStorage):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Configure cloudinary if not already
        cloudinary_url = os.getenv('CLOUDINARY_URL', '')
        if cloudinary_url:
            cloud_name, api_key, api_secret = parse_cloudinary_url(cloudinary_url)
            cloudinary.config(
                cloud_name=cloud_name,
                api_key=api_key,
                api_secret=api_secret,
                secure=True
            )

    def _normalize_name(self, name: str) -> str:
        return name.replace('\\', '/')

    def _save(self, name, content):
        name = self._normalize_name(name)
        base_name, ext = os.path.splitext(name)
        ext = ext.lstrip('.').lower()
        
        # Determine resource type based on file extension
        # PDFs and documents should use 'raw' type for proper MIME type handling
        if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip']:
            resource_type = 'raw'
        else:
            resource_type = 'image'
        
        # For raw files, include extension in public_id (crucial for proper URL generation)
        public_id = base_name
        if resource_type == 'raw' and ext:
            public_id = f"{base_name}.{ext}"
        
        upload_kwargs = {
            'public_id': public_id,
            'resource_type': resource_type,
            'overwrite': True,
            'access_mode': 'public',
        }
            
        response = cloudinary.uploader.upload(content, **upload_kwargs)
        # Return the public_id (which includes extension for raw files)
        return response['public_id']

    def url(self, name) -> str:
        name = self._normalize_name(name)
        base_name, ext = os.path.splitext(name)
        ext = ext.lstrip('.').lower()
        
        # Determine resource type based on file extension
        if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip']:
            resource_type = 'raw'
            # Ensure extension is in name for raw files
            if ext and not name.lower().endswith(f'.{ext}'):
                name = f"{base_name}.{ext}"
        else:
            resource_type = 'image'

        # Try to fetch the actual resource from Cloudinary API to get the correct URL with version
        try:
            resource = cloudinary_api.resource(name, resource_type=resource_type)
            secure_url = resource.get('secure_url')
            if secure_url:
                return secure_url
        except Exception:
            # Fallback if API call fails
            pass

        # Fallback: generate URL using cloudinary utility
        # Note: This may not have the correct version for already-uploaded files
        return cloudinary.utils.cloudinary_url(
            name,
            resource_type=resource_type,
            secure=True,
            sign_url=False,
        )[0]

    def exists(self, name):
        name = self._normalize_name(name)
        base_name, ext = os.path.splitext(name)
        ext = ext.lstrip('.').lower()
        
        # Check with appropriate resource type
        if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip']:
            resource_types = ['raw']
        else:
            resource_types = ['image', 'raw', 'video']
        
        for r_type in resource_types:
            try:
                cloudinary_api.resource(name, resource_type=r_type)
                return True
            except Exception:
                continue
        return False

    def delete(self, name):
        name = self._normalize_name(name)
        base_name, ext = os.path.splitext(name)
        ext = ext.lstrip('.').lower()
        
        # Delete with appropriate resource type
        if ext in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'zip']:
            resource_type = 'raw'
        else:
            resource_type = 'image'
        
        response = cloudinary.uploader.destroy(name, resource_type=resource_type)
        if response.get('result') != 'ok':
            # Try alternate resource type as fallback
            alt_resource_type = 'raw' if resource_type == 'image' else 'image'
            cloudinary.uploader.destroy(name, resource_type=alt_resource_type)