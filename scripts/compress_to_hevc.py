# ==============================================================================
# Script: compress_to_hevc.py
#
# Objetivo:
#   Comprimir vídeos soltos via terminal para o formato HEVC (H.265) para reduzir
#   o tamanho do arquivo localmente, enquanto preserva anexos e áudio.
#
# Lógica Principal:
#   O script detecta automaticamente a placa de vídeo do sistema (usando wmic)
#   e seleciona o melhor codificador de hardware no FFmpeg (hevc_nvenc para
#   NVIDIA, hevc_amf para AMD, hevc_qsv para Intel). Mapeia tudo 1:1.
#
# Uso:
#   Pode ser chamado com python compress_to_hevc.py <entrada> <saida> [qualidade_cq]
#
# Dependências Externas:
#   FFmpeg (deve estar instalado e no PATH do sistema)
# ==============================================================================
# Importação módulo de manipulação de caminhos
import os
# Importação módulo de invocar processos (ffmpeg/wmic)
import subprocess
# Importação módulo de ler sys.args da invocação via prompt
import sys
# Importação módulo timer para cronometrar
import time

# Função para detectar inteligentemente qual hardware o PC possui (Somente no Windows)
def get_gpu_vendor():
    # Docstring explicativa
    """Detecta o fabricante da GPU no Windows para escolher o melhor encoder."""
    # Bloco tentar
    try:
        # Usa o comando nativo Windows wmic para listar a classe 'VideoController' (GPUs) e retorna texto puro
        output = subprocess.check_output(
            "wmic path win32_VideoController get name", shell=True, text=True
        )
        # Padroniza string forçando letras minúsculas (para busca confiável)
        output = output.lower()
        # Se contiver 'nvidia'
        if "nvidia" in output:
            return "nvidia"
        # Se contiver os prefixos da AMD Radeon
        elif "amd" in output or "radeon" in output:
            return "amd"
        # Se for chipset gráfico integrado Intel (Ex: UHD Graphics 630)
        elif "intel" in output:
            return "intel"
    # Se falhar a leitura via prompt do Windows
    except Exception as e:
        # Avisa que deu ruim
        print(f"Não foi possível detectar a GPU automaticamente: {e}")
    # Retorna opção universal se falhar (repassará p/ software libx265)
    return "cpu"

# Função empacotada orquestradora da conversão
def compress_to_hevc(input_file, output_file, quality_level=26):
    # Docstring
    """
    Comprime um vídeo para o formato HEVC (H.265) usando a GPU (se disponível)
    mantendo todas as outras características originais.
    O parâmetro quality_level define o nível de compressão (menor = melhor qualidade e maior arquivo).
    """
    # Valida presença física da fita antes de iniciar o estresse de GPU
    if not os.path.exists(input_file):
        # Aborta e reporta
        print(f"Erro: O arquivo '{input_file}' não foi encontrado.")
        return

    # Evoca o detector de Placas e joga numa string "amd", "nvidia", "intel" ou "cpu"
    gpu = get_gpu_vendor()

    # Array Base Paramétrico (A espinha dorsal imutável do comando que serve pra todos os hardwares)
    command = [
        "ffmpeg",             # Call binário FFmpeg no Path global
        "-i",                 # Argumento flag para input source file
        input_file,           # Path string apontando a fita virgem lida do HD
        "-map",               # Ordem de mapeamento profundo
        "0",                  # Força importação integral, copia todos tracks brutos (vídeo/áudios/subs/fontes/capas/thumbs) do Container 0 (Original file) pra saída.
        "-c:a",               # Codec flag parametrizando Áudio 
        "copy",               # Determina passthrough inalterado perfeito. (Mantém Dolby, DTS, AAC idênticos originais da ISO/Rip)
        "-c:s",               # Codec flag parametrizando Subtitles (Legendas .srt/.ass)
        "copy",               # Determina bitstream direto s/ renderizar imagem, guardando a legenda no container Matroska pra ativar on-demand no player.
        "-c:t",               # Codec flag de 'Attachments' (Tipicamente fontes .ttf/.otf coloridas do formato ASS)
        "copy",               # Carrega anexos perfeitamente evitando desformatação em Anime Hardsubbed/Softsubbed
    ]

    # Prepara a tag númerica da qualidade recebida (CQ ou CRF), formatando em string textual (ex: "26" ou "22")
    qual_str = str(quality_level)
    
    # Lógica seccionada especializada para hardware gráfico. Puxa os shaders certos do driver C++ de cada marca.
    if gpu == "nvidia":
        print(f"GPU NVIDIA detectada. Usando encoder 'hevc_nvenc' com qualidade (CQ) {qual_str}...")
        # NVENC: A API NVENC é incrivelmente rápida. -cq 26 seta CQ target moderado. -preset p4 (medium) balança velocidade x tamanho.
        command.extend(["-c:v", "hevc_nvenc", "-cq", qual_str, "-preset", "p4"])
    elif gpu == "amd":
        print(f"GPU AMD/Radeon detectada. Usando encoder 'hevc_amf' com qualidade (QP) {qual_str}...")
        # AMF: Advanced Media Framework da AMD. 'cqp' = Constant Quantization Parameter. 
        # Adicionado '-vbaq false' (Variance Based Activity Queuing) para silenciar um erro chato "VBAQ is not supported by cqp Rate Control Method" e impedir desbotamento (frames verdes) em placas antigas rx500
        command.extend(["-c:v", "hevc_amf", "-rc", "cqp", "-qp_i", qual_str, "-qp_p", qual_str, "-vbaq", "false"])
    elif gpu == "intel":
        print(f"GPU Intel detectada. Usando encoder 'hevc_qsv' com qualidade global {qual_str}...")
        # QSV: Intel Quick Sync Video embutido nos Celerons e i5's. ICQ = Intelligent Constant Quality. Bem eficaz no baixo watt.
        command.extend(["-c:v", "hevc_qsv", "-global_quality", qual_str])
    else:
        print(f"Nenhuma GPU dedicada detectada. Usando CPU (libx265) com CRF {qual_str}...")
        # FALLBACK: LibX265 cru rodando via Processador/CPU. Muito lento (2fps às vezes) mas gera tamanho reduzidíssimo e imaculado, CRF é o padrão ouro de retenção algorítmica.
        command.extend(["-c:v", "libx265", "-crf", qual_str, "-preset", "fast"])

    # Concatena fechando com o destino output file alvo final do .MKV
    command.append(output_file)

    # UI Banner 
    print(f"Iniciando a compressão para HEVC...")
    print(f"Origem: {input_file}")
    print(f"Destino: {output_file}")
    print("-" * 50)

    # Marca cronômetro
    start_time = time.time()
    # Bloco Try mestre do sistema
    try:
        # Inicia Run síncrono. check=True força erro explícito caso estoure.
        subprocess.run(command, check=True)
        # Corta fita
        end_time = time.time()

        # Calcula matemática tempo absoluto
        elapsed_time = end_time - start_time
        # Desmembra e extrai inteiros em mins/secs pra facilitar leitura do ser humano.
        mins, secs = divmod(elapsed_time, 60)

        # UI Conclusão
        print("-" * 50)
        print(f"Compressão concluída com sucesso! Vídeo salvo em: {output_file}")
        print(f"Tempo de processamento: {int(mins)} minutos e {int(secs)} segundos.")
    # Exceção de Falha da placa ou do arquivo MKV truncado no source corrompendo a leitura a meio caminho da renderização
    except subprocess.CalledProcessError as e:
        print(f"Ocorreu um erro durante a conversão do FFmpeg: {e}")
    # Exceção caso o Windows do cara seja virgem e não tenha a var de ambiente %PATH% com a root folder do binario C:\ffmpeg.exe
    except FileNotFoundError:
        print("Erro: O FFmpeg não foi encontrado no seu sistema.")

