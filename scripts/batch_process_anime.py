# ==============================================================================
# Script: batch_process_anime.py
#
# Objetivo:
#   Processar em lote (e recursivamente) vídeos de uma biblioteca de rede.
#   Copia localmente, sanitiza pastas/arquivos, converte para HEVC,
#   configura legenda PT como padrão e gera log CSV detalhado.
#
# Lógica Principal:
#   Cria uma estrutura de diretórios espelho em "Convertidos" na raiz do disco,
#   com todos os nomes sanitizados (sem espaços). 
#   Pula arquivos já codificados em HEVC para economizar tempo.
#
# Dependências Externas:
#   FFmpeg (deve estar instalado e no PATH do sistema)
# ==============================================================================
import os
import sys
import shutil
import subprocess
import argparse
import time
import re
import json
import csv
from pathlib import Path

def get_gpu_vendor():
    try:
        output = subprocess.check_output(
            "wmic path win32_VideoController get name", shell=True, text=True
        )
        output = output.lower()
        if "nvidia" in output: return "nvidia"
        elif "amd" in output or "radeon" in output: return "amd"
        elif "intel" in output: return "intel"
    except Exception as e:
        print(f"Não foi possível detectar a GPU: {e}")
    return "cpu"

def get_video_codec(file_path):
    try:
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "v:0", file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if "streams" in data and len(data["streams"]) > 0:
            return data["streams"][0].get("codec_name", "").lower()
    except Exception:
        pass
    return ""

def sanitize_name(name):
    """Remove colchetes, aspas e substitui espaços/hífens por underline."""
    name = re.sub(r'[\[\]\'\"‘’“”]', '', name)
    name = re.sub(r'[\s\-]+', '_', name)
    name = re.sub(r'_+', '_', name)
    return name.strip('_')

def get_file_size_mb(path):
    try:
        return os.path.getsize(path) / (1024 * 1024)
    except Exception:
        return 0.0

