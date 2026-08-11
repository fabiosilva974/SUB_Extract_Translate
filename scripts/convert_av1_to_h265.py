#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: convert_av1_to_h265.py
#
# Objetivo:
#   Script dedicado exclusivamente para caçar e converter vídeos que estejam em
#   AV1 (frequentemente em 10-bit) para HEVC (H.265) visando compatibilidade
#   com players e TVs mais antigas.
#
# Lógica Principal:
#   Diferente do conversor principal, este script:
#   1. NÃO usa "-hwaccel cuda" na entrada (pois GPUs antigas não leem AV1 e isso causava o crash).
#      O Processador (CPU) descompacta o AV1, e a NVIDIA (GPU) comprime para H.265.
#   2. NÃO possui o sistema "Anti-Inchaço" (aceita que o arquivo final ficará maior).
#   3. Copia áudio e legendas (FLAC, PGS, etc) intactos.
# ==============================================================================

# Importa o módulo 'os' para interagir com o sistema operacional (caminhos, arquivos)
import os
# Importa 'sys' para lidar com encerramentos e argumentos básicos de sistema
import sys
# Importa 'time' para cronometrar a duração da conversão
import time
# Importa 'json' para ler os dados do ffprobe formatados no terminal
import json
# Importa 'subprocess' para executar comandos no terminal de forma isolada (ffprobe, ffmpeg)
import subprocess
# Importa 'argparse' para lidar com os argumentos de linha de comando lindamente (como caminhos)
import argparse
# Importa 'Path' da biblioteca 'pathlib' para gerenciar caminhos de arquivos de forma segura e fácil
from pathlib import Path
# Importa 'shutil' para mover arquivos facilmente do temporário pro disco final
import shutil

# Definição da função que verifica a alma do arquivo (meta-dados e codec de vídeo)
def get_video_metadata(file_path):
    # Monta a lista de comando do 'ffprobe' solicitando a saída em formato JSON (fácil leitura)
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    # Inicia um bloco de tentativa para lidar com possíveis quebras caso o ffprobe trave
    try:
        # Executa o comando no terminal embutido capturando o texto de saída
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Transforma o texto de saída JSON gigante numa estrutura de dicionário Python (Data)
        data = json.loads(result.stdout)
    # Se der erro ou o comando não rodar
    except Exception:
        # Retorna falso, indicando que falhou em ler os metadados
        return False
        
    # Variável de controle assumindo que o arquivo NÃO É av1 até que se prove o contrário
    is_av1 = False
    # Laço iterando sobre todos os fluxos de mídia (áudio, vídeo, legenda) que o ffprobe achou
    for stream in data.get("streams", []):
        # Puxa o nome do codec do stream atual e joga pra minúsculo (ex: "h264", "av1", "flac")
        codec = stream.get("codec_name", "").lower()
        # Confirma que estamos olhando para a trilha de VÍDEO principal
        if stream.get("codec_type") == "video":
            # Se a string do codec de vídeo contiver 'av1'
            if codec == "av1":
                # Marca a variável afirmando que é AV1 e precisa de intervenção (re-encode pra hevc)
                is_av1 = True
                # Sai da função confirmando que é positivo
                return True
    # Se vasculhou todas as trilhas e não achou AV1, retorna falso para o chamador
    return False

