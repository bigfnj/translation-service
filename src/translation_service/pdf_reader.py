import pdfplumber


def read_slides(pdf_path: str) -> list[dict]:
    """
    Extract all slides from a PDF. Each page = one slide.

    Returns a list of dicts:
      {
        "slide_number": int,       # 1-based page number
        "title": str,              # first non-empty line
        "bullets": list[str],      # lines that started with ●, stripped
        "paragraphs": list[str],   # non-bullet lines after the title
        "raw_text": str,           # original extracted text
      }
    """
    slides = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, 1):
            raw = page.extract_text() or ""
            slide = _parse_page(i, raw)
            slides.append(slide)

    return slides


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
    bullets = []
    paragraphs = []

    for line in lines[1:]:
        if line.startswith("●"):
            bullets.append(line.lstrip("●").strip())
        else:
            paragraphs.append(line)

    return {
        "slide_number": slide_number,
        "title": title,
        "bullets": bullets,
        "paragraphs": paragraphs,
        "raw_text": raw_text,
    }
