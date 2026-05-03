#!/usr/bin/env python3
"""
translate_subtitles.py
======================
Extrai legenda de um arquivo .mkv e traduz para português usando a API Claude.
"""

import os
import re
import sys
import json
import argparse
import subprocess
import tempfile
import glob
import shutil
from pathlib import Path

# ── Configuração da API ────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"
BATCH_SIZE = 40
MAX_TOKENS  = 4096

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def require_tool(name: str):
    result = run(["where" if os.name == "nt" else "which", name], check=False)
    if result.returncode != 0:
        print(f"[ERRO] '{name}' não encontrado. Instale o mkvtoolnix.")
        sys.exit(1)

def list_tracks(mkv_path: str) -> list[dict]:
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

def extract_subtitle(mkv_path: str, track_id: int, out_path: str):
    run(["mkvextract", "tracks", mkv_path, f"{track_id}:{out_path}"])

def pick_track(tracks: list[dict], prefer_lang: str) -> dict | None:
    for t in tracks:
        if t["language"] == prefer_lang: return t
    for t in tracks:
        if t["language"] == "eng": return t
    return tracks[0] if tracks else None

ENTRY_RE = re.compile(r"(\d+)\r?\n([\d:,]+ --> [\d:,]+)\r?\n([\s\S]*?)(?=\n\n|\Z)", re.MULTILINE)

def parse_srt(text: str) -> list[dict]:
    entries = []
    for m in ENTRY_RE.finditer(text.strip()):
        entries.append({"index": m.group(1), "timecode": m.group(2), "text": m.group(3).strip()})
    return entries

def build_srt(entries: list[dict]) -> str:
    return "\n".join([f"{e['index']}\n{e['timecode']}\n{e['text']}\n" for e in entries])

def translate_batch(lines: list[str], source_lang: str = "inglês") -> list[str]:
    import urllib.request
    numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
    prompt = (
        f"Você é um tradutor profissional de legendas de {source_lang} para português brasileiro.\n"
        "Traduza cada linha abaixo mantendo tags HTML e mantendo a ordem.\n"
        f"{numbered}"
    )
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    raw = data["content"][0]["text"].strip()
    result_lines = []
    for line in raw.splitlines():
        m = re.match(r"^\d+\.\s*(.*)", line)
        if m: result_lines.append(m.group(1))
    return result_lines if len(result_lines) == len(lines) else lines

def translate_entries(entries: list[dict], source_lang: str = "inglês") -> list[dict]:
    texts = [e["text"] for e in entries]
    total = len(texts)
    translated_texts = []
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        print(f"  Traduzindo {start+1}–{end} de {total}…")
        translated_texts.extend(translate_batch(texts[start:end], source_lang))
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

def convert_subtitle(input_path: str, output_path: str) -> bool:
    if input_path == output_path: return True
    result = run(["ffmpeg", "-y", "-i", input_path, output_path], check=False)
    return result.returncode == 0 and Path(output_path).exists()

def main():
    parser = argparse.ArgumentParser(description="Extrai e traduz legenda de um arquivo MKV via Claude.")
    parser.add_argument("mkv", nargs='+', help="Arquivo(s) .mkv ou padrão")
    parser.add_argument("--lang", default="eng", help="Idioma da faixa")
    parser.add_argument("--format", choices=["srt", "ass"], default="srt", help="Formato de saída")
    parser.add_argument("--source-lang", default="inglês", help="Idioma de origem")
    parser.add_argument("--output", default=None, help="Saída")
    parser.add_argument("--list-tracks", action="store_true", help="Lista faixas")
    parser.add_argument("--extract-only", action="store_true", help="Apenas extrai")
    args = parser.parse_args()

    mkv_files = []
    for pattern in args.mkv:
        matches = glob.glob(pattern)
        mkv_files.extend(matches) if matches else mkv_files.append(pattern)

    require_tool("mkvmerge")
    require_tool("mkvextract")

    for mkv_path in mkv_files:
        print(f"\nProcessando: {mkv_path}")
        if not Path(mkv_path).exists(): continue

        tracks = list_tracks(mkv_path)
        if not tracks: continue

        if args.list_tracks:
            for t in tracks: print(f"ID={t['id']} lang={t['language']} codec={t['codec']}")
            continue

        track = pick_track(tracks, args.lang)
        with tempfile.TemporaryDirectory() as tmp:
            orig_ext = "ass" if "ass" in track["codec"].lower() else "srt"
            raw_path = os.path.join(tmp, f"sub_orig.{orig_ext}")
            extract_subtitle(mkv_path, track["id"], raw_path)
            
            if args.extract_only:
                final_ext = f".{args.format}"
                dest_path = args.output or Path(mkv_path).with_suffix(final_ext)
                convert_subtitle(raw_path, str(dest_path))
                print(f"✅ Extraído: {dest_path}")
                continue

            srt_internal = os.path.join(tmp, "internal.srt")
            convert_subtitle(raw_path, srt_internal)
            with open(srt_internal, encoding="utf-8", errors="replace") as f: srt_text = f.read()

        entries = parse_srt(srt_text)
        if not ANTHROPIC_API_KEY: sys.exit(1)
        translated = translate_entries(entries, source_lang=args.source_lang)
        out_path = args.output or Path(mkv_path).with_suffix(".pt.srt")
        with open(out_path, "w", encoding="utf-8") as f: f.write(build_srt(translated))
        print(f"✅ Concluído: {out_path}")

if __name__ == "__main__":
    main()
