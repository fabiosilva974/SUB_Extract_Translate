#!/usr/bin/env python3
"""
translate_subtitles.py
======================
Extrai legenda de um arquivo .mkv e traduz para português usando a API Claude.

Uso:
    python translate_subtitles.py *.mkv
    python translate_subtitles.py video1.mkv video2.mkv --lang eng
"""

import os
import re
import sys
import json
import argparse
import subprocess
import tempfile
import glob
from pathlib import Path

# ── Configuração da API ────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = "claude-sonnet-4-20250514"
BATCH_SIZE = 40        # linhas de diálogo por requisição (evita tokens excessivos)
MAX_TOKENS  = 4096


# ── Helpers de processo ────────────────────────────────────────────────────────

def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def require_tool(name: str):
    result = run(["where" if os.name == "nt" else "which", name], check=False)
    if result.returncode != 0:
        print(f"[ERRO] '{name}' não encontrado. Instale o mkvtoolnix.")
        sys.exit(1)


# ── Listagem e extração de faixas ──────────────────────────────────────────────

def list_tracks(mkv_path: str) -> list[dict]:
    """Retorna lista de faixas de legenda do arquivo."""
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
    """Extrai a faixa `track_id` para `out_path` usando mkvextract."""
    run(["mkvextract", "tracks", mkv_path, f"{track_id}:{out_path}"])


def pick_track(tracks: list[dict], prefer_lang: str) -> dict | None:
    """Escolhe a melhor faixa: prefere `prefer_lang`, depois 'eng', depois a primeira."""
    for t in tracks:
        if t["language"] == prefer_lang:
            return t
    for t in tracks:
        if t["language"] == "eng":
            return t
    return tracks[0] if tracks else None


# ── Parsing SRT ───────────────────────────────────────────────────────────────

ENTRY_RE = re.compile(
    r"(\d+)\r?\n"                          # número do bloco
    r"([\d:,]+ --> [\d:,]+)\r?\n"          # timecode
    r"([\s\S]*?)(?=\n\n|\Z)",              # texto (pode ter múltiplas linhas)
    re.MULTILINE,
)

def parse_srt(text: str) -> list[dict]:
    entries = []
    for m in ENTRY_RE.finditer(text.strip()):
        entries.append({
            "index":    m.group(1),
            "timecode": m.group(2),
            "text":     m.group(3).strip(),
        })
    return entries


def build_srt(entries: list[dict]) -> str:
    blocks = []
    for e in entries:
        blocks.append(f"{e['index']}\n{e['timecode']}\n{e['text']}\n")
    return "\n".join(blocks)


# ── Tradução via Claude ────────────────────────────────────────────────────────

