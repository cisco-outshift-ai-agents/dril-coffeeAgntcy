"""Version and dependency utilities for Corto exchange service."""

import logging
import re
from pathlib import Path

try:  
    import tomllib  
except Exception:  
    tomllib = None 

logger = logging.getLogger(__name__)


DISPLAY_NAMES = {
    "agntcy-app-sdk": "AGNTCY App SDK",
    "a2a-sdk": "A2A",
    "ioa-observe-sdk": "Observe SDK",
    "langgraph": "LangGraph",
}


def _extract_name_and_version(spec: str):
    """Extract base package name and version constraint from a dependency spec.

    Returns tuple (base_name, op, version) where op is one of '==', '>=', or '' if unspecified.
    """
    base = spec.split("[")[0].strip()  
    m = re.search(r"(==|>=)\s*([^;\s]+)", base)
    if m:
        op, ver = m.group(1), m.group(2)
        name = base.split(op)[0].strip()
        return name, op, ver

    return base, "", ""


def get_dependencies():
    """Get dependency versions from pyproject.toml and docker-compose.yaml"""
    try:
        dependencies: dict[str, str] = {}

        # Parse pyproject.toml for Python dependencies
        pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
        if pyproject_path.exists() and tomllib is not None:
            with open(pyproject_path, 'rb') as f:
                data = tomllib.load(f)
            
            for dep in data.get('project', {}).get('dependencies', []):
                name, op, ver = _extract_name_and_version(dep)
                display = DISPLAY_NAMES.get(name)
                if not display:
                    continue
                if op == '==':
                    dependencies[display] = f"v{ver}"
                elif op == '>=':
                    dependencies[display] = f">= v{ver}"
                else:
                    dependencies[display] = "unknown"
        
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