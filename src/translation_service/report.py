from pathlib import Path
from datetime import datetime


def write_report(output_dir: str, pdf_name: str, stats: dict, duration_seconds: float) -> None:
    """
    Write a human-readable _report.txt into the output folder.

    stats keys: generated, total, skipped, errors [(slide_num, title, msg)]
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    mins, secs = divmod(int(duration_seconds), 60)
    duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"

    lines = [
        "Translation Service — Processing Report",
        "=" * 40,
        f"Deck:      {pdf_name}",
        f"Date:      {datetime.now().strftime('%m/%d/%Y %H:%M')}",
        f"Duration:  {duration_str}",
        "",
        f"Generated: {stats['generated']} / {stats['total']} content slides",
        f"Skipped:   {stats['skipped_headers']} headers, "
        f"{stats['skipped_empty']} empty, "
        f"{stats['skipped_dupes']} duplicates",
    ]

    if stats.get("cached"):
        lines.append(f"Cached:    {stats['cached']} slides (audio already up to date)")

    lines.append("")
    if stats.get("errors"):
        lines.append(f"Errors ({len(stats['errors'])}):")
        for num, title, msg in stats["errors"]:
            lines.append(f"  slide {num} ({title}): {msg}")
    else:
        lines.append("Errors:    None")

    lines += ["", f"Output:    {out.resolve()}"]

    report_path = out / "_report.txt"
    report_path.write_text("\n".join(lines) + "\n")
    print(f"  Report → {report_path}")


def write_html_player(output_dir: str, pdf_name: str, slides: list[dict]) -> None:
    """
    Write an index.html to output_dir with an audio player for every generated slide,
    organised by week. Paths are relative so the file works from any location.

    slides: list of dicts with keys: week, slide_number, title, wav_path (relative to output_dir)
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    by_week: dict[int, list] = {}
    for s in slides:
        by_week.setdefault(s["week"], []).append(s)

    week_html = ""
    for week_num in sorted(by_week):
        week_html += f'  <h2>Week {week_num}</h2>\n'
        for s in by_week[week_num]:
            week_html += (
                f'  <div class="slide">\n'
                f'    <div class="slide-title">Slide {s["slide_number"]} — {_esc(s["title"])}</div>\n'
                f'    <audio controls src="{s["wav_path"]}"></audio>\n'
                f'  </div>\n'
            )

    date_str = datetime.now().strftime("%m/%d/%Y")
    total = sum(len(v) for v in by_week.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(pdf_name)}</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 820px; margin: 40px auto; padding: 0 16px; background: #f4f4f4; color: #333; }}
  h1 {{ font-size: 1.4em; margin-bottom: 4px; }}
  .meta {{ color: #888; font-size: 0.9em; margin-bottom: 24px; }}
  h2 {{ font-size: 1.1em; color: #555; border-bottom: 2px solid #ddd; padding-bottom: 6px; margin-top: 28px; }}
  .slide {{ background: white; border-radius: 8px; padding: 14px 16px; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .slide-title {{ font-weight: bold; margin-bottom: 8px; font-size: 0.95em; }}
  audio {{ width: 100%; }}
</style>
</head>
<body>
<h1>{_esc(pdf_name)}</h1>
<p class="meta">Generated {date_str} &nbsp;·&nbsp; {total} slides</p>
{week_html}
</body>
</html>"""

    player_path = out / "index.html"
    player_path.write_text(html)
    print(f"  Player  → {player_path}")


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
