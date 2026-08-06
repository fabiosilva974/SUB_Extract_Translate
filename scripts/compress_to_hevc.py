# ==============================================================================
# Script: compress_to_hevc.py
#
# Objetivo:
#   Comprimir vídeos para o formato HEVC (H.265) para reduzir drasticamente o
#   tamanho do arquivo, enquanto preserva todas as características originais
#   do arquivo MKV, como múltiplas faixas de áudio, legendas e anexos (fontes).
#
# Lógica Principal:
#   O script detecta automaticamente a placa de vídeo do sistema (usando wmic)
#   e seleciona o melhor codificador de hardware no FFmpeg (hevc_nvenc para
#   NVIDIA, hevc_amf para AMD, hevc_qsv para Intel) para acelerar a conversão.
#   Ele mapeia todas as faixas (-map 0) e aplica cópia direta para áudio e
#   legendas, re-codificando apenas a trilha de vídeo.
#
# Uso Avançado:
#   O script permite um terceiro parâmetro numérico opcional (ex: 20, 26) 
#   para controlar o nível de qualidade. (Menor número = arquivo maior e 
#   imagem mais fiel ao original. O padrão é 26).
#
# Dependências Externas:
#   FFmpeg (deve estar instalado e no PATH do sistema)
# ==============================================================================
import os
import subprocess
import sys
import time


def get_gpu_vendor():
    """Detecta o fabricante da GPU no Windows para escolher o melhor encoder."""
    try:
        # Usa o comando wmic para listar o nome das placas de vídeo
        output = subprocess.check_output(
            "wmic path win32_VideoController get name", shell=True, text=True
        )
        output = output.lower()
        if "nvidia" in output:
            return "nvidia"
        elif "amd" in output or "radeon" in output:
            return "amd"
        elif "intel" in output:
            return "intel"
    except Exception as e:
        print(f"Não foi possível detectar a GPU automaticamente: {e}")
    return "cpu"


def compress_to_hevc(input_file, output_file, quality_level=26):
    """
    Comprime um vídeo para o formato HEVC (H.265) usando a GPU (se disponível)
    mantendo todas as outras características originais.
    O parâmetro quality_level define o nível de compressão (menor = melhor qualidade e maior arquivo).
    """
    if not os.path.exists(input_file):
        print(f"Erro: O arquivo '{input_file}' não foi encontrado.")
        return

    gpu = get_gpu_vendor()

    # Parâmetros base
    command = [
        "ffmpeg",
        "-i",
        input_file,
        "-map",
        "0",
        "-c:a",
        "copy",
        "-c:s",
        "copy",
        "-c:t",
        "copy",
    ]

    # Adiciona os parâmetros de vídeo dependendo da GPU detectada
    qual_str = str(quality_level)
    
    if gpu == "nvidia":
        print(f"GPU NVIDIA detectada. Usando encoder 'hevc_nvenc' com qualidade (CQ) {qual_str}...")
        command.extend(["-c:v", "hevc_nvenc", "-cq", qual_str, "-preset", "p4"])
    elif gpu == "amd":
        print(f"GPU AMD/Radeon detectada. Usando encoder 'hevc_amf' com qualidade (QP) {qual_str}...")
        # Adicionado '-vbaq false' para silenciar o aviso "VBAQ is not supported by cqp Rate Control Method"
        command.extend(["-c:v", "hevc_amf", "-rc", "cqp", "-qp_i", qual_str, "-qp_p", qual_str, "-vbaq", "false"])
    elif gpu == "intel":
        print(f"GPU Intel detectada. Usando encoder 'hevc_qsv' com qualidade global {qual_str}...")
        command.extend(["-c:v", "hevc_qsv", "-global_quality", qual_str])
    else:
        print(f"Nenhuma GPU dedicada detectada. Usando CPU (libx265) com CRF {qual_str}...")
        command.extend(["-c:v", "libx265", "-crf", qual_str, "-preset", "fast"])

    command.append(output_file)

    print(f"Iniciando a compressão para HEVC...")
    print(f"Origem: {input_file}")
    print(f"Destino: {output_file}")
    print("-" * 50)

    start_time = time.time()
    try:
        subprocess.run(command, check=True)
        end_time = time.time()

        # Calcula o tempo total
        elapsed_time = end_time - start_time
        mins, secs = divmod(elapsed_time, 60)

        print("-" * 50)
        print(f"Compressão concluída com sucesso! Vídeo salvo em: {output_file}")
        print(f"Tempo de processamento: {int(mins)} minutos e {int(secs)} segundos.")
    except subprocess.CalledProcessError as e:
        print(f"Ocorreu um erro durante a conversão do FFmpeg: {e}")
    except FileNotFoundError:
        print("Erro: O FFmpeg não foi encontrado no seu sistema.")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(
            "Uso: python compress_to_hevc.py <arquivo_entrada.mkv> <arquivo_saida.mkv> [qualidade]"
        )
        print("O parâmetro [qualidade] é opcional. Padrão é 26 (menor o número = melhor a imagem e maior o arquivo).\n")
        
        # Valores padrão para testes se não passados os argumentos
        video_original = r"E:\Traducao\Torrent\Katainaka\Erai-raws_Katainaka_no_Ossan_Kensei_ni_Naru_II_-_05_1080p_AMZN_WEB-DL_AVC_EAC3MultiSubB01748EC.mkv"
        video_destino = r"E:\Traducao\Torrent\Katainaka\Erai-raws_Katainaka_no_Ossan_Kensei_ni_Naru_II_-_05_HEVC_Custom.mkv"
        print(f"Executando modo de teste com o arquivo padrão...")
        compress_to_hevc(video_original, video_destino, quality_level=26)
    else:
        video_original = sys.argv[1]
        video_destino = sys.argv[2]
        
        # Pega a qualidade caso passada como terceiro argumento
        qualidade_escolhida = 26
        if len(sys.argv) >= 4:
            try:
                qualidade_escolhida = int(sys.argv[3])
            except ValueError:
                print("Aviso: A qualidade deve ser um número inteiro. Usando padrão (26).")
                
        compress_to_hevc(video_original, video_destino, quality_level=qualidade_escolhida)
