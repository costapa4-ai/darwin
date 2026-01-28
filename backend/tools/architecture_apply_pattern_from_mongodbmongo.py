import logging
import os
from typing import Any, Dict, List, Optional, Tuple, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConfigurationError(Exception):
    """Custom exception for configuration-related errors."""
    pass

class DarwinSystem:
    """
    A class representing the Darwin System, designed with modularity and 
    extensibility in mind, drawing inspiration from MongoDB's architecture.
    """

    def __init__(self, config_file: Optional[str] = None) -> None:
        """
        Initializes the Darwin System.

        Args:
            config_file: Path to the configuration file (optional).
        """
        self.config: Dict[str, Any] = {}
        self.modules: Dict[str, Any] = {}
        try:
            self.load_config(config_file)
        except ConfigurationError as e:
            logging.error(f"Failed to load configuration: {e}")
            # Handle the error gracefully, e.g., use default configurations
            self.config = self.get_default_config()  # Example of using default config
        self.initialize_modules()

    def get_default_config(self) -> Dict[str, Any]:
         """
         Returns a default configuration dictionary.

         Returns:
             A dictionary containing default configuration values.
         """
         return {
             "module1": {"enabled": True, "param1": "default_value"},
             "module2": {"enabled": False}
         }


    def load_config(self, config_file: Optional[str]) -> None:
        """
        Loads configuration from a file.  Supports JSON or YAML.

        Args:
            config_file: Path to the configuration file.

        Raises:
            ConfigurationError: If the file cannot be loaded or parsed.
        """
        if config_file is None:
            logging.info("No configuration file provided, using default configuration.")
            self.config = self.get_default_config()
            return

        try:
            import json
            with open(config_file, 'r') as f:
                if config_file.endswith('.json'):
                    self.config = json.load(f)
                elif config_file.endswith(('.yaml', '.yml')):
                    import yaml
                    self.config = yaml.safe_load(f)
                else:
                    raise ConfigurationError("Unsupported configuration file format. Use JSON or YAML.")
        except FileNotFoundError:
            raise ConfigurationError(f"Configuration file not found: {config_file}")
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Error decoding JSON: {e}")
        except ImportError:
             raise ConfigurationError("PyYAML is required to load YAML configuration files.  Install with 'pip install pyyaml'.")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration: {e}")

    def initialize_modules(self) -> None:
        """
        Initializes modules based on the configuration.  Uses a dynamic
        import mechanism to load modules based on configuration settings.
        This mimics MongoDB's component initialization.
        """
        for module_name, module_config in self.config.items():
            if not isinstance(module_config, dict) or not module_config.get('enabled', False):
                logging.info(f"Module {module_name} is disabled or misconfigured, skipping.")
                continue

            try:
                # Simulate importing a module.  In a real system, this would be
                # a dynamic import using importlib.import_module.  We use a mock
                # for this example.
                module = self._load_module(module_name, module_config)
                self.modules[module_name] = module
                logging.info(f"Module {module_name} initialized.")
            except ImportError as e:
                logging.error(f"Failed to import module {module_name}: {e}")
            except Exception as e:
                logging.error(f"Failed to initialize module {module_name}: {e}")

    def _load_module(self, module_name: str, module_config: Dict[str, Any]) -> Any:
        """
        Mocks loading a module.  In a real system, this would use importlib.

        Args:
            module_name: The name of the module.
            module_config: The configuration for the module.

        Returns:
            A mock module object.
        """
        # In a real implementation, you would use importlib.import_module
        # to dynamically load the module.  For example:
        #
        # import importlib
        # module = importlib.import_module(f"my_modules.{module_name}")
        # return module.MyModuleClass(module_config)

        # For this example, we just return a dictionary representing the module.
        return {"name": module_name, "config": module_config}

    def run(self) -> None:
        """
        Runs the Darwin System.  This would typically involve orchestrating
        the execution of the initialized modules.
        """
        logging.info("Darwin System running...")
        for module_name, module in self.modules.items():
            try:
                # Simulate running the module.  In a real system, this would
                # call a method on the module object.
                self._run_module(module)
                logging.info(f"Module {module_name} executed successfully.")
            except Exception as e:
                logging.error(f"Failed to run module {module_name}: {e}")
        logging.info("Darwin System finished.")

    def _run_module(self, module: Any) -> None:
        """
        Mocks running a module.

        Args:
            module: The module to run.
        """
        # In a real implementation, you would call a method on the module object.
        logging.info(f"Running module: {module['name']}")
        # Simulate some work being done
        if module['name'] == 'module1':
            logging.info(f"Module1 is running with config: {module['config']}")
        elif module['name'] == 'module2':
            logging.info(f"Module2 is running with config: {module['config']}")
        else:
             logging.info(f"Running unknown module: {module['name']}")


def main():
    """
    Main function to demonstrate the Darwin System.
    """
    try:
        system = DarwinSystem("config.json") # Example using a config file
        system.run()

        system2 = DarwinSystem() # Example with no config file (using defaults)
        system2.run()

    except Exception as e:
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    # Create a dummy config.json file for testing
    with open("config.json", "w") as f:
        import json
        json.dump({
            "module1": {"enabled": True, "param1": "value1"},
            "module2": {"enabled": True}
        }, f)

    main()

    # Clean up the dummy config.json file
    os.remove("config.json")