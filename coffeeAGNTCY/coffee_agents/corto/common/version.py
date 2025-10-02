"""Version and dependency utilities for Corto exchange service."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def get_dependencies():
    """Get dependency versions from pyproject.toml and docker-compose.yaml"""
    try:
        import tomllib
        import re
        
        dependencies = {}
        
        # Parse pyproject.toml for Python dependencies
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists():
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
                
            for dep in data.get('project', {}).get('dependencies', []):
                clean_dep = dep.split('[')[0]
                
                # Map internal dependency names to display names
                if clean_dep.startswith('agntcy-app-sdk'):
                    version = clean_dep.split('==')[1] if '==' in clean_dep else clean_dep.split('>=')[1]
                    dependencies['AGNTCY App SDK'] = f"v{version}" if '==' in clean_dep else f">= v{version}"
                elif clean_dep.startswith('a2a-sdk'):
                    version = clean_dep.split('==')[1] if '==' in clean_dep else clean_dep.split('>=')[1]
                    dependencies['A2A'] = f"v{version}" if '==' in clean_dep else f">= v{version}"
                elif clean_dep.startswith('ioa-observe-sdk'):
                    version = clean_dep.split('==')[1] if '==' in clean_dep else clean_dep.split('>=')[1]
                    dependencies['Observe SDK'] = f"v{version}" if '==' in clean_dep else f">= v{version}"
                elif clean_dep.startswith('langgraph'):
                    version = clean_dep.split('==')[1] if '==' in clean_dep else clean_dep.split('>=')[1]
                    dependencies['LangGraph'] = f"v{version}" if '==' in clean_dep else f">= v{version}"
        
        # Get SLIM version from docker-compose.yaml
        compose_path = Path(__file__).parent.parent / "docker-compose.yaml"
        if compose_path.exists():
            with open(compose_path, 'r') as f:
                content = f.read()
                match = re.search(r'ghcr\.io/agntcy/slim:(\d+\.\d+\.\d+)', content)
                if match:
                    dependencies['SLIM'] = f"v{match.group(1)}"
        
        return dependencies
        
    except Exception as e:
        logger.error(f"Error parsing dependencies: {e}")
        return {}