# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import os

from cnoe_agent_utils import LLMFactory
from config.config import LLM_PROVIDER
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_llm():
  """
  Get the LLM provider based on the configuration using cnoe-agent-utils LLMFactory.
  """
  if LLM_PROVIDER == "nvidia-nim":
    return get_nvidia_nim_llm()

  factory = LLMFactory(
    provider=LLM_PROVIDER,
  )
  return factory.get_llm()

def get_nvidia_nim_llm():
  """
  Get the NVIDIA LLM provider based on the configuration using cnoe-agent-utils LLMFactory.
  """
  from langchain_nvidia_ai_endpoints import ChatNVIDIA

  model = os.getenv("NVIDIA_NIM_MODEL", "meta/llama-3.3-70b-instruct")
  api_key = os.getenv("NVIDIA_API_KEY")
  if api_key is None:
    logger.warning("NVIDIA_API_KEY environment variable is not set. Connecting without API key.")
  
  llm = ChatNVIDIA(model=model)
  logger.info(f"Using NVIDIA LLM model: {model}")
  return llm
