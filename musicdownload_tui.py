"""Terminal UI for 音乐下载器, powered by Textual."""

import os
import re
import shutil
import threading

try:
    from musicdl import musicdl

    MUSICDL_AVAILABLE = True
except ImportError:
    musicdl = None
    MUSICDL_AVAILABLE = False

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    DirectoryTree,
    Footer,
    Header,
    Input,
    Label,
    ProgressBar,
    Select,
    Switch,
)

# ── Source maps ───────────────────────────────────────────────────────────────

SOURCE_MAP_CN_TO_EN: dict[str, str] = {
    "苹果音乐": "AppleMusicClient",
    "Deezer": "DeezerMusicClient",
    "5sing": "FiveSingMusicClient",
    "Jamendo": "JamendoMusicClient",
    "Joox": "JooxMusicClient",
    "酷我音乐": "KuwoMusicClient",
    "酷狗音乐": "KugouMusicClient",
    "咪咕音乐": "MiguMusicClient",
    "网易云音乐": "NeteaseMusicClient",
    "QQ音乐": "QQMusicClient",
    "千千音乐": "QianqianMusicClient",
    "Qobuz": "QobuzMusicClient",
    "SoundCloud": "SoundCloudMusicClient",
    "StreetVoice": "StreetVoiceMusicClient",
    "汽水音乐": "SodaMusicClient",
    "Spotify": "SpotifyMusicClient",
    "TIDAL": "TIDALMusicClient",
}
SOURCE_MAP_EN_TO_CN: dict[str, str] = {v: k for k, v in SOURCE_MAP_CN_TO_EN.items()}
DEFAULT_SOURCES: frozenset[str] = frozenset({"酷我音乐", "酷狗音乐"})

# ── Utilities ─────────────────────────────────────────────────────────────────


