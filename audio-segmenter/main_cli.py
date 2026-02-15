import argparse
import os
from core.processor import SegmentProcessor


def main():
    parser = argparse.ArgumentParser(description="CLI for Audio Segmentation Tool")
    parser.add_argument("--video", required=True, help="Path to source video file")
    # Updated to reflect support for both subtitle formats
    parser.add_argument("--subtitle", required=True, help="Path to source subtitle file (.srt or .lrc)")
    parser.add_argument("--output", default="./output", help="Directory for output files")

    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"Error: Video file not found at {args.video}")
        return
    if not os.path.isfile(args.subtitle):
        print(f"Error: Subtitle file not found at {args.subtitle}")
        return

    print("--- Starting Audio Segmentation (CLI Mode) ---")
    try:
        processor = SegmentProcessor(args.video, args.subtitle, args.output, status_callback=print)
        processor.run()
    except Exception as e:
        print(f"\nFatal Error: {e}")
        print("Please ensure FFmpeg is installed correctly.")


if __name__ == "__main__":
    main()