# Definição da função que dispara o rolo compressor (FFmpeg) no arquivo alvo
def encode_av1_to_hevc(input_path, output_path, gpu="nvidia", quality=26):
    # Escolhe o codificador dependendo da marca da placa
    if gpu.lower() == "amd":
        encoder = "hevc_amf"
        # AMD usa parâmetros de qualidade um pouco diferentes do NVENC
        # Adicionado o filtro -pix_fmt yuv420p para evitar crash em GPUs AMD sem suporte a gravação 10-bit
        extra_args = ["-rc", "vbr_peak", "-qp_p", str(quality), "-qp_i", str(quality), "-pix_fmt", "yuv420p"]
    else:
        encoder = "hevc_nvenc"
        extra_args = ["-preset", "p7", "-tune", "hq", "-rc", "vbr", "-cq", str(quality), "-qmin", str(quality), "-qmax", str(quality)]

    # Monta a lista estruturada com todos os comandos mágicos para converter e manter compatibilidade
    cmd = [
        "ffmpeg", "-y",                # Invoca o FFmpeg passando a flag -y para sobrescrever sem perguntar
        # ATENÇÃO: SEM hwaccel na entrada! A CPU deverá decodificar o complexo fluxo AV1 em hardware nativo
        "-i", str(input_path),         # Define o caminho do arquivo de origem que entrará no liquidificador
        "-map", "0",                   # Diz para puxar TODAS as trilhas (múltiplos áudios e legendas) do original
        "-c:v", encoder,               # A saída DE VÍDEO usará a poderosa placa de vídeo escolhida
    ] + extra_args + [
        "-c:a", "copy",                # Copia fielmente todas as trilhas de Áudio (ex: Flac do 07-Ghost ficará imaculado)
        "-c:s", "copy",                # Copia fielmente todas as Legendas PGS sem tocá-las
        "-f", "matroska",              # Obriga a saída a ser um envelopamento padrão Matroska (.MKV universal)
        str(output_path)               # Aponta o destino final, que no nosso caso é a pasta TEMPORÁRIA
    ]
    
    # Roda o FFmpeg anexando-o ao processo de forma contínua (para ler a saída em tempo real)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    # Prepara uma lista vazia para armazenar as linhas de debug
    log_output = []
    
    # Laço mágico lendo cada letra/linha que o FFmpeg vomita na tela de fundo
    for line in process.stdout:
        # Puxa e salva a linha crua na nossa lista de histórico em caso de explosão
        log_output.append(line)
        # Se a linha mencionar 'frame' ou 'time', significa que é uma linha de andamento 22fps, etc
        if "frame=" in line or "time=" in line:
            # Imprime na tela voltando pro começo da linha ( \r ) pra dar sensação de carregamento em barra viva!
            print(f"\r{line.strip()}", end="")
            
    # Espera pacientemente o FFmpeg fechar as portas (seja com sucesso ou com Crash fatal)
    process.wait()
    # Pula uma linha no log para separar a barra de progresso do restante
    print()
    
    # Checa o código de encerramento; Se não for ZERO (0 = Sucesso pleno Linux)
    if process.returncode != 0:
        # Bota a boca no trombone avisando do ERRO CRÍTICO no processo de encoding
        print("\n=== LOG DE ERRO DO FFMPEG ===")
        # Imprime as últimas 15 linhas vomitadas pelo FFmpeg antes de morrer
        print("".join(log_output[-15:]))
        # Encerra o bloco de emergência visual
        print("=============================\n")
        
    # Retorna TRUE se a conversão foi impecável (código zero) ou FALSE se pegou fogo
    return process.returncode == 0

# Função de Orquestração Mestra por arquivo (decide destinos, pastas e invoca o trabalhador)
def process_file(file_path, temp_dir, gpu="nvidia"):
    # Confere se o arquivo original realmente existe e o HD não desconectou do nada
    if not file_path.exists():
        # Se sumiu, aborta sem quebrar e retorna Falso
        return False
        
    # Dispara a busca minuciosa no arquivo pra descobrir se é AV1 por dentro
    is_av1 = get_video_metadata(file_path)
    # Se não for AV1 (for MP4 de celular, H264 antigo, etc)
    if not is_av1:
        # Avisa no Log silencioso e pula de cabeça pro próximo arquivo sem converter
        print(f"[{file_path.name}] Não é AV1. Ignorando.")
        # Retorna falso, pois ele não trabalhou
        return False
        
    # Cria o novo nome batizando a extensão do original para abrigar um .H265.mkv vistoso
    new_name = file_path.stem + ".H265.mkv"
    # Dá um banho de loja no nome removendo marcas velhas de [AV1] das Fansubs para não confundir você
    new_name = new_name.replace("AV1", "").replace("av1", "")
    # Tratamento anti-vírgulas estranhas (exemplo: ficar com dois pontos na string após cortar AV1)
    while ".." in new_name: new_name = new_name.replace("..", ".")
    
    # Destino real no HD onde o arquivo final ficará
    final_dest = file_path.parent / new_name
    # Usa o próprio destino como caminho de saída (sem .part temporário)
    output_path = final_dest

    print(f"\n{'='*50}")
    print("[ START ] Iniciando Conversão de Compatibilidade (AV1 -> H265)")
    print(f" Arquivo: {file_path.name}")
    print(f" Saída:   {new_name}")
    print(f" Hardware: Aceleração {gpu.upper()}")
    print(f"{'='*50}")

    start_time = time.time()

    # Cria lock
    lock_path = file_path.with_suffix('.lock')
    if lock_path.exists():
        print(f"[WARN] Lock existente para {file_path.name}. Pulando.")
        return False
    lock_path.touch()
    try:
        # Converte diretamente para o arquivo de destino
        success = encode_av1_to_hevc(file_path, output_path, gpu=gpu)
    finally:
        if lock_path.exists():
            lock_path.unlink()
    elapsed = time.time() - start_time

    if not success or not final_dest.exists():
        print(" [ERRO CRÍTICO] A conversão do AV1 falhou!")
        if final_dest.exists():
            final_dest.unlink()
        return False

    orig_size = file_path.stat().st_size / (1024*1024)
    new_size = final_dest.stat().st_size / (1024*1024)

    print("\n [ OK ] Conversão Finalizada com Sucesso!")
    print(f" -> Duração: {int(elapsed//60)}m {int(elapsed%60)}s")
    print(f" -> Tamanho: {orig_size:.1f}MB (AV1) ---> {new_size:.1f}MB (H265)")
    if new_size > orig_size:
        print(" ⚠️ Nota: Como esperado, o arquivo H265 ficou MAIOR que o AV1 original.")
    print("\n Tudo certo! O arquivo original AINDA ESTÁ na pasta por segurança.")
    print(f" Verifique se {new_name} está rodando perfeitamente antes de deletar o original.")
    return True

