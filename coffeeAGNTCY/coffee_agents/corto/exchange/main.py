# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from config.logging_config import setup_logging
from graph import shared
from agntcy_app_sdk.factory import AgntcyFactory
from graph.graph import ExchangeGraph
from ioa_observe.sdk.tracing import session_start

setup_logging()
logger = logging.getLogger("corto.supervisor.main")
load_dotenv()

# Initialize the shared agntcy factory with tracing enabled
shared.set_factory(AgntcyFactory("corto.exchange", enable_tracing=True))

app = FastAPI()
# Add CORS middleware
app.add_middleware(
  CORSMiddleware,
  allow_origins=["*"],  # Replace "*" with specific origins if needed
  allow_credentials=True,
  allow_methods=["*"],  # Allow all HTTP methods
  allow_headers=["*"],  # Allow all headers
)

exchange_graph = ExchangeGraph()

class PromptRequest(BaseModel):
  prompt: str

@app.post("/agent/prompt")
async def handle_prompt(request: PromptRequest):
  """
  Processes a user prompt by routing it through the ExchangeGraph.

  Args:
      request (PromptRequest): Contains the input prompt as a string.

  Returns:
      dict: A dictionary containing the agent's response.

  Raises:
      HTTPException: 400 for invalid input, 500 for server-side errors.
  """
  try:
    session_start() # Start a new tracing session
    # Process the prompt using the exchange graph
    result = await exchange_graph.serve(request.prompt)
    logger.info(f"Final result from LangGraph: {result}")
    return {"response": result}
  except ValueError as ve:
    logger.exception(f"ValueError occurred: {str(ve)}")
    raise HTTPException(status_code=400, detail=str(ve))
  except Exception as e:
    logger.exception(f"An error occurred: {str(e)}")
    raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/version")
@app.get("/api/version")
async def version_info():
    """Get deployment and build information"""
    try:
        # Import docker metadata utility
        import sys
        import os
        import json
        import subprocess
        from pathlib import Path
        
        def get_docker_labels():
            """Get Docker labels from current container"""
            try:
                # Try to get labels from environment first (simpler)
                return {
                    'org.opencontainers.image.version': os.getenv('IMAGE_VERSION', 'unknown'),
                    'org.opencontainers.image.created': os.getenv('BUILD_DATE', 'unknown'),
                    'org.opencontainers.image.revision': os.getenv('GIT_COMMIT', 'unknown'),
                    'build.number': os.getenv('BUILD_NUMBER', 'unknown'),
                    'git.branch': os.getenv('GIT_BRANCH', 'unknown'),
                }
            except:
                return {}
        
        def get_pyproject_dependencies():
            """Get dependency versions from pyproject.toml"""
            try:
                import tomllib
                pyproject_path = Path(__file__).parent.parent / "pyproject.toml"
                
                with open(pyproject_path, 'rb') as f:
                    data = tomllib.load(f)
                    
                dependencies = data.get('project', {}).get('dependencies', [])
                extracted_deps = {}
                
                dependency_mapping = {
                    'agntcy-app-sdk': 'AGNTCY App SDK',
                    'a2a-sdk': 'A2A',
                    'ioa-observe-sdk': 'Observe SDK', 
                    'langgraph': 'LangGraph'             # Check both langgraph and langgraph-supervisor
                }
                
                for dep in dependencies:
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
                    
                    # Special handling for langgraph-supervisor (also counts as LangGraph)
                    if clean_dep.startswith('langgraph-supervisor'):
                        if '>=' in clean_dep:
                            version = clean_dep.split('>=')[1]
                            # Only add if we don't already have LangGraph from main langgraph package
                            if 'LangGraph' not in extracted_deps:
                                extracted_deps['LangGraph'] = f">= v{version}"
                
                # Get SLIM version dynamically from docker-compose.yaml
                def get_slim_version():
                    try:
                        compose_path = Path(__file__).parent.parent / "docker-compose.yaml"
                        if compose_path.exists():
                            with open(compose_path, 'r') as f:
                                content = f.read()
                                import re
                                match = re.search(r'ghcr\.io/agntcy/slim:(\d+\.\d+\.\d+)', content)
                                if match:
                                    return f"v{match.group(1)}"
                    except Exception as e:
                        logger.error(f"Error reading SLIM version: {e}")
                    return "v0.4.0"  # Fallback
                
                extracted_deps['SLIM'] = get_slim_version()
                
                return extracted_deps
            except Exception as e:
                logger.error(f"Error parsing pyproject.toml: {e}")
                return {}
        
        # Get Docker metadata
        docker_labels = get_docker_labels()
        dependencies = get_pyproject_dependencies()
        
        # Format build date
        build_date = docker_labels.get('org.opencontainers.image.created', 'unknown')
        if build_date != 'unknown' and 'T' in build_date:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(build_date.replace('Z', '+00:00'))
                build_date = dt.strftime('%B %d, %Y')
            except:
                pass
        
        return {
            "app": {
                "name": "corto-exchange",
                "service": "corto-exchange",
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
            },
            "build": {
                "number": docker_labels.get('build.number', 'unknown'),
                "workflow": docker_labels.get('build.workflow', 'unknown'),
                "actor": docker_labels.get('build.actor', 'unknown'),
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting version info: {e}")
        return {
            "error": "Version information unavailable",
            "app": {"name": "corto-exchange"},
            "build_and_release": {
                "release_version": "unknown",
                "build_date": "unknown"
            },
            "dependencies": {}
        }

# Run the FastAPI server using uvicorn
if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)