import re
import pdfplumber

# All bullet-like prefixes recognised as list items
_BULLET_RE = re.compile(r"^(?:[●•\-\*]|\d+[.\)]\s|\([a-zA-Z]\)\s*)\s*")


def read_slides(pdf_path: str) -> list[dict]:
    """
    Extract all slides from a PDF. Each page = one slide.

    Returns a list of dicts:
      {
        "slide_number": int,       # 1-based page number
        "title": str,              # first non-empty line
        "bullets": list[str],      # list-item lines, prefix stripped
        "paragraphs": list[str],   # non-list lines after the title, wrap-joined
        "raw_text": str,           # original extracted text
      }
    """
    slides = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            raw = page.extract_text() or ""
            slides.append(_parse_page(i, raw))
    return slides


def _is_bullet(line: str) -> bool:
    return bool(_BULLET_RE.match(line))


def _strip_bullet(line: str) -> str:
    return _BULLET_RE.sub("", line).strip()


def _join_wrapped(lines: list[str]) -> list[str]:
    """
    Join consecutive lines where the previous line does not end a sentence.
    pdfplumber wraps long slide text mid-sentence, producing fragments like:
      "Needs are things you must have to be safe, healthy,"
      "and okay."
    These become a single line after joining.
    """
    if not lines:
        return lines
    out = []
    buf = lines[0]
    for line in lines[1:]:
        # Continue buffering if the current buffer doesn't end a sentence
        if not buf.rstrip().endswith((".", "!", "?", ":")):
            buf = buf.rstrip() + " " + line.lstrip()
        else:
            out.append(buf)
            buf = line
    out.append(buf)
    return out


def _parse_page(slide_number: int, raw_text: str) -> dict:
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    if not lines:
        return {
            "slide_number": slide_number,
            "title": "",
            "bullets": [],
            "paragraphs": [],
            "raw_text": raw_text,
        }

    title = lines[0]
    raw_bullets = []
    raw_paragraphs = []

    for line in lines[1:]:
        if _is_bullet(line):
            raw_bullets.append(_strip_bullet(line))
        else:
            raw_paragraphs.append(line)

    # Join wrapped lines in both buckets
    bullets = _join_wrapped(raw_bullets)
    paragraphs = _join_wrapped(raw_paragraphs)

    return {
        "slide_number": slide_number,
        "title": title,
        "bullets": bullets,
        "paragraphs": paragraphs,
        "raw_text": raw_text,
    }
