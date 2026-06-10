"""Main GUI application class for CRTubeGet."""

import os
import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import ttk

# DPI awareness for high-DPI Windows displays (must run before tkinter init)
try:
    import ctypes

    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk
from tkinter import filedialog, messagebox

from .__init__ import __version__
from .downloader import run_analysis, run_download
from .models import VideoEntry
from .utils import find_executable, sanitize_name
from .widgets import VideoProgressRow


# ---------------------------------------------------------------------------
# Error-message UX overrides
# ---------------------------------------------------------------------------

_ERROR_HINTS = [
    (
        # Chromium cookie-DB lock
        lambda msg: "Could not copy" in msg and "cookie" in msg.lower(),
        lambda msg: (
            f"{msg}\n\n"
            "Browser is running and has locked its cookie database.\n\n"
            "Quick fixes:\n"
            "  1. Close the browser completely, retry, then reopen it\n"
            "  2. Switch Browser to Firefox (no lock issue, can stay open)\n"
            "  3. Switch Source to File and use a proper cookies.txt"
        ),
    ),
    (
        # Sign-in required
        lambda msg: "Sign in to confirm" in msg,
        lambda msg: (
            f"{msg}\n\n"
            "Your cookies are missing, expired, or invalid.\n\n"
            "Re-export cookies.txt from the browser extension,\n"
            "or switch Source → Browser and select the browser\n"
            "where you are logged into YouTube."
        ),
    ),
    (
        # OAuth2 deprecated
        lambda msg: "oauth" in msg.lower() and "no longer supported" in msg.lower(),
        lambda msg: (
            f"{msg}\n\n"
            "YouTube has disabled OAuth2 login.\n\n"
            "Switch Source to 'Browser' and select the browser\n"
            "where you are logged into YouTube (Firefox recommended)."
        ),
    ),
]


def _humanize_error(raw: str) -> str:
    """Return a user-friendly error message, or *raw* if no hint matches."""
    for predicate, formatter in _ERROR_HINTS:
        if predicate(raw):
            return formatter(raw)
    return raw


# ---------------------------------------------------------------------------
# App class
# ---------------------------------------------------------------------------