def process_file(file_path, input_anchor, temp_dir, gpu, quality, log_csv_path, force_cpu=False):
    # Calcula o caminho de saída limpo e espelhado
    rel_path = file_path.relative_to(input_anchor)
    clean_parts = [sanitize_name(p) for p in rel_path.parent.parts]
    clean_filename = f"{sanitize_name(file_path.stem)}.mkv"
    
    out_dir = input_anchor / "Convertidos" / Path(*clean_parts)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    final_dest = out_dir / clean_filename
    
    if final_dest.exists():
        print(f"[PULANDO] Arquivo já existe no destino: {clean_filename}")
        return
        
    print(f"\n[{file_path.name}] Iniciando processamento...")
    start_time = time.time()
    
    # Usa o nome original com prefixo 'temp_' para evitar colisão entre múltiplas instâncias do script rodando ao mesmo tempo
    temp_original = Path(temp_dir) / f"temp_{file_path.name}"
    temp_output = Path(temp_dir) / clean_filename
    
    old_size_mb = get_file_size_mb(file_path)
    
    # 1. Copiar para disco local
    print(f"  -> Copiando da rede para temp local...")
    try:
        shutil.copy2(file_path, temp_original)
    except Exception as e:
        print(f"  [ERRO] Falha ao copiar arquivo da rede: {e}")
        return
    
    # 2. Comando FFmpeg
    print(f"  -> Verificando formato de vídeo...")
    codec = get_video_codec(str(temp_original))
    
    external_sub = None
    for f in file_path.parent.iterdir():
        if f.is_file() and f.name != file_path.name:
            if f.stem.startswith(file_path.stem) and f.suffix.lower() in ['.srt', '.ass']:
                external_sub = f
                break

    qual_str = str(quality)
    
    command = [
        "ffmpeg", "-y", "-v", "error", "-stats"
    ]
    
    if external_sub:
        print(f"  -> Legenda externa detectada: {external_sub.name}")
        command.extend([
            "-i", str(temp_original),
            "-i", str(external_sub),
            "-map", "0:v:0",   # Apenas o vídeo principal, ignora capas/thumbnails
            "-map", "0:a",     # Áudios originais
            "-map", "1:s:0",   # Legenda externa (vem primeiro!)
            "-map", "0:s?",    # Legendas originais do vídeo (vem depois)
            "-map", "0:t?",    # Attachments/fontes (se houver)
            "-c:a", "copy",
            "-c:s", "srt" if (file_path.suffix.lower() == '.mp4' or external_sub.suffix.lower() == '.srt') else "copy",
            "-c:t", "copy",
            "-disposition:s", "0",
            "-disposition:s:0", "default",       # A legenda externa (index 0) vira a padrão
            "-metadata:s:s:0", "language=por"    # A legenda externa ganha a tag PT-BR
        ])
    else:
        command.extend([
            "-i", str(temp_original),
            "-map", "0:v:0",
            "-map", "0:a?",
            "-map", "0:s?",
            "-map", "0:t?",
            "-c:a", "copy", 
            "-c:s", "srt" if file_path.suffix.lower() == '.mp4' else "copy", 
            "-c:t", "copy",
            "-disposition:s", "0",
            "-disposition:s:m:language:por", "default"
        ])
    
    if codec == "hevc":
        print(f"  -> Vídeo já está em HEVC! Apenas ajustando legendas e nome...")
        command.extend(["-c:v", "copy"])
    else:
        codec_name = codec.upper() if codec else "Desconhecido"
        print(f"  -> Codificando vídeo de {codec_name} para HEVC e configurando legenda PT...")
        if force_cpu:
            command.extend(["-c:v", "libx265", "-crf", qual_str, "-preset", "fast"])
        elif gpu == "nvidia":
            command.extend(["-c:v", "hevc_nvenc", "-cq", qual_str, "-preset", "p4"])
        elif gpu == "amd":
            command.extend(["-c:v", "hevc_amf", "-rc", "cqp", "-qp_i", qual_str, "-qp_p", qual_str, "-vbaq", "false"])
        elif gpu == "intel":
            command.extend(["-c:v", "hevc_qsv", "-global_quality", qual_str])
        else:
            command.extend(["-c:v", "libx265", "-crf", qual_str, "-preset", "fast"])

    command.append(str(temp_output))
    
    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"  [ERRO] Falha no FFmpeg: {e}")
        if temp_original.exists(): temp_original.unlink()
        if temp_output.exists(): temp_output.unlink()
        return

    # 3. Mover de volta para rede
    print(f"  -> Movendo arquivo finalizado para: {final_dest}")
    try:
        shutil.move(str(temp_output), str(final_dest))
    except Exception as e:
        print(f"  [ERRO] Falha ao mover arquivo para a rede: {e}")
    
    # 4. Limpeza
    if temp_original.exists(): temp_original.unlink()
        
    end_time = time.time()
    elapsed = end_time - start_time
    mins, secs = divmod(elapsed, 60)
    
    new_size_mb = get_file_size_mb(final_dest)
    
    time_str = f"{int(mins)}m {int(secs)}s"
    print(f"  [CONCLUÍDO] Tempo: {time_str} | Tamanho: {old_size_mb:.1f}MB -> {new_size_mb:.1f}MB")
    
    # Grava no Log
    file_exists = os.path.isfile(log_csv_path)
    with open(log_csv_path, mode='a', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(['Caminho Original', 'Nome Original', 'Tamanho Antigo (MB)', 'Tempo Conversão', 'Novo Nome', 'Novo Tamanho (MB)'])
        writer.writerow([str(file_path), file_path.name, f"{old_size_mb:.2f}", time_str, clean_filename, f"{new_size_mb:.2f}"])


def main():
    parser = argparse.ArgumentParser(description="Processa vídeos em lote recursivamente.")
    parser.add_argument("--input", required=True, help="Pasta de origem (ex: V:\\Banksters.S01)")
    parser.add_argument("--temp", default=r"E:\Traducao\TEMP", help="Pasta local temporária")
    parser.add_argument("--quality", type=int, default=26, help="Nível de qualidade")
    parser.add_argument("--recursive", action="store_true", help="Varrer subpastas recursivamente")
    parser.add_argument("--cpu", action="store_true", help="Forçar a codificação via CPU (libx265)")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    temp_dir = Path(args.temp)
    quality = args.quality
    recursive = args.recursive
    force_cpu = args.cpu
    
    if not input_path.exists():
        print(f"Erro: Pasta de origem não existe: {input_path}")
        return
        
    input_anchor = Path(input_path.anchor) # e.g. "V:\"
    log_csv_path = input_anchor / f"compression_log_{input_path.name}.csv"
    
    temp_dir.mkdir(parents=True, exist_ok=True)
    gpu = get_gpu_vendor()
    
    files_to_process = []
    
    print("Mapeando arquivos...")
    if input_path.is_file():
        if input_path.suffix.lower() in ('.mkv', '.mp4'):
            files_to_process.append(input_path)
        else:
            print(f"Erro: O arquivo não é um vídeo suportado (.mkv, .mp4): {input_path}")
            return
    else:
        if recursive:
            for root, _, files in os.walk(input_path):
                for f in files:
                    if f.lower().endswith(('.mkv', '.mp4')):
                        files_to_process.append(Path(root) / f)
        else:
            for f in os.listdir(input_path):
                if f.lower().endswith(('.mkv', '.mp4')):
                    files_to_process.append(input_path / f)
                
    print(f"Encontrados {len(files_to_process)} vídeos para processar.")
    
    for f_path in files_to_process:
        process_file(f_path, input_anchor, temp_dir, gpu, quality, log_csv_path, force_cpu)
        
    print("\nProcessamento em lote finalizado!")

if __name__ == "__main__":
    main()
