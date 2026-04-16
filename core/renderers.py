import re
from rest_framework.renderers import JSONRenderer

def to_camel_case(snake_str):
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def camelize_data(data):
    if isinstance(data, dict):
        new_dict = {}
        for key, value in data.items():
            new_key = to_camel_case(key)
            new_dict[new_key] = camelize_data(value)
        return new_dict
    elif isinstance(data, list):
        return [camelize_data(item) for item in data]
    return data

class CoreJSONRenderer(JSONRenderer):
    """
    Custom renderer to enforce the standard response format:
    {
      "success": true,
      "data": { ... }
    }
    Also converts snake_case keys to camelCase.
    """
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get('response')
        
        # If it's already a standardized error or success response, we might not want to wrap it again
        # However, for simplicity and strict adherence to Section 4:
        
        success = True
        if response and 400 <= response.status_code < 600:
            success = False

        # If data is None (e.g. 204 No Content), data should be None
        # But rules say { "success": true, "data": { ... } }
        
        # Handle cases where data might already have success key (from custom exception handler)
        if isinstance(data, dict) and 'success' in data:
            formatted_data = data
        else:
            if success:
                formatted_data = {
                    "success": True,
                    "data": data
                }
            else:
                # This part is usually handled by custom_exception_handler, 
                # but we provide a fallback here.
                formatted_data = {
                    "success": False,
                    "error": {
                        "code": "ERROR",
                        "message": "An error occurred",
                        "details": data
                    }
                }

        # Handle Pagination structure (moving meta outside data if it exists)
        if success and isinstance(data, dict) and 'results' in data and 'meta' in data:
            formatted_data = {
                "success": True,
                "data": data['results'],
                "meta": data['meta']
            }

        # Camelize the entire payload
        camelized_data = camelize_data(formatted_data)
        
        return super().render(camelized_data, accepted_media_type, renderer_context)
