import re
from rest_framework.parsers import JSONParser

def to_snake_case(camel_str):
    """
    Convert camelCase string to snake_case.
    """
    return re.sub(r'(?<!^)(?=[A-Z])', '_', camel_str).lower()

def snakeize_data(data):
    """
    Recursively convert dictionary keys from camelCase to snake_case.
    """
    if isinstance(data, dict):
        return {to_snake_case(k): snakeize_data(v) for k, v in data.items()}
    if isinstance(data, list):
        return [snakeize_data(i) for i in data]
    return data

class CoreJSONParser(JSONParser):
    """
    Custom JSON parser that converts incoming camelCase keys to snake_case.
    """
    def parse(self, stream, media_type=None, parser_context=None):
        data = super().parse(stream, media_type, parser_context)
        return snakeize_data(data)
