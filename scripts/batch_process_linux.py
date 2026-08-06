import os
import sys
import time
import json
import shutil
import subprocess
import argparse
from pathlib import Path

try:
    from guessit import guessit
except ImportError:
    print("ERRO: Biblioteca 'guessit' não encontrada. Rode: pip install guessit")
    exit(1)

def get_video_metadata(file_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except Exception:
        return None, False
    width = None
    is_hevc = False
    for stream in data.get("streams", []):
        codec = stream.get("codec_name", "").lower()
        if stream.get("codec_type") == "video":
            if not width: width = stream.get("width")
            if codec in ("hevc", "h265", "x265"): is_hevc = True
    return width, is_hevc

def sanitize_title(title):
    title = title.replace("'", "_").replace("’", "_").replace(" ", ".")
    while ".." in title: title = title.replace("..", ".")
    return title

def generate_new_name(original_path, width):
    guess = guessit(original_path.name)
    title = sanitize_title(guess.get('title', original_path.stem))
    year = guess.get('year', '')
    resolution = guess.get('screen_size', '')
        
    if not resolution:
        w = int(width) if width else 0
        if w >= 3800: resolution = "2160p"
        elif w >= 1900: resolution = "1080p"
        elif w >= 1200: resolution = "720p"
        else: resolution = "480p"

    parts = [title]
    if year: parts.append(str(year))
    if resolution and resolution != "Unknown": parts.append(str(resolution))
    parts.append("H265")
    
    return ".".join(parts) + original_path.suffix

def encode_video(input_path, output_path, quality=26):
    cmd = [
        "ffmpeg", "-y",
        "-hwaccel", "cuda",
        "-i", str(input_path),
        "-map", "0",
        "-c:v", "hevc_nvenc",
        "-preset", "p7",
        "-tune", "hq",
        "-rc", "vbr",
        "-cq", str(quality),
        "-qmin", str(quality),
        "-qmax", str(quality),
        "-c:a", "copy",
        "-c:s", "copy",
        str(output_path)
    ]
    
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    log_output = []
    for line in process.stdout:
        log_output.append(line)
        if "frame=" in line or "time=" in line:
            print(f"\r{line.strip()}", end="")
    process.wait()
    print()
    if process.returncode != 0:
        print("\n=== LOG DE ERRO DO FFMPEG ===")
        print("".join(log_output[-15:])) # Imprime as ultimas 15 linhas
        print("=============================\n")
    return process.returncode == 0

def process_file(file_path, temp_dir, delete_original=False):
    if not file_path.exists():
        print(f"Erro: Arquivo não existe {file_path}")
        return False
        
    width, is_hevc = get_video_metadata(file_path)
    if is_hevc:
        print(f"O arquivo {file_path.name} já é HEVC. Pulando.")
        return True
        
    new_name = generate_new_name(file_path, width)
    final_dest = file_path.parent / new_name
    
    if final_dest.exists():
        print(f"O destino já existe: {final_dest.name}. Pulando.")
        return True
        
    print(f"\n[{file_path.name}] Iniciando processamento...")
    print(f"  -> Nome final será: {new_name}")
    
    encoded_temp = file_path.parent / (new_name + ".part")
    
    start_time = time.time()
    print("  -> Lendo do NAS e convertendo para HEVC (NVENC) diretamente na rede...")
    success = encode_video(file_path, encoded_temp)
    elapsed = time.time() - start_time
    
    if not success or not encoded_temp.exists():
        print("  [ERRO] A conversão falhou!")
        if encoded_temp.exists(): encoded_temp.unlink()
        return False
        
    orig_size = file_path.stat().st_size / (1024*1024)
    new_size = encoded_temp.stat().st_size / (1024*1024)
    
    print("  -> Finalizando arquivo convertido...")
    encoded_temp.rename(final_dest)
    
    if delete_original:
        print("  -> Excluindo arquivo original no NAS...")
        file_path.unlink()
    else:
        print("  -> Mantendo arquivo original no NAS (Fase 1 - QA).")
        
    mins, secs = divmod(elapsed, 60)
    print(f"  [CONCLUÍDO] Tempo: {int(mins)}m {int(secs)}s | Tamanho: {orig_size:.1f}MB -> {new_size:.1f}MB")
    return True

def main():
    parser = argparse.ArgumentParser(description="Conversor Nativo Linux (In-Place)")
    parser.add_argument("--input", required=True, help="Arquivo de vídeo para processar")
    parser.add_argument("--temp", default="/home/conversor/TEMP", help="Diretório temporário local")
    parser.add_argument("--delete", action="store_true", help="Deletar o original após sucesso (Fase 3)")
    args = parser.parse_args()
    
    input_path = Path(args.input).resolve()
    temp_dir = Path(args.temp).resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if input_path.is_file():
        process_file(input_path, temp_dir, args.delete)
    else:
        print("Para esta versão, passe o caminho exato do arquivo .mkv")

if __name__ == "__main__":
    main()
