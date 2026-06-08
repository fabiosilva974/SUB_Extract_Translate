#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: audio_to_srt_whisper.py
Objetivo: Utilizar o modelo Whisper (IA da OpenAI) para transcrever o áudio de um
          arquivo de vídeo diretamente para um arquivo de legenda (.srt).
"""
import os
import sys
import argparse
from pathlib import Path
import shutil

# Configura o caminho do FFmpeg (o mesmo usado no seu outro script)
FFMPEG_BIN_DIR = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin"
# Adiciona o FFmpeg ao PATH para que o Whisper consiga encontrá-lo
os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + os.environ.get("PATH", "")

try:
    import whisper
    from whisper.utils import get_writer
except ImportError:
    print("[ERRO] A biblioteca 'openai-whisper' não está instalada.")
    print("Por favor, instale usando o comando no seu terminal/cmd:")
    print("pip install openai-whisper")
    sys.exit(1)

def main():
    # Inicializa o parser para ler argumentos de terminal
    parser = argparse.ArgumentParser(description="Extrai áudio de vídeo e gera legenda (SRT) usando IA (Whisper)")
    parser.add_argument("mkv", help="Caminho para o arquivo de vídeo .mkv")
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Tamanho do modelo de IA. (padrão: small)")
    parser.add_argument("--lang", default=None, help="Idioma do áudio no vídeo (ex: en, pt). Se omitido, o Whisper detecta automaticamente.")
    parser.add_argument("--output", default=None, help="Caminho customizado do arquivo SRT de saída")
    args = parser.parse_args()

    input_file = Path(args.mkv)
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
    print("(Na primeira vez que você rodar com esse modelo, ele fará o download do modelo da internet)")
    # O Whisper carrega o modelo em memória (e faz download caso necessário)
    model = whisper.load_model(args.model)

    print(f"\nIniciando transcrição de áudio para: {input_file.name}")
    print("Isso pode levar de alguns minutos até horas dependendo do tamanho do vídeo e da velocidade do seu computador...")
    
    # O Whisper pode ler o arquivo de vídeo diretamente; internamente ele aciona o FFmpeg para separar o áudio.
    transcribe_options = {"task": "transcribe"}
    if args.lang:
        transcribe_options["language"] = args.lang

    # Executa a transcrição do arquivo
    result = model.transcribe(str(input_file), **transcribe_options)

    # Utiliza as ferramentas nativas do próprio Whisper para exportar os resultados em SRT
    print("\nGerando arquivo SRT...")
    writer = get_writer("srt", output_dir)
    
    # O Whisper pega o nome do arquivo (sem extensão) e adiciona ".srt"
    writer(result, str(input_file))
    
    # O arquivo SRT padrão gerado ficará na pasta `output_dir`
    generated_srt = Path(output_dir) / f"{input_file.stem}.srt"
    final_output_path = Path(output_dir) / f"{output_name}.srt"
    
    if generated_srt.exists() and generated_srt != final_output_path:
        shutil.move(str(generated_srt), str(final_output_path))
        print(f"[SUCESSO] Legenda SRT gerada com sucesso: {final_output_path}")
    elif generated_srt.exists():
         print(f"[SUCESSO] Legenda SRT gerada com sucesso: {generated_srt}")
    else:
         print(f"[AVISO] O arquivo SRT pode nao ter sido gerado ou salvo em {generated_srt}")

if __name__ == "__main__":
    main()
