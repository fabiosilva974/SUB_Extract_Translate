#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: extract_audio.py
#
# Objetivo:
#   Extrair a faixa de áudio de um arquivo .mkv e salvá-la em .mp3.
#   Pode extrair um idioma específico e permite listar as faixas disponíveis.
#
# Lógica Principal:
#   Usa o 'mkvmerge -J' para listar todas as faixas e filtra as de áudio, depois 
#   invoca o 'ffmpeg' extraindo apenas a trilha desejada e encodando em MP3.
#
# Dependências Externas:
#   MKVToolNix (mkvmerge), FFmpeg
# ==============================================================================
# Importa módulo para lidar com operações do sistema operacional
import os
# Importa módulo para interagir com o ambiente de execução Python (ex: sys.exit)
import sys
# Importa módulo para ler e interpretar dados formatados em JSON
import json
# Importa módulo para ler argumentos passados pela linha de comando
import argparse
# Importa módulo para invocar programas externos e gerenciar processos
import subprocess
# Importa a classe Path para manipulação moderna e robusta de caminhos de arquivos
from pathlib import Path

# Configurações de caminhos
# Caminho da pasta onde o MKVToolNix foi instalado no Windows
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
# Caminho absoluto para o executável do ffmpeg
FFMPEG_BIN     = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin\ffmpeg.exe"

# Mapeia nomes de comandos comuns para seus respectivos caminhos completos no disco
TOOLS = {
    # Mapeia "mkvmerge" para o executável que fará a leitura da estrutura do MKV
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    # Mapeia "ffmpeg" para o executável que fará a extração e conversão
    "ffmpeg":    FFMPEG_BIN
}

# Função utilitária que funciona como um "wrapper" (envoltório) para executar processos
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Verifica se o programa a ser chamado (índice 0 da lista) está mapeado em TOOLS
    if cmd[0] in TOOLS:
        # Substitui o nome genérico pelo caminho exato
        cmd[0] = TOOLS[cmd[0]]
    # Executa o comando em background capturando sua saída em modo texto com codificação utf-8
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")

# Função que identifica todas as faixas de áudio que estão embutidas no arquivo MKV
def list_audio_tracks(mkv_path: str) -> list[dict]:
    """
    Usa o mkvmerge para analisar a estrutura do arquivo MKV e retornar uma
    lista contendo metadados (id, idioma, codec, nome) das faixas de áudio.
    """
    # A flag -J faz com que o mkvmerge gere a saída descrevendo a estrutura inteira em JSON
    result = run(["mkvmerge", "-J", mkv_path])
    # Pega essa string JSON e converte para dicionários e listas nativas do Python
    info = json.loads(result.stdout)
    # Inicializa uma lista vazia que vai guardar apenas as faixas de áudio
    tracks = []
    # Itera (faz um loop) por todas as faixas (vídeo, áudio, legenda) encontradas no arquivo
    for t in info.get("tracks", []):
        # Filtra para entrar no IF apenas se a faixa for especificamente do tipo "audio"
        if t["type"] == "audio":
            # Extrai o sub-dicionário de propriedades; se não tiver, pega um dicionário vazio
            props = t.get("properties", {})
            # Monta um dicionário com os dados que nos interessam e coloca na nossa lista "tracks"
            tracks.append({
                "id":       t["id"], # O número de identificação da faixa dentro do arquivo
                "codec":    t.get("codec", ""), # Qual o formato atual do áudio (ex: AAC, AC3)
                "language": props.get("language", "und"), # Idioma do áudio, ou "und" se indefinido
                "name":     props.get("track_name", ""), # Um nome dado à faixa (se houver)
            })
    # Devolve a lista preenchida
    return tracks