def translate_batch(lines: list[str], source_lang: str = "inglês") -> list[str]:
    """Traduz uma lista de textos de legenda para português brasileiro."""
    import urllib.request

    numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
    prompt = (
        f"Você é um tradutor profissional de legendas de {source_lang} para português brasileiro.\n"
        "Traduza cada linha abaixo mantendo:\n"
        "- Tags HTML como <i>, <b>, <font> (se houver)\n"
        "- Quebras de linha internas (\\n)\n"
        "- O mesmo número de itens, na mesma ordem\n"
        "- Naturalidade e fluidez no português\n\n"
        "Retorne APENAS as linhas traduzidas numeradas no mesmo formato (1. texto, 2. texto…), "
        "sem explicações extras.\n\n"
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

    # extrai as linhas numeradas da resposta
    result_lines = []
    for line in raw.splitlines():
        m = re.match(r"^\d+\.\s*(.*)", line)
        if m:
            result_lines.append(m.group(1))

    # fallback: retorna o original se a contagem não bater
    if len(result_lines) != len(lines):
        print(f"  [aviso] resposta com {len(result_lines)} itens para {len(lines)} enviados — usando originais")
        return lines

    return result_lines


def translate_entries(entries: list[dict], source_lang: str = "inglês") -> list[dict]:
    """Traduz todos os blocos de legenda em batches."""
    texts   = [e["text"] for e in entries]
    total   = len(texts)
    translated_texts = []

    for start in range(0, total, BATCH_SIZE):
        end   = min(start + BATCH_SIZE, total)
        batch = texts[start:end]
        pct   = int(end / total * 100)
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({pct}%)…")
        translated_texts.extend(translate_batch(batch, source_lang))

    return [
        {**e, "text": t}
        for e, t in zip(entries, translated_texts)
    ]


# ── Detecção de codec / conversão para SRT ────────────────────────────────────

def convert_to_srt_if_needed(raw_path: str, codec: str) -> str:
    """
    Se a legenda extraída não for SRT (ex: ASS/SSA), converte com ffmpeg.
    Retorna o caminho do arquivo SRT final.
    """
    codec_lower = codec.lower()
    if "subrip" in codec_lower or "srt" in codec_lower:
        return raw_path

    # tenta converter com ffmpeg
    srt_path = raw_path + ".srt"
    result = run(["ffmpeg", "-y", "-i", raw_path, srt_path], check=False)
    if result.returncode == 0 and Path(srt_path).exists():
        print(f"  Convertido de {codec} para SRT via ffmpeg.")
        return srt_path

    print(f"  [aviso] Não foi possível converter o codec '{codec}' automaticamente.")
    sys.exit(1)


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Extrai e traduz legenda de um arquivo MKV para português."
    )
    parser.add_argument("mkv",           nargs='+', help="Arquivo(s) .mkv ou padrão (ex: *.mkv)")
    parser.add_argument("--lang",        default="eng",  help="Código de idioma a extrair (padrão: eng)")
    parser.add_argument("--source-lang", default="inglês", help="Nome do idioma de origem para o prompt")
    parser.add_argument("--output",      default=None,   help="Arquivo de saída .srt")
    parser.add_argument("--list-tracks", action="store_true", help="Lista as faixas de legenda e sai")
    args = parser.parse_args()

    mkv_files = []
    for pattern in args.mkv:
        matches = glob.glob(pattern)
        if matches:
            mkv_files.extend(matches)
        else:
            mkv_files.append(pattern)

    require_tool("mkvmerge")
    require_tool("mkvextract")

    for mkv_path in mkv_files:
        print(f"\n{'='*60}")
        print(f" Processando: {mkv_path}")
        print(f"{'='*60}")

        if not Path(mkv_path).exists():
            print(f"[ERRO] Arquivo não encontrado: {mkv_path}")
            continue

        # ── listar faixas ────────────────────────────────────────────────────────
        tracks = list_tracks(mkv_path)
        if not tracks:
            print(f"[ERRO] Nenhuma faixa encontrada em {mkv_path}")
            continue

        if args.list_tracks:
            print(f"{'ID':>4}  {'Idioma':<8}  {'Codec':<20}  {'Nome'}")
            print("-" * 55)
            for t in tracks:
                print(f"{t['id']:>4}  {t['language']:<8}  {t['codec']:<20}  {t['name']}")
            continue

        # ── escolher faixa ───────────────────────────────────────────────────────
        track = pick_track(tracks, args.lang)
        if track is None: continue

        print(f"\nUsando faixa ID={track['id']}  lang={track['language']}  codec={track['codec']}")

        # ── extrair ──────────────────────────────────────────────────────────────
        with tempfile.TemporaryDirectory() as tmp:
            ext       = "ass" if "ass" in track["codec"].lower() else "srt"
            raw_path  = os.path.join(tmp, f"sub.{ext}")
            print("Extraindo legenda…")
            extract_subtitle(mkv_path, track["id"], raw_path)
            srt_path = convert_to_srt_if_needed(raw_path, track["codec"])
            with open(srt_path, encoding="utf-8", errors="replace") as f:
                srt_text = f.read()

        # ── parsear ──────────────────────────────────────────────────────────────
        entries = parse_srt(srt_text)
        if not entries: continue

        # ── verificar chave ──────────────────────────────────────────────────────
        if not ANTHROPIC_API_KEY:
            print("\n[ERRO] ANTHROPIC_API_KEY não definida.")
            sys.exit(1)

        # ── traduzir ─────────────────────────────────────────────────────────────
        print(f"\nTraduzindo para português…")
        translated = translate_entries(entries, source_lang=args.source_lang)

        # ── salvar ───────────────────────────────────────────────────────────────
        out_path = args.output or Path(mkv_path).with_suffix(".pt.srt")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(build_srt(translated))

        print(f"\n✅ Concluído: {out_path}")


if __name__ == "__main__":
    main()
