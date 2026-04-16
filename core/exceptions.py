from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def core_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        custom_response_data = {
            "success": False,
            "error": {
                "code": "ERROR",
                "message": "An error occurred",
                "details": response.data
            }
        }

        # Handle specific error types
        if response.status_code == 422 or response.status_code == 400:
            custom_response_data["error"]["code"] = "VALIDATION_ERROR"
            custom_response_data["error"]["message"] = "Invalid input data"
        elif response.status_code == 401:
            custom_response_data["error"]["code"] = "UNAUTHORIZED"
            custom_response_data["error"]["message"] = "Authentication credentials were not provided or are invalid"
        elif response.status_code == 403:
            custom_response_data["error"]["code"] = "FORBIDDEN"
            custom_response_data["error"]["message"] = "You do not have permission to perform this action"
        elif response.status_code == 404:
            custom_response_data["error"]["code"] = "NOT_FOUND"
            custom_response_data["error"]["message"] = "The requested resource was not found"
        
        # Mapping DRF key 'detail' to our 'message' if it exists and we don't have a better one
        if isinstance(response.data, dict) and 'detail' in response.data:
            custom_response_data["error"]["message"] = response.data['detail']
            # If details is just the detail message, we might want to clean it up
            if len(response.data) == 1:
                custom_response_data["error"]["details"] = {}

        response.data = custom_response_data

    return response
