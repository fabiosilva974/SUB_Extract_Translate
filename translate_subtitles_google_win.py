#!/usr/bin/env python3
# Importa módulos necessários para sistema, regex, JSON, CLI e processos
import os
import re
import sys
import json
import argparse
import subprocess
import tempfile
import glob
from pathlib import Path
from deep_translator import GoogleTranslator

# ── CONFIGURAÇÃO DE CAMINHOS LOCAIS (WINDOWS) ──────────────────────────────────
# Caminhos específicos da sua máquina para os executáveis
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
FFMPEG_BIN     = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin\ffmpeg.exe"

# Mapeamento dos executáveis para uso no script
TOOLS = {
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    "mkvextract": os.path.join(MKVTOOLNIX_DIR, "mkvextract.exe"),
    "ffmpeg":     FFMPEG_BIN
}

BATCH_SIZE = 30
TARGET_LANG = "pt"

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Substitui o nome do comando pelo caminho absoluto se estiver no dicionário TOOLS
    if cmd[0] in TOOLS:
        cmd[0] = TOOLS[cmd[0]]
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

def require_tool(name: str):
    # Verifica se o arquivo executável existe no caminho configurado
    path = TOOLS.get(name, name)
    if not os.path.exists(path):
        print(f"[ERRO] Ferramenta '{name}' não encontrada em: {path}")
        print("Verifique os caminhos no topo do script.")
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
    parser = argparse.ArgumentParser(description="Tradutor MKV (Versão Windows Otimizada)")
    # Agora aceita um ou mais argumentos (permite *.mkv ser expandido ou passado como lista)
    parser.add_argument("mkv", nargs='+', help="Arquivo(s) .mkv ou padrão (ex: *.mkv)")
    parser.add_argument("--lang", default="eng", help="Idioma (ex: eng)")
    parser.add_argument("--source-lang", default="auto", help="Origem (ex: en, ja)")
    parser.add_argument("--output", default=None, help="Saída .srt")
    parser.add_argument("--list-tracks", action="store_true", help="Lista faixas e sai")
    args = parser.parse_args()

    # Expandir wildcards (necessário no Windows CMD que não expande *.mkv automaticamente)
    mkv_files = []
    for pattern in args.mkv:
        matches = glob.glob(pattern)
        if matches:
            mkv_files.extend(matches)
        else:
            mkv_files.append(pattern) # Mantém original para disparar erro de 'não encontrado' se for o caso

    # Verifica ferramentas uma única vez
    require_tool("mkvmerge")
    require_tool("mkvextract")
    require_tool("ffmpeg")

    for mkv_path in mkv_files:
        print(f"\n{'='*60}")
        print(f" Processando: {mkv_path}")
        print(f"{'='*60}")

        if not Path(mkv_path).exists():
            print(f"[ERRO] Arquivo não encontrado: {mkv_path}")
            continue

        tracks = list_tracks(mkv_path)
        if not tracks:
            print(f"[AVISO] Nenhuma faixa de legenda encontrada em {mkv_path}")
            continue

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
            with open(srt_path, encoding="utf-8", errors="replace") as f: srt_text = f.read()

        entries = parse_srt(srt_text)
        if not entries:
            print(f"  [ERRO] Não foi possível parsear a legenda de {mkv_path}")
            continue

        print(f"  Blocos encontrados: {len(entries)}")
        translated = translate_entries(entries, source_lang=args.source_lang)
        
        # Se houver múltiplos arquivos, o output fixo --output pode ser problemático.
        # Se for None, gera o padrão .pt.srt. Se for definido, usará o mesmo nome para todos (sobrescrevendo).
        if args.output and len(mkv_files) > 1:
            print(f"  [AVISO] --output definido com múltiplos arquivos. Todos usarão o mesmo nome.")
        
        out_path = args.output or Path(mkv_path).with_suffix(".pt.srt")
        with open(out_path, "w", encoding="utf-8") as f: f.write(build_srt(translated))
        print(f"\n✅ Concluído: {out_path}")

if __name__ == "__main__":
    main()
