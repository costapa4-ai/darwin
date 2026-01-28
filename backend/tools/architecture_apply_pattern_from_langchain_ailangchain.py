"""
This module demonstrates applying a pattern inspired by langchain-ai/langchain
for modular and extensible tool integration within the Darwin System.

Specifically, it implements a Chain-of-Responsibility pattern for handling
different types of data processing tasks, allowing for easy addition of new
processors and flexible task execution.
"""

from typing import List, Any, Dict, Optional, Type
from abc import ABC, abstractmethod


class DataProcessor(ABC):
    """
    Abstract base class for data processors in the chain-of-responsibility.

    Each processor handles a specific type of data or processing task.
    """

    def __init__(self, next_processor: Optional["DataProcessor"] = None):
        """
        Initializes the DataProcessor with an optional next processor.

        Args:
            next_processor: The next processor in the chain.
        """
        self.next_processor = next_processor

    @abstractmethod
    def process(self, data: Any) -> Any:
        """
        Abstract method to process the data.

        Args:
            data: The data to be processed.

        Returns:
            The processed data or the original data if not handled.
        """
        pass

    def handle(self, data: Any) -> Any:
        """
        Handles the data by processing it or passing it to the next processor.

        Args:
            data: The data to be handled.

        Returns:
            The processed data or the result from the next processor.
        """
        try:
            result = self.process(data)
            if result is not data:  # Data was processed
                return result
            elif self.next_processor:
                return self.next_processor.handle(data)
            else:
                return data  # No processor handled the data
        except Exception as e:
            print(f"Error in {self.__class__.__name__}: {e}")
            if self.next_processor:
                return self.next_processor.handle(data)
            else:
                return data  # Return original data on error if no next processor


class StringProcessor(DataProcessor):
    """
    A concrete processor that handles string data.
    """

    def process(self, data: Any) -> Any:
        """
        Processes string data by converting it to uppercase.

        Args:
            data: The data to be processed.

        Returns:
            The uppercase version of the string if the data is a string,
            otherwise the original data.
        """
        if isinstance(data, str):
            return data.upper()
        return data


class NumberProcessor(DataProcessor):
    """
    A concrete processor that handles numerical data.
    """

    def process(self, data: Any) -> Any:
        """
        Processes numerical data by squaring it if it's an integer or float.

        Args:
            data: The data to be processed.

        Returns:
            The squared value if the data is an int or float,
            otherwise the original data.
        """
        if isinstance(data, (int, float)):
            return data * data
        return data


class ListProcessor(DataProcessor):
    """
    A concrete processor that handles list data.
    """

    def process(self, data: Any) -> Any:
        """
        Processes list data by reversing it.

        Args:
            data: The data to be processed.

        Returns:
            The reversed list if the data is a list, otherwise the original data.
        """
        if isinstance(data, list):
            return list(reversed(data))
        return data


def create_processing_chain() -> DataProcessor:
    """
    Creates a chain of data processors.

    Returns:
        The head of the processing chain.
    """
    string_processor = StringProcessor()
    number_processor = NumberProcessor(string_processor)
    list_processor = ListProcessor(number_processor)
    return list_processor


def process_data(data: Any, chain: DataProcessor) -> Any:
    """
    Processes data through the given chain of processors.

    Args:
        data: The data to be processed.
        chain: The head of the processing chain.

    Returns:
        The processed data.
    """
    return chain.handle(data)


if __name__ == "__main__":
    # Example Usage
    chain = create_processing_chain()

    string_data = "hello world"
    processed_string = process_data(string_data, chain)
    print(f"Original string: {string_data}, Processed string: {processed_string}")

    number_data = 5
    processed_number = process_data(number_data, chain)
    print(f"Original number: {number_data}, Processed number: {processed_number}")

    list_data = [1, 2, 3, 4, 5]
    processed_list = process_data(list_data, chain)
    print(f"Original list: {list_data}, Processed list: {processed_list}")

    mixed_data = ["test", 10, [6,7,8]]
    processed_mixed = process_data(mixed_data, chain)
    print(f"Original mixed data: {mixed_data}, Processed mixed data: {processed_mixed}")

    dict_data = {"key": "value"}
    processed_dict = process_data(dict_data, chain)
    print(f"Original dict data: {dict_data}, Processed dict data: {processed_dict}")