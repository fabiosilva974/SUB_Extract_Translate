# ==============================================================================
# Script: identify_video_formats.py
#
# Objetivo:
#   Analisar um arquivo de vídeo (como MKV, MP4) e exibir de forma legível
#   os formatos (codecs) de vídeo, áudio e legendas contidos nele, bem como
#   informações gerais sobre as faixas.
#
# Lógica Principal:
#   O script utiliza o utilitário 'ffprobe' (parte do pacote FFmpeg) para 
#   extrair os metadados do arquivo em formato JSON. Em seguida, ele analisa
#   os dados e imprime um relatório consolidado, categorizando vídeo, áudio
#   e legendas, além de reportar os codecs específicos (ex: H.264, HEVC, EAC3).
#
# Dependências Externas:
#   FFmpeg / FFprobe (devem estar instalados e no PATH do sistema)
# ==============================================================================
import os
import sys
import json
import subprocess
import argparse

def format_size(size_bytes):
    """Formata o tamanho do arquivo em bytes para uma unidade legível (KB, MB, GB)."""
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = 0
    while size_bytes >= 1024 and i < len(size_name) - 1:
        size_bytes /= 1024.0
        i += 1
    return f"{size_bytes:.2f} {size_name[i]}"

def analyze_video(file_path):
    """Analisa o arquivo de vídeo usando ffprobe e exibe um relatório."""
    if not os.path.exists(file_path):
        print(f"[ERRO] Arquivo não encontrado: {file_path}")
        return

    print(f"\nAnalisando arquivo: {os.path.basename(file_path)}")
    print("=" * 60)

    # Comando para extrair metadados em formato JSON usando ffprobe
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]

    try:
        # Executa o comando e captura a saída
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        data = json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao executar o ffprobe. Verifique se o vídeo é válido. {e}")
        return
    except FileNotFoundError:
        print("[ERRO] FFprobe não encontrado! Certifique-se de que o FFmpeg está instalado e no PATH.")
        return
    except json.JSONDecodeError:
        print("[ERRO] Falha ao ler os dados JSON retornados pelo ffprobe.")
        return

    # Extrai informações gerais do container (Formato)
    fmt = data.get("format", {})
    size_bytes = int(fmt.get("size", 0))
    duration = float(fmt.get("duration", 0))
    mins, secs = divmod(duration, 60)
    
    print("INFORMAÇÕES GERAIS")
    print(f"  Container : {fmt.get('format_long_name', 'Desconhecido')}")
    print(f"  Tamanho   : {format_size(size_bytes)}")
    print(f"  Duração   : {int(mins)}m {int(secs)}s")
    print("-" * 60)

    # Extrai informações de cada faixa (stream)
    streams = data.get("streams", [])
    
    videos = []
    audios = []
    subs = []

    # Categoriza as faixas
    for stream in streams:
        codec_type = stream.get("codec_type")
        codec_name = stream.get("codec_name", "Desconhecido").upper()
        # Algumas faixas têm nome longo que explica melhor
        codec_long = stream.get("codec_long_name", "")
        
        # Pega a linguagem caso exista nas tags
        tags = stream.get("tags", {})
        language = tags.get("language", "und") # und = undefined (não definido)
        
        if codec_type == "video":
            # Pega a resolução do vídeo
            width = stream.get("width", "?")
            height = stream.get("height", "?")
            videos.append(f"{codec_name} ({codec_long}) - Resolução: {width}x{height}")
            
        elif codec_type == "audio":
            audios.append(f"{codec_name} ({codec_long}) - Idioma: {language}")
            
        elif codec_type == "subtitle":
            subs.append(f"{codec_name} ({codec_long}) - Idioma: {language}")

    # Exibe as informações de Vídeo
    print("VÍDEO")
    if not videos:
        print("  Nenhuma faixa de vídeo encontrada.")
    for idx, v in enumerate(videos, 1):
        print(f"  Faixa {idx}: {v}")
    
    # Exibe as informações de Áudio
    print("\nÁUDIO")
    if not audios:
        print("  Nenhuma faixa de áudio encontrada.")
    for idx, a in enumerate(audios, 1):
        print(f"  Faixa {idx}: {a}")
        
    # Exibe as informações de Legendas
    print("\nLEGENDAS")
    if not subs:
        print("  Nenhuma faixa de legenda encontrada.")
    for idx, s in enumerate(subs, 1):
        print(f"  Faixa {idx}: {s}")
        
    print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description="Analisa e exibe os formatos/codecs de um arquivo de vídeo.")
    parser.add_argument("arquivo", help="Caminho para o arquivo de vídeo a ser analisado (ex: video.mkv)")
    args = parser.parse_args()

    analyze_video(args.arquivo)

if __name__ == "__main__":
    main()
