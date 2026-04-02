"""
Example CrewAI multi-agent file for a webhook-based Human-in-the-Loop flow.

What this file shows:
1) Two agents and two tasks defined with CrewAI classes.
2) A sample kickoff call that sends your webhook URLs to a CrewAI deployment.
3) The second task is marked as requiring human review conceptually.

Important note:
Webhook-based HITL typically applies when you run a deployed CrewAI execution
through the platform/runtime API. The local OSS Crew class below illustrates
agent/task design, while the `kickoff_remote_execution` function shows how you
start the real webhook-enabled run.
"""

from __future__ import annotations

import os
from typing import Any, Dict

import requests
from crewai import Agent, Crew, Process, Task

CREWAI_BASE_URL = os.getenv("CREWAI_BASE_URL", "https://your-crewai-deployment-url")
CREWAI_API_TOKEN = os.getenv("CREWAI_API_TOKEN", "YOUR_CREWAI_API_TOKEN")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://your-public-domain.example.com")
HITL_WEBHOOK_BEARER = os.getenv("HITL_WEBHOOK_BEARER", "my-webhook-secret-token")


def auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {CREWAI_API_TOKEN}",
        "Content-Type": "application/json",
    }


# ----------------------------
# Agents
# ----------------------------
research_agent = Agent(
    role="Purchase Request Researcher",
    goal="Collect the facts required for a purchase-approval decision.",
    backstory=(
        "You gather vendor details, cost, business purpose, risks, and a short recommendation."
    ),
    verbose=True,
)

approval_agent = Agent(
    role="Approval Pack Writer",
    goal="Prepare a clean approval pack for a human reviewer.",
    backstory=(
        "You convert the researcher findings into a concise pack that a manager can approve or reject."
    ),
    verbose=True,
)


# ----------------------------
# Tasks
# ----------------------------
collect_purchase_context = Task(
    description=(
        "Given a purchase request, summarize the requester, amount, vendor, purpose, urgency, "
        "and any known risks. Output a short JSON-style structured summary."
    ),
    expected_output=(
        "A structured summary including amount, vendor, purpose, urgency, risk_notes, and recommendation."
    ),
    agent=research_agent,
)

prepare_human_review_pack = Task(
    description=(
        "Turn the structured summary into a manager-friendly review pack. Keep it concise and clear. "
        "This task is intended to pause for human approval in the deployed runtime."
    ),
    expected_output=(
        "A final approval pack containing what is being requested, why, the recommendation, and review notes."
    ),
    agent=approval_agent,
)

crew = Crew(
    agents=[research_agent, approval_agent],
    tasks=[collect_purchase_context, prepare_human_review_pack],
    process=Process.sequential,
    verbose=True,
)


def kickoff_local_demo() -> Any:
    """
    Local demo of the logical sequence only.
    This does not itself provide webhook HITL.
    """
    inputs = {
        "purchase_request": {
            "requester": "Nora",
            "vendor": "Acme Analytics",
            "amount_usd": 18000,
            "purpose": "Annual BI license renewal",
            "urgency": "high",
        }
    }
    return crew.kickoff(inputs=inputs)


def kickoff_remote_execution(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Start the deployed CrewAI execution with webhook-based HITL enabled.

    Your CrewAI deployment/workflow should contain a human-review step.
    When that step is reached, CrewAI will call the backend webhook:
        POST {PUBLIC_BASE_URL}/webhooks/crewai-hitl

    Your backend stores the pending item and later resumes execution after
    the user clicks Approve/Reject in your UI.
    """
    url = f"{CREWAI_BASE_URL.rstrip('/')}/kickoff"

    payload = {
        "inputs": inputs,
        "humanInputWebhook": {
            "url": f"{PUBLIC_BASE_URL.rstrip('/')}/webhooks/crewai-hitl",
            "authentication": {
                "strategy": "bearer",
                "token": HITL_WEBHOOK_BEARER,
            },
        },
        "taskWebhookUrl": f"{PUBLIC_BASE_URL.rstrip('/')}/webhooks/task",
        "stepWebhookUrl": f"{PUBLIC_BASE_URL.rstrip('/')}/webhooks/step",
        "crewWebhookUrl": f"{PUBLIC_BASE_URL.rstrip('/')}/webhooks/crew",
    }

    response = requests.post(url, headers=auth_headers(), json=payload, timeout=60)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    demo_inputs = {
        "purchase_request_id": "PR-1001",
        "requester": "Nora",
        "vendor": "Acme Analytics",
        "amount_usd": 18000,
        "currency": "USD",
        "purpose": "Annual BI license renewal",
        "urgency": "high",
        "reviewer_user_id": "manager-01",
        "reviewer_email": "manager@example.com",
    }

    # Uncomment the next line if you only want a local crew logic demo.
    # print(kickoff_local_demo())

    # Use this line for the deployed runtime that supports webhook-based HITL.
    print(kickoff_remote_execution(demo_inputs))
