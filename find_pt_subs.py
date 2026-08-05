# ==============================================================================
# Script: find_pt_subs.py
#
# Objetivo:
#   Rascunho simples/experimento para encontrar faixas de legendas em português.
#   Usa FFprobe em vez de mkvmerge para identificar as faixas e testa as primeiras
#   linhas com heurística básica.
#
# Lógica Principal:
#   Invoca o FFprobe para pegar os índices das trilhas de legenda, depois
#   usa o FFmpeg para ler um número pequeno de linhas via pipe. Imprime 
#   os resultados no console se as palavras-chave PT-BR baterem.
#
# Dependências Externas:
#   FFmpeg, FFprobe
# ==============================================================================
import subprocess
import json

def get_subtitle_streams(mkv_path):
    """Obtém os índices das faixas de legenda através do ffprobe."""
    # Comando ffprobe limitando a saída apenas aos índices e tipos de codec, em formato JSON
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=index,codec_type', '-of', 'json', mkv_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    data = json.loads(result.stdout)
    # Extrai o número do índice para todas as trilhas onde codec_type == 'subtitle'
    subs = [s['index'] for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
    return subs

def peek_subtitle(mkv_path, stream_idx):
    """Usa ffmpeg pipe para ler as primeiras 20 linhas da legenda na memória."""
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    # Roda o ffmpeg em um Popen para ler a saída em stream ao invés de esperar o final
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    out = []
    lines_read = 0
    # Lê linha por linha até o limite de 20
    for line in process.stdout:
        out.append(line.strip())
        lines_read += 1
        if lines_read > 20:
            break
    # Força a finalização do processo FFmpeg após coletarmos a amostra desejada
    process.terminate()
    # Retorna o texto concatenado
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
