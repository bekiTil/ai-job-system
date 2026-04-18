import time
import logging
from .ai_client import call_claude, client

logger = logging.getLogger(__name__)

SYSTEM_PROMPTS = {
    "summarize": "You are a summarization assistant. Provide a clear, concise summary of the text the user provides. Keep it to 2-3 sentences.",
    "classify": "You are a document classifier. Classify the provided text into a category (e.g., technical, business, personal, news, academic). Also note the sentiment (positive, negative, neutral) and key topics. Be concise.",
    "extract": "You are an entity extraction assistant. Extract all named entities (people, organizations, locations, dates, monetary values) from the provided text. List each entity with its type.",
}


def process_task(task_type: str, input_text: str) -> str:
    if client:
        logger.info(f"Processing with Claude AI: {task_type}")
        system_prompt = SYSTEM_PROMPTS.get(task_type)
        if not system_prompt:
            return f"Unknown task type: {task_type}"
        try:
            return call_claude(system_prompt, input_text)
        except Exception as e:
            logger.error(f"AI processing failed: {e}")
            raise
    else:
        logger.info(f"No API key — using simulation: {task_type}")
        time.sleep(3)
        word_count = len(input_text.split())
        if task_type == "summarize":
            return f"[Simulated Summary] Your text has {word_count} words. The main topics appear to be about the content you submitted."
        elif task_type == "classify":
            return f"[Simulated Classification] Document type: general text. Word count: {word_count}. Sentiment: neutral."
        elif task_type == "extract":
            return f"[Simulated Extraction] Entities found: none (simulated). Word count: {word_count}."
        else:
            return f"Unknown task type: {task_type}"