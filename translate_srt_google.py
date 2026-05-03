#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Importa os módulos necessários
import os
import re
import sys
import argparse
import glob
from pathlib import Path
from deep_translator import GoogleTranslator

# ── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
BATCH_SIZE = 30
TARGET_LANG = "pt"

# Expressão regular para identificar os blocos de um arquivo SRT
ENTRY_RE = re.compile(
    r"(\d+)\r?\n"                          # Índice
    r"([\d:,]+ --> [\d:,]+)\r?\n"          # Timecode
    r"([\s\S]*?)(?=\n\n|\Z)",              # Texto
    re.MULTILINE,
)

# Função para transformar texto SRT em lista de dicionários
def parse_srt(text: str) -> list[dict]:
    entries = []
    for m in ENTRY_RE.finditer(text.strip()):
        entries.append({
            "index":    m.group(1),
            "timecode": m.group(2),
            "text":     m.group(3).strip(),
        })
    return entries

# Função para reconstruir o arquivo SRT
def build_srt(entries: list[dict]) -> str:
    blocks = []
    for e in entries:
        blocks.append(f"{e['index']}\n{e['timecode']}\n{e['text']}\n")
    return "\n".join(blocks)

# Função para traduzir um lote de textos
def translate_batch(lines: list[str], source_lang: str = "auto") -> list[str]:
    try:
        translator = GoogleTranslator(source=source_lang, target=TARGET_LANG)
        return translator.translate_batch(lines)
    except Exception as e:
        print(f"  [erro na tradução] {e}")
        return lines

# Função que gerencia a tradução de todas as entradas
def translate_entries(entries: list[dict], source_lang: str = "auto") -> list[dict]:
    texts = [e["text"] for e in entries]
    total = len(texts)
    translated_texts = []
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({int(end/total*100)}%)…")
        translated_texts.extend(translate_batch(texts[start:end], source_lang))
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

# Função principal
def main():
    parser = argparse.ArgumentParser(description="Tradutor independente de arquivos SRT via Google Translate.")
    parser.add_argument("srt", nargs='+', help="Arquivo(s) .srt ou padrão (ex: *.srt)")
    parser.add_argument("--source-lang", default="auto", help="Idioma de origem (ex: en, ja, es)")
    parser.add_argument("--output", default=None, help="Arquivo de saída (opcional)")
    args = parser.parse_args()

    # Expandir wildcards para suporte no Windows
    srt_files = []
    for pattern in args.srt:
        matches = glob.glob(pattern)
        if matches:
            srt_files.extend(matches)
        else:
            srt_files.append(pattern)

    for srt_path in srt_files:
        print(f"\n{'='*60}\n Traduzindo: {srt_path}\n{'='*60}")
        
        if not Path(srt_path).exists():
            print(f"[ERRO] Arquivo não encontrado: {srt_path}")
            continue

        try:
            # Lê o arquivo SRT com tratamento de encoding
            with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
                srt_text = f.read()
            
            # Converte para objetos
            entries = parse_srt(srt_text)
            if not entries:
                print(f"[ERRO] Não foi possível encontrar blocos válidos em {srt_path}")
                continue

            print(f"  Blocos encontrados: {len(entries)}")
            
            # Traduz
            translated = translate_entries(entries, source_lang=args.source_lang)
            
            # Define caminho de saída
            out_path = args.output or Path(srt_path).with_suffix(".pt.srt")
            
            # Salva
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(build_srt(translated))
            
            print(f"\n✅ Tradução salva em: {out_path}")

        except Exception as e:
            print(f"[ERRO CRÍTICO] Falha ao processar {srt_path}: {e}")

if __name__ == "__main__":
    main()
