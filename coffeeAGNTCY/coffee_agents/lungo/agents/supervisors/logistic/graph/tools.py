# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

import logging
import re
<<<<<<< HEAD
from typing import Any, Union, Literal, Sequence
from uuid import uuid4
from pydantic import BaseModel


from a2a.types import (
    AgentCard,
    SendMessageRequest,
    MessageSendParams,
    Message,
    Part,
    TextPart,
    Role,
)
from langchain_core.tools import tool
from langchain_core.messages import AnyMessage, ToolMessage
from agntcy_app_sdk.protocols.a2a.protocol import A2AProtocol
from agents.supervisors.logistic.graph.shared import get_factory
from config.config import (
    DEFAULT_MESSAGE_TRANSPORT, 
    TRANSPORT_SERVER_ENDPOINT, 
    FARM_BROADCAST_TOPIC,
    GROUP_CHAT_TOPIC,
)

from agents.logistics.accountant.card import AGENT_CARD as accountant_agent_card
from agents.logistics.shipper.card import AGENT_CARD as shipper_agent_card
from agents.logistics.farm.card import AGENT_CARD as tatooine_agent_card
from agents.supervisors.auction.graph.models import (
    InventoryArgs,
    CreateOrderArgs,
)

from ioa_observe.sdk.decorators import tool as ioa_tool_decorator

logger = logging.getLogger("lungo.logistic.supervisor.tools")

def tools_or_next(tools_node: str, end_node: str = "__end__"):
  """
  Returns a conditional function for LangGraph to determine the next node 
  based on whether the last message contains tool calls.

  If the message includes tool calls, the workflow proceeds to the `tools_node`.
  If the message is a ToolMessage or has no tool calls, the workflow proceeds to `end_node`.

  Args:
    tools_node (str): The name of the node to route to if tool calls are detected.
    end_node (str, optional): The fallback node if no tool calls are found. Defaults to '__end__'.

  Returns:
    Callable: A function compatible with LangGraph conditional edge handling.
  """

  def custom_tools_condition_fn(
    state: Union[list[AnyMessage], dict[str, Any], BaseModel],
    messages_key: str = "messages",
  ) -> Literal[tools_node, end_node]: # type: ignore

    if isinstance(state, list):
      ai_message = state[-1]
    elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
      ai_message = messages[-1]
    elif messages := getattr(state, messages_key, []):
      ai_message = messages[-1]
    else:
      raise ValueError(f"No messages found in input state to tool_edge: {state}")
    
    if isinstance(ai_message, ToolMessage):
        logger.debug("Last message is a ToolMessage, returning end_node: %s", end_node)
        return end_node

    if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
      logger.debug("Last message has tool calls, returning tools_node: %s", tools_node)
      return tools_node
    
    logger.debug("Last message has no tool calls, returning end_node: %s", end_node)
    return end_node

  return custom_tools_condition_fn

def get_farm_card(farm: str) -> AgentCard | None:
    """
    Maps a farm name string to its corresponding AgentCard.

    Args:
        farm (str): The name of the farm (e.g., "Brazil", "Colombia", "Vietnam").

    Returns:
        AgentCard | None: The matching AgentCard if found, otherwise None.
    """
    farm = farm.strip().lower()
    if 'accountant' in farm.lower():
        return accountant_agent_card
    elif 'shipper' in farm.lower():
        return shipper_agent_card
    elif 'tatooine' in farm.lower():
        return tatooine_agent_card
    else:
        logger.error(f"Unknown farm name: {farm}. Expected one of 'accountant', or 'shipper', 'tatooine'.")
        return None