# Função principal onde a mágica acontece
def main():
    # Inicializa o tratador de argumentos do CLI, definindo uma descrição para o script
    parser = argparse.ArgumentParser(description="Extrai áudio do MKV.")
    # Adiciona o argumento obrigatório para o usuário indicar qual o arquivo MKV
    parser.add_argument("mkv", help="Arquivo .mkv de entrada")
    # Adiciona o argumento opcional para forçar a busca de um idioma específico; o padrão é "eng"
    parser.add_argument("--lang", default="eng", help="Idioma da faixa (ex: eng, por). Padrão: eng")
    # Adiciona uma "flag" opcional: se o usuário passar "--list", o script só lista e não extrai
    parser.add_argument("--list", action="store_true", help="Lista as faixas de áudio e sai")
    # Executa a leitura daquilo que o usuário de fato digitou no terminal
    args = parser.parse_args()

    # Transforma a string do arquivo em um objeto Path (facilita manipulação)
    input_file = Path(args.mkv)
    # Checa se o arquivo de vídeo realmente existe na pasta informada
    if not input_file.exists():
        # Informa do erro e mata o programa (código 1)
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    # Invoca a função criada anteriormente para listar os áudios
    tracks = list_audio_tracks(str(input_file))
    
    # Se a intenção do usuário era apenas ver a lista (--list)
    if args.list:
        # Pinta um cabeçalho simpático na tela
        print("\n--- Faixas de Áudio Disponíveis ---")
        print(f"{'ID':>4}  {'Idioma':<8}  {'Codec':<10}  {'Nome'}")
        # Loop que imprime cada faixa de áudio alinhando as informações com espaços (ex: :>4, :<8)
        for t in tracks: 
            print(f"{t['id']:>4}  {t['language']:<8}  {t['codec']:<10}  {t['name']}")
        # Encerra a função principal prematuramente, pois a listagem acabou
        return

    # Inicia a variável onde ficará guardada a faixa que escolhermos
    target_track = None
    # Loop de busca na lista de áudios
    for t in tracks:
        # Se a linguagem da faixa atual bater com o idioma pedido pelo usuário (args.lang)
        if t["language"] == args.lang:
            # Seleciona essa faixa como a desejada
            target_track = t
            # Interrompe o loop de busca (já achou a primeira correspondência)
            break
            
    # Se rodou o loop todo e target_track continuou como None, significa que não achou o idioma
    if not target_track:
        # Imprime o erro informando o idioma que faltou e sugere usar a flag --list
        print(f"[ERRO] Faixa de áudio com idioma '{args.lang}' não encontrada no arquivo.")
        print("Tente rodar com '--list' para ver os idiomas disponíveis.")
        # Encerra o programa com erro
        sys.exit(1)

    # Cria o caminho do arquivo de destino simplesmente trocando a extensão original para ".mp3"
    output_audio = input_file.with_suffix(".mp3")
    
    # Exibe informações na tela sobre o que vai ser feito, pra não deixar o usuário no escuro
    print(f"\nExtraindo faixa de áudio:")
    print(f" - ID da faixa: {target_track['id']}")
    print(f" - Idioma:      {target_track['language']}")
    print(f" - Salvando em: {output_audio.name}")
    print("Por favor, aguarde...")
    
    # Prepara a lista de comandos (cada item é um pedaço do comando) para o executável do ffmpeg
    cmd = [
        # Caminho do executável seguido da flag -y para reescrever arquivos sem pedir permissão
        TOOLS["ffmpeg"], "-y",
        # Informa ao ffmpeg qual será a entrada (-i e o arquivo original)
        "-i", str(input_file),
        # Diz ao ffmpeg que queremos MAPEÁR especificamente o áudio através do seu ID de faixa (0:ID)
        "-map", f"0:{target_track['id']}", 
        # Indica qual codec de áudio usar (-c:a) sendo mp3 (libmp3lame), e qual qualidade (-q:a 2)
        "-c:a", "libmp3lame", "-q:a", "2",
        # Caminho onde vai salvar o arquivo final
        str(output_audio)
    ]
    
    # Dispara a execução do ffmpeg e bloqueia a saída de erros e sucesso da tela (DEVNULL) para ficar limpo
    res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Se o retorno do sistema for 0, quer dizer que o comando encerrou com sucesso absoluto
    if res.returncode == 0:
        # Informa ao usuário que tudo deu certo
        print(f"\n[SUCESSO] Áudio salvo com sucesso!")
        print(f"Caminho: {output_audio}")
    # Se foi diferente de 0, o ffmpeg falhou por algum motivo (arquivo bloqueado, não suportado, etc)
    else:
        # Informa ao usuário que houve problema
        print("\n[ERRO] Falha ao extrair o áudio com FFmpeg.")

# Garante que o método main só rodará se eu não estiver importando esse script em outro lugar
if __name__ == "__main__":
    main()
