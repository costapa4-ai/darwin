"""
Tool Manager: Dynamically loads and manages Darwin-generated tools
"""
import importlib
import inspect
import sys
from pathlib import Path
from typing import Dict, List, Any, Callable


class ToolManager:
    """
    Manages dynamically loaded tools created by Darwin
    """

    def __init__(self, tools_dir: str = "/app/tools"):
        self.tools_dir = Path(tools_dir)
        self.loaded_tools: Dict[str, Any] = {}
        self.tool_functions: Dict[str, Callable] = {}

    def discover_tools(self) -> List[str]:
        """
        Discover all available tools in the tools directory

        Returns:
            List of tool module names (without .py extension)
        """
        if not self.tools_dir.exists():
            print(f"⚠️ Tools directory not found: {self.tools_dir}")
            return []

        tools = []
        for file_path in self.tools_dir.glob("*.py"):
            # Skip __init__.py and tool_manager.py
            if file_path.stem in ['__init__', 'tool_manager']:
                continue

            tools.append(file_path.stem)

        print(f"🔍 Discovered {len(tools)} tools: {', '.join(tools)}")
        return tools

    def load_tool(self, tool_name: str) -> bool:
        """
        Load a specific tool module dynamically

        Args:
            tool_name: Name of the tool module (without .py)

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Ensure tools directory is in Python path
            tools_parent = str(self.tools_dir.parent)
            if tools_parent not in sys.path:
                sys.path.insert(0, tools_parent)

            # Import the module dynamically
            module_name = f"tools.{tool_name}"
            if module_name in sys.modules:
                # Reload if already loaded
                module = importlib.reload(sys.modules[module_name])
            else:
                module = importlib.import_module(module_name)

            self.loaded_tools[tool_name] = module

            # Extract all callable functions from the module
            for name, obj in inspect.getmembers(module):
                if inspect.isfunction(obj) and not name.startswith('_'):
                    function_key = f"{tool_name}.{name}"
                    self.tool_functions[function_key] = obj

            print(f"✅ Loaded tool: {tool_name}")
            return True

        except Exception as e:
            print(f"❌ Failed to load tool '{tool_name}': {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_all_tools(self) -> Dict[str, bool]:
        """
        Load all discovered tools

        Returns:
            Dictionary mapping tool names to load success status
        """
        tools = self.discover_tools()
        results = {}

        for tool_name in tools:
            results[tool_name] = self.load_tool(tool_name)

        successful = sum(1 for success in results.values() if success)
        print(f"📦 Loaded {successful}/{len(tools)} tools successfully")

        return results

    def get_tool(self, tool_name: str) -> Any:
        """
        Get a loaded tool module

        Args:
            tool_name: Name of the tool

        Returns:
            Tool module or None if not loaded
        """
        return self.loaded_tools.get(tool_name)

    def get_function(self, function_key: str) -> Callable:
        """
        Get a specific function from a loaded tool

        Args:
            function_key: Key in format "tool_name.function_name"

        Returns:
            Function object or None if not found
        """
        return self.tool_functions.get(function_key)

    def list_available_functions(self) -> List[str]:
        """
        List all available functions from loaded tools

        Returns:
            List of function keys
        """
        return list(self.tool_functions.keys())

    def call_function(self, function_key: str, *args, **kwargs) -> Any:
        """
        Call a tool function dynamically

        Args:
            function_key: Key in format "tool_name.function_name"
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Result of function call
        """
        func = self.get_function(function_key)
        if not func:
            raise ValueError(f"Function not found: {function_key}")

        return func(*args, **kwargs)

    def reload_tools(self) -> Dict[str, bool]:
        """
        Reload all tools (useful after code updates)

        Returns:
            Dictionary mapping tool names to reload success status
        """
        print("🔄 Reloading all tools...")
        self.loaded_tools.clear()
        self.tool_functions.clear()
        return self.load_all_tools()

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Get information about a loaded tool

        Args:
            tool_name: Name of the tool

        Returns:
            Dictionary with tool information
        """
        tool = self.get_tool(tool_name)
        if not tool:
            return {'error': f'Tool not loaded: {tool_name}'}

        functions = [
            key.split('.')[1]
            for key in self.tool_functions.keys()
            if key.startswith(f"{tool_name}.")
        ]

        return {
            'name': tool_name,
            'module': tool.__name__,
            'doc': tool.__doc__,
            'functions': functions,
            'file': getattr(tool, '__file__', 'unknown')
        }

    def list_all_tools_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all loaded tools

        Returns:
            List of tool information dictionaries
        """
        return [
            self.get_tool_info(tool_name)
            for tool_name in self.loaded_tools.keys()
        ]
