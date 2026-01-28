import requests
from typing import Optional, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def perform_web_search(query: str, num_results: int = 5) -> Optional[list[dict[str, str]]]:
    """
    Performs a web search using the DuckDuckGo Search API.

    Args:
        query: The search query string.
        num_results: The number of search results to return (default: 5).

    Returns:
        A list of dictionaries, where each dictionary represents a search result
        and contains the 'title', 'link', and 'snippet' of the result.
        Returns None if the search fails.
    """

    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "pretty": 1,
            "num_results": num_results  # DuckDuckGo doesn't directly support num_results, handle it after fetching
        }

        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data: dict[str, Any] = response.json()

        results: list[dict[str, str]] = []
        for result in data.get("RelatedTopics", []):
            if isinstance(result, dict):  # Filter out non-dictionary results
                results.append({
                    "title": result.get("Text", "N/A"),
                    "link": result.get("FirstURL", "N/A"),
                    "snippet": result.get("Result", "N/A")
                })
            elif isinstance(result, list):
                 for sub_result in result:
                    if isinstance(sub_result, dict):
                        results.append({
                            "title": sub_result.get("Text", "N/A"),
                            "link": sub_result.get("FirstURL", "N/A"),
                            "snippet": sub_result.get("Result", "N/A")
                        })

        if not results:
            for result in data.get("Results", []):
                results.append({
                    "title": result.get("Text", "N/A"),
                    "link": result.get("FirstURL", "N/A"),
                    "snippet": result.get("Result", "N/A")
                })


        return results[:num_results]  # Ensure we return only the requested number of results

    except requests.exceptions.RequestException as e:
        logging.error(f"Request failed: {e}")
        return None
    except (ValueError, KeyError, TypeError) as e:
        logging.error(f"Error processing JSON response: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")
        return None


if __name__ == '__main__':
    # Example Usage
    search_query = "Python programming"
    num_results_to_fetch = 3
    search_results = perform_web_search(search_query, num_results_to_fetch)

    if search_results:
        print(f"Search results for '{search_query}':")
        for i, result in enumerate(search_results):
            print(f"\nResult {i + 1}:")
            print(f"  Title: {result['title']}")
            print(f"  Link: {result['link']}")
            print(f"  Snippet: {result['snippet']}")
    else:
        print("Search failed.")