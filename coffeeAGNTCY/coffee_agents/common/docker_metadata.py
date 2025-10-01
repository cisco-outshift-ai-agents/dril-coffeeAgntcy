#!/usr/bin/env python3
"""
Docker metadata utility for reading build/deployment information from Docker labels
"""
import json
import os
import subprocess
import tomllib
from pathlib import Path
from typing import Dict, Any, Optional

def get_docker_metadata() -> Dict[str, Any]:
    """
    Read metadata from Docker image labels
    """
    try:
        # Get the current container's image ID
        result = subprocess.run(
            ['cat', '/proc/self/cgroup'], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            # Extract container ID from cgroup info
            for line in result.stdout.split('\n'):
                if 'docker' in line:
                    container_id = line.split('/')[-1][:12]
                    break
            else:
                container_id = None
            
            if container_id:
                # Get image ID from container
                result = subprocess.run(
                    ['docker', 'inspect', container_id, '--format={{.Image}}'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    image_id = result.stdout.strip()
                    
                    # Get labels from image
                    result = subprocess.run(
                        ['docker', 'inspect', image_id, '--format={{json .Config.Labels}}'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        return json.loads(result.stdout.strip() or '{}')
    except:
        pass
    
    # Fallback: try to read from environment if Docker API not available
    return {
        'org.opencontainers.image.version': os.getenv('IMAGE_VERSION', 'unknown'),
        'org.opencontainers.image.created': os.getenv('BUILD_DATE', 'unknown'),
        'org.opencontainers.image.revision': os.getenv('GIT_COMMIT', 'unknown'),
        'build.number': os.getenv('BUILD_NUMBER', 'unknown'),
        'git.branch': os.getenv('GIT_BRANCH', 'unknown'),
    }

def parse_pyproject_dependencies(pyproject_path: Optional[str] = None) -> Dict[str, str]:
    """
    Parse pyproject.toml for dependency versions matching InfoModal requirements
    """
    if pyproject_path is None:
        pyproject_path = Path(__file__).parent / "pyproject.toml"
    
    try:
        with open(pyproject_path, 'rb') as f:
            data = tomllib.load(f)
            
        dependencies = data.get('project', {}).get('dependencies', [])
        
        # Map dependency names to InfoModal display names
        dependency_mapping = {
            'agntcy-app-sdk': 'AGNTCY App SDK',
            'a2a-sdk': 'A2A',
            'ioa-observe-sdk': 'Observe SDK', 
            'identity-service-sdk': 'Identity',
            'mcp': 'MCP',
            'langgraph': 'LangGraph'
        }
        
        extracted_deps = {}
        
        for dep in dependencies:
            # Clean up dependency string (remove [cli] etc.)
            clean_dep = dep.split('[')[0]
            
            for dep_key, display_name in dependency_mapping.items():
                if clean_dep.startswith(dep_key):
                    if '==' in clean_dep:
                        version = clean_dep.split('==')[1]
                        extracted_deps[display_name] = f"v{version}"
                    elif '>=' in clean_dep:
                        version = clean_dep.split('>=')[1]
                        extracted_deps[display_name] = f">= v{version}"
                    break
        
        return extracted_deps
        
    except Exception as e:
        print(f"Error parsing pyproject.toml: {e}")
        return {}

def get_slim_version() -> str:
    """
    Get SLIM version from docker-compose or environment
    """
    # Try to find SLIM version from docker-compose
    try:
        compose_files = [
            Path(__file__).parent / "docker-compose.yaml",
            Path(__file__).parent.parent / "docker-compose.yaml"
        ]
        
        for compose_file in compose_files:
            if compose_file.exists():
                with open(compose_file, 'r') as f:
                    content = f.read()
                    # Look for slim image version
                    import re
                    match = re.search(r'ghcr\.io/agntcy/slim:(\d+\.\d+\.\d+)', content)
                    if match:
                        return f"v{match.group(1)}"
    except:
        pass
    
    return "v0.4.0"  # Default fallback

def get_complete_version_info(service_name: str) -> Dict[str, Any]:
    """
    Get complete version information combining Docker labels and pyproject.toml
    """
    # Get Docker metadata
    docker_labels = get_docker_metadata()
    
    # Get dependency versions
    dependencies = parse_pyproject_dependencies()
    dependencies['SLIM'] = get_slim_version()
    
    # Format build date for InfoModal
    build_date = docker_labels.get('org.opencontainers.image.created', 'unknown')
    if build_date != 'unknown' and 'T' in build_date:
        # Convert ISO format to "Month Day, Year"
        from datetime import datetime
        try:
            dt = datetime.fromisoformat(build_date.replace('Z', '+00:00'))
            build_date = dt.strftime('%B %d, %Y')
        except:
            pass
    
    return {
        "app": {
            "name": service_name,
            "service": service_name,
        },
        "build_and_release": {
            "release_version": docker_labels.get('org.opencontainers.image.version', 'unknown').replace('v', ''),
            "build_date": build_date,
            "build_timestamp": docker_labels.get('org.opencontainers.image.created', 'unknown'),
        },
        "dependencies": dependencies,
        "git": {
            "commit": docker_labels.get('org.opencontainers.image.revision', 'unknown'),
            "commit_short": docker_labels.get('git.commit.short', 'unknown'),
            "branch": docker_labels.get('git.branch', 'unknown'),
            "repository": docker_labels.get('org.opencontainers.image.source', 'unknown'),
        },
        "build": {
            "number": docker_labels.get('build.number', 'unknown'),
            "workflow": docker_labels.get('build.workflow', 'unknown'),
            "actor": docker_labels.get('build.actor', 'unknown'),
        }
    }

if __name__ == "__main__":
    import sys
    service_name = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    metadata = get_complete_version_info(service_name)
    print(json.dumps(metadata, indent=2))