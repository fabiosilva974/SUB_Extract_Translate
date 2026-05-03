#!/usr/bin/env python3
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
from deep_translator import GoogleTranslator

BATCH_SIZE = 30
TARGET_LANG = "pt"

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def require_tool(name: str):
    result = run(["where" if os.name == "nt" else "which", name], check=False)
    if result.returncode != 0:
        print(f"[ERRO] '{name}' não encontrado. Instale o mkvtoolnix e ffmpeg.")
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

def translate_batch(lines: list[str], source_lang: str = "auto") -> list[str]:
    try:
        translator = GoogleTranslator(source=source_lang, target=TARGET_LANG)
        return translator.translate_batch(lines)
    except Exception as e:
        print(f"  [erro na tradução] {e}")
        return lines

def translate_entries(entries: list[dict], source_lang: str = "auto") -> list[dict]:
    texts = [e["text"] for e in entries]
    total = len(texts)
    translated_texts = []
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({int(end/total*100)}%)…")
        translated_texts.extend(translate_batch(texts[start:end], source_lang))
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

def convert_to_srt_if_needed(raw_path: str, codec: str) -> str:
    if "subrip" in codec.lower() or "srt" in codec.lower(): return raw_path
    srt_path = raw_path + ".srt"
    result = run(["ffmpeg", "-y", "-i", raw_path, srt_path], check=False)
    if result.returncode == 0 and Path(srt_path).exists():
        print(f"  Convertido de {codec} para SRT via ffmpeg.")
        return srt_path
    print(f"  [aviso] Não foi possível converter '{codec}' automaticamente.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Extrai e traduz legendas de MKV para português via Google Translate.")
    parser.add_argument("mkv", nargs='+', help="Arquivo(s) .mkv ou padrão (ex: *.mkv)")
    parser.add_argument("--lang", default="eng", help="Idioma da faixa a extrair (padrão: eng)")
    parser.add_argument("--source-lang", default="auto", help="Origem da tradução (ex: en, ja)")
    parser.add_argument("--output", default=None, help="Saída .srt (padrão: .pt.srt ou .srt)")
    parser.add_argument("--list-tracks", action="store_true", help="Lista faixas e sai")
    parser.add_argument("--extract-only", action="store_true", help="Apenas extrai a legenda original sem traduzir")
    args = parser.parse_args()

    mkv_files = []
    for pattern in args.mkv:
        matches = glob.glob(pattern)
        mkv_files.extend(matches) if matches else mkv_files.append(pattern)

    require_tool("mkvmerge")
    require_tool("mkvextract")

    for mkv_path in mkv_files:
        print(f"\n{'='*60}\n Processando: {mkv_path}\n{'='*60}")
        if not Path(mkv_path).exists():
            print(f"[ERRO] Arquivo não encontrado: {mkv_path}")
            continue

        tracks = list_tracks(mkv_path)
        if not tracks: continue

        if args.list_tracks:
            print(f"{'ID':>4}  {'Idioma':<8}  {'Codec':<20}")
            for t in tracks: print(f"{t['id']:>4}  {t['language']:<8}  {t['codec']:<20}")
            continue

        track = pick_track(tracks, args.lang)
        print(f"\nUsando faixa ID={track['id']} ({track['language']}) codec={track['codec']}")

        with tempfile.TemporaryDirectory() as tmp:
            ext = "ass" if "ass" in track["codec"].lower() else "srt"
            raw_path = os.path.join(tmp, f"sub.{ext}")
            print("  Extraindo legenda…")
            extract_subtitle(mkv_path, track["id"], raw_path)
            srt_path = convert_to_srt_if_needed(raw_path, track["codec"])
            
            if args.extract_only:
                dest_path = args.output or Path(mkv_path).with_suffix(".srt")
                shutil.copy(srt_path, dest_path)
                print(f"\n✅ Extração concluída: {dest_path}")
                continue

            with open(srt_path, encoding="utf-8", errors="replace") as f: srt_text = f.read()

        entries = parse_srt(srt_text)
        if not entries: continue

        print(f"  Blocos encontrados: {len(entries)}")
        translated = translate_entries(entries, source_lang=args.source_lang)
        out_path = args.output or Path(mkv_path).with_suffix(".pt.srt")
        with open(out_path, "w", encoding="utf-8") as f: f.write(build_srt(translated))
        print(f"\n✅ Concluído: {out_path}")

if __name__ == "__main__":
    main()
