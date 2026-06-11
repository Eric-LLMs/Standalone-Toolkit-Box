"""GUI entry point for VTT subtitle conversion (LRC / SRT)."""

import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk


class CheckboxListFrame(ttk.Frame):
    """A scrollable frame with a checkbox per item."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._vars: list[tk.BooleanVar] = []
        self._items: list[str] = []
        self._checkbuttons: list[ttk.Checkbutton] = []

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._inner = ttk.Frame(self._canvas)

        self._inner.bind("<Configure>", lambda _: self._canvas.configure(
            scrollregion=self._canvas.bbox("all"),
        ))
        self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")

        self._canvas.bind("<Enter>", self._bind_mousewheel)
        self._canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, _event=None):
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event=None):
        self._canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def clear(self):
        for cb in self._checkbuttons:
            cb.destroy()
        self._vars.clear()
        self._items.clear()
        self._checkbuttons.clear()

    def add(self, filepath: str):
        if filepath in self._items:
            return
        var = tk.BooleanVar(value=True)
        name = os.path.basename(filepath)
        cb = ttk.Checkbutton(self._inner, text=name, variable=var)
        cb.pack(anchor="w", fill="x", padx=4, pady=1)
        self._vars.append(var)
        self._items.append(filepath)
        self._checkbuttons.append(cb)

    def toggle_all(self, checked: bool):
        for var in self._vars:
            var.set(checked)

    @property
    def checked_files(self) -> list[str]:
        return [p for p, v in zip(self._items, self._vars) if v.get()]

    @property
    def file_count(self) -> int:
        return len(self._items)


class Vtt2SrtApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("VTT Subtitle Converter")
        root.geometry("600x550")
        root.resizable(True, True)

        frame = ttk.Frame(root, padding=16)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Title.TLabel", font=("", 14, "bold"))

        ttk.Label(frame, text="VTT Subtitle Converter", style="Title.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 4),
        )

        # ---- source folder ---------------------------------------------------
        src_frame = ttk.LabelFrame(frame, text="Source Folder", padding=8)
        src_frame.grid(row=1, column=0, sticky="ew", pady=(0, 4))
        src_frame.columnconfigure(1, weight=1)

        self.src_dir_var = tk.StringVar()
        ttk.Entry(
            src_frame, textvariable=self.src_dir_var, width=50,
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 4))
        ttk.Button(
            src_frame, text="Browse...", command=self._select_source_folder,
        ).grid(row=0, column=2, sticky="e")
        ttk.Button(
            src_frame, text="Scan", command=self._scan_folder,
        ).grid(row=1, column=2, sticky="e", pady=(4, 0))
        ttk.Label(
            src_frame, text='Pick a folder \u2192 click "Scan" to load .vtt files.',
            foreground="gray",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        # ---- file list with checkboxes ---------------------------------------
        list_frame = ttk.LabelFrame(frame, text="Files to Convert", padding=8)
        list_frame.grid(row=2, column=0, sticky="nsew", pady=4)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        frame.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(list_frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        ttk.Button(
            toolbar, text="Select All", command=lambda: self._file_list.toggle_all(True),
        ).pack(side="left", padx=2)
        ttk.Button(
            toolbar, text="Deselect All", command=lambda: self._file_list.toggle_all(False),
        ).pack(side="left", padx=2)
        self._count_label = ttk.Label(toolbar, text="0 file(s)", foreground="gray")
        self._count_label.pack(side="right", padx=2)

        self._file_list = CheckboxListFrame(list_frame)
        self._file_list.grid(row=1, column=0, sticky="nsew")

        # ---- format selector --------------------------------------------------
        fmt_frame = ttk.LabelFrame(frame, text="Output Format", padding=8)
        fmt_frame.grid(row=3, column=0, sticky="ew", pady=(0, 4))

        self.fmt_var = tk.StringVar(value="lrc")
        ttk.Radiobutton(
            fmt_frame, text="LRC  —  [00:05.07]Subtitle text  (compact, start time only)",
            variable=self.fmt_var, value="lrc",
        ).pack(anchor="w")
        ttk.Radiobutton(
            fmt_frame,
            text="SRT  —  standard SubRip format  (indexed, start & end times)",
            variable=self.fmt_var, value="srt",
        ).pack(anchor="w", pady=(2, 0))

        # ---- output directory -------------------------------------------------
        out_frame = ttk.LabelFrame(frame, text="Output Directory", padding=8)
        out_frame.grid(row=4, column=0, sticky="ew", pady=(4, 0))
        out_frame.columnconfigure(1, weight=1)

        self.out_dir_var = tk.StringVar()
        ttk.Entry(
            out_frame, textvariable=self.out_dir_var, width=50,
        ).grid(row=0, column=0, columnspan=2, sticky="ew", padx=(0, 4))
        ttk.Button(
            out_frame, text="Browse...", command=self._select_output_folder,
        ).grid(row=0, column=2, sticky="e")
        ttk.Label(
            out_frame,
            text="Leave empty to save files next to the original .vtt files.",
            foreground="gray",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(4, 0))

        # ---- progress bar ----------------------------------------------------
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.grid(row=5, column=0, sticky="ew", pady=(8, 2))

        self.status_label = ttk.Label(frame, text="Ready.", anchor="w")
        self.status_label.grid(row=6, column=0, sticky="ew")

        # ---- buttons ---------------------------------------------------------
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=7, column=0, sticky="ew", pady=(8, 0))

        ttk.Button(
            btn_frame, text="Add Files", command=self._add_files,
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="Clear", command=self._clear,
        ).pack(side="left", padx=2)
        ttk.Button(
            btn_frame, text="Convert", command=self._convert,
        ).pack(side="right", padx=2)

        # ---- drag-drop support -----------------------------------------------
        try:
            from tkinterdnd2 import DND_FILES
            from tkinterdnd2 import TkinterDnD

            if isinstance(root, TkinterDnD.Tk):
                root.drop_target_register(DND_FILES)
                root.dnd_bind("<<Drop>>", self._on_drop)
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _select_source_folder(self):
        path = filedialog.askdirectory(title="Select Source Folder")
        if path:
            self.src_dir_var.set(path)

    def _scan_folder(self):
        src_dir = self.src_dir_var.get().strip()
        if not src_dir:
            messagebox.showwarning("No Folder", "Please select a source folder first.")
            return
        if not os.path.isdir(src_dir):
            messagebox.showerror("Invalid Folder", f"Folder not found:\n{src_dir}")
            return

        self._clear()
        vtt_files = sorted(
            p for p in Path(src_dir).iterdir()
            if p.is_file() and p.suffix.lower() == ".vtt"
        )
        if not vtt_files:
            messagebox.showinfo("No VTT Files", f"No .vtt files found in:\n{src_dir}")
            return

        for p in vtt_files:
            self._file_list.add(str(p))
        self._update_count()

    def _update_count(self):
        n = self._file_list.file_count
        self._count_label.configure(text=f"{n} file(s)")

    def _select_output_folder(self):
        path = filedialog.askdirectory(title="Select Output Directory")
        if path:
            self.out_dir_var.set(path)

    def _add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select VTT Files",
            filetypes=[("WebVTT Files", "*.vtt"), ("All Files", "*.*")],
        )
        for p in paths:
            self._file_list.add(p)
        self._update_count()

    def _clear(self):
        self._file_list.clear()
        self._update_count()

    def _on_drop(self, event):
        for item in self.root.splitlist(event.data):
            p = item.strip("{}")
            if p.lower().endswith(".vtt"):
                self._file_list.add(p)
        self._update_count()

    def _convert(self):
        files = self._file_list.checked_files
        if not files:
            messagebox.showwarning("No Files", "Select at least one file to convert.")
            return

        fmt = self.fmt_var.get()
        ext = f".{fmt}"
        out_dir = self.out_dir_var.get().strip()
        total = len(files)
        failed: list[str] = []
        self.progress["maximum"] = total
        self.progress["value"] = 0
        self.status_label.configure(text="Converting...")

        from vtt2srt import vtt_to_srt

        def _worker():
            for i, src in enumerate(files):
                try:
                    if out_dir:
                        out_name = Path(src).with_suffix(ext).name
                        out_path = os.path.join(out_dir, out_name)
                        vtt_to_srt(src, out_path, fmt=fmt)
                    else:
                        vtt_to_srt(src, fmt=fmt)
                except Exception as e:
                    failed.append(f"{os.path.basename(src)}: {e}")
                self.root.after(0, lambda idx=i: self._tick(idx, total))

            self.root.after(0, lambda: self._done(total, failed))

        threading.Thread(target=_worker, daemon=True).start()

    def _tick(self, idx, total):
        self.progress["value"] = idx + 1
        self.status_label.configure(text=f"Converting... {idx + 1}/{total}")

    def _done(self, total, failed):
        if failed:
            detail = "\n".join(failed[:10])
            if len(failed) > 10:
                detail += f"\n... and {len(failed) - 10} more"
            messagebox.showerror(
                "Conversion Errors",
                f"{len(failed)}/{total} file(s) failed:\n\n{detail}",
            )
        else:
            messagebox.showinfo("Done", f"Successfully converted {total} file(s).")
        self.status_label.configure(
            text=f"Done. {total - len(failed)}/{total} succeeded."
            if failed else f"Done. {total} file(s) converted."
        )
        self.progress["value"] = 0


def main():
    root = tk.Tk()
    Vtt2SrtApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
