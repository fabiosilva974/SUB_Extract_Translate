# ==============================================================================
# Script: identify_subs.py
#
# Objetivo:
#   Identifica o idioma de trilhas de legenda sem nome dentro de um arquivo MKV
#   utilizando inteligência heurística para adivinhar a língua pelo texto.
#
# Lógica Principal:
#   O script percorre as trilhas de legenda, lê as primeiras dezenas de linhas 
#   com ffmpeg e passa o resultado para a biblioteca 'langdetect'. O resultado 
#   é convertido para o padrão MKV (ISO 639-2) e gravado em um novo arquivo usando
#   o mkvmerge.
#
# Dependências Externas:
#   MKVToolNix (mkvmerge), FFmpeg, langdetect
# ==============================================================================
import os
import subprocess
import json
import argparse
import glob
from langdetect import detect, DetectorFactory
from pathlib import Path

# Fixa o seed para resultados determinísticos do langdetect
DetectorFactory.seed = 0

# Caminho para o executável do MKVToolNix no Windows
MKVMERGE_PATH = r"C:\Program Files\MKVToolNix\mkvmerge.exe"

# Mapeamento do código de 2 letras do langdetect para o padrão de 3 letras (ISO 639-2) usado no MKV
LANG_MAP = {
    'en': 'eng', 'pt': 'por', 'es': 'spa', 'fr': 'fre', 'de': 'ger',
    'it': 'ita', 'ja': 'jpn', 'zh-cn': 'chi', 'zh-tw': 'chi', 'ko': 'kor',
    'ru': 'rus', 'ar': 'ara', 'nl': 'dut', 'pl': 'pol', 'sv': 'swe',
    'da': 'dan', 'no': 'nor', 'fi': 'fin', 'tr': 'tur', 'el': 'gre',
    'he': 'heb', 'hi': 'hin', 'cs': 'cze', 'hu': 'hun', 'ro': 'rum',
    'th': 'tha', 'vi': 'vie', 'id': 'ind', 'bg': 'bul', 'hr': 'hrv',
    'uk': 'ukr', 'sk': 'slo', 'sl': 'slv',
}

def peek_subtitle(mkv_path, stream_idx):
    """
    Usa ffmpeg para extrair as primeiras falas de uma trilha de legenda
    para fins de detecção de idioma.
    """
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:s:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    # errors='ignore' para evitar crash se a legenda tiver caracteres bizarros
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    out = []
    lines_read = 0
    
    # Lê as primeiras linhas suficientes para detecção (cerca de 40 a 50 blocos de texto)
    for line in process.stdout:
        line = line.strip()
        # Pula as linhas de número de bloco (só digitos) e timecode (-->)
        if line and not line.isdigit() and '-->' not in line:
            # Retira tags HTML básicas se existirem, ex: <i>
            clean_line = line.replace('<i>', '').replace('</i>', '').replace('<b>', '').replace('</b>', '')
            out.append(clean_line)
            lines_read += 1
            if lines_read >= 50:
                break
    process.terminate()
    return ' '.join(out)

def process_mkv(mkv_path):
    base_name = os.path.basename(mkv_path)
    dir_name = os.path.dirname(mkv_path)
    prefix = base_name.replace(".mkv", "")
    out_mkv = os.path.join(dir_name, f"{prefix}_Identified.mkv")
    
    print(f"\n============================================================")
    print(f" Analisando legendas em: {base_name}")
    print(f"============================================================")
    
    # Obtém informações do MKV usando mkvmerge -J
    cmd_j = [MKVMERGE_PATH, "-J", mkv_path]
    try:
        res = subprocess.run(cmd_j, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        info = json.loads(res.stdout)
    except Exception as e:
        print(f"[ERRO] Falha ao ler {base_name} com mkvmerge: {e}")
        return
        
    subtitle_tracks = []
    ffmpeg_sub_idx = 0
    
    for track in info.get("tracks", []):
        if track.get("type") == "subtitles":
            track_id = track.get("id")
            # O ffmpeg numera os streams de legenda como 0:s:0, 0:s:1... 
            # Como iteramos pelas trilhas na mesma ordem, o índice de legenda (ffmpeg_sub_idx) baterá.
            sample_text = peek_subtitle(mkv_path, ffmpeg_sub_idx)
            lang_code_3 = "und"
            
            if len(sample_text.strip()) > 10:
                try:
                    lang_2 = detect(sample_text)
                    lang_code_3 = LANG_MAP.get(lang_2, lang_2)
                    print(f"  - Trilha ID {track_id} (ffmpeg s:{ffmpeg_sub_idx}): Identificado como '{lang_code_3}' ({lang_2})")
                except:
                    print(f"  - Trilha ID {track_id} (ffmpeg s:{ffmpeg_sub_idx}): Não foi possível identificar o idioma.")
            else:
                print(f"  - Trilha ID {track_id} (ffmpeg s:{ffmpeg_sub_idx}): Texto insuficiente para detecção.")
                
            subtitle_tracks.append((track_id, lang_code_3))
            ffmpeg_sub_idx += 1
            
    if not subtitle_tracks:
        print("  - Nenhuma trilha de legenda encontrada.")
        return
        
    cmd = [MKVMERGE_PATH, "-o", out_mkv]
    
    # Configura os idiomas para cada trilha identificada
    for track_id, lang_code in subtitle_tracks:
        if lang_code != "und":
            cmd.extend(["--language", f"{track_id}:{lang_code}"])
            
    cmd.append(mkv_path)
    
    print(f"\nGerando arquivo com metadados corrigidos: {out_mkv} ...")
    try:
        subprocess.run(cmd, check=True)
        print("Arquivo gerado com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO CRÍTICO] Falha na junção do mkv: {e}")

def main():
    parser = argparse.ArgumentParser(description="Identifica o idioma das trilhas de legendas e gera um novo MKV.")
    parser.add_argument("alvo", help="Caminho para um arquivo MKV ou diretório.")
    args = parser.parse_args()
    
    target = args.alvo
    
    if os.path.isfile(target):
        process_mkv(target)
    elif os.path.isdir(target):
        for f in glob.glob(os.path.join(target, "*.mkv")):
            # Evita processar arquivos já processados
            if f.endswith("_Identified.mkv") or f.endswith("_PT.mkv"):
                continue
            process_mkv(f)
    else:
        print(f"[ERRO] Caminho inválido: {target}")

if __name__ == "__main__":
    main()
