import gc
import tracemalloc
import logging
from typing import List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class MemoryLeakDetector:
    """
    A class for detecting memory leaks in Python applications.

    This class uses tracemalloc to track memory allocations and identify potential leaks.
    It provides methods to start and stop tracing, take snapshots of memory usage, and compare snapshots
    to identify allocations that have not been freed.
    """

    def __init__(self, threshold: int = 1024) -> None:
        """
        Initializes the MemoryLeakDetector.

        Args:
            threshold: The minimum size (in bytes) of a memory allocation to be considered for leak detection.
        """
        self.threshold = threshold
        self.snapshot: Optional[tracemalloc.Snapshot] = None
        self.is_tracing = False
        self.logger = logging.getLogger(__name__)

    def start_tracing(self) -> None:
        """
        Starts tracing memory allocations using tracemalloc.
        """
        if self.is_tracing:
            self.logger.warning("Tracing already started.")
            return

        try:
            tracemalloc.start()
            self.is_tracing = True
            self.logger.info("Tracing started.")
        except Exception as e:
            self.logger.error(f"Failed to start tracing: {e}")

    def stop_tracing(self) -> None:
        """
        Stops tracing memory allocations.
        """
        if not self.is_tracing:
            self.logger.warning("Tracing not started.")
            return

        try:
            tracemalloc.stop()
            self.is_tracing = False
            self.logger.info("Tracing stopped.")
        except Exception as e:
            self.logger.error(f"Failed to stop tracing: {e}")

    def take_snapshot(self) -> None:
        """
        Takes a snapshot of the current memory allocations.
        """
        if not self.is_tracing:
            self.logger.warning("Tracing is not active. Start tracing before taking a snapshot.")
            return

        try:
            gc.collect()  # Run garbage collection before taking snapshot
            self.snapshot = tracemalloc.take_snapshot()
            self.logger.info("Snapshot taken.")
        except Exception as e:
            self.logger.error(f"Failed to take snapshot: {e}")

    def compare_snapshots(self) -> List[Tuple[str, int, int]]:
        """
        Compares the current snapshot with the previous snapshot and identifies potential memory leaks.

        Returns:
            A list of tuples, where each tuple contains the file name, line number, and size difference (in bytes)
            of allocations that have increased significantly between the two snapshots.  Returns an empty list if
            no snapshot has been taken or if tracing is not active.
        """
        if not self.is_tracing:
            self.logger.warning("Tracing is not active. Start tracing before comparing snapshots.")
            return []

        if self.snapshot is None:
            self.logger.warning("No snapshot taken. Take a snapshot before comparing.")
            return []

        try:
            gc.collect() # Run garbage collection before comparing snapshots
            snapshot2 = tracemalloc.take_snapshot()
            top_stats = snapshot2.compare_to(self.snapshot, 'lineno')

            leaks: List[Tuple[str, int, int]] = []
            for stat in top_stats:
                if stat.size_diff > self.threshold:
                    filename = stat.traceback[0].filename
                    lineno = stat.traceback[0].lineno
                    size_diff = stat.size_diff
                    leaks.append((filename, lineno, size_diff))
                    self.logger.warning(
                        f"Potential memory leak: {filename}:{lineno}: {size_diff} bytes"
                    )

            self.snapshot = snapshot2  # Update snapshot for next comparison
            return leaks

        except Exception as e:
            self.logger.error(f"Failed to compare snapshots: {e}")
            return []

    def run_detection(self, iterations: int = 1) -> List[Tuple[str, int, int]]:
        """
        Runs memory leak detection for a specified number of iterations.

        Args:
            iterations: The number of iterations to run the detection.

        Returns:
            A list of memory leaks found during the iterations.
        """
        self.start_tracing()
        self.take_snapshot()
        all_leaks: List[Tuple[str, int, int]] = []

        for i in range(iterations):
            leaks = self.compare_snapshots()
            all_leaks.extend(leaks)
            self.logger.info(f"Memory leak detection iteration {i + 1} completed.")

        self.stop_tracing()
        return all_leaks

    def is_currently_tracing(self) -> bool:
        """
        Returns whether tracemalloc is currently tracing memory allocations.

        Returns:
            True if tracing is active, False otherwise.
        """
        return self.is_tracing