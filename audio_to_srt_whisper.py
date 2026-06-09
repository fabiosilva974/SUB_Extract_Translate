#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: audio_to_srt_whisper.py
Objetivo: Utilizar o modelo Whisper (IA da OpenAI) para transcrever o áudio de um
          arquivo de vídeo diretamente para um arquivo de legenda (.srt).
"""
# Importa módulo 'os' para interagir com o sistema operacional e variáveis de ambiente
import os
# Importa módulo 'sys' para funções e variáveis do sistema (ex: sys.exit para finalizar o script)
import sys
# Importa módulo 'argparse' para criar a interface de comandos e tratar argumentos
import argparse
# Importa a classe 'Path' do módulo 'pathlib' para manipulação segura e fácil de caminhos
from pathlib import Path
# Importa módulo 'shutil' para operações em arquivos, como mover e copiar
import shutil

# Configura o diretório onde os executáveis do FFmpeg (necessários pelo Whisper) estão localizados
FFMPEG_BIN_DIR = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin"
# Insere dinamicamente o diretório do FFmpeg na variável de ambiente PATH do Windows,
# garantindo que o Whisper possa invocá-lo durante a extração de áudio do vídeo
os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + os.environ.get("PATH", "")

# Bloco try-except para verificar se as dependências do Whisper estão instaladas
try:
    # Tenta importar o módulo principal do Whisper
    import whisper
    # Tenta importar a função 'get_writer' que ajuda a exportar o resultado para arquivos como SRT
    from whisper.utils import get_writer
except ImportError:
    # Caso a importação falhe, alerta o usuário no console
    print("[ERRO] A biblioteca 'openai-whisper' não está instalada.")
    print("Por favor, instale usando o comando no seu terminal/cmd:")
    print("pip install openai-whisper")
    # Encerra a execução do script com código 1 (indicando erro)
    sys.exit(1)

# Função principal onde fica a lógica do script
def main():
    # Inicializa o 'parser' de argumentos que descreve o que a ferramenta faz
    parser = argparse.ArgumentParser(description="Extrai áudio de vídeo e gera legenda (SRT) usando IA (Whisper)")
    # Define um argumento obrigatório ('mkv') para receber o caminho do vídeo
    parser.add_argument("mkv", help="Caminho para o arquivo de vídeo .mkv")
    # Define o argumento opcional '--model' para escolher qual IA usar, com 'small' de padrão
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"], 
                        help="Tamanho do modelo de IA. (padrão: small)")
    # Define o argumento opcional '--lang' para forçar o idioma; caso omitido, haverá autodetecção
    parser.add_argument("--lang", default=None, help="Idioma do áudio no vídeo (ex: en, pt). Se omitido, o Whisper detecta automaticamente.")
    # Define argumento opcional '--output' caso o usuário deseje salvar com nome/lugar diferente
    parser.add_argument("--output", default=None, help="Caminho customizado do arquivo SRT de saída")
    # Faz a leitura e interpreta os argumentos digitados no console
    args = parser.parse_args()

    # Transforma o caminho do arquivo passado pelo usuário em um objeto Path
    input_file = Path(args.mkv)
    # Valida se o arquivo efetivamente existe no disco
    if not input_file.exists():
        # Exibe erro caso não exista e encerra a execução
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    # Extrai o diretório (pasta) onde o arquivo de entrada está localizado
    output_dir = str(input_file.parent)
    # Extrai o nome base do arquivo (sem a extensão) para ser usado no novo arquivo
    output_name = input_file.stem
    
    # Verifica se o usuário informou um nome/caminho de saída customizado
    if args.output:
        # Transforma o caminho de saída em um objeto Path
        out_path = Path(args.output)
        # Atualiza a variável com o novo diretório de destino
        output_dir = str(out_path.parent)
        # Atualiza o novo nome base que o arquivo de saída deverá ter
        output_name = out_path.stem

    # Exibe mensagem amigável indicando que a IA está sendo iniciada
    print(f"\nCarregando modelo Whisper ({args.model})...")
    print("(Na primeira vez que você rodar com esse modelo, ele fará o download do modelo da internet)")
    # Invoca a função do Whisper que carrega o modelo de linguagem para a memória da máquina
    model = whisper.load_model(args.model)

    # Informa ao usuário que o processo pesado começou
    print(f"\nIniciando transcrição de áudio para: {input_file.name}")
    print("Isso pode levar de alguns minutos até horas dependendo do tamanho do vídeo e da velocidade do seu computador...")
    
    # Cria um dicionário com os parâmetros que serão passados à função de transcrição
    transcribe_options = {"task": "transcribe"}
    # Se o usuário escolheu um idioma, injeta ele nas opções (evita falhas na autodetecção)
    if args.lang:
        transcribe_options["language"] = args.lang

    # Roda a função principal da IA que de fato escuta o áudio e gera os textos e timestamps
    result = model.transcribe(str(input_file), **transcribe_options)

    # Informa que a etapa de processamento terminou e iniciará a exportação do arquivo
    print("\nGerando arquivo SRT...")
    # Chama o utilitário nativo do Whisper preparando-o para gerar o formato 'srt' dentro do 'output_dir'
    writer = get_writer("srt", output_dir)
    
    # Dispara a escrita passando os dados brutos gerados pela IA (result) e qual foi a fonte
    writer(result, str(input_file))
    
    # Determina o caminho final em que o arquivo recém-gerado pelo Whisper caiu (por padrão adota o nome do vídeo)
    generated_srt = Path(output_dir) / f"{input_file.stem}.srt"
    # Determina o caminho que era de fato o desejado pela lógica e pelo usuário final
    final_output_path = Path(output_dir) / f"{output_name}.srt"
    
    # Se a saída original do Whisper existir e o caminho diferir do que queremos, renomeia/move o arquivo
    if generated_srt.exists() and generated_srt != final_output_path:
        shutil.move(str(generated_srt), str(final_output_path))
        print(f"[SUCESSO] Legenda SRT gerada com sucesso: {final_output_path}")
    # Caso ele já esteja com o nome exato (pois não foi passado --output, por exemplo)
    elif generated_srt.exists():
         print(f"[SUCESSO] Legenda SRT gerada com sucesso: {generated_srt}")
    # Em caso de imprevistos em que o arquivo não é encontrado onde esperávamos
    else:
         print(f"[AVISO] O arquivo SRT pode nao ter sido gerado ou salvo em {generated_srt}")

# Permite que o código só execute de verdade se o arquivo for rodado diretamente
if __name__ == "__main__":
    main()