# Função principal (ponto de ignição padrão em Scripts Profissionais Python)
def main():
    # Prepara um módulo avançado de interpretação para as flags do console do usuário Linux
    parser = argparse.ArgumentParser(description="Conversor Dedicado: AV1 para H265 (Compatibilidade)")
    # Adiciona a obrigação do usuário de fornecer OBRIGATORIAMENTE um caminho (Diretório ou MKV exato)
    parser.add_argument("target", help=r"Arquivo .mkv específico ou pasta inteira (ex: U:\Anime-Cartoon)")
    # Prepara uma pasta de manuseio temporária no NVMe do Linux como salvaguarda super-rápida de leitura IOPS
    parser.add_argument("--temp", default=r"/home/conversor/TEMP", help="Diretório temporário (Linux/WSL)")
    # Adiciona flag de placa de vídeo
    parser.add_argument("--gpu", default="nvidia", choices=["nvidia", "amd"], help="Qual placa usar? 'nvidia' (NVENC) ou 'amd' (AMF)")
    # Consolida os atributos que o usuário digitou
    args = parser.parse_args()
    
    # Transforma a String passada (Target) num super-objeto de caminhos da lib Pathlib resolvendo atalhos relativos
    target = Path(args.target).resolve()
    # Puxa o objeto temp (Padrão Home/Linux)
    temp_dir = Path(args.temp).resolve()
    # Garante firmemente que o diretório temp exista, senão, constrói-o brutalmente agora
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    gpu_choice = args.gpu.lower()
    
    # Avalia a raiz fornecida pelo usuário: Se for um arquivo isolado (.MKV, .MP4, etc)
    if target.is_file():
        # Dispara o executor focado na precisão cirúrgica de UM ALVO
        process_file(target, temp_dir, gpu=gpu_choice)
    # Senão, avalia se é a raiz enorme de uma árvore (A pasta inteirona)
    elif target.is_dir():
        # Anuncia ao mundo que a varredura começou
        print(f"Buscando arquivos AV1 dentro da pasta: {target}")
        # Variável para acumular hits
        encontrados = 0
        # Dispara as garras da recursividade caminhando entre as subpastas
        for root, _, files in os.walk(target):
            # Passa a peneira nas centenas de arquivos da pasta varrida
            for f in files:
                # Se bater a extensão
                if f.lower().endswith(('.mkv', '.mp4')):
                    # Recompõe o esqueleto do nome do arquivo (caminho pai + nome filho = raiz inteira)
                    file_path = Path(os.path.join(root, f))
                    # Escaneamento ultra-focado e raso pra saber a real identidade AV1 sem perder século em parsing pesado
                    if get_video_metadata(file_path):
                        # Grita pra trabalhar se a flag AV1 brilhar True
                        process_file(file_path, temp_dir, gpu=gpu_choice)
                        # Soma mais 1 abate no cartel da pasta
                        encontrados += 1
        # Se depois do arrastão terminar os arquivos AV1 = 0
        if encontrados == 0:
            # Anuncia desapontamento
            print("Nenhum arquivo de formato AV1 foi encontrado na pasta fornecida.")
    # Se o que foi imputado nem for arquivo nem diretório (Ou for o limbo)
    else:
        # Apenas nega a existência do universo
        print("O caminho fornecido não existe.")

# A mágica Padrão-Ouro do Python! Se o arquivo não foi importado, mas executado com orgulho pela sua própria batida:
if __name__ == "__main__":
    # Puxe a alavanca
    main()
