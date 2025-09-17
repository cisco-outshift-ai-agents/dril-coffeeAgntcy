# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
from typing import Any
from uuid import uuid4
from pydantic import PrivateAttr

from a2a.types import (
    AgentCard, 
    SendMessageRequest, 
    MessageSendParams, 
    Message, 
    Part, 
    TextPart, 
    Role,
)

from langchain_core.tools import BaseTool
from graph.models import FlavorProfileInput, FlavorProfileOutput
from graph.shared import get_factory
from agntcy_app_sdk.protocols.a2a.protocol import A2AProtocol
from ioa_observe.sdk.decorators import tool

from config.config import DEFAULT_MESSAGE_TRANSPORT, TRANSPORT_SERVER_ENDPOINT

logger = logging.getLogger("corto.supervisor.tools")

class FlavorProfileTool(BaseTool):
    """
    This tool sends a prompt to the A2A agent and returns the flavor profile estimation.
    """
    name: str = "get_flavor_profile"
    description: str = "Estimates the flavor profile of coffee beans based on a given prompt."

    print("creating FlavorProfileTool")

    # private attribute to store client connection
    _client = PrivateAttr()
    
    def __init__(self, remote_agent_card: AgentCard, **kwargs: Any):
        super().__init__(**kwargs)
        self._remote_agent_card = remote_agent_card
        self._client = None

    async def _connect(self):
        logger.info(f"Connecting to remote agent: {self._remote_agent_card.name}")
        factory = get_factory()

        a2a_topic = A2AProtocol.create_agent_topic(self._remote_agent_card)

        transport = factory.create_transport(
            DEFAULT_MESSAGE_TRANSPORT,
            endpoint=TRANSPORT_SERVER_ENDPOINT,
            # SLIM transport requires a routable name (org/namespace/agent) to build the PyName used for request-reply routing
            name="default/default/exchange"
        )
        self._client = await factory.create_client(
            "A2A", 
            agent_topic=a2a_topic,
            agent_url=self._remote_agent_card.url, 
            transport=transport)
        
        logger.info("Connected to remote agent")

    def _run(self, input: FlavorProfileInput) -> float:
        raise NotImplementedError("Use _arun for async execution.")

    async def _arun(self, input: FlavorProfileInput, **kwargs: Any) -> float:
        logger.info("FlavorProfileTool has been called.")
        try:
            if not input.get('prompt'):
                logger.error("Invalid input: Prompt must be a non-empty string.")
                raise ValueError("Invalid input: Prompt must be a non-empty string.")
            resp = await self.send_message(input.get('prompt'))
            return FlavorProfileOutput(flavor_profile=resp)
        except Exception as e:
            logger.error(f"Failed to get flavor profile: {str(e)}")
            raise RuntimeError(f"Failed to get flavor profile: {str(e)}")
    
    @tool(name="exchange_tool")
    async def send_message(self, prompt: str) -> str:
        """
        Sends a message to the flavor profile farm agent via A2A, specifically invoking its `estimate_flavor` skill.
        Args:
            prompt (str): The user input prompt to send to the agent.
        Returns:
            str: The flavor profile estimation returned by the agent.
        """

        print("send_message called with prompt:", prompt)

        # Ensure the client is connected, use async event loop to connect if not
        if not self._client:
            await self._connect()

        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(
                skill_id="estimate_flavor",
                sender_id="coffee-exchange-agent",
                receiver_id="flavor-profile-farm-agent",
                message=Message(
                    message_id=str(uuid4()),
                    role=Role.user,
                    parts=[Part(TextPart(text=prompt))],
                )
            )
        )

        response = await self._client.send_message(request)
        logger.info(f"Response received from A2A agent: {response}")

        if response.root.result:
            if not response.root.result.parts:
                raise ValueError("No response parts found in the message.")
            part = response.root.result.parts[0].root
            if hasattr(part, "text"):
                return part.text
        elif response.root.error:
            raise Exception(f"A2A error: {response.error.message}")

        raise Exception("Unknown response type")