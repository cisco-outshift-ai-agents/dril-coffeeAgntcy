# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from agntcy_app_sdk.factory import AgntcyFactory
from ioa_observe.sdk.tracing import session_start
from common.version import get_dependencies, get_latest_tag_and_date

from config.logging_config import setup_logging
from exchange.graph import shared
from exchange.graph.graph import ExchangeGraph

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

@app.get("/build/info")
async def version_info():
  """Return minimal build info sourced from about.properties."""
  try:
    props_path = Path(__file__).parent.parent / "about.properties"
    if props_path.exists():
      props: dict[str, str] = {}
      with open(props_path, "r") as f:
        for line in f:
          line = line.strip()
          if not line or line.startswith("#"):
            continue
          if "=" in line:
            k, v = line.split("=", 1)
            props[k.strip()] = v.strip()

      app_name = props.get("app.name", "corto-exchange")
      service = props.get("app.service", "corto-exchange")
      version = props.get("build.release_version", props.get("version", "unknown"))
      build_date = props.get("build.date", props.get("date", "unknown"))
      build_ts = props.get("build.timestamp", props.get("timestamp", "unknown"))
      image_name = props.get("image.name", "unknown")
      image_tag = props.get("image.tag", "unknown")
      image = (
        f"{image_name}:{image_tag}" if image_name != "unknown" and image_tag != "unknown" else image_name
      )

      # Fallback to local git metadata if unknown for local builds
      if version == "unknown" or build_date == "unknown" or build_ts == "unknown":
        git_info = get_latest_tag_and_date(Path(__file__).resolve())
        if git_info:
          if version == "unknown":
            version = git_info.get("tag", version)
          if build_date == "unknown":
            build_date = git_info.get("created_iso", build_date)
          if build_ts == "unknown":
            build_ts = git_info.get("created_unix", build_ts)

      return {
        "app": app_name,
        "service": service,
        "version": version,
        "build_date": build_date,
        "build_timestamp": build_ts,
        "image": image,
        "dependencies": get_dependencies(),
      }

    logger.error("No about.properties file found - metadata unavailable")
    git_info = get_latest_tag_and_date(Path(__file__).resolve())
    if git_info:
      return {
        "app": "corto-exchange",
        "service": "corto-exchange",
        "version": git_info.get("tag", "unknown"),
        "build_date": git_info.get("created_iso", "unknown"),
        "build_timestamp": git_info.get("created_unix", "unknown"),
        "image": "unknown",
        "dependencies": get_dependencies(),
      }

    return {
      "app": "corto-exchange",
      "service": "corto-exchange",
      "version": "unknown",
      "build_date": "unknown",
      "build_timestamp": "unknown",
      "image": "unknown",
      "dependencies": get_dependencies(),
    }

  except Exception as e:
    logger.error(f"Error getting version info: {e}")
    return {
      "app": "corto-exchange",
      "service": "corto-exchange",
      "version": "unknown",
      "build_date": "unknown",
      "build_timestamp": "unknown",
      "image": "unknown",
      "dependencies": {},
    }

# Run the FastAPI server using uvicorn
if __name__ == "__main__":
  uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)