def sanitize_filename(filename: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", str(filename))


def format_singers(singers) -> str:
    if isinstance(singers, list):
        return "&".join(str(s) for s in singers)
    return str(singers)


def get_file_format(song_info: dict) -> str:
    for field in ["format", "ext", "file_format", "type"]:
        if song_info.get(field):
            return str(song_info[field]).upper()
    url = song_info.get("download_url", "").lower()
    for ext in ["mp3", "flac", "wav", "m4a", "aac"]:
        if f".{ext}" in url:
            return ext.upper()
    return "?"


# ── CSS ───────────────────────────────────────────────────────────────────────

APP_CSS = """
Screen {
    background: $surface;
}

/* Top panel: sources + config + search */
#top-panel {
    height: auto;
    padding: 1 2;
    background: $panel;
    border-bottom: solid $primary-darken-3;
}

#sources-row {
    height: auto;
    margin-bottom: 1;
}

#sources-grid {
    layout: grid;
    grid-size: 4;
    grid-gutter: 0 1;
    width: 1fr;
    height: auto;
}

#sources-grid Checkbox {
    height: 1;
    padding: 0 0;
    background: transparent;
    border: none;
}

#source-btns {
    width: 10;
    height: auto;
    align: left top;
    padding-top: 0;
}

#source-btns Button {
    width: 8;
    margin-bottom: 1;
}

#config-row {
    height: 5;
    align: left middle;
    margin-bottom: 1;
}

#config-row Label {
    width: auto;
    padding: 0 1;
    color: $text-muted;
}

#limit-input {
    width: 8;
    height: 3;
    padding: 0 1;
}

#save-dir-input {
    width: 1fr;
    height: 3;
    margin-right: 1;
}

#search-row {
    height: 3;
    align: left middle;
}

#search-mode {
    width: 18;
    height: 3;
    margin-right: 1;
}

#search-input {
    width: 1fr;
    height: 3;
    margin-right: 1;
}

#btn-search {
    width: 14;
    background: $primary;
}

/* Results area */
#results-header {
    height: 3;
    align: left middle;
    padding: 0 2;
    background: $panel;
}

#count-label {
    width: 1fr;
    color: $text-muted;
    content-align: left middle;
}

#download-scope {
    width: 18;
    height: 3;
    margin-right: 1;
}

#btn-download {
    width: 12;
    background: $success;
}

DataTable {
    height: 1fr;
}

/* Progress bar row — hidden by default */
#progress-row {
    height: 3;
    align: left middle;
    padding: 0 2;
    background: $panel;
    display: none;
}

#progress-bar {
    width: 1fr;
    margin-right: 1;
}

#progress-label {
    width: 10;
    color: $text-muted;
    content-align: left middle;
}

#btn-cancel {
    width: 8;
}

/* Browse modal */
BrowseScreen {
    align: center middle;
}

#browse-dialog {
    width: 60;
    height: 30;
    border: solid $primary;
    background: $surface;
    padding: 1 2;
}

#browse-dialog Label {
    margin-bottom: 1;
    color: $text-muted;
}

#browse-dialog DirectoryTree {
    height: 1fr;
}

/* Confirm modal */
ConfirmScreen {
    align: center middle;
}

#confirm-dialog {
    width: 60;
    height: auto;
    border: solid $primary;
    background: $surface;
    padding: 2 4;
}

#confirm-msg {
    margin-bottom: 2;
    text-align: center;
}

#confirm-btns {
    align: center middle;
    height: auto;
}

#confirm-btns Button {
    margin: 0 2;
    width: 12;
}
"""

# ── Modal screens ─────────────────────────────────────────────────────────────


class BrowseScreen(ModalScreen[str]):
    BINDINGS = [("escape", "app.pop_screen", "取消")]

    def __init__(self, start_path: str) -> None:
        super().__init__()
        self._start_path = start_path

    def compose(self) -> ComposeResult:
        with Container(id="browse-dialog"):
            yield Label("选择保存目录 (Enter 确认, Escape 取消)")
            yield DirectoryTree(self._start_path, id="dir-tree")

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        self.dismiss(str(event.path))


class ConfirmScreen(ModalScreen[bool]):
    BINDINGS = [("escape", "dismiss_false", "取消")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Container(id="confirm-dialog"):
            yield Label(self._message, id="confirm-msg")
            with Horizontal(id="confirm-btns"):
                yield Button("确认", id="btn-yes", variant="success")
                yield Button("取消", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "btn-yes")

    def action_dismiss_false(self) -> None:
        self.dismiss(False)


# ── Main application ──────────────────────────────────────────────────────────


class MusicDownloaderApp(App[None]):
    TITLE = "🎵 音乐下载器"
    CSS = APP_CSS
    BINDINGS = [
        Binding("ctrl+q", "quit", "退出"),
        Binding("ctrl+f", "focus_search", "搜索框"),
        Binding("ctrl+d", "start_download", "下载"),
        Binding("ctrl+a", "select_all_rows", "全选"),
        Binding("ctrl+u", "deselect_all_rows", "取消全选"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._current_dir = os.path.dirname(os.path.abspath(__file__))
        self._save_dir = os.path.join(self._current_dir, "downloads")
        os.makedirs(self._save_dir, exist_ok=True)
        self._songs: list[dict] = []
        self._checked: set[str] = set()
        self._row_keys: list[str] = []
        self._cancel_event = threading.Event()
        self._music_client = None
        self._is_searching = False
        self._is_downloading = False

    # ── Layout ─────────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Vertical(id="top-panel"):
            # Source checkboxes
            with Horizontal(id="sources-row"):
                with Container(id="sources-grid"):
                    for cn_name in SOURCE_MAP_CN_TO_EN:
                        yield Checkbox(cn_name, value=(cn_name in DEFAULT_SOURCES), compact=True)
                with Vertical(id="source-btns"):
                    yield Button("全选", id="btn-src-all")
                    yield Button("清除", id="btn-src-none")
            # Config row
            with Horizontal(id="config-row"):
                yield Label("每源限制：")
                yield Input("10", id="limit-input")
                yield Label("  保存目录：")
                yield Input(self._save_dir, id="save-dir-input")
                yield Button("浏览", id="btn-browse")
                yield Label("  自动下载：")
                yield Switch(False, id="auto-download")
            # Search row
            with Horizontal(id="search-row"):
                yield Select(
                    [("搜索歌曲", "search"), ("解析歌单", "playlist")],
                    value="search",
                    id="search-mode",
                )
                yield Input(placeholder="输入关键词或歌单链接...", id="search-input")
                yield Button("🔍 搜索", id="btn-search")
        # Results header
        with Horizontal(id="results-header"):
            yield Label("", id="count-label")
            yield Select(
                [("勾选歌曲", "checked"), ("全部", "all"), ("未勾选", "unchecked")],
                value="checked",
                id="download-scope",
            )
            yield Button("⬇ 下载", id="btn-download", disabled=True)
        # Results table
        yield DataTable(id="results-table", cursor_type="row")
        # Progress row (hidden until a download starts)
        with Horizontal(id="progress-row"):
            yield ProgressBar(total=100, id="progress-bar")
            yield Label("", id="progress-label")
            yield Button("取消", id="btn-cancel")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_column("✓", key="check", width=3)
        table.add_column("歌曲名", key="song", width=30)
        table.add_column("歌手", key="singer", width=18)
        table.add_column("专辑", key="album", width=20)
        table.add_column("格式", key="fmt", width=6)
        table.add_column("大小", key="size", width=8)
        table.add_column("时长", key="dur", width=8)
        table.add_column("来源", key="src", width=12)
        if not MUSICDL_AVAILABLE:
            self.notify("musicdl 库未安装！请运行: pip install musicdl", severity="error", timeout=10)

    # ── Source helpers ──────────────────────────────────────────────────────

    def _set_all_sources(self, checked: bool) -> None:
        for cb in self.query_one("#sources-grid").query(Checkbox):
            cb.value = checked

    def _get_selected_sources(self) -> list[str]:
        result = []
        for cb in self.query_one("#sources-grid").query(Checkbox):
            if cb.value:
                cn = cb.label.plain
                if cn in SOURCE_MAP_CN_TO_EN:
                    result.append(SOURCE_MAP_CN_TO_EN[cn])
        return result

    # ── Row check helpers ───────────────────────────────────────────────────

    def _toggle_row(self, row_key: str) -> None:
        table = self.query_one("#results-table", DataTable)
        if row_key in self._checked:
            self._checked.discard(row_key)
            table.update_cell(row_key, "check", "☐", update_width=False)
        else:
            self._checked.add(row_key)
            table.update_cell(row_key, "check", "✓", update_width=False)

    def _set_all_rows_checked(self, checked: bool) -> None:
        table = self.query_one("#results-table", DataTable)
        for rk in self._row_keys:
            if checked:
                self._checked.add(rk)
                table.update_cell(rk, "check", "✓", update_width=False)
            else:
                self._checked.discard(rk)
                table.update_cell(rk, "check", "☐", update_width=False)

    # ── Event handlers ──────────────────────────────────────────────────────

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id
        if btn_id == "btn-search":
            self._do_search()
        elif btn_id == "btn-download":
            self._do_download()
        elif btn_id == "btn-cancel":
            self._cancel_event.set()
            self.notify("正在取消...", timeout=2)
        elif btn_id == "btn-browse":
            self.push_screen(BrowseScreen(self._save_dir), self._on_browse_done)
        elif btn_id == "btn-src-all":
            self._set_all_sources(True)
        elif btn_id == "btn-src-none":
            self._set_all_sources(False)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "search-input":
            self._do_search()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        rk = str(event.row_key.value)
        if rk in self._row_keys:
            self._toggle_row(rk)

    def on_key(self, event) -> None:
        if event.key == "space" and self.focused is not None and isinstance(self.focused, DataTable):
            table = self.query_one("#results-table", DataTable)
            if self._row_keys and 0 <= table.cursor_row < len(self._row_keys):
                self._toggle_row(self._row_keys[table.cursor_row])
            event.prevent_default()

    # ── Actions ─────────────────────────────────────────────────────────────

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_start_download(self) -> None:
        if not self.query_one("#btn-download", Button).disabled:
            self._do_download()

    def action_select_all_rows(self) -> None:
        self._set_all_rows_checked(True)

    def action_deselect_all_rows(self) -> None:
        self._set_all_rows_checked(False)

    # ── Browse ───────────────────────────────────────────────────────────────

    def _on_browse_done(self, result: str | None) -> None:
        if result:
            self._save_dir = result
            self.query_one("#save-dir-input", Input).value = result
            os.makedirs(result, exist_ok=True)

    # ── Search ───────────────────────────────────────────────────────────────

    def _do_search(self) -> None:
        if self._is_searching:
            return
        keyword = self.query_one("#search-input", Input).value.strip()
        if not keyword:
            self.notify("请输入关键词", severity="warning")
            return
        src_names = self._get_selected_sources()
        if not src_names:
            self.notify("请至少选择一个音乐来源", severity="warning")
            return

        limit_str = self.query_one("#limit-input", Input).value.strip()
        try:
            limit = max(1, min(100, int(limit_str)))
        except ValueError:
            limit = 10

        search_mode_val = self.query_one("#search-mode", Select).value
        search_mode = "search" if search_mode_val is Select.BLANK else str(search_mode_val)

        temp_work_dir = os.path.join(self._current_dir, ".musicdl_temp")
        os.makedirs(temp_work_dir, exist_ok=True)
        cfg = {src: {"search_size_per_source": limit, "work_dir": temp_work_dir} for src in src_names}

        try:
            self._music_client = musicdl.MusicClient(
                music_sources=src_names, init_music_clients_cfg=cfg
            )
        except Exception as e:
            self.notify(f"初始化客户端失败：{e}", severity="error")
            return

        self._is_searching = True
        btn = self.query_one("#btn-search", Button)
        btn.disabled = True
        btn.label = "搜索中..."
        self._run_search(keyword, search_mode)

    @work(thread=True)
    def _run_search(self, keyword: str, search_mode: str) -> None:
        try:
            if search_mode == "search":
                results = self._music_client.search(keyword=keyword)
            else:
                results = self._music_client.parseplaylist(keyword)
                if not isinstance(results, dict):
                    results = {"歌单": results}
            self.call_from_thread(self._on_search_done, results)
        except Exception as e:
            self.call_from_thread(self._on_search_error, str(e))

    def _on_search_done(self, results: dict) -> None:
        self._is_searching = False
        btn = self.query_one("#btn-search", Button)
        btn.disabled = False
        btn.label = "🔍 搜索"
        self._load_table(results)
        if self.query_one("#auto-download", Switch).value and self._songs:
            self._start_download_for(self._songs)

    def _on_search_error(self, msg: str) -> None:
        self._is_searching = False
        btn = self.query_one("#btn-search", Button)
        btn.disabled = False
        btn.label = "🔍 搜索"
        self.notify(f"搜索失败：{msg}", severity="error")

    def _load_table(self, search_results: dict) -> None:
        table = self.query_one("#results-table", DataTable)
        table.clear()
        self._songs.clear()
        self._checked.clear()
        self._row_keys.clear()

        all_songs = [song for per_source in search_results.values() for song in per_source]
        for i, song in enumerate(all_songs):
            rk = f"r{i}"
            table.add_row(
                "☐",
                str(song.get("song_name", "")),
                format_singers(song.get("singers", "")),
                str(song.get("album", "")),
                get_file_format(song),
                str(song.get("file_size", "")),
                str(song.get("duration", "")),
                SOURCE_MAP_EN_TO_CN.get(song.get("source", ""), ""),
                key=rk,
            )
            self._songs.append(song)
            self._row_keys.append(rk)

        count = len(all_songs)
        self.query_one("#count-label", Label).update(f"共 {count} 首")
        self.query_one("#btn-download", Button).disabled = count == 0
        if count:
            self.notify(f"找到 {count} 首歌曲", timeout=3)

    # ── Download ──────────────────────────────────────────────────────────────

    def _get_songs_by_scope(self) -> list[dict]:
        scope_val = self.query_one("#download-scope", Select).value
        scope = "checked" if scope_val is Select.BLANK else str(scope_val)
        if scope == "all":
            return list(self._songs)
        if scope == "checked":
            return [self._songs[i] for i, rk in enumerate(self._row_keys) if rk in self._checked]
        return [self._songs[i] for i, rk in enumerate(self._row_keys) if rk not in self._checked]

    def _do_download(self) -> None:
        if self._is_downloading or not self._music_client:
            return
        songs = self._get_songs_by_scope()
        if not songs:
            self.notify("没有符合条件的歌曲", severity="warning")
            return
        msg = f"确定要下载 {len(songs)} 首歌曲？\n保存到：{self._save_dir}"
        self.push_screen(
            ConfirmScreen(msg),
            lambda ok: ok and self._start_download_for(songs),
        )

    def _start_download_for(self, songs: list[dict]) -> None:
        if self._is_downloading:
            return
        self._is_downloading = True
        self._cancel_event.clear()
        total = len(songs)

        self.query_one("#progress-row").display = True
        self.query_one("#progress-bar", ProgressBar).update(total=total, progress=0)
        self.query_one("#progress-label", Label).update(f"0 / {total}")
        self.query_one("#btn-download", Button).disabled = True

        temp_work_dir = os.path.join(self._current_dir, ".musicdl_temp")
        self._run_download(songs, self._save_dir, temp_work_dir)

    @work(thread=True)
    def _run_download(self, songs: list[dict], save_dir: str, temp_dir: str) -> None:
        os.makedirs(save_dir, exist_ok=True)
        os.makedirs(temp_dir, exist_ok=True)
        total = len(songs)
        success = 0
        cancelled = False

        for i, song_info in enumerate(songs):
            if self._cancel_event.is_set():
                cancelled = True
                break
            try:
                results = self._music_client.download(song_infos=[song_info])
                success += self._move_downloaded(results, save_dir)
            except Exception as e:
                print(f"下载失败: {e}")
            self.call_from_thread(self._on_progress, i + 1, total)

        if os.path.isdir(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        self.call_from_thread(self._on_download_done, success, total, cancelled)

    def _move_downloaded(self, downloaded_songs: list, target_dir: str) -> int:
        success = 0
        for song in downloaded_songs:
            save_path = song.get("save_path", "")
            if not save_path or not os.path.exists(save_path):
                continue
            song_name = song.get("song_name", "未知歌曲")
            singer = format_singers(song.get("singers", "未知歌手"))
            album = song.get("album", "")
            identifier = song.get("identifier", "")
            ext = os.path.splitext(save_path)[1].lstrip(".") or song.get("ext", "mp3")

            parts = [song_name, singer]
            if album:
                parts.append(str(album))
            if identifier:
                parts.append(str(identifier))

            base_name = sanitize_filename("-".join(parts))
            dest = os.path.join(target_dir, f"{base_name}.{ext}")
            try:
                if os.path.exists(dest):
                    os.remove(dest)
                shutil.move(save_path, dest)
                success += 1
            except Exception as e:
                print(f"移动文件失败: {e}")

            old_lrc = os.path.splitext(save_path)[0] + ".lrc"
            if os.path.exists(old_lrc):
                new_lrc = os.path.join(target_dir, f"{base_name}.lrc")
                try:
                    if os.path.exists(new_lrc):
                        os.remove(new_lrc)
                    shutil.move(old_lrc, new_lrc)
                except Exception as e:
                    print(f"移动歌词失败: {e}")
        return success

    def _on_progress(self, current: int, total: int) -> None:
        self.query_one("#progress-bar", ProgressBar).advance(1)
        self.query_one("#progress-label", Label).update(f"{current} / {total}")

    def _on_download_done(self, success: int, total: int, cancelled: bool) -> None:
        self._is_downloading = False
        self.query_one("#progress-row").display = False
        self.query_one("#btn-download", Button).disabled = len(self._songs) == 0
        if cancelled and success:
            self.notify(
                f"已取消，成功下载了 {success} 首，保存在：{self._save_dir}", timeout=8
            )
        elif cancelled:
            self.notify("下载已取消", timeout=4)
        else:
            self.notify(
                f"✅ 成功下载 {success} 首！保存在：{self._save_dir}", timeout=8
            )


if __name__ == "__main__":
    MusicDownloaderApp().run()
