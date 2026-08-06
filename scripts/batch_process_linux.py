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

def get_resolution_name(width):
    w = int(width) if width else 0
    if w >= 3800: return "2160p"
    elif w >= 1900: return "1080p"
    elif w >= 1200: return "720p"
    else: return "480p"

def generate_new_name(original_path, width):
    guess = guessit(original_path.name)
    title = guess.get('title', original_path.stem)
    
    alt_title = guess.get('alternative_title')
    if alt_title:
        title = f"{title}.{alt_title}"
        
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
        resolution = get_resolution_name(width)
    
    parts = [title]
    if year:
        parts.append(str(year))
        
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
        
    if resolution and resolution != "Unknown":
        parts.append(str(resolution))
        
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
        "-f", "matroska",
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
    
    if new_size >= orig_size:
        print("  -> [ANTI-INCHAÇO] O arquivo H265 ficou MAIOR que o original H264!")
        print("  -> Descartando a conversão para economizar espaço e mantendo o original intacto.")
        encoded_temp.unlink()
        mins, secs = divmod(elapsed, 60)
        print(f"  [DESCARTADO] Tempo desperdiçado: {int(mins)}m {int(secs)}s | Tamanho: {orig_size:.1f}MB -> {new_size:.1f}MB")
        return True

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
    parser.add_argument("--input", help="Arquivo de vídeo único para processar")
    parser.add_argument("--csv", help="Caminho para o mapa_filmes_renomeio.csv gerado pelo planner")
    parser.add_argument("--all", action="store_true", help="Processar todos os arquivos do CSV (ignora a flag de Lote Piloto)")
    parser.add_argument("--temp", default="/home/conversor/TEMP", help="Diretório temporário local")
    parser.add_argument("--delete", action="store_true", help="Deletar o original após sucesso (Fase 3)")
    args = parser.parse_args()
    
    temp_dir = Path(args.temp).resolve()
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    if args.input:
        input_path = Path(args.input).resolve()
        if input_path.is_file():
            process_file(input_path, temp_dir, args.delete)
        else:
            print("Para --input, passe o caminho exato do arquivo .mkv")
    
    elif args.csv:
        csv_path = Path(args.csv).resolve()
        if not csv_path.exists():
            print(f"Erro: CSV não encontrado em {csv_path}")
            return
            
        import csv as csv_lib
        to_process = []
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv_lib.DictReader(f, delimiter=';')
            for row in reader:
                if args.all or row.get('Lote_Piloto') == 'SIM':
                    to_process.append(row['Caminho_Completo_Original'])
                    
        desc = "toda a biblioteca de filmes" if args.all else "o Lote Piloto"
        print(f"Encontrados {len(to_process)} vídeos para {desc}.")
        for path_str in to_process:
            # Universal Path Translator (Windows -> Linux)
            path_str = path_str.replace("\\\\192.168.0.99\\Media\\", "/mnt/Media/")
            path_str = path_str.replace("U:\\", "/mnt/") # Caso use driver mapeado
            path_str = path_str.replace("\\", "/")
            
            file_path = Path(path_str)
            process_file(file_path, temp_dir, args.delete)
            
        print(f"\nProcessamento concluído para {desc}!")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
