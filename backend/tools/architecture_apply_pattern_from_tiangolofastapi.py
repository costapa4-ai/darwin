from typing import Any, Dict, Callable, TypeVar, Type, Optional
from functools import wraps
import inspect

T = TypeVar('T')


def singleton(cls: Type[T], top_k: int = None, **kwargs) -> Type[T]:
    """
    A decorator to create a singleton class.

    Args:
        cls: The class to be decorated.
        top_k: Optional limit for results (ignored, for compatibility)
        **kwargs: Additional optional arguments (ignored for compatibility)

    Returns:
        The singleton class.
    """
    instances: Dict[Type[T], T] = {}

    @wraps(cls)
    def getinstance(*args: Any, **kwargs: Any) -> T:
        """
        Get the instance of the class.

        Args:
            *args: Arguments for the class constructor.
            **kwargs: Keyword arguments for the class constructor.

        Returns:
            The instance of the class.
        """
        if cls not in instances:
            try:
                instances[cls] = cls(*args, **kwargs)
            except Exception as e:
                print(f"Error creating singleton instance: {e}")
                raise
        return instances[cls]

    return getinstance


def dependency_injection(func: Callable[..., Any], top_k: int = None, **kwargs) -> Callable[..., Any]:
    """
    A decorator to automatically inject dependencies into a function.

    This decorator inspects the function's signature and attempts to
    resolve dependencies from a global registry (dependencies_registry).

    Args:
        func: The function to decorate.
        top_k: Optional limit for results (ignored, for compatibility)
        **kwargs: Additional optional arguments (ignored for compatibility)

    Returns:
        The decorated function.
    """
    signature = inspect.signature(func)
    parameters = signature.parameters

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        """
        The wrapper function that injects dependencies.

        Args:
            *args: Arguments passed to the original function.
            **kwargs: Keyword arguments passed to the original function.

        Returns:
            The result of the original function.
        """
        injected_kwargs: Dict[str, Any] = {}
        for name, param in parameters.items():
            if name in kwargs:
                # Use explicitly passed arguments
                continue

            if param.annotation != inspect.Parameter.empty:
                dep = dependencies_registry.get(param.annotation)
                if dep:
                    injected_kwargs[name] = dep

        # Merge injected dependencies with existing keyword arguments
        final_kwargs = {**injected_kwargs, **kwargs}

        try:
            return func(*args, **final_kwargs)
        except Exception as e:
            print(f"Error during dependency injection or function execution: {e}")
            raise

    return wrapper


class DependenciesRegistry:
    """
    A registry for dependencies.
    """

    def __init__(self) -> None:
        """
        Initialize the dependencies registry.
        """
        self.dependencies: Dict[Type[Any], Any] = {}

    def register(self, dependency_type: Type[T], dependency_instance: T) -> None:
        """
        Register a dependency.

        Args:
            dependency_type: The type of the dependency.
            dependency_instance: The instance of the dependency.
        """
        self.dependencies[dependency_type] = dependency_instance

    def get(self, dependency_type: Type[T]) -> Optional[T]:
        """
        Get a dependency.

        Args:
            dependency_type: The type of the dependency.

        Returns:
            The dependency instance, or None if not found.
        """
        return self.dependencies.get(dependency_type)


# Global dependencies registry
dependencies_registry = DependenciesRegistry()


if __name__ == '__main__':
    # Example Usage:
    class Database:
        """
        A simple database class.
        """

        def __init__(self, connection_string: str):
            """
            Initialize the database.

            Args:
                connection_string: The connection string.
            """
            self.connection_string = connection_string

        def connect(self) -> None:
            """
            Connect to the database.
            """
            print(f"Connecting to database: {self.connection_string}")

    # Create a database instance
    db = Database("localhost:5432")

    # Register the database instance in the dependencies registry
    dependencies_registry.register(Database, db)

    @dependency_injection
    def get_users(db: Database) -> None:
        """
        A function to get users from the database.

        Args:
            db: The database instance (injected).
        """
        db.connect()
        print("Getting users from the database...")

    # Call the function
    get_users()

    @singleton
    class Config:
        """
        A singleton configuration class.
        """
        def __init__(self, api_key: str):
            """
            Initializes the Config instance.
            """
            self.api_key = api_key

        def get_api_key(self) -> str:
            """
            Returns the API Key
            """
            return self.api_key

    config1 = Config(api_key="test_key")
    config2 = Config(api_key="another_key") # This will return the same instance

    print(config1.get_api_key()) # Output: test_key
    print(config2.get_api_key()) # Output: test_key (same instance, same key)

    print(config1 is config2) # Output: True