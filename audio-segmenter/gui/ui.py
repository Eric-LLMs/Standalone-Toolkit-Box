import tkinter as tk
from tkinter import filedialog, messagebox
import threading
from core.processor import SegmentProcessor


class AudioSegmenterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Audio Segmenter Tool")
        # Increased window size to prevent button cut-offs and enabled resizing
        self.root.geometry("700x550")
        self.root.resizable(True, True)

        self.video_path_var = tk.StringVar()
        self.srt_path_var = tk.StringVar()
        self.output_dir_var = tk.StringVar()

        self._setup_ui()

    def _setup_ui(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        header_label = tk.Label(main_frame, text="Audio Segmentation Tool", font=("Arial", 16, "bold"))
        header_label.pack(pady=(0, 20))

        input_group = tk.LabelFrame(main_frame, text="Input Selection", padx=10, pady=10)
        input_group.pack(fill=tk.X, pady=5)

        self._create_path_selector(input_group, "Video File (.mp4, etc.):", self.video_path_var, self._browse_video)

        # Updated label to reflect dual format support
        self._create_path_selector(input_group, "Subtitle File (.srt, .lrc):", self.srt_path_var, self._browse_srt)

        output_group = tk.LabelFrame(main_frame, text="Output Configuration", padx=10, pady=10)
        output_group.pack(fill=tk.X, pady=10)

        self._create_path_selector(output_group, "Output Directory:", self.output_dir_var, self._browse_output,
                                   is_dir=True)

        start_btn = tk.Button(main_frame, text="▶ Start Segmentation", command=self._start_process_thread,
                              bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), height=2)
        start_btn.pack(fill=tk.X, pady=(20, 10))

        self.status_label = tk.Label(main_frame, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#f0f0f0",
                                     pady=5)
        self.status_label.pack(fill=tk.X, side=tk.BOTTOM)

    def _create_path_selector(self, parent, label_text, path_var, browse_command, is_dir=False):
        frame = tk.Frame(parent)
        frame.pack(fill=tk.X, pady=5)

        # Increased label width to fit the text properly
        lbl = tk.Label(frame, text=label_text, width=25, anchor=tk.W)
        lbl.pack(side=tk.LEFT)

        entry = tk.Entry(frame, textvariable=path_var)
        entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        btn_text = "Browse Folder..." if is_dir else "Browse File..."
        btn = tk.Button(frame, text=btn_text, command=browse_command)
        btn.pack(side=tk.LEFT)

    def _browse_video(self):
        filename = filedialog.askopenfilename(title="Select Video File",
                                              filetypes=(
                                              ("Video files", "*.mp4 *.mkv *.mov *.avi"), ("All files", "*.*")))
        if filename: self.video_path_var.set(filename)

    def _browse_srt(self):
        # Added .lrc to the file filter
        filename = filedialog.askopenfilename(title="Select Subtitle File",
                                              filetypes=(("Subtitle files", "*.srt *.lrc"), ("All files", "*.*")))
        if filename: self.srt_path_var.set(filename)

    def _browse_output(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname: self.output_dir_var.set(dirname)

    def _update_status(self, message):
        self.status_label.config(text=f" Status: {message}")
        self.root.update_idletasks()

    def _start_process_thread(self):
        if not self.video_path_var.get() or not self.srt_path_var.get() or not self.output_dir_var.get():
            messagebox.showerror("Error", "Please select all input paths and the output directory.")
            return

        processing_thread = threading.Thread(target=self._run_process_logic, daemon=True)
        processing_thread.start()

    def _run_process_logic(self):
        try:
            processor = SegmentProcessor(
                video_path=self.video_path_var.get(),
                srt_path=self.srt_path_var.get(),
                output_dir=self.output_dir_var.get(),
                status_callback=self._update_status
            )
            processor.run()
            messagebox.showinfo("Success", "Segmentation complete! Check output folder.")

        except Exception as e:
            err_msg = f"An error occurred:\n{str(e)}\n\nEnsure FFmpeg is installed."
            self._update_status("Error during processing.")
            messagebox.showerror("Processing Error", err_msg)
            print(f"GUI Error Catch: {e}")