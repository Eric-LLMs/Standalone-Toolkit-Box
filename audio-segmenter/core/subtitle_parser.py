import re


def time_to_ms(time_str):
    """Converts SRT timestamp format to milliseconds."""
    try:
        h, m, s_ms = time_str.split(':')
        s, ms = s_ms.split(',')
        total_ms = (int(h) * 3600000) + (int(m) * 60000) + (int(s) * 1000) + int(ms)
        return total_ms
    except ValueError as e:
        raise ValueError(f"Invalid time format: {time_str}") from e


def parse_srt_file(srt_path):
    """Parses an SRT file and returns a list of segment dictionaries."""
    segments = []
    try:
        with open(srt_path, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    except UnicodeDecodeError:
        with open(srt_path, 'r', encoding='latin-1') as f:
            content = f.read()

    pattern = re.compile(
        r'(\d+)\s*?\n(\d{2}:\d{2}:\d{2},\d{3})\s-->\s(\d{2}:\d{2}:\d{2},\d{3})\s*?\n(.*?)(?=\n\n|\Z)',
        re.DOTALL | re.MULTILINE
    )

    matches = pattern.findall(content)

    for match in matches:
        index, start_str, end_str, text_block = match
        clean_text = text_block.replace('\n', ' ').replace('\r', '').strip()

        if clean_text:
            segments.append({
                'index': int(index),
                'start_ms': time_to_ms(start_str),
                'end_ms': time_to_ms(end_str),
                'text': clean_text
            })

    return segments


def lrc_time_to_ms(time_str):
    """Converts LRC timestamp format to milliseconds."""
    match = re.match(r'\[(\d+):(\d+)\.(\d+)\]', time_str)
    if not match:
        return None

    minutes = int(match.group(1))
    seconds = int(match.group(2))
    ms_str = match.group(3)
    milliseconds = int(ms_str.ljust(3, '0')[:3])

    return (minutes * 60000) + (seconds * 1000) + milliseconds


def parse_lrc_file(lrc_path):
    """Parses an LRC file and returns a list of segment dictionaries."""
    segments = []

    try:
        with open(lrc_path, 'r', encoding='utf-8-sig') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(lrc_path, 'r', encoding='latin-1') as f:
            lines = f.readlines()

    raw_segments = []
    for line in lines:
        match = re.match(r'(\[\d+:\d+\.\d+\])(.*)', line.strip())
        if match:
            start_ms = lrc_time_to_ms(match.group(1))
            text = match.group(2).strip()
            if start_ms is not None:
                raw_segments.append({'start_ms': start_ms, 'text': text})

    for i in range(len(raw_segments)):
        start_ms = raw_segments[i]['start_ms']
        text = raw_segments[i]['text']

        if not text:
            continue

        if i < len(raw_segments) - 1:
            end_ms = raw_segments[i + 1]['start_ms']
        else:
            end_ms = start_ms + 3000

        segments.append({
            'index': i + 1,
            'start_ms': start_ms,
            'end_ms': end_ms,
            'text': text
        })
    return segments