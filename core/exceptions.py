from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def core_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        # Default starting values
        message = "An error occurred"
        code = "ERROR"
        
        # Handle status-based defaults
        if response.status_code == 400:
            code = "VALIDATION_ERROR"
            message = "Invalid input data"
        elif response.status_code == 401:
            code = "UNAUTHORIZED"
            message = "Authentication credentials were not provided or are invalid"
        elif response.status_code == 403:
            code = "FORBIDDEN"
            message = "You do not have permission to perform this action"
        elif response.status_code == 404:
            code = "NOT_FOUND"
            message = "The requested resource was not found"
        elif response.status_code == 429:
            code = "THROTTLED"
            message = "Request was throttled"

        # Try to extract a more specific error message from the response data
        if isinstance(response.data, dict):
            # 1. Check for 'detail' (standard for many DRF errors)
            if 'detail' in response.data:
                message = response.data['detail']
            
            # 2. Check for validation errors (non_field_errors or field-specific)
            elif response.status_code == 400:
                # Prioritize non_field_errors (common for password validation)
                # Check both snake_case and camelCase just in case
                non_field_errors = response.data.get('non_field_errors') or response.data.get('nonFieldErrors')
                
                if non_field_errors and isinstance(non_field_errors, list) and len(non_field_errors) > 0:
                    # Use the first error message
                    message = str(non_field_errors[0])
                elif not non_field_errors:
                    # Try to get the first field-specific error
                    first_field = next(iter(response.data), None)
                    if first_field:
                        field_errors = response.data[first_field]
                        if isinstance(field_errors, list) and len(field_errors) > 0:
                            # e.g., "newPassword: This field is required"
                            message = str(field_errors[0])
                        elif isinstance(field_errors, str):
                            message = field_errors

        custom_response_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": response.data
            }
        }

        # If details is just the detail message itself, we can empty it out
        if isinstance(response.data, dict) and len(response.data) == 1 and 'detail' in response.data:
            custom_response_data["error"]["details"] = {}

        response.data = custom_response_data

    return response
