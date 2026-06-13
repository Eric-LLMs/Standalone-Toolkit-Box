"""Custom tkinter widgets for per-video progress display."""

import tkinter as tk
from tkinter import ttk

from .models import VideoEntry


class VideoProgressRow:
    """A single row in the scrollable progress area.

    Displays a checkbox, truncated title, progress bar, and status label
    for one video entry.
    """

    def __init__(self, parent: ttk.Frame, entry: VideoEntry):
        self.entry = entry
        self.frame = ttk.Frame(parent)

        # Checkbox
        self.check_var = tk.BooleanVar(value=entry.checked)
        cb = ttk.Checkbutton(self.frame, variable=self.check_var,
                             command=self._on_check)
        cb.grid(row=0, column=0, padx=2)

        # Title (truncated to 70 characters)
        title = entry.title or "(unavailable)"
        display = title[:70] + "..." if len(title) > 70 else title
        self.title_label = ttk.Label(self.frame, text=display, anchor="w")
        self.title_label.grid(row=0, column=1, sticky="ew", padx=2)

        # Progress bar
        self.progress_bar = ttk.Progressbar(self.frame, mode="determinate",
                                            maximum=100)
        self.progress_bar.grid(row=0, column=2, padx=4, sticky="ew")

        # Status / speed label
        self.status_label = ttk.Label(self.frame, text="Pending", width=22,
                                      anchor="w")
        self.status_label.grid(row=0, column=3, padx=4)

        # Column weights for stretching
        self.frame.columnconfigure(1, weight=1, minsize=120)
        self.frame.columnconfigure(2, weight=1, minsize=80)

    # -- internal ----------------------------------------------------------

    def _on_check(self) -> None:
        self.entry.checked = self.check_var.get()

    # -- public API --------------------------------------------------------

    def update_progress(self, pct: float, speed: str, eta: str) -> None:
        """Update the progress bar and speed/ETA display."""
        self.progress_bar["value"] = pct
        self.status_label.configure(text=f"{pct:5.1f}%  {speed}  ETA: {eta}")

    def update_status(self, status: str, error_msg: str = "") -> None:
        """Update the status label based on the video state."""
        if status == "completed":
            self.progress_bar["value"] = 100
            self.status_label.configure(text="Completed", foreground="green")
        elif status == "downloading":
            self.status_label.configure(text="Downloading...", foreground="blue")
        elif status == "error":
            msg = error_msg[:50] if error_msg else "Error"
            self.status_label.configure(text=f"Error: {msg}", foreground="red")
            self.progress_bar["value"] = 0
        elif status == "pending":
            self.status_label.configure(text="Pending", foreground="gray")
            self.progress_bar["value"] = 0
