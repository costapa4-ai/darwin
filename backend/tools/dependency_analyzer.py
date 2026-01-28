import os
import sys
import importlib
import traceback
from typing import List, Dict, Tuple, Optional
import ast


class DependencyAnalyzer:
    """
    A tool for analyzing Python file dependencies.

    This class provides functionality to extract import statements from Python
    files and identify dependencies between them. It supports both standard
    library imports and local module imports.
    """

    def __init__(self, project_root: str = ".") -> None:
        """
        Initializes the DependencyAnalyzer.

        Args:
            project_root: The root directory of the project to analyze.
        """
        self.project_root = project_root
        self.dependencies: Dict[str, List[str]] = {}  # {module: [dependencies]}

    def analyze_file(self, file_path: str) -> List[str]:
        """
        Analyzes a single Python file and extracts its dependencies.

        Args:
            file_path: The path to the Python file to analyze.

        Returns:
            A list of module names that the file depends on.
        """
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            return []
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return []

        dependencies: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    dependencies.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                dependencies.append(node.module)

        return dependencies

    def analyze_directory(self, directory: str) -> None:
        """
        Analyzes all Python files in a directory and its subdirectories.

        Args:
            directory: The directory to analyze.
        """
        for root, _, files in os.walk(directory):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    module_name = self.file_path_to_module_name(file_path)
                    self.dependencies[module_name] = self.analyze_file(file_path)

    def file_path_to_module_name(self, file_path: str) -> str:
        """
        Converts a file path to a module name.

        Args:
            file_path: The path to the Python file.

        Returns:
            The module name corresponding to the file path.
        """
        relative_path = os.path.relpath(file_path, self.project_root)
        module_name = relative_path.replace(".py", "").replace(os.sep, ".")
        return module_name

    def get_dependencies(self) -> Dict[str, List[str]]:
        """
        Returns the analyzed dependencies.

        Returns:
            A dictionary where keys are module names and values are lists of
            their dependencies.
        """
        return self.dependencies

    def print_dependencies(self) -> None:
        """
        Prints the analyzed dependencies to the console.
        """
        for module, deps in self.dependencies.items():
            print(f"Module: {module}")
            for dep in deps:
                print(f"  -> {dep}")

    def visualize_dependencies(self, output_file: str = "dependencies.dot") -> None:
        """
        Generates a Graphviz DOT file visualizing the dependencies.

        Args:
            output_file: The name of the output DOT file.
        """
        try:
            with open(output_file, "w") as f:
                f.write("digraph Dependencies {\n")
                for module, deps in self.dependencies.items():
                    for dep in deps:
                        f.write(f'    "{module}" -> "{dep}";\n')
                f.write("}\n")
            print(f"Dependency graph written to {output_file}")
        except Exception as e:
            print(f"Error generating dependency graph: {e}")

    def find_circular_dependencies(self) -> List[List[str]]:
        """
        Finds circular dependencies in the project.

        Returns:
            A list of circular dependency cycles, where each cycle is a list
            of module names.
        """
        visited: Dict[str, bool] = {}
        recursion_stack: Dict[str, bool] = {}
        cycles: List[List[str]] = []

        def dfs(module: str, path: List[str]) -> bool:
            visited[module] = True
            recursion_stack[module] = True
            path.append(module)

            for neighbor in self.dependencies.get(module, []):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif recursion_stack.get(neighbor, False):
                    cycle_start_index = path.index(neighbor)
                    cycle = path[cycle_start_index:]
                    cycles.append(cycle)
                    return True

            recursion_stack[module] = False
            path.pop()
            return False

        for module in self.dependencies:
            if module not in visited:
                dfs(module, [])

        return cycles


def main(project_root: str = ".") -> None:
    """
    Main function to run the dependency analyzer.

    Args:
        project_root: The root directory of the project to analyze.
    """
    analyzer = DependencyAnalyzer(project_root)
    analyzer.analyze_directory(project_root)
    analyzer.print_dependencies()

    circular_dependencies = analyzer.find_circular_dependencies()
    if circular_dependencies:
        print("\nCircular Dependencies Found:")
        for cycle in circular_dependencies:
            print(" -> ".join(cycle))
    else:
        print("\nNo Circular Dependencies Found.")

    analyzer.visualize_dependencies()


if __name__ == "__main__":
    project_root = "."  # Default to current directory
    if len(sys.argv) > 1:
        project_root = sys.argv[1]  # Use directory from command line argument

    main(project_root)