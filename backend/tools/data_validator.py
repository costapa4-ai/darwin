import json
from typing import Any, Dict, List, Optional, Tuple, Union
import jsonschema
from jsonschema import validate, ValidationError


class DataValidator:
    """
    A class for validating data against a JSON schema.

    This class provides methods for loading schemas from files or dictionaries,
    validating data against a schema, and retrieving validation errors.

    Attributes:
        schema (dict): The JSON schema to validate against.
    """

    def __init__(self, schema: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes a DataValidator object.

        Args:
            schema (Optional[dict]): The JSON schema to validate against.
                                      If None, the schema must be loaded later.
                                      Defaults to None.
        """
        self.schema: Optional[Dict[str, Any]] = schema

    def load_schema_from_file(self, file_path: str) -> None:
        """
        Loads a JSON schema from a file.

        Args:
            file_path (str): The path to the JSON schema file.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not a valid JSON file.
        """
        try:
            with open(file_path, "r") as f:
                self.schema = json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Schema file not found: {file_path}")
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in file: {file_path}", e.doc, e.pos)

    def load_schema_from_dict(self, schema_dict: Dict[str, Any]) -> None:
        """
        Loads a JSON schema from a dictionary.

        Args:
            schema_dict (dict): The JSON schema as a dictionary.
        """
        self.schema = schema_dict

    def validate_data(self, data: Any) -> Tuple[bool, Optional[List[str]]]:
        """
        Validates data against the loaded JSON schema.

        Args:
            data (Any): The data to validate.

        Returns:
            Tuple[bool, Optional[List[str]]]: A tuple containing:
                - A boolean indicating whether the data is valid.
                - A list of error messages if the data is invalid, or None if valid.

        Raises:
            ValueError: If no schema has been loaded.
        """
        if self.schema is None:
            raise ValueError("No schema loaded. Please load a schema before validating data.")

        try:
            validate(instance=data, schema=self.schema)
            return True, None  # Data is valid, no errors
        except ValidationError as e:
            # Collect error messages from the validation error
            errors = [e.message]
            return False, errors  # Data is invalid, return the errors
        except jsonschema.exceptions.SchemaError as e:
            errors = [str(e)]
            return False, errors
        except Exception as e:
            errors = [str(e)]
            return False, errors

    def get_validation_errors(self, data: Any) -> Optional[List[str]]:
        """
        Validates data and returns a list of validation errors.

        Args:
            data (Any): The data to validate.

        Returns:
            Optional[List[str]]: A list of error messages if the data is invalid,
                                or None if the data is valid.

        Raises:
            ValueError: If no schema has been loaded.
        """
        is_valid, errors = self.validate_data(data)
        if is_valid:
            return None
        else:
            return errors

    def is_valid(self, data: Any) -> bool:
        """
        Checks if the data is valid against the loaded schema.

        Args:
            data (Any): The data to validate.

        Returns:
            bool: True if the data is valid, False otherwise.

        Raises:
            ValueError: If no schema has been loaded.
        """
        is_valid, _ = self.validate_data(data)
        return is_valid


if __name__ == '__main__':
    # Example Usage
    schema_data = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0},
            "email": {"type": "string", "format": "email"}
        },
        "required": ["name", "age", "email"]
    }

    data_validator = DataValidator()
    data_validator.load_schema_from_dict(schema_data)

    valid_data = {"name": "John Doe", "age": 30, "email": "john.doe@example.com"}
    invalid_data = {"name": "John Doe", "age": -5, "email": "invalid-email"}

    is_valid, errors = data_validator.validate_data(valid_data)
    if is_valid:
        print("Valid data is valid.")
    else:
        print("Valid data is invalid.")
        print(f"Errors: {errors}")

    is_valid, errors = data_validator.validate_data(invalid_data)
    if is_valid:
        print("Invalid data is valid.")
    else:
        print("Invalid data is invalid.")
        print(f"Errors: {errors}")

    # Example using schema file
    try:
        data_validator.load_schema_from_file("schema.json") # Create schema.json to test this part
    except FileNotFoundError as e:
        print(e)

    # Example checking if data is valid directly
    is_valid = data_validator.is_valid(valid_data)
    print(f"Data is valid: {is_valid}")