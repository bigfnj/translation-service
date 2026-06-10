import re
from pathlib import Path

import fitz  # PyMuPDF


def _slug(title: str) -> str:
    s = title.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")[:30]


def render_slide_images(pdf_path: str, slides: list[dict], output_dir: str) -> dict[int, dict]:
    """
    Render each content slide page to a full-size JPEG and a thumbnail.

    Returns {slide_number: {"image": rel_path, "thumb": rel_path}}
    where paths are relative to output_dir.

    Idempotent: skips pages whose images already exist.
    """
    out = Path(output_dir)
    img_dir = out / "images"
    img_dir.mkdir(parents=True, exist_ok=True)

    result: dict[int, dict] = {}
    doc = fitz.open(str(pdf_path))

    for slide in slides:
        page_idx = slide["slide_number"] - 1  # fitz is 0-indexed
        if page_idx < 0 or page_idx >= len(doc):
            continue

        stem = f"slide_{slide['slide_number']:02d}_{_slug(slide['title'])}"
        full_path  = img_dir / f"{stem}.jpg"
        thumb_path = img_dir / f"{stem}_thumb.jpg"

        need_full  = not full_path.exists()
        need_thumb = not thumb_path.exists()

        if need_full or need_thumb:
            page = doc[page_idx]
            if need_full:
                page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)).save(str(full_path))
            if need_thumb:
                page.get_pixmap(matrix=fitz.Matrix(0.22, 0.22)).save(str(thumb_path))

        result[slide["slide_number"]] = {
            "image": f"images/{stem}.jpg",
            "thumb": f"images/{stem}_thumb.jpg",
        }

    doc.close()
    return result
