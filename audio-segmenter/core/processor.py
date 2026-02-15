import os
import csv
import hashlib
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from .subtitle_parser import parse_srt_file, parse_lrc_file


class SegmentProcessor:
    def __init__(self, video_path, srt_path, output_dir, status_callback=None):
        self.video_path = video_path
        self.srt_path = srt_path
        self.output_dir = output_dir
        self.segments_dir = os.path.join(self.output_dir, "audio_segments")
        self.csv_path = os.path.join(self.output_dir, "metadata.csv")
        self.status_callback = status_callback

    def _update_status(self, message, percent=None):
        """Helper to safely trigger the callback with percentage data."""
        if self.status_callback:
            try:
                # GUI Callback handles (message, percent)
                self.status_callback(message, percent)
            except TypeError:
                # CLI Callback fallback
                if percent is not None:
                    self.status_callback(f"{message} ({percent}%)")
                else:
                    self.status_callback(message)

    def _ensure_dirs(self):
        os.makedirs(self.segments_dir, exist_ok=True)

    def _extract_full_audio(self):
        self._update_status("Extracting full audio track from video (this may take a while)...", 10)
        temp_audio_path = os.path.join(self.output_dir, "temp_full.mp3")

        if not os.path.exists(self.video_path):
            raise FileNotFoundError(f"Video file path invalid: {self.video_path}")

        try:
            video = VideoFileClip(self.video_path)
            video.audio.write_audiofile(temp_audio_path, bitrate="192k", verbose=False, logger=None)
            video.close()
            return temp_audio_path
        except Exception as e:
            self._update_status(f"Error during extraction: {e}")
            raise e

    def _generate_filename(self, index, text_snippet):
        hash_input = f"{index}-{text_snippet}".encode('utf-8')
        filename_hash = hashlib.md5(hash_input).hexdigest()[:12]
        return f"seg_{filename_hash}.mp3"

    def run(self):
        self._ensure_dirs()
        csv_data = []

        self._update_status("Parsing subtitle file...", 2)

        if self.srt_path.lower().endswith('.lrc'):
            segments_data = parse_lrc_file(self.srt_path)
        else:
            segments_data = parse_srt_file(self.srt_path)

        total_segments = len(segments_data)

        if total_segments == 0:
            self._update_status("Error: No valid segments found in subtitle file.", 0)
            return

        # 10% progress reaches here
        temp_audio_path = self._extract_full_audio()

        self._update_status("Loading audio into memory for slicing...", 30)
        full_audio = AudioSegment.from_file(temp_audio_path)

        self._update_status(f"Starting segmentation of {total_segments} clips...", 35)

        for i, seg in enumerate(segments_data):
            start_ms = seg['start_ms']
            end_ms = seg['end_ms']
            text = seg['text']

            if start_ms >= end_ms or start_ms > len(full_audio):
                continue

            clip = full_audio[start_ms:end_ms]

            filename = self._generate_filename(seg['index'], text[:10])
            output_path = os.path.join(self.segments_dir, filename)

            clip.export(output_path, format="mp3")
            csv_data.append([text, os.path.abspath(output_path), filename])

            # Calculate progress mapping from 35% to 95%
            current_progress = 35 + int(((i + 1) / total_segments) * 60)

            if (i + 1) % 2 == 0 or (i + 1) == total_segments:
                self._update_status(f"Processed {i + 1}/{total_segments} segments.", current_progress)

        self._update_status("Writing CSV metadata file...", 98)
        with open(self.csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Transcript Text', 'Absolute Audio Path', 'Hashed Filename'])
            writer.writerows(csv_data)

        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

        self._update_status(f"Completed! Output saved to: {self.output_dir}", 100)