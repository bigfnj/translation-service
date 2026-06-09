# Translation Service — Build Plan

## Learner Context (read this first)
- Student: high school age, autism, 2nd-grade education level, from Mexico
- Cannot read or write — audio is the **primary** and only delivery mechanism
- Mexican Spanish dialect only (`es_MX`)
- Register: `tú` throughout, short declarative sentences, no idioms, no lists read aloud
- Voice must be consistent all year — same reference audio clips every run
- Audio pattern per slide: English term → English sentences → 1.5s pause → Spanish term → Spanish sentences

## Decisions Log
- Translation engine: **Claude API** (anthropic SDK)
- TTS engine: **Coqui XTTS v2** (local, RTX 4090 24GB)
- Audio format: **One combined .wav per content slide** (English + Spanish, pause between)
- Input: **PDF for now** — Google Slides API is Backlog Item #1
- Dependency manager: **uv** with `pyproject.toml`
- Slide classification: slides with no bullet points = header → skip

---

## Phase 0 — Environment Setup

> Run once before anything else. All ML packages go inside the project venv via `uv` — never system-wide.

- [x] `uv init` inside `/home/bigfnj/projects/translation-service` (creates `pyproject.toml`)
- [x] Install PyTorch with CUDA 12.4 support (must come before Coqui TTS):
  ```
  uv add torch torchaudio --index https://download.pytorch.org/whl/cu124
  ```
- [x] Install remaining project dependencies:
  ```
  uv add TTS anthropic pdfplumber python-dotenv
  ```
  > Note: Coqui TTS requires Python < 3.12 — project pinned to Python 3.11 via `uv python pin 3.11`
- [x] Verify CUDA is visible to PyTorch → `True` (RTX 4090 confirmed)
- [x] Verify Coqui TTS imports cleanly → `TTS OK`
- [x] Verify Anthropic SDK imports cleanly → `Anthropic SDK OK, version: 0.107.1`
- [ ] Note: XTTS v2 model weights (~1.8GB) download automatically on first audio generation run — not during install

> **No local LLM needed.** Translation uses Claude API. XTTS v2 is a speech synthesis model, not an LLM.

---

## Phase 1 — Project Scaffold

- [x] Create `pyproject.toml` with uv (`uv init`)
- [x] Create `src/translation_service/` package structure
- [x] Create `voices/` directory with placeholder README for reference audio clips
- [x] Create `output/` directory with `.gitkeep`
- [x] Create `.env.example` with `ANTHROPIC_API_KEY=` placeholder
- [x] Create `CLAUDE.md` documenting learner profile, linguistic rules, voice settings, and pipeline overview
- [x] Initialize git repo and first commit

---

## Phase 2 — PDF Parser

- [x] Add `pdfplumber` or `pypdf` as dependency via `uv add`
- [x] Implement `src/translation_service/pdf_reader.py`
  - [x] Extract text content per page (each page = one slide)
  - [x] Return structured list: `[{slide_number, title, bullets, paragraphs, raw_text}]`
  - [x] Handles both Week 1 bullet format and Weeks 2–4 paragraph format
- [x] Implement `src/translation_service/classifier.py`
  - [x] Rule: title-only or empty = header → `type: "header"` or `"empty"`
  - [x] Rule: any content after title = content → `type: "content"`
  - [x] Deduplicates exact-match repeated pages → `type: "duplicate"` (Line Cook, Kitchen)
  - [x] Tracks current week number and assigns to each content slide
- [x] Write test: ran classifier against full PDF → 38 content, 22 headers, 26 empty, 2 duplicates — verified correct

---

## Phase 3 — Translation Engine

- [x] Add `ollama` Python package as dependency via `uv add` (switched from Anthropic API to local Qwen2.5 32B)
- [x] Implement `src/translation_service/translator.py`
  - [x] System prompt encodes all linguistic rules:
    - Mexican Spanish (`es_MX`)
    - 2nd-grade vocabulary ceiling
    - Short declarative sentences (subject → verb → object)
    - `tú` register
    - No subordinate clauses, no idioms, no comma-separated lists read aloud
    - Repeat the key term at least once in the body sentences
    - Concrete, literal language only
  - [x] Input: English term + bullet points
  - [x] Output: structured dict `{term_es, sentences_es: []}`
  - [x] Cache translations to `output/.translation_cache.json` — never re-translate a slide that hasn't changed
- [x] Implement `src/translation_service/script_builder.py`
  - [x] Input: English content + translated Spanish content
  - [x] Output: ordered list of audio segments with language tags
  - [x] Pause segment = 1.5 second silence injected between English and Spanish blocks
