import ast
import os
import sys
from typing import List, Tuple, Dict, Any


def calculate_cyclomatic_complexity(source_code: str) -> int:
    """
    Calculates the cyclomatic complexity of a given Python source code string.

    Args:
        source_code: The Python source code as a string.

    Returns:
        The cyclomatic complexity as an integer. Returns 1 for empty or trivial code.
        Returns -1 if there's an error parsing the code.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return -1  # Indicate an error during parsing

    complexity = 1  # Base complexity

    for node in ast.walk(tree):
        if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.ExceptHandler,
                             ast.FunctionDef, ast.AsyncFunctionDef, ast.With, ast.AsyncWith,
                             ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp,
                             ast.BoolOp)):  # Boolean operations also increase complexity
            complexity += 1
        elif isinstance(node, ast.ConditionalExp):
            complexity += 1 #Ternary operator
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr): #Bitwise or operator
            complexity += 1
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitAnd): #Bitwise and operator
            complexity += 1

    return complexity


def analyze_file_complexity(filepath: str) -> Tuple[str, int]:
    """
    Analyzes the cyclomatic complexity of a Python file.

    Args:
        filepath: The path to the Python file.

    Returns:
        A tuple containing the filepath and its cyclomatic complexity.
        Returns (filepath, -1) if the file cannot be read or parsed.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            source_code = file.read()
        complexity = calculate_cyclomatic_complexity(source_code)
        return filepath, complexity
    except FileNotFoundError:
        return filepath, -1
    except Exception:  # Catch any other exceptions during file reading or parsing
        return filepath, -1


def analyze_directory_complexity(directory: str) -> List[Tuple[str, int]]:
    """
    Analyzes the cyclomatic complexity of all Python files in a directory.

    Args:
        directory: The path to the directory.

    Returns:
        A list of tuples, where each tuple contains the filepath and its cyclomatic complexity.
    """
    results: List[Tuple[str, int]] = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                filepath, complexity = analyze_file_complexity(filepath)
                results.append((filepath, complexity))
    return results


def main(path: str) -> None:
    """
    Main function to analyze code complexity for a given file or directory.

    Args:
        path: The path to the file or directory to analyze.
    """
    if os.path.isfile(path):
        filepath, complexity = analyze_file_complexity(path)
        if complexity == -1:
            print(f"Error analyzing file: {filepath}")
        else:
            print(f"File: {filepath}, Cyclomatic Complexity: {complexity}")
    elif os.path.isdir(path):
        results = analyze_directory_complexity(path)
        for filepath, complexity in results:
            if complexity == -1:
                print(f"Error analyzing file: {filepath}")
            else:
                print(f"File: {filepath}, Cyclomatic Complexity: {complexity}")
    else:
        print(f"Error: Invalid path: {path}")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        path = sys.argv[1]
        main(path)
    else:
        print("Please provide a file or directory path as a command-line argument.")