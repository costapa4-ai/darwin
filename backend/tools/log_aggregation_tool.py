import os
import glob
import time
import gzip
import shutil
from typing import List, Dict, Optional
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def create_parser() -> argparse.ArgumentParser:
    """Creates and configures the argument parser."""
    parser = argparse.ArgumentParser(
        description="Aggregates log files from specified directories into a single file."
    )
    parser.add_argument(
        "--source",
        "-s",
        type=str,
        nargs="+",
        required=True,
        help="List of source directories to aggregate logs from.",
    )
    parser.add_argument(
        "--destination",
        "-d",
        type=str,
        required=True,
        help="Destination file to aggregate logs into.",
    )
    parser.add_argument(
        "--pattern",
        "-p",
        type=str,
        default="*.log",
        help="Glob pattern to match log files (default: *.log).",
    )
    parser.add_argument(
        "--compress",
        "-c",
        action="store_true",
        help="Compress the aggregated log file using gzip.",
    )
    parser.add_argument(
        "--delete_source",
        action="store_true",
        help="Delete source files after aggregation.",
    )
    parser.add_argument(
        "--exclude",
        "-e",
        type=str,
        nargs="+",
        default=[],
        help="List of filenames to exclude from aggregation.",
    )

    return parser


def find_log_files(source_dirs: List[str], pattern: str, exclude_files: List[str]) -> List[str]:
    """
    Finds log files matching the given pattern in the specified source directories,
    excluding specified files.

    Args:
        source_dirs: A list of source directories to search in.
        pattern: A glob pattern to match log files.
        exclude_files: A list of filenames to exclude.

    Returns:
        A list of absolute paths to the found log files.
    """
    log_files: List[str] = []
    for source_dir in source_dirs:
        try:
            if not os.path.isdir(source_dir):
                logging.warning(f"Source directory '{source_dir}' does not exist or is not a directory. Skipping.")
                continue

            search_path = os.path.join(source_dir, pattern)
            files = glob.glob(search_path)
            for file in files:
                abs_path = os.path.abspath(file)
                if os.path.basename(abs_path) not in exclude_files:
                    log_files.append(abs_path)
                else:
                    logging.info(f"Excluding file: {abs_path}")
        except Exception as e:
            logging.error(f"Error finding log files in '{source_dir}': {e}")
    return log_files


def aggregate_logs(log_files: List[str], destination_file: str) -> None:
    """
    Aggregates the content of the given log files into a single destination file.

    Args:
        log_files: A list of absolute paths to the log files to aggregate.
        destination_file: The absolute path to the destination file.
    """
    try:
        with open(destination_file, "w", encoding="utf-8") as outfile:
            for log_file in log_files:
                try:
                    with open(log_file, "r", encoding="utf-8") as infile:
                        for line in infile:
                            outfile.write(line)
                except UnicodeDecodeError as ude:
                    logging.warning(f"UnicodeDecodeError reading {log_file}: {ude}. Trying with 'latin-1'")
                    try:
                        with open(log_file, "r", encoding="latin-1") as infile:
                            for line in infile:
                                outfile.write(line)
                    except Exception as e:
                        logging.error(f"Failed to read {log_file} even with latin-1 encoding: {e}")

                except Exception as e:
                    logging.error(f"Error reading or writing log file '{log_file}': {e}")
    except Exception as e:
        logging.error(f"Error aggregating logs into '{destination_file}': {e}")


def compress_file(file_path: str) -> None:
    """
    Compresses the given file using gzip.

    Args:
        file_path: The absolute path to the file to compress.
    """
    try:
        with open(file_path, "rb") as f_in:
            with gzip.open(file_path + ".gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(file_path)
        logging.info(f"Successfully compressed '{file_path}' to '{file_path}.gz'")
    except Exception as e:
        logging.error(f"Error compressing file '{file_path}': {e}")


def delete_files(files: List[str]) -> None:
    """
    Deletes the specified files.

    Args:
        files: A list of absolute paths to the files to delete.
    """
    for file in files:
        try:
            os.remove(file)
            logging.info(f"Successfully deleted '{file}'")
        except Exception as e:
            logging.error(f"Error deleting file '{file}': {e}")


def main() -> None:
    """
    Main function to parse arguments, find log files, aggregate them,
    compress the result (optionally), and delete source files (optionally).
    """
    parser = create_parser()
    args = parser.parse_args()

    source_dirs: List[str] = args.source
    destination_file: str = args.destination
    pattern: str = args.pattern
    compress: bool = args.compress
    delete_source: bool = args.delete_source
    exclude_files: List[str] = args.exclude

    logging.info(f"Starting log aggregation from {source_dirs} to {destination_file}")

    log_files: List[str] = find_log_files(source_dirs, pattern, exclude_files)

    if not log_files:
        logging.warning("No log files found matching the criteria.")
        return

    logging.info(f"Found {len(log_files)} log files to aggregate.")

    aggregate_logs(log_files, destination_file)

    if compress:
        compress_file(destination_file)

    if delete_source:
        delete_files(log_files)

    logging.info("Log aggregation completed.")


if __name__ == "__main__":
    main()