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
        ext = ext.lstrip('.')
        upload_kwargs = {
            'public_id': base_name,
            'resource_type': 'auto',
        }
        if ext:
            upload_kwargs['format'] = ext
        response = cloudinary.uploader.upload(content, **upload_kwargs)
        return response['public_id']

    def url(self, name) -> str:
        name = self._normalize_name(name)
        try:
            resource = cloudinary_api.resource(name)
            secure_url = resource.get('secure_url')
            if secure_url:
                return secure_url
            url = resource.get('url')
            if url:
                return url
        except Exception:
            pass
        return cloudinary.utils.cloudinary_url(name, secure=True)[0]

    def exists(self, name):
        name = self._normalize_name(name)
        try:
            cloudinary_api.resource(name)
            return True
        except Exception:
            return False

    def delete(self, name):
        name = self._normalize_name(name)
        cloudinary.uploader.destroy(name)