- [x] Write test: translated Host + 4 other slides across all 4 weeks — quality verified

> **Decision:** Switched from Claude API to local Qwen2.5 32B (Q3_K_M) via Ollama. No API cost.
> Model runs with `num_gpu=40` (40/64 layers on GPU ~9.5 GB VRAM, rest on CPU) to avoid WSL2 VRAM contention.
> Known limitation: PDF line-wraps create orphaned fragments in English script — fix in Phase 7.

---

## Phase 4 — TTS Engine (Coqui XTTS v2)

- [x] `TTS` (coqui-tts) already installed as dependency
- [x] Reference audio clips provided:
  - [x] `voices/english_reference.wav` — 11.6s, 48kHz stereo
  - [x] `voices/spanish_reference.wav` — 7.9s, 48kHz stereo
- [x] Implement `src/translation_service/tts_engine.py`
  - [x] Load XTTS v2 model once at startup (model stays in VRAM for batch runs)
  - [x] `synthesize_segment(text, lang)` → synthesizes using language-appropriate reference clip
  - [x] `generate_silence(duration_seconds)` → returns silence audio array
  - [x] `combine_and_save(segments, output_path)` → concatenates all segments, saves as `.wav`
  - [x] `generate_slide_audio(script_segments, output_path)` → full slide in one call
- [x] Write test: generated `output/test/slide_04_host.wav` — all 11 segments (EN + pause + ES)

> **Fixes applied:**
> - `transformers` pinned to `==4.44.2` — v5.x requires PyTorch 2.7+ (`float8_e8m0fnu`)
> - `torch.load` monkey-patched during model load to use `weights_only=False` — PyTorch 2.6 tightened defaults, breaking Coqui's checkpoint loading (safe: XTTS v2 is a trusted public model)
> - `COQUI_TOS_AGREED=1` env var required to skip interactive license prompt

---

## Phase 5 — Pipeline Orchestrator

- [ ] Implement `src/translation_service/pipeline.py`
  - [ ] Accept input: path to PDF
  - [ ] For each slide:
    1. Classify (header → skip with log, content → process)
    2. Translate (check cache first)
    3. Build script
    4. Generate audio
    5. Save to `output/<week_folder>/slide_<NN>_<term_slug>.wav`
  - [ ] Print progress: `[3/12] Generating audio: slide_03_host.wav`
  - [ ] Print summary at end: total slides processed, skipped, audio files written
- [ ] Implement `cli.py` entry point
  - [ ] `python cli.py --pdf "path/to/slides.pdf" --output output/`
  - [ ] `--dry-run` flag: translate and print scripts without generating audio (useful for reviewing translations before committing TTS time)

---

## Phase 6 — First Full Run

- [ ] Run pipeline against `Food Service Industry - Behind the Scenes.pdf`
- [ ] Review all translation scripts with `--dry-run` before generating audio
- [ ] Correct any translation issues (update system prompt if needed, re-run)
- [ ] Generate all audio files
- [ ] Listen to at least one slide per week, verify:
  - [ ] English is clear and natural
  - [ ] Spanish is natural Mexican Spanish (not literal translation)
  - [ ] Pause between English and Spanish is correct length
  - [ ] Voice is consistent across all files
- [ ] Organize output files, verify naming convention is clean

---

## Phase 7 — Polish & Hardening

- [ ] Add `--week` filter flag: `python cli.py --pdf slides.pdf --week 2` (process only one week)
- [ ] Add `--slide` filter flag for single-slide debugging
- [ ] Graceful error handling: if TTS fails on one slide, log and continue (don't abort whole run)
- [ ] Add `CLAUDE.md` content for the translation system prompt history (track prompt versions)
- [ ] Final test: run a fresh PDF through the complete pipeline start to finish

---

## Backlog (Future Enhancements)

- [ ] **#1 — Google Slides API integration**: replace PDF input with direct Google Slides URL. One-time OAuth setup via Google Cloud Console. Teacher pastes the Slides URL, pipeline reads live deck. No PDF export step needed.
- [ ] **#2 — Slide change detection**: compare current deck against last run, only re-process slides that changed. Saves time when teacher adds a few slides mid-year.
- [ ] **#3 — Voice warmth upgrade**: evaluate ElevenLabs voice clone of a known speaker vs. XTTS v2 reference. Run quality comparison before committing.
- [ ] **#4 — Web UI**: simple local Flask or Gradio interface so teacher can upload PDF and download audio ZIP without touching the terminal.
- [ ] **#5 — Multi-student profiles**: store separate voice/register/complexity settings per student if other students are added to the program.

---

## Current Status
> **Phase 5 — Pipeline Orchestrator** (not started)
