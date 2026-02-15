# 🎬 Audio Segmenter Tool

**A standalone utility to extract audio from video and split it into segments based on SRT subtitles.**

This tool is designed for creating speech-to-text datasets, language learning materials, or quickly extracting dialog clips. It processes a video file and a corresponding subtitle file, outputting individual MP3 clips and a CSV metadata file linking text to audio.

## 🌟 Features

* **Dual Format Support:** Native support for both `.srt` and `.lrc` lyrics files.
* **Precise Cutting:** Uses Millisecond-level precision.
* **Hashed Filenames:** Generates unique, hashed filenames for segments to avoid conflicts.
* **Dual Interfaces:** Includes both a Command Line Interface (CLI) for automation and a GUI for ease of use on Windows.
* **CSV Metadata:** Outputs a 3-column CSV: `Transcript Text, Absolute Audio Path, Hashed Filename`.

---

## 📂 Project Structure

This tool follows a modular architecture, separating the core processing logic from the user interface:

```text
audio-segmenter/
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── srt_parser.py       # Parses subtitles & handles time formatting
│   ├── subtitle_parser.py  # Parses subtitles & handles time formatting, supports both SRT and LRC
│   └── processor.py        # Audio extraction, slicing, and CSV generation
├── gui/                    # Graphical User Interface
│   ├── __init__.py
│   └── ui.py               # Tkinter layout and threading logic
├── output/                 # Default directory for generated files
├── main_cli.py             # Entry point for Command Line Interface
├── main_gui.py             # Entry point for GUI (Used for building .exe)
├── requirements.txt        # Python dependencies list
└── README.md               # This documentation file

```

---

## 🛠️ Prerequisites

Before using this tool, you must have the following installed:

### 1. Python 3.8+

Ensure Python is installed and added to your system PATH.

### 2. FFmpeg (Crucial Requirement)

This tool relies on FFmpeg for media processing. It must be installed and accessible via your system's command line.

* **Windows:** [Download build](https://www.gyan.dev/ffmpeg/builds/), extract it, and add the `bin` folder to your System Environment Variables (PATH).
* **macOS (Homebrew):** `brew install ffmpeg`
* **Linux (apt):** `sudo apt update && sudo apt install ffmpeg`

---

## 📦 Installation (Conda Recommended)

We highly recommend using [Conda](https://docs.conda.io/en/latest/miniconda.html) for this project because it can automatically handle the FFmpeg dependency, saving you from manual system PATH configurations.

1.  **Navigate to the tool directory:**
    ```bash
    cd audio-segmenter
    ```

2.  **Create a new Conda environment:**
    *(We recommend Python 3.9 or 3.10 for best compatibility)*
    ```bash
    conda create -n audio-segmenter python=3.10 -y
    ```

3.  **Activate the environment:**
    ```bash
    conda activate audio-segmenter
    ```

4.  **Install FFmpeg via Conda-Forge:**
    *(This is the magic step! No manual downloading required)*
    ```bash
    conda install -c conda-forge ffmpeg -y
    ```

5.  **Install the required Python packages:**
    ```bash
    pip install -r requirements.txt
    ```
  
---

## 🖥️ Usage (GUI - Windows Version)

For desktop users, the graphical interface is the easiest method.

1. Run the GUI launcher script:
```bash
python main_gui.py  
```


*(Or run the compiled `.exe` if you have built it).*
2. **Select Inputs:**
* Click **Browse Video** to select your source media file (mp4, mkv, etc.).
* Click **Browse Subtitle** to select the matching subtitle file (`.srt` or `.lrc`).
* Click **Browse Output** to choose where the folder of clips and the CSV will be saved.


3. **Run:**
* Click **Start Segmentation**. The status bar at the bottom will update progress.
* Upon completion, find the `metadata.csv` and an `audio_segments` folder in your output directory.



**CSV Output Format (3 Columns):**
`Transcript Text, Absolute Audio Path, Hashed Filename`

---

## ⌨️ Usage (CLI - Command Line)

For developers or server automation.

```bash
python main_cli.py --video /path/to/video.mp4 --subtitle /path/to/subs.lrc --output /path/to/output_dir
```

**Arguments:**

* `--video`: Path to the source video file.
* `--subtitle`: Path to the SRT or LRC subtitle file.
* `--output`: (Optional) Directory to save output. Defaults to `./output`.

---



##  🏗️ Building a Truly Portable Windows EXE

By default, the `.exe` requires FFmpeg to be installed on the target system. To create a **completely standalone** version that includes FFmpeg inside the `.exe`, follow these steps:

### 1. Requirements for Building

You can package this tool into a single `.exe` file that runs on any Windows machine **without** requiring Python or a pre-installed FFmpeg.

* Download `ffmpeg.exe` (Version 5.0+ recommended, "Release Essentials" version) (e.g., from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/)) .
* Place `ffmpeg.exe` in the root of the `audio-segmenter/` folder (next to `main_gui.py`).
* Ensure you have modified `main_gui.py` to include the `sys._MEIPASS` path routing logic.

### 2. Run the Portable Build Command
This command bundles the FFmpeg binary, your code, and the required metadata into a single executable file.
(the --clean and --copy-metadata imageio flags are strictly required) from the root directory

```bash
pyinstaller --noconfirm --clean --onefile --windowed --name "AudioSegmenter" --copy-metadata imageio --add-data "core;core" --add-data "gui;gui" --add-binary "ffmpeg.exe;." main_gui.py
```

- File Size: The file will be around 80MB-120MB because it now contains the FFmpeg engine.
- Portability: You can now copy this AudioSegmenter.exe to a computer that has zero Python or FFmpeg installed, and it will work perfectly.

---

### 3. The resulting `AudioSegmenter.exe` will be found in the `dist/` folder.


