"""Bilingual system prompts. Choose `prompts_tr` or `prompts_en` based on athlete.language."""
from backend.i18n import prompts_tr, prompts_en


def get_prompts(language: str):
    """Return the prompt module for the given language. Default to TR."""
    return prompts_en if language == "en" else prompts_tr
