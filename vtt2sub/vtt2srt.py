"""VTT subtitle converter — pure stdlib, zero dependencies.

Supports two output formats:

  LRC  — [MM:SS.ms]Text (compact, start time only)
  SRT  — standard SubRip format (indexed, start --> end)
"""

import re
from pathlib import Path

# Flexible VTT timestamp regex — supports:
#   HH:MM:SS.mmm   (hours optional, ms 2-3 digits)
#   MM:SS.mmm
#   MM:SS.mm
_TS_RE = re.compile(
    r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{1,3})"
    r"\s*-->\s*"
    r"(?:(\d+):)?(\d{2}):(\d{2})\.(\d{1,3})"
)


def vtt_to_srt(vtt_path: str | Path, srt_path: str | Path | None = None,
               fmt: str = "lrc") -> str:
    """Convert a WebVTT file to LRC or SRT format.

    Args:
        vtt_path: Path to the source .vtt file.
        srt_path: Path for the output file (default: same name, extension from *fmt*).
        fmt: Output format — ``"lrc"`` or ``"srt"``.

    Returns:
        The path where the output file was written.

    Raises:
        FileNotFoundError: If *vtt_path* does not exist.
        ValueError: If the file contains no valid subtitle cues or *fmt* is unknown.
    """
    fmt = fmt.lower()
    if fmt not in ("lrc", "srt"):
        raise ValueError(f"Unknown format: {fmt!r}. Choose 'lrc' or 'srt'.")

    vtt_path = Path(vtt_path)

    if not vtt_path.exists():
        raise FileNotFoundError(f"File not found: {vtt_path}")

    ext = f".{fmt}"
    if srt_path is None:
        srt_path = vtt_path.with_suffix(ext)
    else:
        srt_path = Path(srt_path)

    raw = vtt_path.read_text(encoding="utf-8-sig")

    # ---- strip WEBVTT header block -----------------------------------------
    body = _strip_header(raw)
    if not body:
        raise ValueError("No subtitle content found in VTT file")

    # ---- split into cue blocks by double-newlines --------------------------
    # YouTube VTT puts a whitespace-only line inside each cue, so using
    # single blank lines as separators would break cues apart.
    raw_blocks = re.split(r"\n{2,}", body)

    cues: list[dict] = []
    for raw_block in raw_blocks:
        lines = raw_block.splitlines()
        ts_line = ""
        text_lines: list[str] = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue  # skip whitespace-only lines within a cue
            if "-->" in stripped:
                ts_line = stripped
            elif not stripped.startswith(("NOTE", "STYLE", "REGION")):
                clean = _strip_vtt_tags(stripped)
                if clean:
                    text_lines.append(clean)

        if not ts_line or not text_lines:
            continue

        m = _TS_RE.search(ts_line)
        if not m:
            continue

        cues.append({
            "start": _parse_ts_groups(m, 1),
            "end":   _parse_ts_groups(m, 5),
            "text_lines": text_lines,
        })

    if not cues:
        raise ValueError("No valid subtitle cues found in VTT file")

    # ---- write output -------------------------------------------------------
    if fmt == "lrc":
        output = _build_lrc(cues)
    else:
        output = _build_srt(cues)

    srt_path.write_text(output, encoding="utf-8")
    return str(srt_path)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _strip_header(raw: str) -> str:
    """Remove the WEBVTT header block (up to the first blank line)."""
    if not raw.startswith("WEBVTT"):
        return raw.strip()
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    idx = raw.find("\n\n")
    if idx == -1:
        idx = raw.find("\n")
        if idx == -1:
            return ""
        return raw[idx + 1:].strip()
    return raw[idx + 2:].strip()


def _strip_vtt_tags(line: str) -> str:
    """Strip all VTT markup: <c>, <v>, <b>, <i>, word-level timestamps, etc."""
    # Remove word-level timestamp tags like <00:00:05.680>
    line = re.sub(r"<\d+:\d{2}:\d{2}\.\d{1,3}>", "", line)
    # Remove <c.xxx>, <c>, </c> (color/class spans — multi-class support)
    line = re.sub(r"</?c(?:\.\w+)*>", "", line)
    # Remove <v.xxx>, <v>, </v> (voice spans)
    line = re.sub(r"</?v(?:\.\w+)*>", "", line)
    # Remove <b>, <i>, <u>, <lang>, </b>, </i>, </u>, </lang>, etc.
    line = re.sub(r"</?[a-z]+>", "", line)
    # VTT escape sequences
    line = line.replace("\\N", "\n").replace("\\n", "\n").replace("\\h", "")
    # Collapse multiple spaces
    line = re.sub(r" {2,}", " ", line)
    return line.strip()


def _parse_ts_groups(m: re.Match, base: int) -> tuple[int, int, int, int]:
    """Extract (hours, minutes, seconds, milliseconds) from regex match groups."""
    h = int(m.group(base) or 0)
    mi = int(m.group(base + 1))
    s = int(m.group(base + 2))
    ms_raw = m.group(base + 3)
    # Normalize to 3 digits (e.g. "07" → 70 → "070")
    ms = int(ms_raw.ljust(3, "0")[:3])
    return (h, mi, s, ms)


# ------------------------------------------------------------------
# Format builders
# ------------------------------------------------------------------

def _build_lrc(cues: list[dict]) -> str:
    """Build LRC output — deduplicate overlapping text, merge same-timestamp lines."""
    entries: list[tuple[str, str]] = []  # (timestamp, text)
    seen: set[str] = set()
    for cue in cues:
        h, m, s, ms = cue["start"]
        total_min = h * 60 + m
        cs = ms // 10  # truncate to 2 digits (hundredths of a second)
        ts = f"[{total_min:02d}:{s:02d}.{cs:02d}]"
        for text in cue["text_lines"]:
            if text in seen:
                continue
            entries.append((ts, text))
            seen.add(text)
            if len(seen) > 20:
                # Re-seed from last 5 output entries
                seen.clear()
                for prev_ts, prev_text in entries[-5:]:
                    seen.add(prev_text)

    # Merge consecutive entries with the same timestamp
    lines: list[str] = []
    for ts, text in entries:
        if lines and lines[-1].startswith(ts):
            lines[-1] = f"{ts}{lines[-1][len(ts):]} {text}"
        else:
            lines.append(f"{ts}{text}")
    return "\n".join(lines) + "\n"


def _build_srt(cues: list[dict]) -> str:
    """Build standard SRT output — multi-line text preserved with \\n."""
    blocks: list[str] = []
    for i, cue in enumerate(cues, 1):
        start = _fmt_srt_ts(*cue["start"])
        end   = _fmt_srt_ts(*cue["end"])
        text = "\n".join(cue["text_lines"])
        blocks.append(f"{i}\n{start} --> {end}\n{text}")
    return "\n\n".join(blocks) + "\n"


def _fmt_srt_ts(h: int, m: int, s: int, ms: int) -> str:
    """Format a timestamp as SRT: ``HH:MM:SS,mmm``."""
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
