import os
import sys
import json
import argparse
import subprocess
import re
from pathlib import Path
import tempfile
import glob

"""
Script: extract_en_sub.py
Objetivo: Procura a faixa de legenda em Inglês dentro de um ou mais arquivos MKV
          fazendo uma análise heurística do conteúdo das legendas, sem confiar
          cegamente nos metadados da faixa. Suporta arquivos individuais ou diretórios.
"""

# Configura o diretório padrão onde o pacote de ferramentas MKVToolNix fica instalado
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
# Configura o diretório exato do executável FFmpeg
FFMPEG_BIN     = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin\ffmpeg.exe"

# Cria um dicionário que associa o nome do comando ao caminho exato no Windows
TOOLS = {
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    "ffmpeg":    FFMPEG_BIN
}

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    if cmd[0] in TOOLS:
        cmd[0] = TOOLS[cmd[0]]
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")

def list_subtitle_tracks(mkv_path: str) -> list[dict]:
    result = run(["mkvmerge", "-J", mkv_path])
    info = json.loads(result.stdout)
    tracks = []
    for t in info.get("tracks", []):
        if t["type"] == "subtitles":
            props = t.get("properties", {})
            tracks.append({
                "id":       t["id"],
                "codec":    t.get("codec", ""),
                "language": props.get("language", "und"),
                "name":     props.get("track_name", ""),
            })
    return tracks

def is_english(text: str) -> int:
    """
    Retorna uma pontuação baseada na quantidade de palavras muito comuns 
    na língua inglesa.
    """
    en_words = [r"\bthe\b", r"\bbe\b", r"\bto\b", r"\bof\b", r"\band\b", r"\ba\b", 
                r"\bin\b", r"\bthat\b", r"\bhave\b", r"\bi\b", r"\bit\b", r"\bfor\b", 
                r"\bnot\b", r"\bon\b", r"\bwith\b", r"\bhe\b", r"\bas\b", r"\byou\b", 
                r"\bdo\b", r"\bat\b", r"\bthis\b", r"\bbut\b", r"\bhis\b", r"\bby\b", 
                r"\bfrom\b"]
    score = 0
    text_lower = text.lower()
    for word_pattern in en_words:
        score += len(re.findall(word_pattern, text_lower))
    return score

def process_mkv(input_file: Path):
    print(f"\n--- Processando '{input_file.name}' ---")
    if not input_file.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        return

    print(f"Listando faixas de '{input_file.name}'...")
    tracks = list_subtitle_tracks(str(input_file))
    
    if not tracks:
        print("[ERRO] Nenhuma faixa de legenda encontrada no arquivo.")
        return
        
    print(f"Encontradas {len(tracks)} faixas de legenda. Extraindo para análise...")
    
    best_track = None
    best_score = 0
    best_text = ""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        maps = []
        track_files = {}
        for t in tracks:
            tmp_srt = Path(tmpdir) / f"{t['id']}.srt"
            track_files[t['id']] = tmp_srt
            maps.extend(["-map", f"0:{t['id']}", str(tmp_srt)])
        
        cmd = [TOOLS["ffmpeg"], "-y", "-i", str(input_file)] + maps
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("Analisando o idioma das legendas...")
        for t in tracks:
            tmp_srt = track_files[t['id']]
            if tmp_srt.exists():
                try:
                    text = tmp_srt.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        text = tmp_srt.read_text(encoding="latin-1")
                    except:
                        continue
                
                score = is_english(text)
                if score > best_score:
                    best_score = score
                    best_track = t
                    best_text = text

    if best_track and best_score > 10: 
        print(f"[SUCESSO] Faixa de legenda em Inglês identificada!")
        print(f" - ID da faixa original: {best_track['id']}")
        print(f" - Pontuação de similaridade com EN: {best_score}")
        
        output_srt = input_file.with_suffix(".en.srt")
        output_srt.write_text(best_text, encoding="utf-8")
        print(f"Legenda salva em: {output_srt}")
    else:
        print("[ERRO] Não foi possível identificar com confiança uma faixa de legenda em Inglês.")

def main():
    parser = argparse.ArgumentParser(description="Procura e extrai a faixa de legenda em Inglês de um ou mais arquivos MKV, ou de um diretório.")
    parser.add_argument("paths", nargs="+", help="Arquivo(s) .mkv ou diretório(s) de entrada")
    args = parser.parse_args()

    mkv_files = []
    
    # Expand paths using glob to handle wildcards passed by terminal
    expanded_paths = []
    for path_str in args.paths:
        if "*" in path_str or "?" in path_str:
            expanded_paths.extend(glob.glob(path_str))
        else:
            expanded_paths.append(path_str)
    
    for path_str in expanded_paths:
        p = Path(path_str)
        if p.is_file() and p.suffix.lower() == ".mkv":
            if p not in mkv_files:
                mkv_files.append(p)
        elif p.is_dir():
            for mkv_file in p.glob("*.mkv"):
                if mkv_file not in mkv_files:
                    mkv_files.append(mkv_file)
        else:
            print(f"[AVISO] Ignorando caminho inválido ou não-mkv: {path_str}")

    if not mkv_files:
        print("[ERRO] Nenhum arquivo MKV válido encontrado para processar.")
        sys.exit(1)
        
    print(f"Total de arquivos MKV para processar: {len(mkv_files)}")
    
    for mkv in mkv_files:
        process_mkv(mkv)

if __name__ == "__main__":
    main()
