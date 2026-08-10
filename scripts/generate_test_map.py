import os
import csv
import json
import subprocess
from pathlib import Path

try:
    from guessit import guessit
except ImportError:
    pass

def get_video_metadata(file_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
    except Exception:
        return None, False
    width = None
    is_hevc = False
    for stream in data.get("streams", []):
        codec_name = stream.get("codec_name", "").lower()
        if stream.get("codec_type") == "video":
            if not width: width = stream.get("width")
            if codec_name in ("hevc", "h265", "x265"): is_hevc = True
    return width, is_hevc

def sanitize_title(title):
    title = title.replace("'", "_").replace("’", "_")
    title = title.replace(" ", ".")
    while ".." in title: title = title.replace("..", ".")
    return title

def generate_new_name(original_path, width):
    guess = guessit(original_path.name)
    title = guess.get('title', original_path.stem)
    alt_title = guess.get('alternative_title')
    if alt_title: title = f"{title}.{alt_title}"
    year = guess.get('year', '')
    season = guess.get('season')
    episode = guess.get('episode')
    episode_title = guess.get('episode_title')
    if not season and not episode and episode_title:
        title = f"{title}.{episode_title}"
        episode_title = None
    title = sanitize_title(title)
    
    resolution = guess.get('screen_size')
    if not resolution:
        w = int(width) if width else 0
        if w >= 3800: resolution = "2160p"
        elif w >= 1900: resolution = "1080p"
        elif w >= 1200: resolution = "720p"
        else: resolution = "480p"
    
    parts = [title]
    if year: parts.append(str(year))
    if season is not None:
        if isinstance(season, list): season = season[0]
        s_str = f"S{int(season):02d}"
        if episode is not None:
            if isinstance(episode, list): episode = episode[0]
            s_str += f"E{int(episode):02d}"
        parts.append(s_str)
    elif episode is not None:
        if isinstance(episode, list): episode = episode[0]
        parts.append(f"E{int(episode):02d}")
    if episode_title:
        if isinstance(episode_title, list): episode_title = episode_title[0]
        parts.append(sanitize_title(episode_title))
    if resolution and resolution != "Unknown": parts.append(str(resolution))
    parts.append("H265")
    return ".".join(parts) + original_path.suffix

paths = [
    r"U:\Anime-Cartoon\A Certain",
    r"U:\Anime-Cartoon\LegendoftheGalacticHeroes-GingaEiyuuDensetsu",
    r"U:\Anime-Cartoon\Haikyuu!!"
]

data = []

print("Mapeando arquivos e metadados...")
for p in paths:
    d = Path(p)
    if not d.exists(): continue
    files = []
    for root, _, fs in os.walk(d):
        for f in fs:
            if f.lower().endswith(('.mkv', '.mp4', '.avi')):
                fp = Path(root) / f
                try:
                    size = os.path.getsize(fp)
                    files.append((fp, size))
                except:
                    pass
    # Pega os 5 maiores arquivos não-HEVC
    files.sort(key=lambda x: x[1], reverse=True)
    count = 0
    for fp, size in files:
        if count >= 5:
            break
        width, is_hevc = get_video_metadata(fp)
        if is_hevc:
            continue
        new_name = generate_new_name(fp, width)
        size_mb = size / (1024 * 1024)
        data.append({
            'old_path': str(fp),
            'new_name': new_name,
            'old_name': fp.name,
            'size_mb': size_mb,
            'folder': fp.parent.name
        })
        count += 1

out_path = Path(r"E:\Traducao\scripts\test_map.csv")
with open(out_path, mode='w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f, delimiter=';')
    writer.writerow(['Lote_Piloto', 'Tamanho_MB', 'Nome_Original', 'Novo_Nome_Padronizado', 'Pasta_Pai', 'Caminho_Completo_Original'])
    for d in data:
        size_str = f"{d['size_mb']:.2f}".replace('.', ',')
        writer.writerow(["SIM", size_str, d['old_name'], d['new_name'], d['folder'], d['old_path']])

print(f"CSV de mapeamento gerado com {len(data)} arquivos: {out_path}")
