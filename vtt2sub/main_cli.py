"""CLI entry point for VTT subtitle conversion (LRC / SRT)."""

import argparse
import sys

from vtt2srt import vtt_to_srt


def main():
    parser = argparse.ArgumentParser(
        description="Convert WebVTT (.vtt) subtitles to LRC or SRT format.",
    )
    parser.add_argument(
        "input", nargs="?", help="Path to the source .vtt file.",
    )
    parser.add_argument(
        "-o", "--output", default=None,
        help="Path for the output file (default: same name, .lrc or .srt extension).",
    )
    parser.add_argument(
        "-b", "--batch", nargs="+", default=None,
        help="Batch convert multiple .vtt files.",
    )
    parser.add_argument(
        "-f", "--fmt", default="lrc", choices=["lrc", "srt"],
        help="Output format: lrc (compact) or srt (standard). Default: lrc.",
    )
    args = parser.parse_args()

    if not args.input and not args.batch:
        parser.error("Either provide an input file or use -b for batch mode.")

    try:
        if args.batch:
            for f in args.batch:
                out = vtt_to_srt(f, fmt=args.fmt)
                print(f"  OK: {f} -> {out}")
        else:
            out = vtt_to_srt(args.input, args.output, fmt=args.fmt)
            print(f"OK: {args.input} -> {out}")
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
