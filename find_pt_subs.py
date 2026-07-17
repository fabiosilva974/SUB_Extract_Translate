import subprocess
import json

def get_subtitle_streams(mkv_path):
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=index,codec_type', '-of', 'json', mkv_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    data = json.loads(result.stdout)
    subs = [s['index'] for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
    return subs

def peek_subtitle(mkv_path, stream_idx):
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    out = []
    lines_read = 0
    for line in process.stdout:
        out.append(line.strip())
        lines_read += 1
        if lines_read > 20:
            break
    process.terminate()
    return '\n'.join(out)

files = [
    r"Z:\Traducao\Lucky.2026.S01E01.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv",
    r"Z:\Traducao\Lucky.2026.S01E02.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv"
]

for f in files:
    print(f"File: {f}")
    subs = get_subtitle_streams(f)
    print(f"Found subtitle streams: {subs}")
    for s in subs:
        content = peek_subtitle(f, s)
        if ' não ' in content.lower() or ' você ' in content.lower() or ' que ' in content.lower() or ' para ' in content.lower():
            # A simple heuristic for Portuguese, though 'que', 'para' also in Spanish
            # Let's print out the first few text lines
            lines = [l for l in content.split('\n') if l and not l.isdigit() and '-->' not in l]
            text = " ".join(lines[:3])
            print(f"Stream {s}: {text}")
