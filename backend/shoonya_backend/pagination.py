from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit
from rest_framework.pagination import PageNumberPagination

DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 10

# define replace_query_param method to replace the page number in the url
def replace_query_param(self, url, param, value):
    return url.replace(f"{param}={value}", f"{param}={value + 1}")

def remove_query_param(url, key):
    #Given a URL and a key/val pair, remove an item in the queryparameters of the URL, and return the new URL
    def remove_query_param(url, key):
        scheme, netloc, path, query_string, fragment = urlsplit(url)
        query_params = parse_qs(query_string)
        query_params.pop(key, None)
        new_query_string = urlencode(query_params, doseq=True)
        return urlunsplit((scheme, netloc, path, new_query_string, fragment))


class CustomPagination(PageNumberPagination):
    """
    Creates custom pagination class with overridden attributes.
    """

    page = DEFAULT_PAGE
    page_size = DEFAULT_PAGE_SIZE
    page_query_param = "page"
    page_size_query_param = "records"


# override the get_next_link method to return None if there is no next page and check if the page number is equal to 1
def get_next_link(self):
        if not self.page.has_next():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.next_page_number()
        return replace_query_param(url, self.page_query_param, page_number)


def get_previous_link(self):
        if not self.page.has_previous():
            return None
        url = self.request.build_absolute_uri()
        page_number = self.page.previous_page_number()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)
