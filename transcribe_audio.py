#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: transcribe_audio.py
#
# Objetivo:
#   Recebe um arquivo de áudio (.mp3, .wav) e usa o modelo IA Whisper para 
#   gerar a legenda (.srt) correspondente. Permite transcrição direta ou
#   tradução de áudio de idioma estrangeiro nativa para o inglês.
#
# Lógica Principal:
#   Instancia o modelo do Whisper e processa o arquivo de áudio chamando a função 
#   'transcribe()'. Por fim, converte os timestamps e dados gerados usando
#   o utilitário 'get_writer' exportando como arquivo SRT.
#
# Dependências Externas:
#   FFmpeg, openai-whisper
# ==============================================================================
# Importa módulo 'os' para interagir com o sistema operacional e modificar variáveis de ambiente
import os
# Importa módulo 'sys' para funções fundamentais como matar o processo em caso de erro
import sys
# Importa módulo 'argparse' para criar a interface que lê os parâmetros digitados pelo usuário
import argparse
# Importa 'Path' para trabalhar com caminhos e checar existência de arquivos de forma simples
from pathlib import Path
# Importa módulo 'shutil' para mover/renomear os arquivos criados
import shutil

# Configura o caminho fixo onde estão guardados os executáveis do FFmpeg
FFMPEG_BIN_DIR = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin"
# Insere esse caminho no começo da variável PATH do sistema
# Isso é essencial porque a biblioteca 'whisper' não deixa configurar caminho do ffmpeg direto no código
os.environ["PATH"] = FFMPEG_BIN_DIR + os.pathsep + os.environ.get("PATH", "")

# Tenta importar as ferramentas da IA da OpenAI
try:
    # Módulo core da IA Whisper
    import whisper
    # Módulo acessório que formata o texto que a IA entende em arquivo de legenda (.srt)
    from whisper.utils import get_writer
# Caso caia na exceção é porque não fez 'pip install openai-whisper'
except ImportError:
    # Exibe a falha e avisa qual o problema
    print("[ERRO] A biblioteca 'openai-whisper' não está instalada.")
    # Aborta o código devolvendo código 1 (falhou)
    sys.exit(1)

# Função principal do script
def main():
    # Inicializa o 'parser' de argumentos que descreve a utilidade do script
    parser = argparse.ArgumentParser(description="Transcreve arquivo de áudio para legenda (SRT)")
    # Recebe obrigatoriamente qual é o arquivo
    parser.add_argument("audio", help="Caminho para o arquivo de áudio (ex: .mp3, .wav)")
    # Argumento opcional para ditar a qualidade da IA usada. Default "small" tem bom balanço entre rapidez/peso
    parser.add_argument("--model", default="small", choices=["tiny", "base", "small", "medium", "large"])
    # Argumento opcional de qual idioma a IA deve ouvir. Default japonês ("ja") porque foi ajustado pra anime
    parser.add_argument("--lang", default="ja", help="Idioma do áudio. Padrão: en")
    # Argumento para ditar o que a IA vai fazer: Transcrever puro (transcribe) ou traduzir para INGLÊS (translate)
    # Obs: o Whisper original só traduz NATIVAMENTE para o inglês
    parser.add_argument("--task", default="transcribe", choices=["transcribe", "translate"], help="Tarefa: 'transcribe' (mantém o idioma original) ou 'translate' (traduz direto para INGLÊS)")
    # Permite escolher onde salvar o arquivo SRT gerado
    parser.add_argument("--output", default=None, help="Caminho customizado de saída do arquivo SRT")
    # Captura e constrói o objeto com os parâmetros lidos do console
    args = parser.parse_args()

    # Gera a representação via Path
    input_file = Path(args.audio)
    # Valida se o arquivo base existe
    if not input_file.exists():
        # Informa caso o usuário passe caminho errado
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    # Identifica em qual pasta o arquivo original está
    output_dir = str(input_file.parent)
    # Pega o nome do arquivo ignorando a extensão final (.mp3)
    output_name = input_file.stem
    # Avalia se usuário preencheu a flag --output
    if args.output:
        # Pega a nova rota fornecida
        out_path = Path(args.output)
        # Recalcula diretório baseado na rota do usuário
        output_dir = str(out_path.parent)
        # Recalcula nome do arquivo final
        output_name = out_path.stem

    print(f"\nCarregando modelo Whisper ({args.model})...")
    # Acessa os arquivos do modelo; caso seja a primeira vez e o PC não tenha os pesos baixados, ele baixa agora
    model = whisper.load_model(args.model)

    print(f"\nIniciando tarefa '{args.task}' de áudio para: {input_file.name}")
    
    # Prepara o dicionário de opções para passar ao Whisper
    transcribe_options = {"task": args.task}
    # Checa a questão da linguagem
    if args.lang:
        # Se veio idioma na variável, adiciona à configuração do processador
        transcribe_options["language"] = args.lang

    # Executa o processamento do áudio via IA; o programa trava aqui até o fim da IA
    result = model.transcribe(str(input_file), **transcribe_options)

    # Informa início de processo de salvamento em arquivo
    print("\nGerando arquivo SRT...")
    # Prepara um escritor especializado em saídas estilo SubRip ("srt") a salvar na nossa pasta
    writer = get_writer("srt", output_dir)
    # Aciona o método do escritor fornecendo o objeto resultado e o nome base que queremos usar
    writer(result, str(input_file))
    
    # Determina onde o escritor salvou segundo suas regras (nomeOriginal.srt)
    generated_srt = Path(output_dir) / f"{input_file.stem}.srt"
    # Determina como NÓS queríamos salvar (se não houver output será igual ao gerado)
    final_output_path = Path(output_dir) / f"{output_name}.srt"
    
    # Testa se temos que corrigir o nome do arquivo final
    if generated_srt.exists() and generated_srt != final_output_path:
        # Renomeia/move o arquivo gerado
        shutil.move(str(generated_srt), str(final_output_path))
        print(f"[SUCESSO] Legenda gerada com sucesso: {final_output_path}")
    # Se o nome já estava certinho...
    elif generated_srt.exists():
         print(f"[SUCESSO] Legenda gerada com sucesso: {generated_srt}")
    # Caso ocorra falha no 'get_writer'
    else:
         print(f"[AVISO] Arquivo não salvo em: {generated_srt}")

# Padrão Python para tornar esse script independente de execuções modulares
if __name__ == "__main__":
    main()
