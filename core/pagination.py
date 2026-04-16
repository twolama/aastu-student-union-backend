from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
import math

class CorePagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100

    def get_paginated_response(self, data):
        total_items = self.page.paginator.count
        total_pages = math.ceil(total_items / self.get_page_size(self.request))
        
        return Response({
            'results': data,
            'meta': {
                'page': self.page.number,
                'limit': self.get_page_size(self.request),
                'total': total_items,
                'totalPages': total_pages
            }
        })
