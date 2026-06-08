#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: transcribe_audio.py
Objetivo: Recebe um arquivo de áudio (.mp3, .wav) e usa o modelo IA Whisper para 
          gerar a legenda (.srt) correspondente. Permite transcrição direta ou
          tradução de áudio de idioma estrangeiro para o inglês.
"""
import os
import sys
import argparse
from pathlib import Path
import shutil

# Configura o caminho do FFmpeg
FFMPEG_BIN_DIR = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin"
os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + os.environ.get("PATH", "")

try:
    import whisper
    from whisper.utils import get_writer
except ImportError:
    print("[ERRO] A biblioteca 'openai-whisper' não está instalada.")
    sys.exit(1)

def main():
    # Definição dos argumentos aceitos via linha de comando
    parser = argparse.ArgumentParser(description="Transcreve arquivo de áudio para legenda (SRT)")
    parser.add_argument("audio", help="Caminho para o arquivo de áudio (ex: .mp3, .wav)")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"])
    parser.add_argument("--lang", default="ja", help="Idioma do áudio. Padrão: en")
    parser.add_argument("--task", default="transcribe", choices=["transcribe", "translate"], help="Tarefa: 'transcribe' (mantém o idioma original) ou 'translate' (traduz direto para INGLÊS)")
    parser.add_argument("--output", default=None, help="Caminho customizado de saída do arquivo SRT")
    args = parser.parse_args()

    input_file = Path(args.audio)
    if not input_file.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    output_dir = str(input_file.parent)
    output_name = input_file.stem
    if args.output:
        out_path = Path(args.output)
        output_dir = str(out_path.parent)
        output_name = out_path.stem

    print(f"\nCarregando modelo Whisper ({args.model})...")
    model = whisper.load_model(args.model)

    print(f"\nIniciando tarefa '{args.task}' de áudio para: {input_file.name}")
    
    # Prepara o dicionário de opções para passar ao Whisper
    transcribe_options = {"task": args.task}
    if args.lang:
        transcribe_options["language"] = args.lang

    # Executa o processamento do áudio via IA
    result = model.transcribe(str(input_file), **transcribe_options)

    print("\nGerando arquivo SRT...")
    writer = get_writer("srt", output_dir)
    writer(result, str(input_file))
    
    generated_srt = Path(output_dir) / f"{input_file.stem}.srt"
    final_output_path = Path(output_dir) / f"{output_name}.srt"
    
    if generated_srt.exists() and generated_srt != final_output_path:
        shutil.move(str(generated_srt), str(final_output_path))
        print(f"[SUCESSO] Legenda gerada com sucesso: {final_output_path}")
    elif generated_srt.exists():
         print(f"[SUCESSO] Legenda gerada com sucesso: {generated_srt}")
    else:
         print(f"[AVISO] Arquivo não salvo em: {generated_srt}")

if __name__ == "__main__":
    main()
