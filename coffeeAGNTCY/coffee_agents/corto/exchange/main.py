# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import json
import logging
import os
from pathlib import Path

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
from common.version import get_dependencies

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
  """Get deployment and build information from about.properties"""
  try:
    props_path = Path(__file__).parent.parent / "about.properties"
    if props_path.exists():
      # Parse simple key=value properties
      props: dict[str, str] = {}
      with open(props_path, "r") as f:
        for line in f:
          line = line.strip()
          if not line or line.startswith("#"):
            continue
          if "=" in line:
            k, v = line.split("=", 1)
            props[k.strip()] = v.strip()

      logger.info("Loaded metadata from about.properties file")

      about_data = {
        "app": {
          "name": props.get("app.name", "corto-exchange"),
          "service": props.get("app.service", "corto-exchange"),
        },
        "build_and_release": {
          "release_version": props.get("build.release_version", props.get("version", "unknown")),
          "build_date": props.get("build.date", props.get("date", "unknown")),
          "build_timestamp": props.get("build.timestamp", props.get("timestamp", "unknown")),
        },
        "git": {
          "commit": props.get("git.commit", "unknown"),
          "commit_short": props.get("git.commit.short", "unknown"),
          "branch": props.get("git.branch", "unknown"),
        },
        "build": {
          "number": props.get("build.number", "unknown"),
          "workflow": props.get("build.workflow", "unknown"),
          "actor": props.get("build.actor", "unknown"),
        },
        "image": {
          "name": props.get("image.name", "unknown"),
          "tag": props.get("image.tag", "unknown"),
        },
      }

      about_data["dependencies"] = get_dependencies()
      return about_data

    logger.error("No about.properties file found - metadata unavailable")
    return {
      "error": "about.properties file not found - deployment metadata unavailable",
      "app": {"name": "corto-exchange"},
      "dependencies": get_dependencies(),
    }

  except Exception as e:
    logger.error(f"Error getting version info: {e}")
    return {
      "error": "Version information unavailable",
      "app": {"name": "corto-exchange"},
      "build_and_release": {
        "release_version": "unknown",
        "build_date": "unknown",
      },
      "dependencies": {},
    }

# Run the FastAPI server using uvicorn
if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)