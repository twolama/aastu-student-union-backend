from drf_spectacular.openapi import AutoSchema
from rest_framework import serializers

class AASTUAutoSchema(AutoSchema):
    """
    Custom OpenAPI schema class for the AASTU Student Union UI.
    Optimizes file/image uploads and automatically groups endpoints by Django app or manual tags.
    """

    def _map_serializer_field(self, field, direction, bypass_extensions=False):
        # 0. Custom mapping for JSON and list fields
        json_fields = {
            'attendance': {'type': 'object'},
            'logistics': {'type': 'object'},
            'links': {'type': 'object'},
            'volunteers': {'type': 'array', 'items': {'type': 'object'}},
            'tags': {'type': 'array', 'items': {'type': 'string'}},
            'procedure_steps': {'type': 'array', 'items': {'type': 'string'}},
        }
        
        if field.field_name in json_fields:
            return json_fields[field.field_name]

        # 1. Standard instance check for file/image fields
        is_file = isinstance(field, (serializers.ImageField, serializers.FileField))

        # 2. String-based class name fallback (extra safety)
        if not is_file:
            if field.__class__.__name__ in ['ImageField', 'FileField']:
                is_file = True
            elif any(c.__name__ in ['ImageField', 'FileField'] for c in field.__class__.__mro__):
                is_file = True

        # Ensure Swagger shows a 'File' upload button instead of a simple string
        if direction == 'request' and is_file:
            return {'type': 'string', 'format': 'binary'}

        schema = super()._map_serializer_field(field, direction, bypass_extensions)

        # Handle the field renaming for Swagger consistency
        if field.field_name == 'response_data':
            field.field_name = 'data'

        return schema

    def get_tags(self):
        # 1. Look for 'schema_tags' attribute on the ViewSet for explicit control
        if hasattr(self.view, 'schema_tags'):
            return self.view.schema_tags
            
        view_name = self.view.__class__.__name__
        
        # 2. Manual mapping for Auth and special views
        tag_map = {
            'TokenObtainPairView': ['Authentication'],
            'TokenRefreshView': ['Authentication'],
            'TokenVerifyView': ['Authentication'],
            'CustomTokenObtainPairView': ['Authentication'],
            'RegisterView': ['Authentication'],
            'ForgotPasswordView': ['Authentication'],
            'ResetPasswordView': ['Authentication'],
            'ChangePasswordView': ['Authentication'],
            'ProfileViewSet': ['User | Profile'],
            'SystemStatsView': ['Admin | Stats'],
            'HealthCheckView': ['Admin | Stats'],
        }
        
        if view_name in tag_map:
            return tag_map[view_name]

        # 3. Default: Group by App Name (e.g., 'clubs' -> 'Clubs')
        # This prevents the need to update every view manually.
        module_path = self.view.__class__.__module__
        if '.' in module_path:
            app_label = module_path.split('.')[0]
            # Convert 'aastu_su_backend' or 'clubs' to 'Clubs'
            if app_label != 'aastu_su_backend':
                return [app_label.replace('_', ' ').capitalize()]

        return super().get_tags()
