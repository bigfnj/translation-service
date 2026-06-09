import re
from pathlib import Path

from .pdf_reader import read_slides
from .classifier import classify_slides
from .translator import translate_slide
from .script_builder import build_script, format_script_preview
from .tts_engine import generate_slide_audio


def _term_slug(title: str) -> str:
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    return slug.strip("_")[:30]


def run(pdf_path: str, output_dir: str = "output", dry_run: bool = False,
        week_filter: int = None, slide_filter: int = None) -> None:
    """
    Full pipeline: read PDF → classify → translate → build script → generate audio.

    dry_run=True: translate and print scripts, skip audio generation.
    week_filter: process only slides from the given week number.
    slide_filter: process only the slide at the given slide_number.
    """
    print(f"Reading PDF: {pdf_path}")
    slides = read_slides(pdf_path)
    classified = classify_slides(slides)

    content = [s for s in classified if s["type"] == "content"]
    skipped = [s for s in classified if s["type"] in ("header", "empty", "duplicate")]

    print(f"  {len(content)} content slides, {len(skipped)} skipped "
          f"({sum(1 for s in classified if s['type']=='header')} headers, "
          f"{sum(1 for s in classified if s['type']=='empty')} empty, "
          f"{sum(1 for s in classified if s['type']=='duplicate')} duplicates)")

    # Apply filters
    if week_filter is not None:
        content = [s for s in content if s["week"] == week_filter]
        print(f"  Filtered to week {week_filter}: {len(content)} slides")

    if slide_filter is not None:
        content = [s for s in content if s["slide_number"] == slide_filter]
        print(f"  Filtered to slide {slide_filter}: {len(content)} slides")

    if not content:
        print("No content slides found — PDF may be image-only or not a vocabulary deck.")
        return 0

    total = len(content)
    generated = 0
    errors = []

    for i, slide in enumerate(content, 1):
        label = f"[{i}/{total}] slide_{slide['slide_number']:02d}_{_term_slug(slide['title'])}"

        try:
            translation = translate_slide(slide)
            script = build_script(slide, translation)

            if dry_run:
                print(format_script_preview(slide, script))
                print()
                continue

            week_dir = Path(output_dir) / f"week{slide['week']}"
            out_file = week_dir / f"slide_{slide['slide_number']:02d}_{_term_slug(slide['title'])}.wav"

            print(f"{label}")
            generate_slide_audio(script, str(out_file))
            generated += 1

        except Exception as e:
            print(f"{label} ERROR: {e}")
            errors.append((slide["slide_number"], slide["title"], str(e)))

    if dry_run:
        print(f"Dry run complete — {total} scripts printed, no audio generated.")
        return total

    print()
    print(f"Done. {generated}/{total} audio files written to {output_dir}/")
    if errors:
        print(f"  {len(errors)} error(s):")
        for num, title, msg in errors:
            print(f"    slide {num} ({title}): {msg}")
    return generated
