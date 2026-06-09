# Translation Service — Claude Project Context

## What this project does

Converts educational slide decks (PDF, eventually Google Slides) into per-slide audio files
in both English and Mexican Spanish. Built for a specific learner with a specific profile.
Read the learner context before touching anything.

## Learner Profile (non-negotiable)

- High school age, autism, 2nd-grade education level
- From Mexico — Mexican Spanish (`es_MX`) only, not neutral Latin American, not Castilian
- Cannot read or write — audio is the sole delivery mechanism
- Voice consistency matters significantly; the same reference clips must be used all year
- Audio is played by the teacher while the student views the slide visually

## Audio Format Per Slide

Each content slide produces one `.wav` file structured as:

```
[English term — spoken clearly]
[English bullet 1 rewritten as a short sentence]
[English bullet 2 rewritten as a short sentence]
...
[1.5 second silence]
[Spanish term — spoken clearly]
[Spanish sentence 1]
[Spanish sentence 2]
...
```

Header slides (no bullets, short title only) are skipped entirely — no audio generated.

## Translation Rules (enforce in every Claude API call)

Target: Mexican Spanish, `es_MX`
Register: `tú` throughout (informal, student-facing)
Vocabulary ceiling: 2nd-grade level — use the simplest possible word that preserves meaning
Sentence structure: short declarative sentences, subject → verb → object
Maximum sentence length: ~10 words
No subordinate clauses, no idioms, no figures of speech, no comma-separated lists read aloud
Repeat the key vocabulary term at least once within the body sentences
Concrete and literal only — this learner does not process abstract language

### Example (correct)

English input:
  Term: Host
  Bullets: A person who welcomes guests / Takes reservations / Greets customers and shows them to their tables

Translation output:
  Term: Anfitrión
  Sentences:
    El anfitrión trabaja en el restaurante.
    El anfitrión saluda a las personas.
    El anfitrión los lleva a su mesa.

### Example (wrong — do not do this)

  El anfitrión da la bienvenida a los huéspedes, toma las reservaciones y los guía a sus mesas.

Why wrong: one long sentence, lists read aloud, "huéspedes" is too formal, no repetition of key term.

## Voice Settings

TTS engine: Coqui XTTS v2 (local, RTX 4090)
Reference clips live in `voices/`:
  - `voices/english_reference.wav` — English voice (locked in, do not change)
  - `voices/spanish_reference.wav` — Mexican Spanish voice (locked in, do not change)

Do not change the reference clips once set. Consistency all year is a requirement.

## Project Structure

```
src/translation_service/
  pdf_reader.py      — extracts slide content from PDF (term + bullets per page)
  classifier.py      — classifies each slide as header (skip) or content (process)
  translator.py      — sends content to Claude API, returns accessible Spanish
  script_builder.py  — structures the audio script (ordered segments with language tags)
  tts_engine.py      — Coqui XTTS v2 wrapper, generates and combines audio segments
  pipeline.py        — orchestrates all steps for a full PDF run

cli.py               — entry point: python cli.py --pdf path/to/slides.pdf
voices/              — reference audio clips (wav files, not committed to git)
output/              — generated audio files land here
```

## How to Run

```bash
# Copy .env.example to .env and add your Anthropic API key
cp .env.example .env

# Place reference audio clips in voices/
# (see voices/README.md)

# Dry run — translate and print scripts without generating audio
uv run python cli.py --pdf "Food Service Industry - Behind the Scenes.pdf" --dry-run

# Full run — translate and generate all audio files
uv run python cli.py --pdf "Food Service Industry - Behind the Scenes.pdf"
```

## Translation Cache

Translations are cached to `output/.translation_cache.json`.
If a slide's content has not changed, the cached translation is used — no API call made.
Delete the cache file to force a full re-translation.

## Backlog

See PLAN.md for full backlog. Item #1 is Google Slides API integration to replace PDF input.

## Dependencies

Managed by uv. Python 3.11 required (Coqui TTS does not support 3.12+).
PyTorch is the CUDA 12.4 build — do not upgrade without verifying GPU compatibility.
