import os
import sys
import time
import json
import subprocess
import argparse
import platform
import csv
import re
from pathlib import Path
from datetime import datetime

try:
    from guessit import guessit
except ImportError:
    print("ERRO: Biblioteca 'guessit' não encontrada. Rode: pip install guessit")
    exit(1)

def detect_environment():
    """Detecta o sistema operacional e a placa de vídeo do servidor atual."""
    os_name = platform.system()
    gpu = "cpu"
    
    # Mapeamento Direto Baseado na Infra do Usuário
    if os_name == "Linux":
        gpu = "nvidia"
    elif os_name == "Windows":
        gpu = "amd"
        
    print(f"[INFO] Sistema Operacional: {os_name}")
    print(f"[INFO] Hardware de Aceleração Destinado: {gpu.upper()}")
    return os_name, gpu

def translate_path(path_str, os_name):
    """Traduz o caminho da rede do CSV para a plataforma atual"""
    if os_name == "Linux":
        path_str = path_str.replace("\\\\192.168.0.99\\Media\\", "/mnt/Media/")
        path_str = path_str.replace("U:\\", "/mnt/")
        path_str = path_str.replace("\\", "/")
    elif os_name == "Windows":
        path_str = path_str.replace("/mnt/Media/", "\\\\192.168.0.99\\Media\\")
        path_str = path_str.replace("/", "\\")
    return path_str

def sanitize_title(title):
    title = re.sub(r'[\[\]\(\)\'\":!]', '', title)
    title = re.sub(r'[\s\-]+', '.', title)
    title = re.sub(r'\.+', '.', title)
    return title.strip('.')

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

def get_video_metadata(file_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    try:
        # Decodificação manual para evitar erros de encodings do Windows PowerShell com CP1252
        result = subprocess.run(cmd, capture_output=True, check=True)
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
    except Exception:
        return None, False, None
    
    width = None
    is_hevc = False
    for stream in data.get('streams', []):
        if stream.get('codec_type') == 'video':
            width = stream.get('width')
            if stream.get('codec_name') in ['hevc', 'h265']:
                is_hevc = True
            break
            
    duration = None
    try:
        if 'format' in data and 'duration' in data['format']:
            duration = float(data['format']['duration'])
    except Exception:
        pass
            
    return width, is_hevc, duration

def encode_video(input_path, output_path, gpu, duration_secs):
    command = ["ffmpeg", "-y"]
    
    if gpu == "nvidia":
        command.extend(["-hwaccel", "cuda"])
    elif gpu == "amd":
        command.extend(["-hwaccel", "dxva2"])
        
    # SILENCE FFMPEG SPAM AND ENABLE PROGRESS OUTPUT TO STDOUT
    command.extend(["-v", "error", "-nostats", "-progress", "-"])
        
    command.extend(["-i", str(input_path)])
    
    if gpu == "nvidia":
        command.extend([
            "-c:v", "hevc_nvenc",
            "-cq", "25",
            "-preset", "p4"
        ])
    elif gpu == "amd":
        command.extend([
            "-c:v", "hevc_amf",
            "-rc", "cqp",
            "-qp_i", "26",
            "-qp_p", "26",
            "-vbaq", "false"
        ])
    else:
        command.extend([
            "-c:v", "libx265",
            "-crf", "26",
            "-preset", "fast"
        ])
        
    command.extend([
        "-c:a", "copy",
        "-c:s", "copy",
        "-disposition:s", "0",
        "-disposition:s:m:language:por", "default",
        str(output_path)
    ])
    
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        
        last_report_pct = -10
        last_report_time = time.time()
        current_fps = "0"
        
        for line in process.stdout:
            if line.startswith("fps="):
                current_fps = line.split("=")[1].strip()
            elif line.startswith("out_time_us="):
                try:
                    val = line.split("=")[1].strip()
                    if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                        out_time_us = int(val)
                        if duration_secs and duration_secs > 0:
                            pct = (out_time_us / 1_000_000) / duration_secs * 100
                            # Imprime a cada 5% de progresso ou a cada 5 minutos
                            if (pct - last_report_pct >= 5) or (time.time() - last_report_time > 300):
                                print(f"    -> Progresso: {pct:.1f}% | Taxa: {current_fps} fps")
                                last_report_pct = pct
                                last_report_time = time.time()
                                sys.stdout.flush()
                except ValueError:
                    pass
                    
        _, stderr = process.communicate()
        if process.returncode != 0:
            print(f"  [ERRO] FFmpeg falhou com código {process.returncode}")
            if stderr.strip():
                print(f"  [ERRO DETALHES] {stderr.strip()}")
            return False
        return True
    except Exception as e:
        print(f"  [ERRO] Falha ao executar FFmpeg: {e}")
        return False

def process_file(file_path, delete_original, os_name, gpu, index, total):
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    
    # 1. VERIFICAÇÃO DE LOCK (CONCORRÊNCIA)
    if lock_file.exists():
        print(f"\n[{index}/{total}] [{file_path.name}] [LOCK] Outra máquina está processando. Pulando...")
        sys.stdout.flush()
        return 0, 0
        
    # 2. TENTA CRIAR O LOCK (Exclusão Mútua)
    try:
        lock_file.touch(exist_ok=False)
    except FileExistsError:
        print(f"\n[{index}/{total}] [{file_path.name}] [LOCK] Outra máquina pegou no mesmo milissegundo. Pulando...")
        sys.stdout.flush()
        return 0, 0
    except Exception as e:
        print(f"\n[{index}/{total}] [{file_path.name}] Erro ao criar lock: {e}")
        sys.stdout.flush()
        return 0, 0

    try:
        orig_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
        
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n=======================================================")
        print(f"[{start_time_str}] [{index}/{total}] Iniciando processamento ({os_name}):")
        sys.stdout.flush()
        
        width, is_hevc, duration = get_video_metadata(file_path)
        
        if width is None:
            print("  [ERRO] Não foi possível ler metadados. Vídeo corrompido?")
            return orig_mb, orig_mb
            
        new_name = generate_new_name(file_path, width)
        final_dest = file_path.parent / new_name
        
        print(f"  -> Entrada: {file_path}")
        print(f"  -> Saída:   {final_dest}")
        if duration:
            mins, secs = divmod(duration, 60)
            print(f"  -> Duração: {int(mins)}m {int(secs)}s | Tamanho: {orig_mb:.1f} MB")
        sys.stdout.flush()
        
        final_dest = file_path.parent / new_name
        
        if final_dest.exists() or (file_path.name == new_name and is_hevc):
            print("  -> O arquivo final já existe ou já está no padrão. Pulando.")
            if delete_original and file_path.name != new_name and file_path.exists():
                print("  -> Deletando original obsoleto...")
                file_path.unlink()
            final_mb = final_dest.stat().st_size / (1024*1024) if final_dest.exists() else orig_mb
            return orig_mb, final_mb
            
        # Manter a extensão no final para o FFmpeg entender o formato (ex: _part_Filme.mkv)
        encoded_temp = file_path.parent / f"_part_{new_name}"
        
        print(f"  -> Convertendo para HEVC ({gpu.upper()}) pela rede...")
        sys.stdout.flush()
        start_time = time.time()
        success = encode_video(file_path, encoded_temp, gpu, duration)
        elapsed = time.time() - start_time
        
        if not success or not encoded_temp.exists():
            print("  [ERRO] A conversão falhou!")
            if encoded_temp.exists(): encoded_temp.unlink()
            return orig_mb, orig_mb
            
        # 3. VERIFICAÇÃO ANTI-INCHAÇO
        orig_size = file_path.stat().st_size / (1024*1024)
        new_size = encoded_temp.stat().st_size / (1024*1024)
        
        if new_mb >= orig_mb:
            print("  -> [ANTI-INCHAÇO] Arquivo novo ficou MAIOR que o original H264!")
            print("  -> Descartando a conversão para economizar espaço.")
            encoded_temp.unlink()
            mins, secs = divmod(elapsed, 60)
            end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"  [{end_time_str}] [DESCARTADO] Tempo desperdiçado: {int(mins)}m {int(secs)}s | {orig_mb:.1f}MB -> {new_mb:.1f}MB")
            return orig_mb, orig_mb
            
        print("  -> Finalizando...")
        encoded_temp.rename(final_dest)
        
        if delete_original:
            print("  -> Excluindo arquivo original no NAS...")
            file_path.unlink()
        else:
            print("  -> Mantendo original no NAS (Fase 1 - QA).")
            
        mins, secs = divmod(elapsed, 60)
        end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  [{end_time_str}] [CONCLUÍDO] Tempo Total: {int(mins)}m {int(secs)}s | {orig_mb:.1f}MB -> {new_mb:.1f}MB")
        
        return orig_mb, new_mb
        
    finally:
        # GARANTIA DE LIMPEZA: Sempre deleta o arquivo de trava, ocorra sucesso ou erro
        if lock_file.exists():
            lock_file.unlink()

