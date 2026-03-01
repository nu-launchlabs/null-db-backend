"""
Pagination configuration.
"""

from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """
    Default pagination for all list endpoints.

    Query params: ?page=1&page_size=20
    Max page size capped at 100 to prevent abuse.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100