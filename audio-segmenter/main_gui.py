import os
import sys
import subprocess
import tkinter as tk
from gui.ui import AudioSegmenterApp

# ==========================================
# Suppress Subprocess Console Windows
# ==========================================
if os.name == 'nt':
    _original_popen = subprocess.Popen


    def _patched_popen(*args, **kwargs):
        if 'creationflags' not in kwargs:
            kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
        else:
            kwargs['creationflags'] |= subprocess.CREATE_NO_WINDOW
        return _original_popen(*args, **kwargs)


    subprocess.Popen = _patched_popen

# ==========================================
# Portable Environment Configuration
# ==========================================
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS

    ffmpeg_bin = os.path.join(bundle_dir, "ffmpeg.exe")
    ffprobe_bin = os.path.join(bundle_dir, "ffprobe.exe")

    os.environ["IMAGEIO_FFMPEG_EXE"] = ffmpeg_bin
    os.environ["PATH"] = bundle_dir + os.pathsep + os.environ.get("PATH", "")

# ==========================================
# Application Entry Point
# ==========================================
if __name__ == "__main__":
    root = tk.Tk()
    app = AudioSegmenterApp(root)
    root.mainloop()