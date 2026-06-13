"""yt-dlp integration: option builders, analysis worker, download worker.

All functions in this module are intentionally free of tkinter imports so
they can run on background threads without touching the UI toolkit.
"""

import os
import re
from typing import Any

import yt_dlp

# yt-dlp percent strings contain ANSI color codes, e.g. "\x1b[0;94m 42.5%\x1b[0m"
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

from .models import VideoEntry


# ---------------------------------------------------------------------------
# Public option builders
# ---------------------------------------------------------------------------

def build_analysis_opts(settings: dict[str, Any]) -> dict:
    """Minimal yt-dlp options for URL analysis (playlist detection, metadata)."""
    opts: dict[str, Any] = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "noplaylist": False,
    }
    _apply_cookie_opts(opts, settings)
    _apply_js_runtime(opts, settings)
    return opts


def build_download_opts(settings: dict[str, Any]) -> dict:
    """yt-dlp options for a single video download."""
    opts: dict[str, Any] = {
        "outtmpl": os.path.join(
            str(settings["output_dir"]), "%(title)s.%(ext)s"
        ),
        "format": (
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]"
            "/best/bestvideo+bestaudio"
        ),
        "merge_output_format": "mp4",
        "retries": 15,
        "fragment_retries": 15,
        "socket_timeout": 60,
        "noplaylist": True,
        "ignoreerrors": False,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }
    _apply_cookie_opts(opts, settings)
    _apply_js_runtime(opts, settings)
    if settings.get("ffmpeg_path"):
        opts["ffmpeg_location"] = settings["ffmpeg_path"]
    return opts


# ---------------------------------------------------------------------------
# Background workers  (called from non-main threads)
# ---------------------------------------------------------------------------

def run_analysis(
    url: str,
    settings: dict[str, Any],
    ui_queue,
) -> None:
    """Extract metadata for *url* and post results/errors to *ui_queue*."""
    try:
        opts = build_analysis_opts(settings)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if info is None:
            ui_queue.put(
                ("analysis_error", "Could not retrieve video information.")
            )
            return

        if "entries" in info and info.get("_type") != "video":
            _handle_playlist(info, ui_queue)
        else:
            _handle_single_video(info, url, ui_queue)

    except Exception as exc:
        ui_queue.put(("analysis_error", str(exc)))


def run_download(
    entry: VideoEntry,
    settings: dict[str, Any],
    ui_queue,
) -> None:
    """Download *entry* and post progress/status messages to *ui_queue*."""
    if entry.cancel_event.is_set():
        ui_queue.put(("status", entry.index, "pending", "Cancelled"))
        return

    opts = build_download_opts(settings)
    opts["progress_hooks"] = [_make_progress_hook(entry, ui_queue)]

    try:
        ui_queue.put(("status", entry.index, "downloading", None))
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([entry.url])
        ui_queue.put(("status", entry.index, "completed", None))
    except yt_dlp.utils.DownloadCancelled:
        ui_queue.put(("status", entry.index, "pending", "Cancelled"))
    except Exception as exc:
        ui_queue.put(("status", entry.index, "error", str(exc)))


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _apply_cookie_opts(opts: dict, settings: dict[str, Any]) -> None:
    """Inject cookie/auth options into *opts* based on *settings*."""
    mode = settings.get("cookie_mode", "file")

    if mode == "oauth2":
        opts["username"] = "oauth2"
        opts["password"] = ""
    elif mode == "browser":
        browser = settings.get("browser", "")
        if browser:
            opts["cookiesfrombrowser"] = (browser,)
    else:  # file
        cookie_file = str(settings.get("cookie_file", ""))
        if cookie_file and os.path.isfile(cookie_file):
            opts["cookiefile"] = cookie_file


def _apply_js_runtime(opts: dict, settings: dict[str, Any]) -> None:
    """Add deno JS runtime for n-challenge solving, if available."""
    deno_path = settings.get("deno_path")
    if deno_path:
        opts["javascript_runtimes"] = [f"deno:{deno_path}"]
        opts["remote_components"] = ["ejs:github"]


def _make_progress_hook(entry: VideoEntry, ui_queue):
    """Return a closure that posts download progress to *ui_queue*."""

    def _hook(d: dict) -> None:
        if entry.cancel_event.is_set():
            raise yt_dlp.utils.DownloadCancelled("User cancelled")
        if d.get("status") == "downloading":
            raw = _ANSI_RE.sub("", d.get("_percent_str", "0%"))
            raw = raw.replace("%", "").strip()
            try:
                pct = float(raw)
            except (ValueError, TypeError):
                pct = 0.0
            ui_queue.put((
                "progress",
                entry.index,
                pct,
                d.get("_speed_str", ""),
                d.get("_eta_str", ""),
            ))

    return _hook


def _handle_playlist(info: dict, ui_queue) -> None:
    """Parse playlist entries and push ``analysis_result`` to queue."""
    playlist_title = info.get("title", "Unknown Playlist")
    entries: list[VideoEntry] = []

    for i, entry in enumerate(info.get("entries", [])):
        if entry is None:
            continue
        title = entry.get("title") or f"Video {i + 1}"
        vid_id = entry.get("id", "")
        vid_url = entry.get("url") or f"https://www.youtube.com/watch?v={vid_id}"

        raw_duration = entry.get("duration") or ""
        duration_str = ""
        if raw_duration:
            try:
                mins, secs = divmod(int(raw_duration), 60)
                duration_str = f"{mins}:{secs:02d}"
            except (ValueError, TypeError):
                pass

        entries.append(VideoEntry(
            index=i,
            title=title,
            url=vid_url,
            checked=True,
            duration=duration_str,
        ))

    if not entries:
        ui_queue.put(
            ("analysis_error",
             "Playlist is empty or all entries are private.")
        )
        return

    ui_queue.put(("analysis_result", playlist_title, entries))


def _handle_single_video(info: dict, url: str, ui_queue) -> None:
    """Parse a single video and push ``analysis_result`` to queue."""
    title = info.get("title", "Unknown Video")
    video_url = info.get("webpage_url", url)
    entry = VideoEntry(index=0, title=title, url=video_url, checked=True)
    ui_queue.put(("analysis_result", None, [entry]))
