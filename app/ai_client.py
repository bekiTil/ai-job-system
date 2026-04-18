import os
import logging
from anthropic import Anthropic

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

client = Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def call_claude(system_prompt: str, user_message: str) -> str:
    if not client:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    logger.info("Calling Claude API")

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_message}
        ],
    )

    result = response.content[0].text
    logger.info(f"Claude responded with {len(result)} characters")
    return result