@tool(args_schema=CreateOrderArgs)
# @ioa_tool_decorator(name="create_order")
async def create_order(farm: str, quantity: int, price: float) -> str:
    """
    Sends a request to create a coffee order with a specific farm.

    Args:
        farm (str): The target farm for the order.
        quantity (int): Quantity of coffee to order.
        price (float): Proposed price per unit.

    Returns:
        str: Confirmation message or error string from the farm agent.
    """

    if DEFAULT_MESSAGE_TRANSPORT != "SLIM":
        raise ValueError("Currently only SLIM transport is supported for logistic agents.")

    farm = farm.strip().lower()

    logger.info(f"Creating order with price: {price}, quantity: {quantity}")
    if price <= 0 or quantity <= 0:
        return "Price and quantity must be greater than zero."
    
    if farm == "":
        return "No farm was provided, please provide a farm to create an order."

    # Shared factory & transport
    factory = get_factory()
    transport = factory.create_transport(
        DEFAULT_MESSAGE_TRANSPORT,
        endpoint=TRANSPORT_SERVER_ENDPOINT,
        name="default/default/logistic_graph"
    )

    client = await factory.create_client(
        "A2A",
        # Due to the limitation in SLIM. To create an A2A client, we use a topic with at least one listener,
        # which is the routable name of the Brazil agent.
        agent_topic=A2AProtocol.create_agent_topic(shipper_agent_card),
        transport=transport,
    )

    request = SendMessageRequest(
        id=str(uuid4()),
        params=MessageSendParams(
            message=Message(
                messageId=str(uuid4()),
                role=Role.user,
                parts=[Part(TextPart(text=f"Create an order with price {price} and quantity {quantity}. Status: RECEIVED_ORDER"))],
            ),
        )
    )

    recipients = [A2AProtocol.create_agent_topic(farm_card) for farm_card in [shipper_agent_card, tatooine_agent_card, accountant_agent_card ]] #, farm ]]
    logger.info(f"Broadcasting order creation to recipients: {recipients}")

    responses = await client.broadcast_message(request, broadcast_topic=GROUP_CHAT_TOPIC, recipients=recipients,
                                               end_message="DELIVERED", group_chat=True, timeout=60)

    logger.debug("Raw A2A responses: %s", responses)
    formatted_responses = _summarize_a2a_responses(responses)
    logger.info("Formatted responses: %s", formatted_responses)

    return formatted_responses

def _summarize_a2a_responses(responses: Sequence) -> str:
  """
  Build a concise status line from A2A SendMessageResponse objects.

  Rules:
  - Skip any message whose text contains 'idle' (case-insensitive).
  - Aggregate all non-'delivered' statuses per agent in order of appearance (comma separated).
  - Each 'delivered' status (case-insensitive exact match within the text) is emitted
    as its own segment even if the agent appeared earlier.
  - Preserve original chronological order for:
      * First appearance of each agent (for aggregated segment)
      * Final delivered events
  - Append '(final)' if any delivered status was seen.
  """
  agent_status_order: list[str] = []                 # Order of first non-final appearance per agent
  agent_status_map: dict[str, list[str]] = {}        # agent -> list of non-final statuses
  delivered_segments: list[str] = []                 # Collected "Agent: DELIVERED" segments in order
  delivered_seen = False

  for r in responses:
    try:
      msg = r.root.result  # Underlying Message
      name = (msg.metadata or {}).get("name", "Unknown")
      parts = msg.parts or []
      text = ""
      for p in parts:
        part_obj = getattr(p, "root", p)
        cand = getattr(part_obj, "text", "") or ""
        if cand:
          text = cand.strip()
          break
      if not text:
        continue
      if "idle" in text.lower():
        continue
      # Normalize status token (we keep full text, but detect delivered)
=======
from typing import Any, Sequence
from uuid import uuid4

from a2a.types import (
  Message,
  MessageSendParams,
  Part,
  Role,
  SendMessageRequest,
  TextPart,
)
from agntcy_app_sdk.protocols.a2a.protocol import A2AProtocol
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from agents.logistics.accountant.card import AGENT_CARD as ACCOUNTANT_CARD
from agents.logistics.farm.card import AGENT_CARD as TATOOINE_CARD
from agents.logistics.shipper.card import AGENT_CARD as SHIPPER_CARD
from agents.supervisors.logistic.graph.models import CreateOrderArgs
from agents.supervisors.logistic.graph.shared import get_factory
from config.config import (
  DEFAULT_MESSAGE_TRANSPORT,
  GROUP_CHAT_TOPIC,
  TRANSPORT_SERVER_ENDPOINT,
)
from common.logistic_states import LogisticStatus

logger = logging.getLogger("lungo.logistic.supervisor.tools")


def next_tools_or_end(state: dict[str, Any]) -> str:
  """
  Routing helper for LangGraph:
  - If the last AI message has tool calls -> go to tools node.
  - If the last message is a ToolMessage or has no tool calls -> end.
  Expects state['messages'] to be a non-empty list.
  """
  msg = state["messages"][-1]
  if isinstance(msg, ToolMessage):
    return "__end__"
  return "orders_tools" if getattr(msg, "tool_calls", None) else "__end__"


