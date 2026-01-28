import os
import typing as t
from werkzeug.utils import cached_property


class DarwinConfig(dict):
    """
    A configuration object that allows setting configuration values
    as attributes. It's inspired by Flask's configuration object.
    """

    def __init__(
        self,
        defaults: t.Optional[t.Mapping[str, t.Any]] = None,
    ) -> None:
        """
        Initializes the configuration object.

        Args:
            defaults: A dictionary of default configuration values.
        """
        super().__init__(defaults or {})

    def from_object(self, obj: object) -> None:
        """
        Updates the values from the given object.  An object can be of one
        of the following two types:

        -   a string: in this case the object with that name will be imported
        -   an actual object reference: that object is used directly

        Objects are usually either modules or classes.

        Just the uppercase attributes of the object are added to the
        configuration.

        Args:
            obj: The object to load configuration values from.
        """
        if isinstance(obj, str):
            obj = __import__(obj, None, None, ["*"])

        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def from_pyfile(self, filename: str, silent: bool = False) -> bool:
        """
        Updates the values from a Python file.

        Args:
            filename: The name of the Python file.
            silent: If set to ``True`` the loading errors are ignored.

        Returns:
            ``True`` if the file was loaded successfully, ``False`` otherwise.
        """
        d = {}
        try:
            with open(filename, "rb") as config_file:
                exec(compile(config_file.read(), filename, "exec"), d)
        except OSError as e:
            if silent:
                return False
            e.strerror = f"Unable to load configuration file ({e.strerror})"
            raise
        except Exception as e:
            raise RuntimeError(
                f"Unable to load configuration file: {e.__class__.__name__}: {e}"
            ) from e

        self.from_mapping(d)
        return True

    def from_mapping(self, *mapping: t.Mapping[str, t.Any]) -> None:
        """
        Updates the configuration like :meth:`update` ignoring items with
        non-upper keys.

        :param mapping: a mapping with configuration keys.
        """
        for map in mapping:
            for key, value in map.items():
                if key.isupper():
                    self[key] = value

    def get_namespace(
        self, namespace: str, lowercase: bool = True, trim_namespace: bool = True
    ) -> dict[str, t.Any]:
        """
        Returns a dictionary of configuration values for a given namespace.

        Args:
            namespace: The namespace to filter configuration values by.
            lowercase: If set to ``True`` the keys are converted to lowercase.
            trim_namespace: If set to ``True`` the namespace is removed from the keys.

        Returns:
            A dictionary of configuration values for the given namespace.
        """
        rv: dict[str, t.Any] = {}
        for key, value in self.items():
            if not key.startswith(namespace):
                continue
            if trim_namespace:
                key = key[len(namespace) :]
            if lowercase:
                key = key.lower()
            rv[key] = value
        return rv

    def __setitem__(self, key: str, value: t.Any) -> None:
        """
        Sets a configuration value.

        Args:
            key: The key of the configuration value.
            value: The value of the configuration value.
        """
        super().__setitem__(key, value)

    def __getattr__(self, name: str) -> t.Any:
        """
        Gets a configuration value as an attribute.

        Args:
            name: The name of the configuration value.

        Returns:
            The value of the configuration value.
        """
        try:
            return self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

    def __setattr__(self, name: str, value: t.Any) -> None:
        """
        Sets a configuration value as an attribute.

        Args:
            name: The name of the configuration value.
            value: The value of the configuration value.
        """
        self[name] = value

    def __delattr__(self, name: str) -> None:
        """
        Deletes a configuration value as an attribute.

        Args:
            name: The name of the configuration value.
        """
        try:
            del self[name]
        except KeyError:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")


class Darwin:
    """
    The base class for a Darwin application.  It provides core
    functionality such as configuration loading.
    """

    def __init__(self, import_name: str, instance_path: t.Optional[str] = None) -> None:
        """
        Initializes the Darwin application.

        Args:
            import_name: The name of the package or module that this
                object is being created in.
            instance_path: The path to the instance folder for the
                application.  If not provided, it will be determined
                based on the import name.
        """
        self.import_name = import_name

        if instance_path is None:
            instance_path = self.auto_find_instance_path()
        self.instance_path = instance_path

        self.config = self.make_config(None)  # type: DarwinConfig
        self.root_path = os.path.dirname(os.path.abspath(self.import_name))

    def auto_find_instance_path(self) -> str:
        """
        Finds the instance path automatically based on the import name.

        Returns:
            The path to the instance folder.
        """
        prefix = os.environ.get("DARWIN_APP")
        if prefix is None:
            prefix = os.path.abspath(self.import_name)

        return os.path.join(prefix + "-instance")

    def make_config(self, instance_relative_config: t.Optional[bool] = False) -> DarwinConfig:
        """
        Creates the configuration object.  The default implementation
        returns an instance of :class:`DarwinConfig`.

        Args:
            instance_relative_config: Indicates if the configuration is
                relative to the instance path.

        Returns:
            The configuration object.
        """
        root_path = self.instance_path if instance_relative_config else self.root_path
        return DarwinConfig(root_path=root_path)

    def run(self, debug: bool = False, **kwargs: t.Any) -> None:
        """
        A placeholder for running the application.  Subclasses should
        override this method to provide the actual application execution.

        Args:
            debug: Enable or disable debug mode.
            kwargs: Additional keyword arguments to pass to the application.
        """
        print("Darwin application running (placeholder).")
        print(f"Debug mode: {debug}")
        print(f"Additional arguments: {kwargs}")


if __name__ == "__main__":
    # Example usage:
    class Config:
        DEBUG = True
        SECRET_KEY = "super-secret"  # In real app, load from env or secure source

    app = Darwin(__name__)
    app.config.from_object(Config)
    print(f"Debug: {app.config['DEBUG']}")
    print(f"Secret Key: {app.config.SECRET_KEY}")  # Access as attribute
    app.run()