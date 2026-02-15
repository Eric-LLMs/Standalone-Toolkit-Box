import os
import sys

# ==========================================
# PyInstaller FFmpeg Path Routing
# ==========================================
if getattr(sys, 'frozen', False):
    # If running as a bundled executable, point to the extracted temp folder
    bundle_dir = sys._MEIPASS
    ffmpeg_path = os.path.join(bundle_dir, "ffmpeg.exe")
    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_path

import tkinter as tk
from gui.ui import AudioSegmenterApp

# This file is the entry point for building the exe.
# It initializes the Tkinter root window and starts the main loop.

if __name__ == "__main__":
    try:
        # Attempt to handle high DPI displays on Windows for sharper UI
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass # Fail silently on non-Windows systems

    root = tk.Tk()
    app = AudioSegmenterApp(root)
    # Set a basic icon if available (ensure assets folder exists if using this)
    # root.iconbitmap("assets/icon.ico")
    root.mainloop()