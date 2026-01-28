"""
This module demonstrates a simplified implementation of Django's URL routing
and view handling mechanism, drawing inspiration from its architecture.

It provides a basic `URLResolver` class to map URL patterns to view functions
and a `resolve` function to find the appropriate view for a given path.

This is a simplified example and does not include all the features of Django's
URL routing system.
"""

import re
from typing import Callable, List, Tuple, Optional, Dict, Any
from urllib.parse import urlparse

class URLResolver:
    """
    A class that maps URL patterns to view functions.

    Attributes:
        urlpatterns (List[Tuple[str, Callable]]): A list of URL patterns and their
            corresponding view functions. Each tuple contains a URL pattern (a regex string)
            and a view function (a callable).
    """

    def __init__(self, urlpatterns: List[Tuple[str, Callable]]):
        """
        Initializes the URLResolver with a list of URL patterns.

        Args:
            urlpatterns (List[Tuple[str, Callable]]): A list of URL patterns and
                their corresponding view functions.
        """
        self.urlpatterns = urlpatterns

    def resolve(self, path: str) -> Optional[Callable]:
        """
        Resolves a URL path to a view function.

        Args:
            path (str): The URL path to resolve.

        Returns:
            Optional[Callable]: The view function that matches the path, or None if no
                match is found.
        """
        for pattern, view in self.urlpatterns:
            match = re.match(f"^{pattern}$", path)
            if match:
                return view
        return None


def simple_view(request: Dict[str, Any]) -> str:
    """
    A simple view function that returns a string.

    Args:
        request (Dict[str, Any]): A dictionary representing the request object.

    Returns:
        str: A string containing a greeting message.
    """
    return "Hello, Darwin System!"


def dynamic_view(request: Dict[str, Any], name: str) -> str:
    """
    A view function that takes a dynamic parameter.

    Args:
        request (Dict[str, Any]): A dictionary representing the request object.
        name (str): The name parameter passed in the URL.

    Returns:
        str: A string containing a personalized greeting message.
    """
    return f"Hello, {name}!"


def resolve(path: str, url_resolver: URLResolver) -> Optional[Callable]:
    """
    Resolves a URL path to a view function using a URLResolver.

    Args:
        path (str): The URL path to resolve.
        url_resolver (URLResolver): The URLResolver to use for resolving the path.

    Returns:
        Optional[Callable]: The view function that matches the path, or None if no
            match is found.
    """
    try:
        view_func = url_resolver.resolve(path)
        return view_func
    except Exception as e:
        print(f"Error resolving URL: {e}")  # Log the error for debugging
        return None


def handle_request(path: str, url_resolver: URLResolver) -> str:
    """
    Handles a request by resolving the URL and calling the corresponding view function.

    Args:
        path (str): The URL path of the request.
        url_resolver (URLResolver): The URLResolver to use for resolving the path.

    Returns:
        str: The response from the view function, or an error message if the URL
            cannot be resolved.
    """
    try:
        view_func = resolve(path, url_resolver)
        if view_func:
            # Simulate passing a request object
            request = {}  # type: Dict[str, Any]
            if view_func is simple_view:
                return view_func(request)
            elif view_func is dynamic_view:
                # Extract the name from the path (simplified example)
                name = path.split('/')[-1]
                return view_func(request, name)
            else:
                return "View function found but could not be executed"
        else:
            return "404 Not Found"
    except Exception as e:
        print(f"Error handling request: {e}")  # Log the error
        return "500 Internal Server Error"


if __name__ == '__main__':
    # Define URL patterns
    urlpatterns: List[Tuple[str, Callable]] = [
        (r"^/$", simple_view),
        (r"^/hello/$", simple_view),
        (r"^/hello/(?P<name>\w+)/$", dynamic_view),  # Example using named groups (not directly used here for simplicity)
    ]

    # Create a URL resolver
    url_resolver = URLResolver(urlpatterns)

    # Example usage
    test_paths = ["/", "/hello/", "/hello/world/", "/about/"]
    for path in test_paths:
        response = handle_request(path, url_resolver)
        print(f"Path: {path}, Response: {response}")