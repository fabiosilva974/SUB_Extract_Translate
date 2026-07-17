"""
Script para identificar o idioma das faixas de legenda em arquivos MKV.
Como os arquivos de vídeo fornecidos não possuíam tags de idioma nos metadados das faixas de legenda,
este script utiliza o ffprobe para listar todas as faixas e o ffmpeg para ler os primeiros segundos
de cada faixa. O texto extraído é salvo em um arquivo de texto para que possamos inspecionar visualmente
e identificar qual faixa corresponde ao Português (ou qualquer outro idioma desejado).
"""

import subprocess
import json

def get_subtitle_streams(mkv_path):
    """
    Obtém uma lista de índices (streams) de legendas do arquivo MKV.
    
    Comando executado:
    ffprobe -v error -show_entries stream=index,codec_type -of json <arquivo_mkv>
    
    -v error: Suprime avisos e informações desnecessárias.
    -show_entries stream=index,codec_type: Pede para mostrar apenas o índice do stream e o tipo do codec.
    -of json: Formata a saída em JSON para facilitar o parsing no Python.
    """
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=index,codec_type', '-of', 'json', mkv_path]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    data = json.loads(result.stdout)
    
    # Filtra os streams onde o tipo de codec é 'subtitle'
    subs = [s['index'] for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
    return subs

def peek_subtitle(mkv_path, stream_idx):
    """
    Extrai as primeiras linhas de uma faixa de legenda específica usando o ffmpeg.
    
    Comando executado:
    ffmpeg -i <arquivo_mkv> -map 0:<stream_idx> -f srt -v quiet -
    
    -i <arquivo>: Arquivo de entrada.
    -map 0:<stream_idx>: Seleciona apenas a faixa de legenda desejada do primeiro input (0).
    -f srt: Força a saída no formato SRT.
    -v quiet: Impede que o ffmpeg exiba logs (para não poluir a saída do nosso script).
    -: Envia o resultado para a saída padrão (stdout) onde o Python vai ler.
    """
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    
    # Executa o processo de forma assíncrona para que possamos interrompê-lo assim que lermos o suficiente
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    out = []
    lines_read = 0
    for line in process.stdout:
        out.append(line.strip())
        lines_read += 1
        # Lemos apenas as primeiras 20 linhas do SRT para não precisar extrair a legenda inteira
        if lines_read > 20:
            break
            
    process.terminate() # Encerra o ffmpeg prematuramente para poupar tempo
    return '\n'.join(out)

# Lista de arquivos para inspecionar
files = [
    r"Z:\Traducao\Lucky.2026.S01E01.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv",
    r"Z:\Traducao\Lucky.2026.S01E02.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv"
]

# Escrevemos os resultados em um arquivo de texto
with open('subtitles_peek.txt', 'w', encoding='utf-8') as f_out:
    for f in files:
        f_out.write(f"File: {f}\n")
        subs = get_subtitle_streams(f)
        for s in subs:
            content = peek_subtitle(f, s)
            # Limpa o formato SRT (remove números e timestamps '-->') para obtermos apenas o texto
            lines = [l for l in content.split('\n') if l and not l.isdigit() and '-->' not in l]
            # Pega apenas as 3 primeiras linhas de diálogo
            text = " ".join(lines[:3])
            f_out.write(f"Stream {s}: {text}\n")

