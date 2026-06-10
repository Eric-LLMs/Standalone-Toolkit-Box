#!/usr/bin/env python3
"""CRTubeGet — YouTube Video/Playlist Downloader with GUI.

Usage:
    python CRTubeGet.py

For packaging into a standalone executable, see README.md.
"""

import tkinter as tk

from crtubeget.app import CRTubeGetApp


def main():
    root = tk.Tk()
    CRTubeGetApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
