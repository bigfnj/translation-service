import shutil
import time
from datetime import datetime
from pathlib import Path

from watchdog.events import FileSystemEventHandler, FileCreatedEvent
from watchdog.observers import Observer

from .pipeline import run as run_pipeline

_INTAKE_DIR = Path("intake")
_PROCESSED_DIR = _INTAKE_DIR / "processed"
_OUTPUT_DIR = Path("output")
_STABLE_CHECKS = 3      # consecutive size-equal reads before treating file as ready
_STABLE_INTERVAL = 1.0  # seconds between stability checks


def _wait_for_stable(path: Path) -> None:
    """Block until the file size stops changing (copy/write is complete)."""
    last_size = -1
    stable = 0
    while stable < _STABLE_CHECKS:
        size = path.stat().st_size
        if size == last_size:
            stable += 1
        else:
            stable = 0
            last_size = size
        time.sleep(_STABLE_INTERVAL)


def _output_dir_for(pdf_path: Path) -> str:
    stem = pdf_path.stem  # filename without extension
    date = datetime.now().strftime("%m-%d-%Y")
    return str(_OUTPUT_DIR / f"{stem} - {date}")


def _process(pdf_path: Path) -> None:
    print(f"\n[intake] Detected: {pdf_path.name}")
    print(f"[intake] Waiting for file to finish writing...")
    _wait_for_stable(pdf_path)

    output_dir = _output_dir_for(pdf_path)
    print(f"[intake] Output → {output_dir}")

    try:
        run_pipeline(pdf_path=str(pdf_path), output_dir=output_dir)
        dest = _PROCESSED_DIR / pdf_path.name
        shutil.move(str(pdf_path), str(dest))
        print(f"[intake] Moved to processed: {dest}")
    except Exception as e:
        print(f"[intake] ERROR processing {pdf_path.name}: {e}")
        print(f"[intake] File left in intake/ for retry.")


class _PDFHandler(FileSystemEventHandler):
    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and event.src_path.endswith(".pdf"):
            _process(Path(event.src_path))

    def on_moved(self, event):
        # Handles files moved/renamed into the intake folder
        if hasattr(event, "dest_path") and event.dest_path.endswith(".pdf"):
            _process(Path(event.dest_path))


def watch(intake_dir: str = str(_INTAKE_DIR)) -> None:
    """
    Start the intake folder watcher. Blocks until KeyboardInterrupt.
    Processes any PDFs already sitting in intake/ on startup,
    then watches for new arrivals.
    """
    intake = Path(intake_dir)
    intake.mkdir(parents=True, exist_ok=True)
    _PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Process anything already in the folder (e.g. dropped while watcher was off)
    existing = list(intake.glob("*.pdf"))
    if existing:
        print(f"[intake] Found {len(existing)} PDF(s) already in intake/ — processing now.")
        for pdf in existing:
            _process(pdf)

    observer = Observer()
    observer.schedule(_PDFHandler(), str(intake), recursive=False)
    observer.start()

    print(f"\n[intake] Watching {intake.resolve()} for new PDFs...")
    print(f"[intake] Press Ctrl+C to stop.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[intake] Watcher stopped.")

    observer.join()
