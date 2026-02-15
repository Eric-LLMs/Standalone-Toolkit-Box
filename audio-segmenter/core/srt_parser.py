import re


def time_to_ms(time_str):
    """
    Converts SRT timestamp format (00:00:05,123) to milliseconds (integer).
    """
    try:
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split(',')
        total_ms = (int(h) * 3600000) + (int(m) * 60000) + (int(s) * 1000) + int(ms)
        return total_ms
    except ValueError as e:
        raise ValueError(f"Invalid time format: {time_str}") from e


def parse_srt_file(srt_path):
    """
    Parses an SRT file and returns a list of segment dictionaries.
    Each dict contains: index, start_ms, end_ms, text.
    """
    segments = []
    try:
        with open(srt_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"SRT file not found: {srt_path}")
    except UnicodeDecodeError:
        # Fallback for older non-utf8 srt files
        with open(srt_path, 'r', encoding='latin-1') as f:
            content = f.read()

    # Regex to match standard SRT blocks.
    # It handles potential variations in line breaks (\n vs \r\n).
    pattern = re.compile(
        r'(\d+)\s*?\n(\d{2}:\d{2}:\d{2},\d{3})\s-->\s(\d{2}:\d{2}:\d{2},\d{3})\s*?\n(.*?)(?=\n\n|\Z)',
        re.DOTALL | re.MULTILINE
    )

    matches = pattern.findall(content)

    if not matches:
        print("Warning: No subtitle segments found based on regex matching.")

    for match in matches:
        index, start_str, end_str, text_block = match

        # Clean up the text block: remove newlines and extra spaces
        clean_text = text_block.replace('\n', ' ').replace('\r', '').strip()

        if clean_text:  # Only add if there is actual text
            segments.append({
                'index': int(index),
                'start_ms': time_to_ms(start_str),
                'end_ms': time_to_ms(end_str),
                'text': clean_text
            })

    return segments