class CRTubeGetApp:
    """CRTubeGet main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("CRTubeGet - YouTube Downloader")
        self.root.geometry("1024x720")
        self.root.minsize(800, 500)

        # ---- thread-safe UI queue ----------------------------------------
        self.ui_queue: queue.Queue = queue.Queue()

        # ---- path defaults -----------------------------------------------
        script_dir = Path(__file__).parent.parent  # repo root
        self._default_output = str(script_dir / "dataset")
        self._default_cookie = str(script_dir / "cookies.txt")
        if not os.path.exists(self._default_cookie):
            self._default_cookie = ""

        # ---- tkinter variables ------------------------------------------
        self.output_var = tk.StringVar(value=self._default_output)
        self.cookie_var = tk.StringVar(value=self._default_cookie)
        self.cookie_mode = tk.StringVar(value="file")
        self.browser_var = tk.StringVar(value="chrome")
        self.concurrency_var = tk.IntVar(value=3)
        self.auto_subfolder = tk.BooleanVar(value=True)

        # ---- executable auto-detection ----------------------------------
        self.ffmpeg_path = find_executable("ffmpeg", [
            r"C:\ffmpeg\bin\ffmpeg.exe",
        ])
        # deno: project root first (bundled), then PATH via shutil.which()
        bundled_deno = str(script_dir / "deno.exe")
        self.deno_path = find_executable("deno", [
            bundled_deno,
        ])

        # ---- state ------------------------------------------------------
        self.videos: list[VideoEntry] = []
        self.playlist_title: str = ""
        self.executor: ThreadPoolExecutor | None = None
        self.downloading: bool = False
        self.completed_count: int = 0
        self.error_count: int = 0
        self.total_selected: int = 0
        self._effective_output_subdir: str = ""

        self.progress_rows: dict[int, VideoProgressRow] = {}

        # ---- build UI ---------------------------------------------------
        self._build_ui()

        # ---- warn if tools missing --------------------------------------
        missing = []
        if not self.ffmpeg_path:
            missing.append("ffmpeg")
        if not self.deno_path:
            missing.append("deno")
            self.root.after(500, self._prompt_install_deno)
        if missing:
            self._set_status(
                f"Warning: {', '.join(missing)} not found. "
                "Some features may not work."
            )

        # ---- start UI queue polling -------------------------------------
        self.root.after(100, self._poll_ui_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ==================================================================
    # Settings collector
    # ==================================================================

    def _collect_settings(self) -> dict:
        """Return a dict of settings to pass to downloader functions."""
        output_dir = self.output_var.get()
        if self._effective_output_subdir:
            output_dir = os.path.join(output_dir,
                                      self._effective_output_subdir)
        return {
            "output_dir": output_dir,
            "cookie_mode": self.cookie_mode.get(),
            "cookie_file": self.cookie_var.get(),
            "browser": self.browser_var.get(),
            "deno_path": self.deno_path,
            "ffmpeg_path": self.ffmpeg_path,
        }

    # ==================================================================
    # UI Construction
    # ==================================================================

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(5, weight=1)

        style = ttk.Style()
        style.configure("Title.TLabel", font=("", 14, "bold"))

        r = 0
        # Title
        ttk.Label(
            self.root, text="CRTubeGet - YouTube Downloader",
            style="Title.TLabel",
        ).grid(row=r, column=0, pady=(8, 4), sticky="w", padx=8)
        r += 1

        # URL bar
        url_frame = ttk.Frame(self.root)
        url_frame.columnconfigure(1, weight=1)
        ttk.Label(url_frame, text="URL:").grid(row=0, column=0, padx=4)
        self.url_entry = ttk.Entry(url_frame)
        self.url_entry.grid(row=0, column=1, sticky="ew", padx=4)
        self.url_entry.bind("<Return>", lambda e: self._on_analyze())
        self.analyze_btn = ttk.Button(
            url_frame, text="Analyze", command=self._on_analyze
        )
        self.analyze_btn.grid(row=0, column=2, padx=4)
        url_frame.grid(row=r, column=0, sticky="ew", padx=8, pady=4)
        r += 1

        self._sep(r)
        r += 1

        # Action bar
        action_frame = ttk.Frame(self.root)
        self.analysis_label = ttk.Label(
            action_frame, text="Enter a YouTube URL and click Analyze."
        )
        self.analysis_label.grid(row=0, column=0, sticky="w", padx=4)
        action_frame.columnconfigure(0, weight=1)

        self.select_all_btn = ttk.Button(
            action_frame, text="Select All",
            command=lambda: self._toggle_all(True),
        )
        self.deselect_all_btn = ttk.Button(
            action_frame, text="Deselect All",
            command=lambda: self._toggle_all(False),
        )
        self.download_btn = ttk.Button(
            action_frame, text="Download Selected",
            command=self._on_download_selected,
        )
        self.stop_btn = ttk.Button(
            action_frame, text="Stop All", command=self._on_stop_all,
        )

        action_frame.grid(row=r, column=0, sticky="ew", padx=8, pady=4)
        r += 1

        self._sep(r)
        r += 1

        # Overall progress
        overall_frame = ttk.Frame(self.root)
        self.overall_bar = ttk.Progressbar(
            overall_frame, mode="determinate", maximum=100,
        )
        self.overall_bar.grid(row=0, column=0, sticky="ew", padx=4)
        self.overall_label = ttk.Label(
            overall_frame, text="Ready", width=30, anchor="center",
        )
        self.overall_label.grid(row=0, column=1, padx=4)
        overall_frame.columnconfigure(0, weight=1)
        overall_frame.grid(row=r, column=0, sticky="ew", padx=8, pady=4)
        r += 1

        # Scrollable progress area
        scroll_outer = ttk.Frame(self.root)
        self.progress_canvas = tk.Canvas(scroll_outer, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            scroll_outer, orient="vertical",
            command=self.progress_canvas.yview,
        )
        self.scrollable_frame = ttk.Frame(self.progress_canvas)

        def _on_frame_configure(event):
            self.progress_canvas.configure(
                scrollregion=self.progress_canvas.bbox("all"),
            )

        self.scrollable_frame.bind("<Configure>", _on_frame_configure)

        def _on_canvas_configure(event):
            self.progress_canvas.itemconfig(
                "window_frame", width=event.width,
            )

        self.progress_canvas.bind("<Configure>", _on_canvas_configure)

        self.progress_canvas.create_window(
            (0, 0), window=self.scrollable_frame, anchor="nw",
            tags="window_frame",
        )
        self.progress_canvas.configure(yscrollcommand=scrollbar.set)
        self.progress_canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        scroll_outer.columnconfigure(0, weight=1)
        scroll_outer.rowconfigure(0, weight=1)

        def _on_mousewheel(event):
            self.progress_canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units",
            )

        self.progress_canvas.bind(
            "<Enter>",
            lambda e: self.progress_canvas.bind_all(
                "<MouseWheel>", _on_mousewheel,
            ),
        )
        self.progress_canvas.bind(
            "<Leave>",
            lambda e: self.progress_canvas.unbind_all("<MouseWheel>"),
        )

        scroll_outer.grid(row=r, column=0, sticky="nsew", padx=8, pady=4)
        r += 1

        self._sep(r)
        r += 1

        # Settings bar
        settings_frame = ttk.Frame(self.root)
        settings_frame.columnconfigure(1, weight=1, minsize=100)
        settings_frame.columnconfigure(4, weight=1, minsize=100)

        ttk.Label(settings_frame, text="Output:").grid(
            row=0, column=0, padx=4, sticky="e",
        )
        self.output_entry = ttk.Entry(
            settings_frame, textvariable=self.output_var,
        )
        self.output_entry.grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(
            settings_frame, text="Browse", width=7,
            command=self._browse_output,
        ).grid(row=0, column=2, padx=2)

        ttk.Label(settings_frame, text="Cookie:").grid(
            row=0, column=3, padx=4, sticky="e",
        )
        self.cookie_entry = ttk.Entry(
            settings_frame, textvariable=self.cookie_var,
        )
        self.cookie_entry.grid(row=0, column=4, sticky="ew", padx=2)
        ttk.Button(
            settings_frame, text="Browse", width=7,
            command=self._browse_cookie,
        ).grid(row=0, column=5, padx=2)

        ttk.Label(settings_frame, text="Source:").grid(
            row=0, column=6, padx=(8, 2), sticky="e",
        )
        cookie_mode_frame = ttk.Frame(settings_frame)
        for text, value in [
            ("File", "file"), ("Browser", "browser"), ("OAuth2", "oauth2"),
        ]:
            ttk.Radiobutton(
                cookie_mode_frame, text=text, variable=self.cookie_mode,
                value=value, command=self._on_cookie_mode_change,
            ).pack(side="left")
        self.browser_combo = ttk.Combobox(
            cookie_mode_frame, textvariable=self.browser_var,
            values=["chrome", "firefox", "edge", "brave", "opera"],
            state="readonly", width=10,
        )
        cookie_mode_frame.grid(row=0, column=7, padx=2, sticky="w")

        ttk.Label(settings_frame, text="Parallel:").grid(
            row=0, column=8, padx=(12, 2), sticky="e",
        )
        ttk.Spinbox(
            settings_frame, from_=1, to=8, width=4,
            textvariable=self.concurrency_var,
        ).grid(row=0, column=9, padx=2)

        ttk.Checkbutton(
            settings_frame, text="Subfolder", variable=self.auto_subfolder,
        ).grid(row=0, column=10, padx=(6, 2))

        settings_frame.grid(row=r, column=0, sticky="ew", padx=8, pady=4)
        r += 1

        # Status bar
        self.status_label = ttk.Label(
            self.root, text="Ready.", relief="sunken", anchor="w",
        )
        self.status_label.grid(row=r, column=0, sticky="ew", padx=8, pady=(2, 4))

        # Initial button visibility
        self._set_action_buttons_visible(False)
        self.stop_btn.configure(state="disabled")

    @staticmethod
    def _sep(row: int) -> None:
        ttk.Separator().grid(row=row, column=0, sticky="ew", padx=8, pady=2)

    # ==================================================================
    # First-run helper
    # ==================================================================

    def _prompt_install_deno(self) -> None:
        """Show a one-time dialog guiding the user to install deno."""
        if self.deno_path:
            return  # already found
        script_dir = Path(__file__).parent.parent
        target = script_dir / "deno.exe"
        messagebox.showinfo(
            "deno Not Found",
            "deno (JavaScript runtime) is required to solve YouTube's "
            "n-sig challenge.\n\n"
            "Quick fix:\n"
            "  1. Download deno from:\n"
            "     https://github.com/denoland/deno/releases/latest\n"
            "     (get deno-x86_64-pc-windows-msvc.zip)\n\n"
            "  2. Extract deno.exe and place it here:\n"
            f"     {target}\n\n"
            "  3. Restart CRTubeGet\n\n"
            "Or install via winget:\n"
            "  winget install DenoLand.Deno",
        )

    # ==================================================================
    # Settings callbacks
    # ==================================================================

    def _browse_output(self) -> None:
        d = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.output_var.get(),
        )
        if d:
            self.output_var.set(d)

    def _browse_cookie(self) -> None:
        f = filedialog.askopenfilename(
            title="Select Cookie File",
            filetypes=[("Netscape Cookie Files", "*.txt"), ("All Files", "*.*")],
        )
        if f:
            self.cookie_var.set(f)

    def _on_cookie_mode_change(self) -> None:
        mode = self.cookie_mode.get()
        if mode == "browser":
            self.cookie_entry.configure(state="disabled")
            self.browser_combo.pack(side="left", padx=(4, 0))
        elif mode == "oauth2":
            self.cookie_entry.configure(state="disabled")
            self.browser_combo.pack_forget()
        else:  # file
            self.cookie_entry.configure(state="normal")
            self.browser_combo.pack_forget()

    # ==================================================================
    # Analysis
    # ==================================================================

    def _on_analyze(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Input Required",
                                   "Please enter a YouTube URL.")
            return

        self.analyze_btn.configure(state="disabled", text="Analyzing...")
        self.analysis_label.configure(text="Analyzing URL, please wait...")
        self._set_status("Analyzing...")
        self._clear_progress_area()

        settings = self._collect_settings()
        thread = threading.Thread(
            target=run_analysis,
            args=(url, settings, self.ui_queue),
            daemon=True,
        )
        thread.start()

    # ==================================================================
    # Download orchestration
    # ==================================================================

    def _on_download_selected(self) -> None:
        if self.downloading:
            return

        selected = [v for v in self.videos if v.checked]
        if not selected:
            messagebox.showinfo("No Selection",
                                "No videos selected for download.")
            return

        out_dir = self.output_var.get()
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as e:
            messagebox.showerror("Error",
                                 f"Cannot create output directory:\n{e}")
            return

        self.downloading = True
        self.completed_count = 0
        self.error_count = 0
        self.total_selected = len(selected)

        for v in selected:
            v.progress = 0.0
            v.status = "pending"
            v.speed = ""
            v.eta = ""
            v.error_msg = ""
            v.cancel_event.clear()

        self.overall_bar["value"] = 0
        self.overall_label.configure(
            text=f"0/{self.total_selected} completed",
        )
        self._update_progress_rows_status(selected)
        self.download_btn.configure(state="disabled")
        self.analyze_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self._set_status(f"Downloading {self.total_selected} video(s)...")

        settings = self._collect_settings()
        max_workers = self.concurrency_var.get()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        for v in selected:
            self.executor.submit(run_download, v, settings, self.ui_queue)

        self.root.after(100, self._check_completion)

    def _check_completion(self) -> None:
        if not self.downloading or self.executor is None:
            return
        if self.completed_count + self.error_count >= self.total_selected:
            self._on_downloads_finished()
        else:
            self.root.after(200, self._check_completion)

    def _on_downloads_finished(self) -> None:
        self.downloading = False
        if self.executor:
            self.executor.shutdown(wait=False)
            self.executor = None

        summary = f"Completed: {self.completed_count}/{self.total_selected}"
        if self.error_count > 0:
            summary += f" | Errors: {self.error_count}"
        self.overall_label.configure(text=summary)
        self._set_status(summary)
        self.download_btn.configure(state="normal")
        self.analyze_btn.configure(state="normal", text="Analyze")
        self.stop_btn.configure(state="disabled")

    def _on_stop_all(self) -> None:
        for v in self.videos:
            if v.status in ("pending", "downloading"):
                v.cancel_event.set()
        self._set_status("Stopping all downloads...")
        self.stop_btn.configure(state="disabled")

    # ==================================================================
    # UI queue polling (main-thread only)
    # ==================================================================

    def _poll_ui_queue(self) -> None:
        try:
            while True:
                msg = self.ui_queue.get_nowait()
                self._handle_message(msg)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self._poll_ui_queue)

    def _handle_message(self, msg: tuple) -> None:
        msg_type = msg[0]

        if msg_type == "analysis_result":
            _, playlist_title, entries = msg
            self.playlist_title = playlist_title
            self._on_analysis_complete(playlist_title, entries)
            self.videos = entries

        elif msg_type == "analysis_error":
            _, error_msg = msg
            self.analyze_btn.configure(state="normal", text="Analyze")
            self.analysis_label.configure(text="Analysis failed.")
            self._set_status("Analysis failed.")
            messagebox.showerror("Analysis Error",
                                 _humanize_error(error_msg))

        elif msg_type == "progress":
            _, idx, pct, speed, eta = msg
            if idx in self.progress_rows:
                self.progress_rows[idx].update_progress(pct, speed, eta)
            if self.total_selected > 0:
                total = sum(
                    v.progress for v in self.videos if v.checked
                ) / self.total_selected
                self.overall_bar["value"] = total
            if idx < len(self.videos):
                self.videos[idx].progress = pct
                self.videos[idx].speed = speed
                self.videos[idx].eta = eta

        elif msg_type == "status":
            _, idx, status, error_msg = msg
            if idx < len(self.videos):
                self.videos[idx].status = status
                if error_msg:
                    self.videos[idx].error_msg = error_msg
            if idx in self.progress_rows:
                self.progress_rows[idx].update_status(status, error_msg)
            if status == "completed":
                self.completed_count += 1
                self.overall_label.configure(
                    text=f"{self.completed_count}/{self.total_selected} completed",
                )
            elif status == "error":
                self.error_count += 1

    # ==================================================================
    # UI helpers
    # ==================================================================

    def _on_analysis_complete(
        self, playlist_title: str | None, entries: list[VideoEntry],
    ) -> None:
        self._clear_progress_area()

        if playlist_title:
            self.analysis_label.configure(
                text=f"Playlist: {playlist_title}  ({len(entries)} videos)",
            )
        else:
            self.analysis_label.configure(
                text=f"Single Video: {entries[0].title}",
            )

        # Auto subfolder
        if self.auto_subfolder.get():
            title = playlist_title if playlist_title else entries[0].title
            self._effective_output_subdir = sanitize_name(title)

        is_playlist = playlist_title is not None
        self._set_action_buttons_visible(is_playlist)

        self.scrollable_frame.columnconfigure(0, weight=1)
        for entry in entries:
            row = VideoProgressRow(self.scrollable_frame, entry)
            row.frame.grid(row=entry.index, column=0, sticky="ew",
                           pady=1, padx=2)
            self.progress_rows[entry.index] = row

        self.download_btn.configure(state="normal")
        self.analyze_btn.configure(state="normal", text="Analyze")
        self._set_status(f"Analysis complete. {len(entries)} video(s) found.")

        if is_playlist:
            self.root.after(200, self._ask_download_playlist,
                            entries, playlist_title)
        else:
            self._set_status(f"Auto-downloading: {entries[0].title}")
            self.root.after(200, self._on_download_selected)

    def _ask_download_playlist(
        self, entries: list[VideoEntry], playlist_title: str,
    ) -> None:
        count = len(entries)
        answer = messagebox.askyesno(
            "Playlist Detected",
            f"This video is part of a playlist:\n\n"
            f"  {playlist_title}\n\n"
            f"Contains {count} video(s) total.\n\n"
            f"Download ALL videos in this playlist?\n\n"
            f"(Click 'No' to download only this single video.)",
        )
        if not answer:
            for v in entries:
                v.checked = (v.index == 0)
            for idx, row in self.progress_rows.items():
                row.check_var.set(idx == 0)
            self._set_status("Downloading single video only...")
            self.root.after(100, self._on_download_selected)

    def _set_action_buttons_visible(self, visible: bool) -> None:
        if visible:
            self.select_all_btn.grid(row=0, column=1, padx=2)
            self.deselect_all_btn.grid(row=0, column=2, padx=2)
            self.download_btn.grid(row=0, column=3, padx=(8, 2))
            self.stop_btn.grid(row=0, column=4, padx=2)
        else:
            self.select_all_btn.grid_forget()
            self.deselect_all_btn.grid_forget()
            self.download_btn.grid(row=0, column=3, padx=(8, 2))
            self.stop_btn.grid(row=0, column=4, padx=2)

    def _toggle_all(self, checked: bool) -> None:
        for v in self.videos:
            v.checked = checked
        for row in self.progress_rows.values():
            row.check_var.set(checked)

    def _clear_progress_area(self) -> None:
        for row in self.progress_rows.values():
            row.frame.destroy()
        self.progress_rows.clear()
        self.videos.clear()
        self.completed_count = 0
        self.error_count = 0
        self.total_selected = 0
        self._effective_output_subdir = ""
        self.overall_bar["value"] = 0
        self.overall_label.configure(text="Ready")

    def _update_progress_rows_status(
        self, entries: list[VideoEntry],
    ) -> None:
        for v in entries:
            if v.index in self.progress_rows:
                self.progress_rows[v.index].update_status(v.status)

    def _set_status(self, text: str) -> None:
        self.status_label.configure(text=text)

    def _on_closing(self) -> None:
        if self.downloading:
            if not messagebox.askyesno(
                "Confirm Exit",
                "Downloads are in progress. Cancel and exit?",
            ):
                return
            self._on_stop_all()
        if self.executor:
            self.executor.shutdown(wait=False)
        self.root.destroy()
