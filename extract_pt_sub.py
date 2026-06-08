import os
import sys
import json
import argparse
import subprocess
import re
from pathlib import Path
import tempfile

"""
Script: extract_pt_sub.py
Objetivo: Procura a faixa de legenda em Português dentro de um arquivo MKV
          fazendo uma análise heurística do conteúdo das legendas, sem confiar
          cegamente nos metadados da faixa, que frequentemente são incorretos.
"""

MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
FFMPEG_BIN     = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin\ffmpeg.exe"

TOOLS = {
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    "ffmpeg":    FFMPEG_BIN
}

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    if cmd[0] in TOOLS:
        cmd[0] = TOOLS[cmd[0]]
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")

def list_subtitle_tracks(mkv_path: str) -> list[dict]:
    """Lista todas as faixas de legenda (subtitles) do arquivo MKV."""
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

def is_portuguese(text: str) -> int:
    """
    Retorna uma pontuação baseada na quantidade de palavras muito comuns 
    na língua portuguesa. Quanto maior a pontuação, maior a chance de ser PT-BR.
    """
    pt_words = [r"\bnão\b", r"\bvocê\b", r"\bcom\b", r"\bum\b", r"\buma\b", r"\bele\b", r"\bela\b", r"\bisso\b", r"\baqui\b", r"\bquem\b", r"\bmuito\b", r"\btambém\b", r"\bsão\b", r"\bvocês\b", r"\bestá\b", r"\bjá\b"]
    score = 0
    text_lower = text.lower()
    for word_pattern in pt_words:
        # Usa regex com \b (word boundary) para não encontrar trechos no meio de palavras maiores
        score += len(re.findall(word_pattern, text_lower))
    return score

def main():
    parser = argparse.ArgumentParser(description="Procura e extrai a faixa de legenda em Português de um MKV, identificando pelo conteúdo.")
    parser.add_argument("mkv", help="Arquivo .mkv de entrada")
    args = parser.parse_args()

    input_file = Path(args.mkv)
    if not input_file.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    print(f"Listando faixas de '{input_file.name}'...")
    tracks = list_subtitle_tracks(str(input_file))
    
    if not tracks:
        print("[ERRO] Nenhuma faixa de legenda encontrada no arquivo.")
        sys.exit(1)
        
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
        
        # Extrai todas as legendas do arquivo ao mesmo tempo usando -map no ffmpeg
        # Isso economiza tempo não precisando ler o vídeo enorme repetidas vezes
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
                
                score = is_portuguese(text)
                if score > best_score:
                    best_score = score
                    best_track = t
                    best_text = text

    if best_track and best_score > 10:  # Mínimo de ocorrências para ter certeza
        print(f"\n[SUCESSO] Faixa de legenda em Português identificada!")
        print(f" - ID da faixa original: {best_track['id']}")
        print(f" - Pontuação de similaridade com PT: {best_score}")
        
        output_srt = input_file.with_suffix(".pt.srt")
        output_srt.write_text(best_text, encoding="utf-8")
        print(f"Legenda salva em: {output_srt}")
    else:
        print("\n[ERRO] Não foi possível identificar com confiança uma faixa de legenda em Português.")

if __name__ == "__main__":
    main()
