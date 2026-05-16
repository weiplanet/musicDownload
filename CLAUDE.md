# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
