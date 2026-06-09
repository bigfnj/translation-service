import json
import hashlib
from pathlib import Path

import ollama

_MODEL = "qwen2.5:32b-instruct-q3_K_M"
_CACHE_PATH = Path("output/.translation_cache.json")

_SYSTEM_PROMPT = """\
You are a Mexican Spanish transcreation specialist for a student with autism who has a 2nd-grade education level. \
The student is from Mexico, cannot read or write, and learns entirely through spoken audio.

Your job is NOT to translate literally. Your job is to rewrite the content so it is:
- Clear and natural when spoken aloud in Mexican Spanish
- Understandable to a 2nd-grade student with no academic vocabulary
- Appropriate for a student with autism: concrete, literal, no figures of speech, no idioms

STRICT RULES — follow every one, no exceptions:
1. Language: Mexican Spanish (es_MX) only — not neutral Latin American, not Castilian
2. Register: tú throughout — informal, student-facing
3. Vocabulary ceiling: 2nd-grade level. Use the simplest possible word that preserves meaning.
   - "anfitrión" not "huésped" (too formal)
   - "lleva" not "escolta"
   - "personas" not "clientela"
4. Sentence structure: subject → verb → object. One idea per sentence.
5. Maximum sentence length: 10 words. Short is better than long.
6. NO subordinate clauses. NO "que" clauses. NO "cuando/si/aunque" structures.
7. NO comma-separated lists. Each item in the English bullets becomes its own sentence.
8. NO idioms, NO metaphors, NO figures of speech.
9. Repeat the key vocabulary term (the Spanish term) at least once inside the body sentences.
10. Concrete and literal only. Do not add information that was not in the original.

OUTPUT FORMAT — you must return valid JSON, nothing else:
{
  "term_es": "<the Spanish vocabulary term, 1-3 words>",
  "sentences_es": [
    "<sentence 1>",
    "<sentence 2>",
    "<sentence 3>"
  ]
}

EXAMPLE INPUT:
Term: Host
Bullets:
- A person who welcomes guests
- Takes reservations
- Greets customers and shows them to their tables

CORRECT OUTPUT:
{
  "term_es": "Anfitrión",
  "sentences_es": [
    "El anfitrión trabaja en el restaurante.",
    "El anfitrión saluda a las personas.",
    "El anfitrión los lleva a su mesa."
  ]
}

WRONG OUTPUT (do not do this):
{
  "term_es": "Anfitrión",
  "sentences_es": [
    "El anfitrión da la bienvenida a los huéspedes, toma las reservaciones y los guía a sus mesas."
  ]
}
Why wrong: one long sentence, lists read aloud, "huéspedes" is too formal.
"""


def _cache_key(slide: dict) -> str:
    content = json.dumps({
        "title": slide["title"],
        "bullets": slide.get("bullets", []),
        "paragraphs": slide.get("paragraphs", []),
    }, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text())
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2))


def _build_user_message(slide: dict) -> str:
    lines = [f"Term: {slide['title']}"]
    content_lines = slide.get("bullets") or slide.get("paragraphs") or []
    if content_lines:
        lines.append("Bullets:")
        for item in content_lines:
            lines.append(f"- {item}")
    return "\n".join(lines)


def translate_slide(slide: dict) -> dict:
    """
    Translate a single content slide using Qwen2.5 32B via Ollama.

    Returns a dict:
      {
        "term_es": str,
        "sentences_es": list[str],
      }

    Results are cached by content hash to avoid re-translating unchanged slides.
    """
    cache = _load_cache()
    key = _cache_key(slide)

    if key in cache:
        return cache[key]

    user_message = _build_user_message(slide)

    response = ollama.chat(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        format="json",
        options={
            "temperature": 0.2,
            # Offload 40 of 64 layers to GPU (~9.5 GB VRAM), rest run on CPU.
            # Slower than full-GPU but fits safely in WSL2 on a 24 GB card.
            "num_gpu": 40,
        },
    )

    raw = response["message"]["content"]
    result = json.loads(raw)

    # Normalise: ensure expected keys exist
    if "term_es" not in result or "sentences_es" not in result:
        raise ValueError(f"Unexpected translation output for slide '{slide['title']}': {raw}")

    cache[key] = result
    _save_cache(cache)

    return result


def is_cached(slide: dict) -> bool:
    """Return True if this slide's translation is already in the cache (content unchanged)."""
    return _cache_key(slide) in _load_cache()
