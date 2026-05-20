#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

# Configurações de caminhos
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

def list_audio_tracks(mkv_path: str) -> list[dict]:
    result = run(["mkvmerge", "-J", mkv_path])
    info = json.loads(result.stdout)
    tracks = []
    for t in info.get("tracks", []):
        if t["type"] == "audio":
            props = t.get("properties", {})
            tracks.append({
                "id":       t["id"],
                "codec":    t.get("codec", ""),
                "language": props.get("language", "und"),
                "name":     props.get("track_name", ""),
            })
    return tracks

def main():
    parser = argparse.ArgumentParser(description="Extrai áudio do MKV.")
    parser.add_argument("mkv", help="Arquivo .mkv de entrada")
    parser.add_argument("--lang", default="eng", help="Idioma da faixa (ex: eng, por). Padrão: eng")
    parser.add_argument("--list", action="store_true", help="Lista as faixas de áudio e sai")
    args = parser.parse_args()

    input_file = Path(args.mkv)
    if not input_file.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    tracks = list_audio_tracks(str(input_file))
    
    if args.list:
        print("\n--- Faixas de Áudio Disponíveis ---")
        print(f"{'ID':>4}  {'Idioma':<8}  {'Codec':<10}  {'Nome'}")
        for t in tracks: 
            print(f"{t['id']:>4}  {t['language']:<8}  {t['codec']:<10}  {t['name']}")
        return

    # Procura a faixa do idioma especificado (por padrão "eng")
    target_track = None
    for t in tracks:
        if t["language"] == args.lang:
            target_track = t
            break
            
    if not target_track:
        print(f"[ERRO] Faixa de áudio com idioma '{args.lang}' não encontrada no arquivo.")
        print("Tente rodar com '--list' para ver os idiomas disponíveis.")
        sys.exit(1)

    # Define o nome do arquivo de saída como .mp3
    output_audio = input_file.with_suffix(".mp3")
    
    print(f"\nExtraindo faixa de áudio:")
    print(f" - ID da faixa: {target_track['id']}")
    print(f" - Idioma:      {target_track['language']}")
    print(f" - Salvando em: {output_audio.name}")
    print("Por favor, aguarde...")
    
    # Extrai usando FFmpeg
    cmd = [
        TOOLS["ffmpeg"], "-y",
        "-i", str(input_file),
        "-map", f"0:{target_track['id']}",
        "-c:a", "libmp3lame", "-q:a", "2",
        str(output_audio)
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if res.returncode == 0:
        print(f"\n[SUCESSO] Áudio salvo com sucesso!")
        print(f"Caminho: {output_audio}")
    else:
        print("\n[ERRO] Falha ao extrair o áudio com FFmpeg.")

if __name__ == "__main__":
    main()