def main():
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
        
    parser = argparse.ArgumentParser(description="Conversor Universal (Cluster Ready)")
    parser.add_argument("--csv", help="Caminho para o arquivo CSV de lista")
    parser.add_argument("--all", action="store_true", help="Processa toda a biblioteca em vez de só o piloto")
    parser.add_argument("--delete", action="store_true", help="Deleta o arquivo original após converter")
    
    args = parser.parse_args()
    
    if not args.csv:
        parser.print_help()
        sys.exit(1)
        
    os_name, gpu = detect_environment()
        
    try:
        with open(args.csv, newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            to_process = []
            for row in reader:
                if args.all or row.get('Lote_Piloto') == 'SIM':
                    path_str = row['Caminho_Completo_Original']
                    path_str = translate_path(path_str, os_name)
                    to_process.append(path_str)
                    
        initial_bytes = 0
        for path_str in to_process:
            p = Path(path_str)
            if p.exists():
                initial_bytes += p.stat().st_size
                
        initial_gb = initial_bytes / (1024**3)
        
        batch_start_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n[{batch_start_str}] Encontrados {len(to_process)} vídeos para conversão paralela.")
        print(f"-> Volume Total Inicial da Fila: {initial_gb:.2f} GB")
        sys.stdout.flush()
        
        total_videos = len(to_process)
        total_orig_mb = 0
        total_new_mb = 0
        
        for i, path_str in enumerate(to_process, start=1):
            o_mb, n_mb = process_file(Path(path_str), args.delete, os_name, gpu, i, total_videos)
            total_orig_mb += o_mb
            total_new_mb += n_mb
            
        batch_end_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        total_orig_gb = total_orig_mb / 1024
        total_new_gb = total_new_mb / 1024
        economia_gb = total_orig_gb - total_new_gb
        
        print("\n=======================================================")
        print(f"[{batch_end_str}] Processamento em lote concluído!")
        print(f"-> Volume Inicial Total (Processado): {total_orig_gb:.2f} GB")
        print(f"-> Volume Final Total   (Processado): {total_new_gb:.2f} GB")
        print(f"-> Espaço Economizado               : {economia_gb:.2f} GB")
        sys.stdout.flush()
            
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")

if __name__ == "__main__":
    main()
