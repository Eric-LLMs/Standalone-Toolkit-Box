import os
import sys
import subprocess
import threading
import hashlib
import csv
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ==========================================
# 1. 全局猴子补丁 (Monkey Patch) - 必须在顶部！
# 拦截所有底层 subprocess 调用，强制隐藏 FFmpeg 黑框
# ==========================================
if os.name == 'nt':
    _original_popen = subprocess.Popen


    def _patched_popen(*args, **kwargs):
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW | kwargs.get('creationflags', 0)
        return _original_popen(*args, **kwargs)


    subprocess.Popen = _patched_popen

# ==========================================
# 2. PyInstaller 环境变量配置
# 确保打包后的 exe 能找到内置的 ffmpeg.exe
# ==========================================
if getattr(sys, 'frozen', False):
    bundle_dir = sys._MEIPASS
    os.environ["IMAGEIO_FFMPEG_EXE"] = os.path.join(bundle_dir, "ffmpeg.exe")
    os.environ["PATH"] = bundle_dir + os.pathsep + os.environ.get("PATH", "")

# 必须在补丁和环境变量配置完成后，再导入音视频处理库
import moviepy.editor as mp
from pydub import AudioSegment


class AudioSegmenterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Segmenter v1.2 - Stable")
        self.root.geometry("600x400")
        self.root.resizable(False, False)

        # Variables
        self.video_path = tk.StringVar()
        self.subtitle_path = tk.StringVar()
        self.output_dir = tk.StringVar()

        self.create_widgets()

    def create_widgets(self):
        padding = {'padx': 10, 'pady': 10}

        # Video Row
        tk.Label(self.root, text="Video File:").grid(row=0, column=0, sticky="e", **padding)
        tk.Entry(self.root, textvariable=self.video_path, width=50).grid(row=0, column=1, **padding)
        tk.Button(self.root, text="Browse", command=self.browse_video).grid(row=0, column=2, **padding)

        # Subtitle Row
        tk.Label(self.root, text="Subtitle (.srt/.lrc):").grid(row=1, column=0, sticky="e", **padding)
        tk.Entry(self.root, textvariable=self.subtitle_path, width=50).grid(row=1, column=1, **padding)
        tk.Button(self.root, text="Browse", command=self.browse_subtitle).grid(row=1, column=2, **padding)

        # Output Row
        tk.Label(self.root, text="Output Directory:").grid(row=2, column=0, sticky="e", **padding)
        tk.Entry(self.root, textvariable=self.output_dir, width=50).grid(row=2, column=1, **padding)
        tk.Button(self.root, text="Browse", command=self.browse_output).grid(row=2, column=2, **padding)

        # Progress Bar & Status
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.grid(row=3, column=0, columnspan=3, pady=(20, 5))

        self.status_label = tk.Label(self.root, text="Ready to process.", fg="blue")
        self.status_label.grid(row=4, column=0, columnspan=3)

        # Start Button
        self.start_btn = tk.Button(self.root, text="Start Segmentation", command=self.start_processing, bg="#4CAF50",
                                   fg="white", font=("Arial", 10, "bold"))
        self.start_btn.grid(row=5, column=0, columnspan=3, pady=20, ipadx=20, ipady=5)

    def browse_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.mp4 *.mkv *.avi")])
        if path: self.video_path.set(path)

    def browse_subtitle(self):
        path = filedialog.askopenfilename(filetypes=[("Subtitle Files", "*.srt *.lrc")])
        if path: self.subtitle_path.set(path)

    def browse_output(self):
        path = filedialog.askdirectory()
        if path: self.output_dir.set(path)

    def update_status(self, msg, progress=None):
        """Thread-safe GUI update"""
        self.root.after(0, lambda: self.status_label.config(text=msg))
        if progress is not None:
            self.root.after(0, lambda: self.progress_var.set(progress))

    def parse_lrc(self, file_path):
        """
        [FIXED]: Supports both [MM:SS.xx] and [HH:MM:SS.xx]
        [FIXED]: Merges consecutive lines with identical timestamps to avoid
                 zero-duration segments that cause ffmpeg errors.
        """
        subs = []
        pattern = re.compile(r'\[(?:(\d{2}):)?(\d{2}):(\d{2}\.\d{1,3})\]')

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Step 1: Extract raw timestamp-text pairs
        raw_items = []
        for line in lines:
            match = pattern.search(line)
            if match:
                h, m, s = match.groups()
                h = int(h) if h else 0
                m = int(m)
                s = float(s)
                start_time = h * 3600 + m * 60 + s
                text = line[match.end():].strip()
                if text:
                    raw_items.append({'start': start_time, 'text': text})

        if not raw_items:
            return subs

        # Step 2: Merge consecutive items with the same timestamp (within 1ms)
        merged_items = []
        for item in raw_items:
            if merged_items and abs(merged_items[-1]['start'] - item['start']) < 0.001:
                merged_items[-1]['text'] += " " + item['text']
            else:
                merged_items.append({'start': item['start'], 'text': item['text']})

        # Step 3: Compute end times from the next different timestamp
        for i, item in enumerate(merged_items):
            if i < len(merged_items) - 1:
                end_time = merged_items[i + 1]['start']
            else:
                end_time = item['start'] + 5.0  # Default 5s for the last line
            subs.append({
                'start': item['start'],
                'end': end_time,
                'text': item['text'],
            })
        return subs

    def parse_srt(self, file_path):
        subs = []
        with open(file_path, 'r', encoding='utf-8') as f:
            blocks = f.read().strip().split('\n\n')

        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                time_line = lines[1]
                text = " ".join(lines[2:]).strip()

                # Parse 00:00:00,000 --> 00:00:00,000
                times = time_line.split(' --> ')
                if len(times) == 2:
                    start_str = times[0].replace(',', '.')
                    end_str = times[1].replace(',', '.')

                    def time_to_sec(t_str):
                        h, m, s = t_str.split(':')
                        return int(h) * 3600 + int(m) * 60 + float(s)

                    start_time = time_to_sec(start_str)
                    end_time = time_to_sec(end_str)
                    subs.append({'start': start_time, 'end': end_time, 'text': text})
        return subs

    def process_audio(self):
        video = self.video_path.get()
        sub = self.subtitle_path.get()
        out_dir = self.output_dir.get()

        if not all([video, sub, out_dir]):
            self.root.after(0, lambda: messagebox.showerror("Error", "Please select all files and output directory."))
            self.update_status("Error: Missing inputs.")
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            return

        try:
            self.update_status("Parsing subtitle file...", 0)
            if sub.lower().endswith('.lrc'):
                subtitles = self.parse_lrc(sub)
            elif sub.lower().endswith('.srt'):
                subtitles = self.parse_srt(sub)
            else:
                raise ValueError("Unsupported subtitle format.")

            total_subs = len(subtitles)
            if total_subs == 0:
                raise ValueError("No valid subtitle timestamps found.")

            self.update_status("Extracting audio from video (this may take a moment)...", 5)
            temp_audio_path = os.path.join(out_dir, "temp_full_audio.wav")
            video_clip = mp.VideoFileClip(video)
            video_clip.audio.write_audiofile(temp_audio_path, logger=None)  # logger=None hides moviepy console output
            video_clip.close()

            self.update_status("Loading audio into memory...", 10)
            full_audio = AudioSegment.from_file(temp_audio_path)

            csv_data = []

            for i, item in enumerate(subtitles):
                start_ms = int(item['start'] * 1000)
                end_ms = int(item['end'] * 1000)

                if start_ms >= end_ms:
                    continue

                # Skip segments that start beyond the audio duration
                audio_len_ms = len(full_audio)
                if start_ms >= audio_len_ms:
                    continue

                # Clamp end time to audio length (video may be shorter than subtitles)
                if end_ms > audio_len_ms:
                    end_ms = audio_len_ms

                text = item['text']

                # Generate MD5 hash for filename
                hash_md5 = hashlib.md5(text.encode('utf-8')).hexdigest()[:12]
                file_name = f"seg_{hash_md5}.mp3"
                out_path = os.path.join(out_dir, file_name)

                # Slice and export
                segment = full_audio[start_ms:end_ms]
                segment.export(out_path, format="mp3")

                csv_data.append([text, os.path.abspath(out_path), file_name])

                # Update progress
                progress = 10 + (i + 1) / total_subs * 90
                self.update_status(f"Processing {i + 1}/{total_subs} clips...", progress)

            self.update_status("Saving metadata.csv...", 99)
            csv_path = os.path.join(out_dir, "metadata.csv")
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['Transcript Text', 'Absolute Audio Path', 'Hashed Filename'])
                writer.writerows(csv_data)

            # Cleanup temp file
            if os.path.exists(temp_audio_path):
                os.remove(temp_audio_path)

            self.update_status("Segmentation Complete! 🎉", 100)
            self.root.after(0, lambda: messagebox.showinfo("Success", f"Successfully extracted {total_subs} clips!"))

        except Exception as e:
            self.update_status(f"Error: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Processing Error", str(e)))

        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))

    def start_processing(self):
        self.start_btn.config(state=tk.DISABLED)
        # Run in a separate thread to prevent GUI freezing
        threading.Thread(target=self.process_audio, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    app = AudioSegmenterApp(root)
    root.mainloop()