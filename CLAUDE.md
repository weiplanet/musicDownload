# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

These rules apply to every task in this project unless explicitly overridden.
Bias: caution over speed on non-trivial work. Use judgment on trivial tasks.

## Rule 1 — Think Before Coding
State assumptions explicitly. If uncertain, ask rather than guess.
Present multiple interpretations when ambiguity exists.
Push back when a simpler approach exists.
Stop when confused. Name what's unclear.

## Rule 2 — Simplicity First
Minimum code that solves the problem. Nothing speculative.
No features beyond what was asked. No abstractions for single-use code.
Test: would a senior engineer say this is overcomplicated? If yes, simplify.

## Rule 3 — Surgical Changes
Touch only what you must. Clean up only your own mess.
Don't "improve" adjacent code, comments, or formatting.
Don't refactor what isn't broken. Match existing style.

## Rule 4 — Goal-Driven Execution
Define success criteria. Loop until verified.
Don't follow steps. Define success and iterate.
Strong success criteria let you loop independently.

## Rule 5 — Use the model only for judgment calls
Use me for: classification, drafting, summarization, extraction.
Do NOT use me for: routing, retries, deterministic transforms.
If code can answer, code answers.

## Rule 6 — Token budgets are not advisory
Per-task: 4,000 tokens. Per-session: 30,000 tokens.
If approaching budget, summarize and start fresh.
Surface the breach. Do not silently overrun.

## Rule 7 — Surface conflicts, don't average them
If two patterns contradict, pick one (more recent / more tested).
Explain why. Flag the other for cleanup.
Don't blend conflicting patterns.

## Rule 8 — Read before you write
Before adding code, read exports, immediate callers, shared utilities.
"Looks orthogonal" is dangerous. If unsure why code is structured a way, ask.

## Rule 9 — Tests verify intent, not just behavior
Tests must encode WHY behavior matters, not just WHAT it does.
A test that can't fail when business logic changes is wrong.

## Rule 10 — Checkpoint after every significant step
Summarize what was done, what's verified, what's left.
Don't continue from a state you can't describe back.
If you lose track, stop and restate.

## Rule 11 — Match the codebase's conventions, even if you disagree
Conformance > taste inside the codebase.
If you genuinely think a convention is harmful, surface it. Don't fork silently.

## Rule 12 — Fail loud
"Completed" is wrong if anything was skipped silently.
"Tests pass" is wrong if any were skipped.
Default to surfacing uncertainty, not hiding it.

## Setup & Running

```bash
# Create and activate virtual environment (Python 3.13 required)
python -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the app
python musicdownload.py
```

Note: `requirements.txt` lists `PyQt5` but the codebase uses `PySide6` — both are installed. `musicdl` is treated as optional; the app warns on startup if it's missing.

Downloaded files land in `已下载音乐/` (created automatically in the working directory). `musicdl` writes to a temp dir `.musicdl_temp/` during download; `DownloadThread` then renames and moves files to the target directory.

## Architecture

The entire application lives in `musicdownload.py` (single-file). `musicdownload_debug.py` and `musicdownload_test.py` are copies of the same file.

**Threading model** — all network I/O is off the main thread:
- `SearchThread` (QThread): calls `musicdl.MusicClient.search()` or `parseplaylist()`, emits `finished(dict)` or `error(str)`
- `DownloadThread` (QThread): calls `musicdl.MusicClient.download()`, then renames/moves resulting files; emits `finished(int)` (success count) or `error(str)`
- `ImageDownloadTask` (QRunnable) + `ImageWorkerSignals` (QObject): album art is fetched via a `QThreadPool` (max 10 concurrent). `QRunnable` cannot emit signals directly, so `ImageWorkerSignals` is the signal carrier.

**Main window — `MusicDownloader` (QMainWindow)**:
- `source_map_cn_to_en`: maps Chinese UI labels to `musicdl` client class names (e.g. `"酷我音乐" → "KuwoMusicClient"`)
- `music_records`: `dict[str, dict]` — row index (as string) → song info dict from musicdl
- `init_music_client()`: creates `musicdl.MusicClient` with per-source config (`search_size_per_source`, `work_dir`)
- `_start_download_task()`: shared helper that shows `SimpleProgressDialog`, starts `DownloadThread`, wires signals
- `setup_top()` / `setup_table()`: build the two UI sections (source checkboxes + search bar; results table + download controls)

**Custom widgets**:
- `ModernComboBox`, `ModernSpinBox`: subclass Qt widgets to draw custom drop-down arrows/spinners via `paintEvent`
- `FlowLayout` (QLayout): wrapping flow layout used for the source checkbox grid
- `SimpleProgressDialog`: frameless, modal indeterminate progress dialog

**Supported music sources** (17 total, default: 酷我+酷狗):
Apple Music, Deezer, 5sing, Jamendo, Joox, 酷我, 酷狗, 咪咕, 网易云, QQ, 千千, Qobuz, SoundCloud, StreetVoice, 汽水, Spotify, TIDAL

## Key Conventions

- Song info dicts from `musicdl` use varying field names across sources; use helper methods `get_file_format()` and `get_album_image_url()` which probe multiple field names for robustness.
- Downloaded file naming: `sanitize_filename(songname-singer[-album][-id]).ext` — duplicate filenames are overwritten (existing file is deleted first).
- LRC lyric files follow the same base name as the audio file and are moved alongside it.
