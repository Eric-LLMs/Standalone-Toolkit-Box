# 🛠️ Standalone Toolkit Box

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)

**A curated collection of atomic, standalone Python scripts and GUI utilities for daily automation.**

## 💡 Core Philosophy

This repository embraces a strictly **"Standalone"** design philosophy:
* 🚫 **Zero Coupling:** Every tool here is an independent universe. There are absolutely no code dependencies between Tool A and Tool B.
* 📦 **Isolated Environments:** Each tool directory contains its own `requirements.txt` or environment setup. Say goodbye to dependency hell.
* 🚀 **Plug & Play:** Need a specific utility? Just navigate to its directory and run it. No bloated global installations are required at the root level.

---

## 🧰 Tool Directory

Click on a tool's name to navigate to its dedicated directory and view detailed usage instructions.

| Tool Name | Category | Description | Tech Stack |
| :--- | :--- | :--- | :--- |
| 🎬 **[Audio Segmenter](./audio-segmenter/)** | Media Processing | Extracts audio from video and precisely slices it based on `.srt` or `.lrc` subtitle timestamps. Supports both GUI and CLI. | `Tkinter`, `moviepy`, `pydub` |
| 🚧 *(Upcoming Tool)* | TBD | ... | ... |
| 🚧 *(Upcoming Tool)* | TBD | ... | ... |

*(More handy utilities coming soon...)*

---

## 🚀 Getting Started

**⚠️ Important: Do NOT install dependencies at the root level of this repository.**

1. Clone this repository to your local machine:
   ```bash
   git clone https://github.com/your-username/Standalone-Toolkit-Box.git
   cd Standalone-Toolkit-Box


2. Pick the tool you need from the directory above and navigate to its folder. For example:
```bash
cd audio-segmenter

```


3. Read the `README.md` located *inside* that specific tool's folder for instructions on setting up its isolated environment and running the scripts.

---

## 🏗️ Development & Contribution Guidelines

If you plan to add a new "gadget" to this toolkit, you must strictly follow these "atomic" rules:

1. **Independent Folder:** Create a dedicated folder for the new tool (use `kebab-case` naming, e.g., `my-new-tool`).
2. **Exclusive Environment:** You must provide a `requirements.txt` specifically inside the tool's folder.
3. **Standalone Documentation:** Include a dedicated `README.md` inside the tool's folder detailing its specific parameters and usage.
4. **Path Safety:** Never use absolute paths within the tool's code, and strictly prohibit cross-directory imports from other tools in the box.

```
