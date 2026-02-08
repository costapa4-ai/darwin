"""
Multi-stage Docker build configuration and utilities for the Darwin System.

This module provides Docker build configurations and utilities for creating
optimized, multi-stage Docker images for both backend and frontend services.
The multi-stage approach reduces final image size by 30-50% and improves
security by excluding build tools from production images.
"""

import os
import subprocess
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class BuildConfig:
    """Configuration for Docker multi-stage builds."""
    
    service_name: str
    base_image: str
    build_image: str
    runtime_image: str
    work_dir: str
    build_deps: List[str]
    runtime_deps: List[str]
    copy_artifacts: List[Tuple[str, str]]


class DockerMultiStageBuilder:
    """
    Manages multi-stage Docker builds for the Darwin System.
    
    This class provides utilities to generate optimized Dockerfiles using
    multi-stage builds, significantly reducing final image sizes and improving
    security by separating build-time and runtime dependencies.
    """
    
    def __init__(self, project_root: str = ".", top_k: int = None, **kwargs):
        """
        Initialize the Docker multi-stage builder.
        
        Args:
            project_root: Root directory of the project
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        self.project_root = Path(project_root)
        self.backend_config = self._get_backend_config()
        self.frontend_config = self._get_frontend_config()
    
    def _get_backend_config(self) -> BuildConfig:
        """
        Get build configuration for backend service.
        
        Returns:
            BuildConfig object for backend
        """
        return BuildConfig(
            service_name="backend",
            base_image="python:3.11-slim",
            build_image="python:3.11",
            runtime_image="python:3.11-slim",
            work_dir="/app",
            build_deps=[
                "build-essential",
                "gcc",
                "g++",
                "git",
                "curl",
            ],
            runtime_deps=[
                "libpq5",
                "curl",
                "ca-certificates",
            ],
            copy_artifacts=[
                ("/root/.cache/pip", "/root/.cache/pip"),
                ("/app", "/app"),
            ]
        )
    
    def _get_frontend_config(self) -> BuildConfig:
        """
        Get build configuration for frontend service.
        
        Returns:
            BuildConfig object for frontend
        """
        return BuildConfig(
            service_name="frontend",
            base_image="node:18-alpine",
            build_image="node:18",
            runtime_image="nginx:alpine",
            work_dir="/app",
            build_deps=[
                "python3",
                "make",
                "g++",
            ],
            runtime_deps=[],
            copy_artifacts=[
                ("/app/build", "/usr/share/nginx/html"),
                ("/app/nginx.conf", "/etc/nginx/conf.d/default.conf"),
            ]
        )
    
    def generate_backend_dockerfile(
        self,
        output_path: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate optimized multi-stage Dockerfile for backend service.
        
        Args:
            output_path: Path to save the Dockerfile (optional)
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Generated Dockerfile content as string
            
        Raises:
            IOError: If unable to write Dockerfile to specified path
        """
        config = self.backend_config
        
        dockerfile_content = f"""# Multi-stage Docker build for {config.service_name}
# Stage 1: Build stage with all build dependencies
FROM {config.build_image} AS builder

# Set working directory
WORKDIR {config.work_dir}

# Install build dependencies
RUN apt-get update && \\
    apt-get install -y --no-install-recommends \\
    {' '.join(config.build_deps)} && \\
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install dependencies with pip cache
RUN --mount=type=cache,target=/root/.cache/pip \\
    pip install --upgrade pip && \\
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run any build steps (compile, optimize, etc.)
RUN python -m compileall . || true

# Stage 2: Runtime stage with minimal dependencies
FROM {config.runtime_image} AS runtime

# Set working directory
WORKDIR {config.work_dir}

# Install only runtime dependencies
RUN apt-get update && \\
    apt-get install -y --no-install-recommends \\
    {' '.join(config.runtime_deps)} && \\
    rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code from builder
COPY --from=builder {config.work_dir} {config.work_dir}

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \\
    PYTHONUNBUFFERED=1 \\
    PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONPATH={config.work_dir}

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \\
    chown -R appuser:appuser {config.work_dir}

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
        
        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(dockerfile_content)
                logger.info(f"Backend Dockerfile written to {output_path}")
            except IOError as e:
                logger.error(f"Failed to write Dockerfile to {output_path}: {e}")
                raise
        
        return dockerfile_content
    
    def generate_frontend_dockerfile(
        self,
        output_path: Optional[str] = None,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate optimized multi-stage Dockerfile for frontend service.
        
        Args:
            output_path: Path to save the Dockerfile (optional)
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Generated Dockerfile content as string
            
        Raises:
            IOError: If unable to write Dockerfile to specified path
        """
        config = self.frontend_config
        
        dockerfile_content = f"""# Multi-stage Docker build for {config.service_name}
# Stage 1: Build stage with Node.js and build tools
FROM {config.build_image} AS builder

# Set working directory
WORKDIR {config.work_dir}

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies with npm cache
RUN --mount=type=cache,target=/root/.npm \\
    npm ci --only=production && \\
    npm cache clean --force

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Stage 2: Runtime stage with Nginx
FROM {config.runtime_image} AS runtime

# Copy built assets from builder
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx configuration if exists
COPY --from=builder /app/nginx.conf /etc/nginx/conf.d/default.conf || true

# Expose port
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

# Run nginx
CMD ["nginx", "-g", "daemon off;"]
"""
        
        if output_path:
            try:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(dockerfile_content)
                logger.info(f"Frontend Dockerfile written to {output_path}")
            except IOError as e:
                logger.error(f"Failed to write Dockerfile to {output_path}: {e}")
                raise
        
        return dockerfile_content
    
    def build_image(
        self,
        service: str,
        tag: str = "latest",
        no_cache: bool = False,
        top_k: int = None,
        **kwargs
    ) -> bool:
        """
        Build Docker image using multi-stage Dockerfile.
        
        Args:
            service: Service name ('backend' or 'frontend')
            tag: Docker image tag
            no_cache: Whether to build without cache
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            True if build succeeded, False otherwise
            
        Raises:
            ValueError: If invalid service name is provided
        """
        if service not in ["backend", "frontend"]:
            raise ValueError(f"Invalid service: {service}. Must be 'backend' or 'frontend'")
        
        # Generate Dockerfile
        dockerfile_path = self.project_root / f"Dockerfile.{service}"
        if service == "backend":
            self.generate_backend_dockerfile(str(dockerfile_path))
        else:
            self.generate_frontend_dockerfile(str(dockerfile_path))
        
        # Build Docker image
        image_name = f"darwin-{service}:{tag}"
        build_cmd = [
            "docker", "build",
            "-f", str(dockerfile_path),
            "-t", image_name,
        ]
        
        if no_cache:
            build_cmd.append("--no-cache")
        
        build_cmd.append(str(self.project_root))
        
        try:
            logger.info(f"Building Docker image: {image_name}")
            result = subprocess.run(
                build_cmd,
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"Successfully built {image_name}")
            logger.debug(result.stdout)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to build {image_name}: {e}")
            logger.error(e.stderr)
            return False
    
    def get_image_size(self, service: str, tag: str = "latest", top_k: int = None, **kwargs) -> Optional[str]:
        """
        Get the size of a built Docker image.
        
        Args:
            service: Service name ('backend' or 'frontend')
            tag: Docker image tag
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Image size as string or None if image not found
        """
        image_name = f"darwin-{service}:{tag}"
        
        try:
            result = subprocess.run(
                ["docker", "images", image_name, "--format", "{{.Size}}"],
                check=True,
                capture_output=True,
                text=True
            )
            size = result.stdout.strip()
            logger.info(f"Image {image_name} size: {size}")
            return size
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get image size for {image_name}: {e}")
            return None