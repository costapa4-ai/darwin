"""
This module demonstrates applying architectural patterns inspired by
the `anthropics/anthropic-sdk-python` repository, focusing on code
organization, error handling, and maintainability.  Specifically, it
emphasizes:

1.  **Clear Separation of Concerns:** Dividing functionalities into
    distinct modules and classes.
2.  **Robust Error Handling:** Implementing comprehensive error
    handling with specific exception types.
3.  **Asynchronous Operations:** Utilizing asyncio for non-blocking
    operations (not explicitly requested, but demonstrates a common
    pattern).

This is a simplified example and can be expanded based on the specific
needs of the Darwin System.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional, Type, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class APIError(Exception):
    """Base class for API related exceptions."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class AuthenticationError(APIError):
    """Exception raised for authentication failures."""
    pass


class RateLimitError(APIError):
    """Exception raised when rate limits are exceeded."""
    pass


class ServiceUnavailableError(APIError):
    """Exception raised when the service is unavailable."""
    pass


class APIClient:
    """
    A base class for interacting with an API.  Handles authentication,
    request building, and error handling.
    """

    def __init__(self, api_key: str, base_url: str):
        """
        Initializes the API client.

        Args:
            api_key: The API key for authentication.
            base_url: The base URL of the API.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.session = None  # Placeholder for an actual HTTP session (e.g., aiohttp)

    async def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Makes a request to the API endpoint.  Simulates an API call.

        Args:
            method: The HTTP method (e.g., "GET", "POST").
            endpoint: The API endpoint.
            data: The request data (optional).

        Returns:
            The JSON response from the API.

        Raises:
            APIError: If the API returns an error.
            AuthenticationError: If authentication fails.
            RateLimitError: If rate limits are exceeded.
            ServiceUnavailableError: If the service is unavailable.
            Exception: For any other unexpected errors.
        """
        url = f"{self.base_url}/{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        logging.info(f"Making {method} request to {url} with data: {data}")

        # Simulate API response based on endpoint.  In a real implementation,
        # this would use an HTTP library to make the actual request.
        if endpoint == "auth":
            if self.api_key == "valid_key":
                response_data = {"status": "success", "message": "Authentication successful"}
                status_code = 200
            else:
                response_data = {"status": "error", "message": "Invalid API key"}
                status_code = 401
        elif endpoint == "data":
            response_data = {"data": {"key1": "value1", "key2": "value2"}}
            status_code = 200
        elif endpoint == "rate_limited":
            response_data = {"status": "error", "message": "Rate limit exceeded"}
            status_code = 429
        elif endpoint == "unavailable":
            response_data = {"status": "error", "message": "Service unavailable"}
            status_code = 503
        else:
            response_data = {"status": "error", "message": "Unknown endpoint"}
            status_code = 404

        try:
            # Simulate network latency
            await asyncio.sleep(0.1)

            if status_code == 401:
                raise AuthenticationError("Authentication failed", status_code=status_code)
            elif status_code == 429:
                raise RateLimitError("Rate limit exceeded", status_code=status_code)
            elif status_code == 503:
                raise ServiceUnavailableError("Service unavailable", status_code=status_code)
            elif status_code >= 400:
                raise APIError(f"API error: {response_data['message']}", status_code=status_code)

            logging.info(f"Received response: {response_data}")
            return response_data
        except APIError as e:
            logging.error(f"API Error: {e}")
            raise
        except Exception as e:
            logging.exception("An unexpected error occurred:")
            raise

    async def get_data(self) -> Dict[str, Any]:
        """
        Retrieves data from the API.

        Returns:
            The data from the API.
        """
        return await self._request("GET", "data")

    async def authenticate(self) -> Dict[str, Any]:
        """
        Authenticates with the API.

        Returns:
            The authentication response.
        """
        return await self._request("POST", "auth")

    async def trigger_rate_limit(self) -> Dict[str, Any]:
        """
        Simulates triggering a rate limit error.

        Returns:
            The API response (will likely raise an exception).
        """
        return await self._request("GET", "rate_limited")

    async def trigger_unavailable(self) -> Dict[str, Any]:
        """
        Simulates triggering a service unavailable error.

        Returns:
            The API response (will likely raise an exception).
        """
        return await self._request("GET", "unavailable")


async def main():
    """
    Main function to demonstrate the API client.
    """
    api_key = "valid_key"  # Replace with your actual API key
    base_url = "https://example.com/api"  # Replace with your actual API base URL

    client = APIClient(api_key, base_url)

    try:
        auth_response = await client.authenticate()
        print(f"Authentication response: {auth_response}")

        data = await client.get_data()
        print(f"Data: {data}")

        # Example of triggering a rate limit error
        # await client.trigger_rate_limit() # Commented out to prevent the error from always occurring

        # Example of triggering a service unavailable error
        # await client.trigger_unavailable() # Commented out to prevent the error from always occurring

    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
    except RateLimitError as e:
        print(f"Rate limit exceeded: {e}")
    except ServiceUnavailableError as e:
        print(f"Service unavailable: {e}")
    except APIError as e:
        print(f"API error: {e}")
    except Exception as e:
        logging.exception("An unexpected error occurred:")
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    asyncio.run(main())