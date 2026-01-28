"""
This module demonstrates a simplified version of the Kubernetes controller pattern.
It includes a basic resource definition, a controller that reconciles the resource,
and a simple in-memory store. This is a conceptual example and does not represent
the full complexity of Kubernetes.

Key patterns inspired by Kubernetes:

1.  **Declarative Configuration:** Resources are defined declaratively, specifying
    the desired state.
2.  **Controllers:** Controllers continuously reconcile the actual state with the
    desired state.
3.  **Event-Driven Architecture:** Controllers react to events (e.g., resource changes)
    to trigger reconciliation loops.
"""

import time
import threading
from typing import Dict, Any, Callable, List, Optional
from uuid import uuid4


class Resource:
    """
    Represents a generic resource with a desired state.
    """

    def __init__(self, name: str, spec: Dict[str, Any], uid: Optional[str] = None) -> None:
        """
        Initializes a Resource object.

        Args:
            name: The name of the resource.
            spec: A dictionary representing the desired state of the resource.
            uid: Unique identifier for the resource. If None, a new UUID is generated.
        """
        self.name = name
        self.spec = spec
        self.uid = uid if uid else str(uuid4())

    def __repr__(self) -> str:
        return f"Resource(name='{self.name}', spec={self.spec}, uid='{self.uid}')"


class ResourceStore:
    """
    A simple in-memory store for resources.
    """

    def __init__(self) -> None:
        """
        Initializes an empty ResourceStore.
        """
        self.resources: Dict[str, Resource] = {}
        self._lock = threading.Lock()  # Protects resource access in multithreaded context

    def add(self, resource: Resource) -> None:
        """
        Adds a resource to the store.

        Args:
            resource: The resource to add.
        """
        with self._lock:
            self.resources[resource.uid] = resource

    def get(self, uid: str) -> Optional[Resource]:
        """
        Retrieves a resource from the store by UID.

        Args:
            uid: The UID of the resource to retrieve.

        Returns:
            The resource if found, otherwise None.
        """
        with self._lock:
            return self.resources.get(uid)

    def update(self, uid: str, new_spec: Dict[str, Any]) -> None:
        """
        Updates the spec of a resource in the store.

        Args:
            uid: The UID of the resource to update.
            new_spec: The new spec for the resource.
        """
        with self._lock:
            resource = self.resources.get(uid)
            if resource:
                resource.spec = new_spec
            else:
                raise ValueError(f"Resource with UID {uid} not found")

    def delete(self, uid: str) -> None:
        """
        Deletes a resource from the store.

        Args:
            uid: The UID of the resource to delete.
        """
        with self._lock:
            if uid in self.resources:
                del self.resources[uid]
            else:
                raise ValueError(f"Resource with UID {uid} not found")

    def list(self) -> List[Resource]:
        """
        Lists all resources in the store.

        Returns:
            A list of all resources.
        """
        with self._lock:
            return list(self.resources.values())


class Controller:
    """
    A generic controller that reconciles resources.
    """

    def __init__(self, resource_store: ResourceStore, reconcile_func: Callable[[Resource], None], name: str, polling_interval: int = 5) -> None:
        """
        Initializes a Controller object.

        Args:
            resource_store: The ResourceStore to use.
            reconcile_func: The function to call to reconcile a resource.
            name: The name of the controller.
            polling_interval: The interval (in seconds) at which to poll the resource store.
        """
        self.resource_store = resource_store
        self.reconcile_func = reconcile_func
        self.name = name
        self.polling_interval = polling_interval
        self._stop_event = threading.Event()

    def run(self) -> None:
        """
        Starts the controller loop.
        """
        print(f"Controller '{self.name}' started.")
        while not self._stop_event.is_set():
            try:
                resources = self.resource_store.list()
                for resource in resources:
                    try:
                        self.reconcile_func(resource)
                    except Exception as e:
                        print(f"Error reconciling resource {resource.name}: {e}")

                time.sleep(self.polling_interval)
            except Exception as e:
                print(f"Error in controller loop: {e}")
                time.sleep(self.polling_interval)

        print(f"Controller '{self.name}' stopped.")

    def stop(self) -> None:
        """
        Stops the controller loop.
        """
        print(f"Stopping controller '{self.name}'...")
        self._stop_event.set()


def example_reconcile_function(resource: Resource) -> None:
    """
    A simple example reconcile function.

    Args:
        resource: The resource to reconcile.
    """
    print(f"Reconciling resource: {resource.name}, Spec: {resource.spec}")
    # Simulate some work
    time.sleep(1)
    print(f"Resource {resource.name} reconciled.")


if __name__ == "__main__":
    # Example Usage
    store = ResourceStore()

    # Define a resource
    resource1 = Resource(name="my-resource", spec={"replicas": 3})
    store.add(resource1)

    # Define another resource
    resource2 = Resource(name="another-resource", spec={"image": "nginx:latest"})
    store.add(resource2)

    # Create a controller
    controller = Controller(store, example_reconcile_function, name="ExampleController")

    # Start the controller in a separate thread
    controller_thread = threading.Thread(target=controller.run)
    controller_thread.daemon = True  # Allow the main thread to exit even if the controller is running
    controller_thread.start()

    # Let the controller run for a while
    time.sleep(10)

    # Update a resource
    try:
        store.update(resource1.uid, {"replicas": 5})
    except ValueError as e:
        print(e)

    # Let the controller run for a while longer
    time.sleep(10)

    # Stop the controller
    controller.stop()
    controller_thread.join()

    print("Done.")