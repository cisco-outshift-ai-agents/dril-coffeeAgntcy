# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import os

from cnoe_agent_utils import LLMFactory
from config.config import LLM_PROVIDER
from common.circuit_llm import AzureChatOpenAIWrapper
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_llm():
  """
  Get the LLM provider based on the configuration using cnoe-agent-utils LLMFactory.
  """
  print("using LLM provider:", LLM_PROVIDER)
  if LLM_PROVIDER == "nvidia-nim":
    return get_nvidia_nim_llm()
  elif LLM_PROVIDER == "circuit":
    return get_circuit_llm()

  factory = LLMFactory(
    provider=LLM_PROVIDER,
  )
  return factory.get_llm()

def get_circuit_llm():
  client_id = os.getenv("CIRCUIT_CLIENT_ID")
  client_secret = os.getenv("CIRCUIT_CLIENT_SECRET")
  app_key = os.getenv("CIRCUIT_APP_KEY")

  if client_id is None or client_secret is None or app_key is None:
    raise ValueError("CIRCUIT_CLIENT_ID, CIRCUIT_CLIENT_SECRET, and CIRCUIT_APP_KEY environment variables must be set for Circuit LLM provider.")
  
  endpoint = os.getenv("CIRCUIT_LLM_API_ENDPOINT", "https://chat-ai.cisco.com")
  model = os.getenv("CIRCUIT_LLM_API_MODEL_NAME", "gpt-4o-mini")
  version = os.getenv("CIRCUIT_LLM_API_VERSION", "2025-04-01-preview")
  
  llm = AzureChatOpenAIWrapper(
    client_id=client_id,
    client_secret=client_secret,
    app_key=app_key,
    azure_endpoint=endpoint,
    deployment_name=model,
    api_version=version,
  )

  llm = llm.get_llm()

  logger.info(f"Using Circuit LLM model: {model} at endpoint: {endpoint}")
  return llm

def get_nvidia_nim_llm():
  """
  Get the NVIDIA LLM provider based on the configuration using cnoe-agent-utils LLMFactory.
  """
  from langchain_nvidia_ai_endpoints import ChatNVIDIA

  model = os.getenv("NVIDIA_NIM_MODEL", "openai/gpt-oss-20b")
  model_endpoint = os.getenv("NVIDIA_NIM_MODEL_ENDPOINT", None)
  api_key = os.getenv("NVIDIA_API_KEY")
  if api_key is None:
    logger.warning("NVIDIA_API_KEY environment variable is not set. Connecting without API key.")

  if model_endpoint:
    llm = ChatNVIDIA(
      model=model,
      base_url=model_endpoint,
      api_key=api_key,
    )
    logger.info(f"Using NVIDIA LLM model: {model} at custom endpoint: {model_endpoint}")
    return llm
  
  llm = ChatNVIDIA(
    model=model,
  )
  logger.info(f"Using NVIDIA LLM model: {model}")
  return llm