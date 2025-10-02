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
    """Get deployment and build information"""
    try:
        about_file = Path(__file__).parent.parent / ".about"
        if about_file.exists():
            with open(about_file, 'r') as f:
                about_data = json.load(f)
                logger.info("Loaded metadata from .about file")
                
                about_data["dependencies"] = get_dependencies()
                return about_data
        
        logger.error("No .about file found - metadata unavailable")
        return {
            "error": ".about file not found - deployment metadata unavailable",
            "app": {"name": "corto-exchange"},
            "dependencies": get_dependencies()
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