@tool(args_schema=CreateOrderArgs)
async def create_order(farm: str, quantity: int, price: float) -> str:
  """
  Broadcast a coffee order request to shipper, farm, and accountant agents via SLIM.

  Args:
      farm: Target farm name (currently informational; broadcast goes to fixed set).
      quantity: Units requested (must be > 0).
      price: Proposed unit price (must be > 0).

  Returns:
      Aggregated status summary string.
  """
  if DEFAULT_MESSAGE_TRANSPORT != "SLIM":
    raise ValueError("Only SLIM transport is supported for logistic agents.")

  farm = farm.strip().lower()
  logger.info("Creating order | farm=%s quantity=%s price=%s", farm or "<none>", quantity, price)

  if price <= 0 or quantity <= 0:
    return "Price and quantity must both be greater than zero."
  if not farm:
    return "No farm provided. Please specify a farm."

  factory = get_factory()
  transport = factory.create_transport(
    DEFAULT_MESSAGE_TRANSPORT,
    endpoint=TRANSPORT_SERVER_ENDPOINT,
    name="default/default/logistic_graph",
  )

  try:
    client = await factory.create_client(
      "A2A",
      # Use shipper routable name to satisfy SLIM client creation requirement.
      agent_topic=A2AProtocol.create_agent_topic(SHIPPER_CARD),
      transport=transport,
    )

    request = SendMessageRequest(
      id=str(uuid4()),
      params=MessageSendParams(
        message=Message(
          messageId=str(uuid4()),
          role=Role.user,
          parts=[
            Part(
              TextPart(
                # Note the status must be included to trigger the logistic flow
                text = f"Create an order with price {price} and quantity {quantity}. Status: {LogisticStatus.RECEIVED_ORDER.value}"
              )
            )
          ],
        )
      ),
    )
  except Exception as e:
    logger.error("Failed to create A2A client or message request: %s", e)

  recipients = [
    A2AProtocol.create_agent_topic(card)
    for card in (SHIPPER_CARD, TATOOINE_CARD, ACCOUNTANT_CARD)
  ]
  logger.info("Broadcasting order to recipients: %s", recipients)

  responses = await client.broadcast_message(
    request,
    broadcast_topic=GROUP_CHAT_TOPIC,
    recipients=recipients,
    end_message="DELIVERED",
    group_chat=True,
    timeout=60,
  )

  logger.debug("Raw group chat responses: %s", responses)
  formatted = _summarize_a2a_responses(responses)
  logger.info("Summarized order status: %s", formatted)
  return formatted


def _summarize_a2a_responses(responses: Sequence[Any]) -> str:
  """
  Summarize A2A SendMessageResponse objects into a single status line.

  Rules:
    - Skip messages containing 'idle' (case-insensitive).
    - Aggregate non-final statuses per agent in first-seen order.
    - Each 'delivered' (case-insensitive whole word) status becomes its own segment.
    - Preserve chronological order for first agent appearance and delivered segments.
    - Append '(final)' if any delivered status was observed.
  """
  agent_first_order: list[str] = []
  agent_statuses: dict[str, list[str]] = {}
  delivered_segments: list[str] = []
  delivered_seen = False

  for response in responses:
    try:
      msg = response.root.result  # Underlying message object
      name = (msg.metadata or {}).get("name", "Unknown")
      parts = msg.parts or []
      text = next(
        (
          getattr(getattr(p, "root", p), "text", "").strip()
          for p in parts
          if getattr(getattr(p, "root", p), "text", "").strip()
        ),
        "",
      )
      if not text or "idle" in text.lower():
        continue

>>>>>>> main
      if re.search(r"\bdelivered\b", text, re.IGNORECASE):
        delivered_seen = True
        delivered_segments.append(f"{name}: {text}")
        continue
<<<<<<< HEAD
      # Aggregate non-final statuses
      if name not in agent_status_map:
        agent_status_map[name] = []
        agent_status_order.append(name)
      # Avoid immediate duplicate of last appended status for that agent
      if not agent_status_map[name] or agent_status_map[name][-1] != text:
        agent_status_map[name].append(text)
    except Exception:
      continue

  if not agent_status_order and not delivered_segments:
    return "No non-idle status updates received."

  segments: list[str] = []

  # Build aggregated segments for non-final statuses
  for agent in agent_status_order:
    statuses = agent_status_map[agent]
    if statuses:
      segments.append(f"{agent}: {', '.join(statuses)}")

  # Append delivered segments in the chronological order they were captured
=======

      if name not in agent_statuses:
        agent_statuses[name] = []
        agent_first_order.append(name)

      if not agent_statuses[name] or agent_statuses[name][-1] != text:
        agent_statuses[name].append(text)
    except Exception:  # noqa: BLE001
      # Skip malformed entries silently
      continue

  if not agent_first_order and not delivered_segments:
    return "No non-idle status updates received."

  segments: list[str] = [
    f"{agent}: {', '.join(agent_statuses[agent])}"
    for agent in agent_first_order
    if agent_statuses[agent]
  ]
>>>>>>> main
  segments.extend(delivered_segments)

  summary = "Order status updates: " + " | ".join(segments)
  if delivered_seen:
    summary += " (final)"
  return summary
