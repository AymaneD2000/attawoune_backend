from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Default pagination that lets clients control page size via ?page_size=."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 1000
