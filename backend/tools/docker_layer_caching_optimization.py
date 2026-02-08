"""
Optimized Dockerfile generator for the Darwin System.

This module creates a production-ready Dockerfile with optimized layer caching
to minimize rebuild times and bandwidth usage during development.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Any


class DockerfileOptimizer:
    """
    Generates optimized Dockerfiles with proper layer caching strategy.
    
    The optimizer follows best practices:
    - Install system dependencies first (rarely change)
    - Copy and install Python requirements before code (change less frequently)
    - Copy application code last (changes most frequently)
    - Use multi-stage builds when applicable
    - Minimize layer count while maintaining cache efficiency
    """
    
    def __init__(
        self,
        base_image: str = "python:3.11-slim",
        working_dir: str = "/app",
        port: int = 8000,
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize the Dockerfile optimizer.
        
        Args:
            base_image: Base Docker image to use
            working_dir: Working directory inside container
            port: Port to expose
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
        """
        self.base_image = base_image
        self.working_dir = working_dir
        self.port = port
        self.system_packages: List[str] = []
        self.python_packages_file: str = "requirements.txt"
        self.extra_files: List[str] = []
        
    def add_system_packages(
        self,
        packages: List[str],
        top_k: int = None,
        **kwargs
    ) -> None:
        """
        Add system packages to install.
        
        Args:
            packages: List of system packages
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
        """
        self.system_packages.extend(packages)
        
    def set_requirements_file(
        self,
        filename: str,
        top_k: int = None,
        **kwargs
    ) -> None:
        """
        Set the Python requirements file name.
        
        Args:
            filename: Requirements file name
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
        """
        self.python_packages_file = filename
        
    def generate_optimized_dockerfile(
        self,
        output_path: Optional[str] = None,
        use_multistage: bool = False,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate an optimized Dockerfile with proper layer caching.
        
        The generated Dockerfile follows this order for optimal caching:
        1. Base image and metadata
        2. System dependencies (apt packages)
        3. Working directory setup
        4. Requirements file copy
        5. Python dependencies installation
        6. Application code copy
        7. Runtime configuration
        
        Args:
            output_path: Path to save Dockerfile, if None returns as string
            use_multistage: Whether to use multi-stage build
            top_k: For compatibility with tool registry
            **kwargs: Additional compatibility parameters
            
        Returns:
            Generated Dockerfile content as string
            
        Raises:
            IOError: If unable to write to output_path
            ValueError: If configuration is invalid
        """
        try:
            if use_multistage:
                dockerfile_content = self._generate_multistage_dockerfile()
            else:
                dockerfile_content = self._generate_single_stage_dockerfile()
            
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(dockerfile_content)
                
            return dockerfile_content
            
        except IOError as e:
            raise IOError(f"Failed to write Dockerfile to {output_path}: {e}")
        except Exception as e:
            raise ValueError(f"Failed to generate Dockerfile: {e}")
    
    def _generate_single_stage_dockerfile(self) -> str:
        """
        Generate a single-stage optimized Dockerfile.
        
        Returns:
            Dockerfile content as string
        """
        lines = [
            f"# Optimized Dockerfile with layer caching",
            f"# Base image - changes rarely",
            f"FROM {self.base_image}",
            "",
            "# Set environment variables for Python",
            "ENV PYTHONUNBUFFERED=1 \\",
            "    PYTHONDONTWRITEBYTECODE=1 \\",
            "    PIP_NO_CACHE_DIR=1 \\",
            "    PIP_DISABLE_PIP_VERSION_CHECK=1",
            "",
        ]
        
        # System packages - change infrequently
        if self.system_packages:
            lines.extend([
                "# Install system dependencies - cached unless packages change",
                "RUN apt-get update && apt-get install -y --no-install-recommends \\",
            ])
            for i, pkg in enumerate(self.system_packages):
                suffix = " \\" if i < len(self.system_packages) - 1 else ""
                lines.append(f"    {pkg}{suffix}")
            lines.extend([
                "    && apt-get clean \\",
                "    && rm -rf /var/lib/apt/lists/*",
                "",
            ])
        
        # Working directory
        lines.extend([
            f"# Set working directory",
            f"WORKDIR {self.working_dir}",
            "",
        ])
        
        # Copy requirements first - critical for caching
        lines.extend([
            "# Copy requirements file FIRST - this layer is cached unless requirements change",
            f"COPY {self.python_packages_file} .",
            "",
            "# Install Python dependencies - cached unless requirements.txt changes",
            f"RUN pip install --no-cache-dir -r {self.python_packages_file}",
            "",
        ])
        
        # Copy application code last - changes most frequently
        lines.extend([
            "# Copy application code LAST - this layer rebuilds on any code change",
            "COPY . .",
            "",
        ])
        
        # Runtime configuration
        lines.extend([
            f"# Expose port",
            f"EXPOSE {self.port}",
            "",
            "# Health check",
            'HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\',
            f'    CMD python -c "import requests; requests.get(\'http://localhost:{self.port}/health\')" || exit 1',
            "",
            "# Run application",
            'CMD ["python", "main.py"]',
        ])
        
        return "\n".join(lines)
    
    def _generate_multistage_dockerfile(self) -> str:
        """
        Generate a multi-stage optimized Dockerfile for smaller final images.
        
        Returns:
            Dockerfile content as string
        """
        lines = [
            "# Multi-stage optimized Dockerfile with layer caching",
            "",
            "# Build stage - includes build dependencies",
            f"FROM {self.base_image} AS builder",
            "",
            "# Set environment variables",
            "ENV PYTHONUNBUFFERED=1 \\",
            "    PYTHONDONTWRITEBYTECODE=1 \\",
            "    PIP_NO_CACHE_DIR=1 \\",
            "    PIP_DISABLE_PIP_VERSION_CHECK=1",
            "",
        ]
        
        # System packages for builder
        if self.system_packages:
            lines.extend([
                "# Install build dependencies",
                "RUN apt-get update && apt-get install -y --no-install-recommends \\",
            ])
            for i, pkg in enumerate(self.system_packages):
                suffix = " \\" if i < len(self.system_packages) - 1 else ""
                lines.append(f"    {pkg}{suffix}")
            lines.extend