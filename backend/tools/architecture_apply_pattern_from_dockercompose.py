"""
This module demonstrates applying architectural patterns inspired by Docker Compose
to improve code organization, modularity, and maintainability.  Specifically, it
focuses on a simplified version of the Compose's approach to configuration
management and service orchestration.

This example provides a basic framework and can be extended with more features.
"""

import os
import yaml
from typing import Dict, Any, Optional, List
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ConfigError(Exception):
    """Custom exception for configuration-related errors."""
    pass


class Service:
    """
    Represents a service, similar to a service definition in Docker Compose.
    """

    def __init__(self, name: str, config: Dict[str, Any]) -> None:
        """
        Initializes a Service instance.

        Args:
            name: The name of the service.
            config: A dictionary containing the service configuration.
        """
        self.name = name
        self.config = config
        self.dependencies: List[str] = []  # List of service names this service depends on

    def __repr__(self) -> str:
        return f"Service(name='{self.name}', config={self.config})"

    def start(self) -> None:
        """
        Simulates starting the service.  In a real application, this would
        perform the actual service startup.
        """
        try:
            logging.info(f"Starting service: {self.name}")
            # Simulate service startup logic based on configuration
            if 'command' in self.config:
                command = self.config['command']
                logging.info(f"Executing command: {command}")
                # In a real implementation, use subprocess.run or similar
            else:
                logging.info(f"Service {self.name} started (no command defined)")

        except Exception as e:
            logging.error(f"Error starting service {self.name}: {e}")

    def stop(self) -> None:
        """
        Simulates stopping the service.
        """
        logging.info(f"Stopping service: {self.name}")


class Project:
    """
    Represents a project, analogous to a Docker Compose project. It manages
    a collection of services.
    """

    def __init__(self, name: str, config_path: str) -> None:
        """
        Initializes a Project instance.

        Args:
            name: The name of the project.
            config_path: The path to the project configuration file (e.g., a YAML file).
        """
        self.name = name
        self.config_path = config_path
        self.services: Dict[str, Service] = {}
        self.load_config()

    def load_config(self) -> None:
        """
        Loads the project configuration from the specified YAML file.
        """
        try:
            with open(self.config_path, 'r') as f:
                config_data: Dict[str, Any] = yaml.safe_load(f)

            if 'services' not in config_data:
                raise ConfigError("Missing 'services' section in the configuration file.")

            for service_name, service_config in config_data['services'].items():
                self.services[service_name] = Service(service_name, service_config)

            # Resolve dependencies after loading all services
            if 'services' in config_data:
                for service_name, service_config in config_data['services'].items():
                    if 'depends_on' in service_config:
                        dependencies = service_config['depends_on']
                        if not isinstance(dependencies, list):
                            raise ConfigError(f"depends_on for service {service_name} must be a list")
                        for dep_name in dependencies:
                            if dep_name not in self.services:
                                raise ConfigError(f"Service {service_name} depends on unknown service {dep_name}")
                            self.services[service_name].dependencies.append(dep_name)


        except FileNotFoundError:
            logging.error(f"Configuration file not found: {self.config_path}")
            raise ConfigError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            logging.error(f"Error parsing YAML file: {e}")
            raise ConfigError(f"Error parsing YAML file: {e}")
        except ConfigError as e:
            logging.error(f"Configuration error: {e}")
            raise
        except Exception as e:
            logging.error(f"An unexpected error occurred: {e}")
            raise

    def start_service(self, service_name: str) -> None:
        """
        Starts a specific service, ensuring its dependencies are started first.

        Args:
            service_name: The name of the service to start.
        """
        try:
            if service_name not in self.services:
                raise ValueError(f"Service '{service_name}' not found.")

            service = self.services[service_name]

            # Start dependencies first
            for dependency_name in service.dependencies:
                self.start_service(dependency_name)

            service.start()

        except ValueError as e:
            logging.error(e)
        except Exception as e:
            logging.error(f"Error starting service {service_name}: {e}")

    def stop_service(self, service_name: str) -> None:
        """
        Stops a specific service.

        Args:
            service_name: The name of the service to stop.
        """
        try:
            if service_name not in self.services:
                raise ValueError(f"Service '{service_name}' not found.")

            self.services[service_name].stop()

        except ValueError as e:
            logging.error(e)
        except Exception as e:
            logging.error(f"Error stopping service {service_name}: {e}")

    def start_all_services(self) -> None:
        """
        Starts all services defined in the project.
        """
        logging.info("Starting all services...")
        for service_name in self.services:
            self.start_service(service_name)

    def stop_all_services(self) -> None:
        """
        Stops all services defined in the project.
        """
        logging.info("Stopping all services...")
        for service_name in self.services:
            self.stop_service(service_name)


def main() -> None:
    """
    Main function to demonstrate the usage of the Project and Service classes.
    """
    try:
        # Create a sample configuration file (in-memory for this example)
        config_data: Dict[str, Any] = {
            'services': {
                'db': {
                    'command': 'start_database.sh',
                },
                'web': {
                    'command': 'run_web_server.sh',
                    'depends_on': ['db']
                },
                'cache': {}
            }
        }

        # Write the config_data to a temporary file
        config_file_path = "temp_config.yaml"  # Define a temporary file name
        with open(config_file_path, 'w') as f:
            yaml.dump(config_data, f)

        # Create a Project instance
        project = Project("MyProject", config_file_path)

        # Start all services
        project.start_all_services()

        # Stop all services
        project.stop_all_services()

        # Clean up the temporary file
        os.remove(config_file_path)

    except ConfigError as e:
        logging.error(f"Configuration error: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()