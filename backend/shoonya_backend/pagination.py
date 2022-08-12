from rest_framework.pagination import PageNumberPagination

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10


class CustomPagination(PageNumberPagination):
    """
    Creates custom pagination class with overridden attributes.
    """

    page = DEFAULT_PAGE
    page_size = DEFAULT_PAGE_SIZE
    page_query_param = "page"
    page_size_query_param = "records"
