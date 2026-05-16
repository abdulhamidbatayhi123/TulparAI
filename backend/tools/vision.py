"""Vision tool — analyze images via NVIDIA-hosted VLM.

Use cases (described in the tool schema so the Reasoner knows when to call):
  - Meal photo  → identify foods + estimate portions  → orchestrator pipes
                  the food names into get_food_macros() per item
  - Injury photo → describe location + severity for triage suggestion
  - Training/form photo → posture + technique observations
  - Body composition photo → general physique observations
                  (NOT diagnostic — defer to professional)

Default model: nvidia/llama-3.2-90b-vision-instruct
  - Tier 1 vision-language model
  - Multilingual including Turkish

Lighter fallback: nvidia/nemotron-nano-12b-v2-vl (faster, smaller, fewer params)

We pass images either as data URLs (data:image/png;base64,...) or as plain
public URLs. Frontend sends base64; we wrap to a data URL.
"""
from __future__ import annotations

import base64
from openai import OpenAI

from backend.config import settings

# Lazy singleton — created on first call so importing this file is cheap
_client: OpenAI | None = None

# Try the big VLM first; if it 404s in the catalog at runtime, fall back
PRIMARY_VLM = "meta/llama-3.2-90b-vision-instruct"
FALLBACK_VLM = "nvidia/nemotron-nano-12b-v2-vl"


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=settings.nvidia_api_key,
            base_url=settings.nvidia_base_url,
        )
    return _client


def _to_data_url(image_input: str) -> str:
    """Accept either a `data:image/...;base64,...` URL, a raw base64 string,
    or an http(s) URL. Always return something the OpenAI image-content shape
    will accept."""
    if not image_input:
        return ""
    if image_input.startswith(("data:", "http://", "https://")):
        return image_input
    # Assume raw base64 of a jpeg/png — default to jpeg, browsers send JPEG most often
    return f"data:image/jpeg;base64,{image_input}"


def analyze(image: str, prompt: str = "Describe this image.", language: str = "tr") -> dict:
    """Call a VLM on the image with the given user prompt.

    Args:
      image:    data URL OR raw base64 OR http(s) URL
      prompt:   what to ask the VLM (e.g. "What foods are in this meal, and
                roughly how many grams of each?")
      language: response language ("tr" / "en")

    Returns:
      { "description": str, "model": str, "error": str|None }

    The Reasoner is expected to feed `description` back into its context and
    call subsequent tools (e.g. get_food_macros) per food identified.
    """
    if not image:
        return {"description": "", "error": "no image provided", "model": None}

    image_url = _to_data_url(image)
    lang_directive = (
        "Respond in Turkish."
        if language == "tr"
        else "Respond in English."
    )

    system_msg = (
        "You are a vision specialist for a sport adviser. Be CONCISE and FACTUAL. "
        "If you see food, list each item with an estimated weight in grams. "
        "If you see an injury/swelling/bruise, describe location and severity but say "
        "'medical professional should evaluate'. "
        "If you see a training pose, describe posture + visible technique cues. "
        "Never diagnose. " + lang_directive
    )

    client = _get_client()

    for model in (PRIMARY_VLM, FALLBACK_VLM):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
                temperature=0.2,
                max_tokens=800,
            )
            msg = resp.choices[0].message
            text = (msg.content or "") or (getattr(msg, "reasoning_content", "") or "")
            return {
                "description": text.strip(),
                "model": model,
                "error": None,
            }
        except Exception as e:
            # Try the next model on any error (e.g. model not in catalog, rate limit)
            last_error = f"{type(e).__name__}: {e}"

    return {"description": "", "error": last_error, "model": None}


def encode_file_to_base64(path: str) -> str:
    """Convenience helper for tests / CLI — read a file and return base64 string."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")
