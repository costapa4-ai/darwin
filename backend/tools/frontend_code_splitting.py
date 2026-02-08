"""
Code splitting utility for frontend bundle optimization.

This module provides utilities to generate configuration for React-based code splitting
using React.lazy() and Suspense. It helps reduce initial bundle size and improve
page load performance by splitting the application into smaller chunks.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class RouteConfig:
    """Configuration for a lazy-loaded route."""
    
    path: str
    component_path: str
    chunk_name: str
    preload: bool = False
    prefetch: bool = False


@dataclass
class CodeSplitConfig:
    """Configuration for code splitting setup."""
    
    routes: List[RouteConfig]
    suspense_fallback: str = "Loading..."
    error_boundary: bool = True
    webpack_magic_comments: bool = True


class CodeSplitGenerator:
    """
    Generates code splitting configuration and templates for React applications.
    
    This class provides methods to create optimized route configurations with
    lazy loading, generate React component templates, and manage webpack
    chunk configurations.
    """
    
    def __init__(
        self,
        output_dir: str = "./frontend/src/routes",
        config_path: str = "./frontend/code-split.config.json",
        top_k: int = None,
        **kwargs
    ):
        """
        Initialize the code split generator.
        
        Args:
            output_dir: Directory to output generated files
            config_path: Path to save configuration file
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        self.output_dir = Path(output_dir)
        self.config_path = Path(config_path)
        self.routes: List[RouteConfig] = []
        
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directories: {e}")
            raise
    
    def add_route(
        self,
        path: str,
        component_path: str,
        chunk_name: Optional[str] = None,
        preload: bool = False,
        prefetch: bool = False,
        top_k: int = None,
        **kwargs
    ) -> None:
        """
        Add a route configuration for code splitting.
        
        Args:
            path: URL path for the route
            component_path: Import path to the component
            chunk_name: Custom webpack chunk name
            preload: Whether to preload this chunk
            prefetch: Whether to prefetch this chunk
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        if chunk_name is None:
            chunk_name = path.strip('/').replace('/', '-') or 'home'
        
        route = RouteConfig(
            path=path,
            component_path=component_path,
            chunk_name=chunk_name,
            preload=preload,
            prefetch=prefetch
        )
        self.routes.append(route)
        logger.info(f"Added route: {path} -> {component_path}")
    
    def generate_lazy_component_template(
        self,
        route: RouteConfig,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate React lazy component template with error boundary.
        
        Args:
            route: Route configuration
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Generated React component code as string
        """
        magic_comment = f"/* webpackChunkName: \"{route.chunk_name}\" */"
        preload_comment = "/* webpackPreload: true */" if route.preload else ""
        prefetch_comment = "/* webpackPrefetch: true */" if route.prefetch else ""
        
        comments = " ".join(filter(None, [magic_comment, preload_comment, prefetch_comment]))
        
        template = f"""import React, {{ lazy, Suspense }} from 'react';
import ErrorBoundary from '../components/ErrorBoundary';
import LoadingSpinner from '../components/LoadingSpinner';

// Lazy load component for route: {route.path}
const {route.chunk_name.replace('-', '_').title()}Component = lazy(() =>
  import({comments} '{route.component_path}')
    .catch(err => {{
      console.error('Failed to load component {route.chunk_name}:', err);
      return {{ default: () => <div>Failed to load page. Please refresh.</div> }};
    }})
);

const {route.chunk_name.replace('-', '_').title()}Route = () => (
  <ErrorBoundary>
    <Suspense fallback={{<LoadingSpinner />}}>
      <{route.chunk_name.replace('-', '_').title()}Component />
    </Suspense>
  </ErrorBoundary>
);

export default {route.chunk_name.replace('-', '_').title()}Route;
"""
        return template
    
    def generate_router_config(
        self,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate React Router configuration with lazy routes.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Generated router configuration code
        """
        imports = []
        routes_jsx = []
        
        for route in self.routes:
            component_name = f"{route.chunk_name.replace('-', '_').title()}Route"
            import_path = f"./routes/{route.chunk_name}"
            imports.append(f"import {component_name} from '{import_path}';")
            routes_jsx.append(f"  <Route path=\"{route.path}\" element={{<{component_name} />}} />")
        
        template = f"""import React from 'react';
import {{ BrowserRouter as Router, Routes, Route }} from 'react-router-dom';
{chr(10).join(imports)}

const AppRouter = () => (
  <Router>
    <Routes>
{chr(10).join(routes_jsx)}
      <Route path="*" element={{<div>404 - Page Not Found</div>}} />
    </Routes>
  </Router>
);

export default AppRouter;
"""
        return template
    
    def generate_error_boundary(
        self,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate React Error Boundary component.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Error boundary component code
        """
        template = """import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    // Log to error tracking service
    if (window.gtag) {
      window.gtag('event', 'exception', {
        description: error.message,
        fatal: false,
      });
    }
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <h2>Something went wrong.</h2>
          <p>Please try refreshing the page.</p>
          <button onClick={() => window.location.reload()}>
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
"""
        return template
    
    def generate_loading_spinner(
        self,
        top_k: int = None,
        **kwargs
    ) -> str:
        """
        Generate loading spinner component.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Loading spinner component code
        """
        template = """import React from 'react';
import './LoadingSpinner.css';

const LoadingSpinner: React.FC = () => (
  <div className="loading-spinner-container">
    <div className="loading-spinner"></div>
    <p>Loading...</p>
  </div>
);

export default LoadingSpinner;
"""
        return template
    
    def save_config(
        self,
        top_k: int = None,
        **kwargs
    ) -> None:
        """
        Save code splitting configuration to JSON file.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
        """
        config = CodeSplitConfig(routes=self.routes)
        config_dict = {
            'routes': [asdict(route) for route in config.routes],
            'suspense_fallback': config.suspense_fallback,
            'error_boundary': config.error_boundary,
            'webpack_magic_comments': config.webpack_magic_comments
        }
        
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info(f"Configuration saved to {self.config_path}")
        except IOError as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def generate_all(
        self,
        top_k: int = None,
        **kwargs
    ) -> Dict[str, str]:
        """
        Generate all code splitting files.
        
        Args:
            top_k: For compatibility with tool registry
            **kwargs: Additional arguments for compatibility with tool registry
            
        Returns:
            Dictionary mapping file paths to generated content
        """
        generated_files = {}
        
        # Generate lazy component templates
        for route in self.routes:
            file_path = self.output_dir / f"{route.chunk_name}.tsx"
            content = self.generate_lazy_component_template(route)
            generated_files[str(file_path)] = content
            
            try:
                with open(file_path, 'w') as f:
                    f.write(content)
                logger.info(f"Generated component: {file_path}")
            except IOError as e:
                logger.error(f"Failed to write file {file_path}: {e}")
        
        # Generate router configuration
        router_path = self.output_dir.parent / "AppRouter.tsx"
        router_content = self.generate_router_config()
        generated_files[str(router_path)] = router_content
        
        try:
            with open(router_path, 'w') as f:
                f.write(router_content)
            logger.info(f"Generated router: {router_path}")
        except IOError as e:
            logger.error(f"Failed to write router file: {e}")
        
        # Generate error boundary
        error_boundary_path = self.output_dir.parent / "components" / "ErrorBoundary.tsx"
        error_boundary_path.parent.mkdir(parents=True, exist_ok=True)
        error_boundary_content = self.generate_error_boundary()
        generated_files[str(error_boundary_path)] = error_boundary_content
        
        try:
            with open(error_boundary_path, 'w') as f:
                f.write(error_boundary_content)
            logger.info(f"Generated error boundary: {error_boundary_path}")
        except IOError as e:
            logger.error(f"Failed to write error boundary file: {e}")
        
        # Generate loading spinner
        loading_spinner_path = self.output_dir.parent / "components" / "LoadingSpinner.tsx"
        loading_spinner_content = self.generate_loading_spinner()
        generated_files[str(loading_spinner_path)] = loading_spinner_content
        
        try:
            with open(loading_spinner_path, 'w') as f:
                f.write(loading_spinner_content)
            logger.info(f"Generated loading spinner: {loading_spinner_path}")
        except IOError as e:
            logger.error(f"Failed to write loading spinner file: {e}")
        
        # Save configuration
        self.save_config()
        
        return generated_files