# Copyright AGNTCY Contributors (https://github.com/agntcy)
# SPDX-License-Identifier: Apache-2.0

from a2a.types import (
    AgentCapabilities, 
    AgentCard,
    AgentSkill)

AGENT_SKILL = AgentSkill(
    id="get_accounting_status",
    name="Get Accounting Status",
<<<<<<< HEAD
    description="Returns the accounting status of coffee beans from the farms.",
    tags=["coffee", "accounting"],
    examples=[
        "What is the current accounting status of my coffee order?",
        "How much coffee does the Brazil farm produce?",
        "What is the yield of the Brazil coffee farm in pounds?",
        "How many pounds of coffee does the Brazil farm produce?",
    ]
)   
=======
    description="Returns the accounting / payment status of coffee bean orders.",
    tags=["coffee", "accounting", "payments"],
    examples=[
        "Has the order moved from CUSTOMS_CLEARANCE to PAYMENT_COMPLETE yet?",
        "Confirm payment completion for the Colombia shipment.",
        "Did the Brazil order clear CUSTOMS_CLEARANCE and get marked PAYMENT_COMPLETE?",
        "Is any payment still pending after CUSTOMS_CLEARANCE?",
        "Mark the 50 lb Colombia order as PAYMENT_COMPLETE if customs is cleared.",
    ]
)
>>>>>>> main

AGENT_CARD = AgentCard(
    name='Accountant agent',
    id='accountant-agent',
<<<<<<< HEAD
    description='An AI agent that ships coffee beans and sends account updates.',
=======
    description='An AI agent that confirms the payment.',
>>>>>>> main
    url='',
    version='1.0.0',
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[AGENT_SKILL],
    supportsAuthenticatedExtendedCard=False,
)