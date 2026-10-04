from rest_framework.pagination import PageNumberPagination

class StandardPagination(PageNumberPagination):
    """
    Every list endpoint returns the same envelope:

        {"count": int, "next": url|null, "previous": url|null, "results": [...]}

    Clients can tune the page with ?page=N&page_size=M (capped at 100).
    """
    
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100