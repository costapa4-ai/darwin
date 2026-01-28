"""
Documentation Generator Module

This module provides a class, DocumentationGenerator, that automatically
generates documentation for Python code.  It leverages the `inspect`
module to analyze code structure and extracts docstrings, function
signatures, and other relevant information to create comprehensive
documentation in Markdown format.
"""

import inspect
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

class DocumentationGenerator:
    """
    A class for automatically generating documentation for Python code.
    """

    def __init__(self, module: Any, output_dir: str = "docs") -> None:
        """
        Initializes the DocumentationGenerator with a module to document and
        an output directory for the generated documentation.

        Args:
            module: The Python module to document.
            output_dir: The directory where the documentation will be saved.
        """
        self.module = module
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_documentation(self) -> None:
        """
        Generates documentation for the module and saves it to a Markdown file.
        """
        module_name = self.module.__name__
        output_file = os.path.join(self.output_dir, f"{module_name}.md")

        try:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(f"# Module: {module_name}\n\n")
                f.write(f"{inspect.getdoc(self.module) or 'No module docstring.'}\n\n")

                self._document_classes(f)
                self._document_functions(f)

            print(f"Documentation generated successfully for {module_name} at {output_file}")

        except Exception as e:
            print(f"Error generating documentation for {module_name}: {e}")

    def _document_classes(self, f: Any) -> None:
        """
        Documents classes within the module.

        Args:
            f: The file object to write the documentation to.
        """
        f.write("## Classes\n\n")
        for name, obj in inspect.getmembers(self.module):
            if inspect.isclass(obj) and obj.__module__ == self.module.__name__:
                f.write(f"### Class: {name}\n\n")
                f.write(f"{inspect.getdoc(obj) or 'No class docstring.'}\n\n")
                self._document_methods(obj, f)

    def _document_methods(self, cls: type, f: Any) -> None:
        """
        Documents methods within a class.

        Args:
            cls: The class object.
            f: The file object to write the documentation to.
        """
        f.write("#### Methods:\n\n")
        for name, method in inspect.getmembers(cls):
            if inspect.isfunction(method) and hasattr(method, '__qualname__') and method.__qualname__.startswith(cls.__name__ + '.'):
                try:
                    signature = inspect.signature(method)
                    f.write(f"##### `{name}{signature}`\n\n")
                    f.write(f"{inspect.getdoc(method) or 'No method docstring.'}\n\n")
                except Exception as e:
                    f.write(f"##### `{name}`\n\n")
                    f.write(f"Could not generate signature: {e}\n\n")
                    f.write(f"{inspect.getdoc(method) or 'No method docstring.'}\n\n")

    def _document_functions(self, f: Any) -> None:
        """
        Documents functions within the module.

        Args:
            f: The file object to write the documentation to.
        """
        f.write("## Functions\n\n")
        for name, obj in inspect.getmembers(self.module):
            if inspect.isfunction(obj) and obj.__module__ == self.module.__name__:
                try:
                    signature = inspect.signature(obj)
                    f.write(f"### `{name}{signature}`\n\n")
                    f.write(f"{inspect.getdoc(obj) or 'No function docstring.'}\n\n")
                except Exception as e:
                    f.write(f"### `{name}`\n\n")
                    f.write(f"Could not generate signature: {e}\n\n")
                    f.write(f"{inspect.getdoc(obj) or 'No function docstring.'}\n\n")


if __name__ == '__main__':
    """
    Example usage of the DocumentationGenerator.
    """
    # Create a dummy module for demonstration
    class ExampleClass:
        """
        An example class.
        """
        def __init__(self, value: int) -> None:
            """
            Initializes the ExampleClass.

            Args:
                value: An integer value.
            """
            self.value = value

        def get_value(self) -> int:
            """
            Returns the value.

            Returns:
                The value.
            """
            return self.value

    def example_function(arg1: str, arg2: int) -> str:
        """
        An example function.

        Args:
            arg1: A string argument.
            arg2: An integer argument.

        Returns:
            A string.
        """
        return f"arg1: {arg1}, arg2: {arg2}"

    # Create a dummy module
    import types
    example_module = types.ModuleType('example_module')
    example_module.ExampleClass = ExampleClass
    example_module.example_function = example_function
    example_module.__doc__ = "This is an example module."

    # Generate documentation for the dummy module
    doc_generator = DocumentationGenerator(example_module, output_dir="example_docs")
    doc_generator.generate_documentation()