# Bloco Idiomático Inicializador Standalone
if __name__ == "__main__":
    # Verifica validade de inserção de argumentos Shell exigindo no min input e output params (ex: compress.py C:\old.mkv D:\new.mkv)
    if len(sys.argv) < 3:
        # Banner de Ajuda Didático
        print(
            "Uso: python compress_to_hevc.py <arquivo_entrada.mkv> <arquivo_saida.mkv> [qualidade]"
        )
        print("O parâmetro [qualidade] é opcional. Padrão é 26 (menor o número = melhor a imagem e maior o arquivo).\n")
        
        # Hardcoded Sandbox Paths (Valores padrão cimentados temporários p/ testes debug rápidos quando se digita só 'python file.py' no terminal sem enviar parametros)
        video_original = r"E:\Traducao\Torrent\Katainaka\Erai-raws_Katainaka_no_Ossan_Kensei_ni_Naru_II_-_05_1080p_AMZN_WEB-DL_AVC_EAC3MultiSubB01748EC.mkv"
        video_destino = r"E:\Traducao\Torrent\Katainaka\Erai-raws_Katainaka_no_Ossan_Kensei_ni_Naru_II_-_05_HEVC_Custom.mkv"
        print(f"Executando modo de teste com o arquivo padrão...")
        # Starta
        compress_to_hevc(video_original, video_destino, quality_level=26)
    # Se passou tudo OK nos args
    else:
        # Isola Input vindo do argumento índice 1
        video_original = sys.argv[1]
        # Isola Output do argumento índice 2
        video_destino = sys.argv[2]
        
        # Iniciação da Qualidade com Padrão CQ/CRF = 26
        qualidade_escolhida = 26
        # Se um terceiro índice foi injetado opcionalmente
        if len(sys.argv) >= 4:
            # Tenta converter
            try:
                # Transforma input string texto solto no powershell pra Int puro formatado (ex "20" virou int(20))
                qualidade_escolhida = int(sys.argv[3])
            # Em caso de alguém escrever literal text "python file.py file.mp4 file_new.mp4 ExcelenteQualidade"
            except ValueError:
                # Aviso que rejeitou fallback pra default
                print("Aviso: A qualidade deve ser um número inteiro. Usando padrão (26).")
                
        # Empurra Start Function Oficial com Qualidade Custom setada.
        compress_to_hevc(video_original, video_destino, quality_level=qualidade_escolhida)
