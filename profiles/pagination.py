from urllib.parse import urlparse
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class ProfilePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "limit"
    max_page_size = 50
    
    def get_paginated_response(self, data):
        return Response({
            "status": "success",
            "page": self.page.number,
            "limit": self.page.paginator.per_page,
            "total": self.page.paginator.count,
            "total_pages": self.page.paginator.num_pages,
            "links": {
                "self": self.request.get_full_path(),
                "next": self.to_relative(self.get_next_link()),
                "prev": self.to_relative(self.get_previous_link())
            },
            "data": data
        }, status=200)
        
        
    def to_relative(self, abs_url):
        if not abs_url:
            return None
        parsed = urlparse(abs_url)
        return parsed.path + ("?" + parsed.query if parsed.query else "")

