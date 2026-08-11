# ==============================================================================
# Script: batch_process_universal.py
#
# Objetivo:
#   Processar em lote vídeos a partir de uma lista em arquivo CSV ("Cluster Ready").
#   Padroniza nomes usando a biblioteca guessit, converte vídeos para HEVC (H.265),
#   e gerencia bloqueios de arquivo (.lock) para evitar conflitos em rede (Cluster).
#
# Lógica Principal:
#   Traduz caminhos dinamicamente entre Windows/Linux, configurando a aceleração 
#   de hardware (Nvidia/AMD) adequadamente. Possui proteção heurística "Anti-inchaço" 
#   para descartar conversões que fiquem maiores que os arquivos H.264 originais.
#
# Dependências Externas:
#   guessit (requer instalação via pip)
#   FFmpeg e FFprobe (devem estar instalados e no PATH do sistema)
# ==============================================================================

# Importação do módulo de interações com o sistema operacional
import os
# Importação do módulo para interações com variáveis e funções do interpretador Python
import sys
# Importação do módulo para manipulação de tempo (sleep, medição de tempo)
import time
# Importação do módulo para manipulação de dados no formato JSON
import json
# Importação do módulo para gerenciar e executar subprocessos (ex: ffmpeg e ffprobe)
import subprocess
# Importação do módulo para criar interfaces de linha de comando e processar argumentos
import argparse
# Importação do módulo para recuperar informações sobre a plataforma e sistema operacional
import platform
# Importação do módulo para leitura e escrita de arquivos CSV
import csv
# Importação do módulo de expressões regulares para busca e substituição de textos
import re
# Importação da classe Path do módulo pathlib, para manipular caminhos de arquivos de forma moderna
from pathlib import Path
# Importação da classe datetime para manipulação e formatação de datas e horas
from datetime import datetime

# Bloco try/except para importar a biblioteca 'guessit', que pode não estar instalada
try:
    # Importa a função guessit, usada para extrair informações (título, episódio, etc.) do nome do arquivo
    from guessit import guessit
# Se ocorrer um erro de importação (biblioteca ausente)
except ImportError:
    # Exibe uma mensagem de erro amigável ao usuário sugerindo a instalação
    print("ERRO: Biblioteca 'guessit' não encontrada. Rode: pip install guessit")
    # Encerra o script com código de erro 1 (falha)
    exit(1)

# Função para detectar o sistema operacional e definir a GPU baseada no ambiente
def detect_environment():
    # Retorna uma docstring que explica o que a função faz
    """Detecta o sistema operacional e a placa de vídeo do servidor atual."""
    # Obtém o nome do sistema operacional (ex: 'Windows', 'Linux')
    os_name = platform.system()
    # Define o fallback de aceleração por hardware para 'cpu' como padrão inicial
    gpu = "cpu"
    
    # Mapeamento Direto Baseado na Infraestrutura específica do Usuário
    # Se o sistema operacional for Linux
    if os_name == "Linux":
        # Assume que a máquina Linux tem uma placa NVIDIA
        gpu = "nvidia"
    # Se o sistema operacional for Windows
    elif os_name == "Windows":
        # Assume que a máquina Windows tem uma placa AMD
        gpu = "amd"
        
    # Exibe no console o sistema operacional detectado
    print(f"[INFO] Sistema Operacional: {os_name}")
    # Exibe no console a GPU que será utilizada para aceleração
    print(f"[INFO] Hardware de Aceleração Destinado: {gpu.upper()}")
    # Retorna o sistema operacional e a gpu
    return os_name, gpu

# Função para traduzir o caminho de rede listado no CSV para a plataforma atual (Cross-platform)
def translate_path(path_str, os_name):
    # Retorna uma docstring que explica o propósito da função
    """Traduz o caminho da rede do CSV para a plataforma atual"""
    # Se o sistema que estiver rodando for Linux
    if os_name == "Linux":
        # Substitui a barra invertida padrão do Windows pela montagem Linux /mnt/Media/
        path_str = path_str.replace("\\\\192.168.0.99\\Media\\", "/mnt/Media/")
        # Também substitui o drive mapeado U:\ pela montagem Linux
        path_str = path_str.replace("U:\\", "/mnt/Media/")
        # Converte quaisquer barras invertidas restantes para barras normais do Linux
        path_str = path_str.replace("\\", "/")
    # Se o sistema que estiver rodando for Windows
    elif os_name == "Windows":
        # Substitui a montagem do Linux pelo caminho de rede padrão do Windows
        path_str = path_str.replace("/mnt/Media/", "\\\\192.168.0.99\\Media\\")
        # Converte as barras normais (estilo Unix) para barras invertidas (estilo Windows)
        path_str = path_str.replace("/", "\\")
    # Retorna o caminho de arquivo devidamente ajustado
    return path_str

# Função para limpar o título e remover caracteres indesejados
def sanitize_title(title):
    # Remove chaves, colchetes, parênteses, aspas, exclamações e dois-pontos usando regex
    title = re.sub(r'[\[\]\(\)\'\":!]', '', title)
    # Substitui qualquer espaço em branco ou hifens isolados por um ponto
    title = re.sub(r'[\s\-]+', '.', title)
    # Substitui dois ou mais pontos seguidos por apenas um ponto (evitando "nome..filme")
    title = re.sub(r'\.+', '.', title)
    # Remove qualquer ponto que possa ter sobrado no começo ou no fim da string
    return title.strip('.')

# Função para padronizar o nome da resolução do vídeo com base em sua largura em pixels
def get_resolution_name(width):
    # Converte a largura para inteiro se existir, senão define como 0
    w = int(width) if width else 0
    # Se a largura for 3800 ou superior, considera a resolução como 4K (2160p)
    if w >= 3800: return "2160p"
    # Se for 1900 ou superior, considera como Full HD (1080p)
    elif w >= 1900: return "1080p"
    # Se for 1200 ou superior, considera como HD (720p)
    elif w >= 1200: return "720p"
    # Para larguras menores que 1200, cai no caso padrão (SD / 480p)
    else: return "480p"

# Função que usa guessit para gerar um nome padronizado para o arquivo de mídia
def generate_new_name(original_path, width):
    # Usa guessit no nome base do arquivo (sem extensão) para extrair os metadados textuais
    guess = guessit(original_path.name)
    # Tenta extrair o título; se falhar, usa o nome do arquivo (stem = nome sem extensão)
    title = guess.get('title', original_path.stem)
    
    # Busca um possível título alternativo extraído
    alt_title = guess.get('alternative_title')
    # Se houver título alternativo
    if alt_title:
        # Anexa o título alternativo ao principal separado por ponto
        title = f"{title}.{alt_title}"
        
    # Extrai o ano de lançamento (se houver, senão string vazia)
    year = guess.get('year', '')
    # Extrai o número da temporada
    season = guess.get('season')
    # Extrai o número do episódio
    episode = guess.get('episode')
    # Extrai o título específico do episódio
    episode_title = guess.get('episode_title')
    
    import re
    # Override de segurança para Animes (Ex: [Erai-raws] Tokyo 24-ku - 11 ...)
    # Impede que números no nome (24-ku) sejam confundidos com o episódio
    anime_match = re.match(r'^(?:\[.*?\]\s*)?(.+?)\s+-\s+(\d+(?:\.\d+)?(?:v\d+)?)', original_path.name)
    if anime_match:
        title = anime_match.group(1)
        episode = anime_match.group(2)
        season = None
        episode_title = None
    
    # Se não for uma série (sem temporada ou episódio numérico) mas possuir um "título de episódio" detectado
    if not season and not episode and episode_title:
        # Anexa o subtítulo ao título principal
        title = f"{title}.{episode_title}"
        # Zera a variável de episódio para evitar duplicação depois
        episode_title = None
        
    # Chama a função de higienização do título final (limpa pontos e caracteres extras)
    title = sanitize_title(title)
    
    # Tenta extrair a resolução (ex: '1080p') detectada no nome original
    resolution = guess.get('screen_size')
    # Se não achou no nome, tenta derivar matematicamente pela largura do vídeo (width)
    if not resolution:
        # Chama a função que determina a resolução usando os pixels reais
        resolution = get_resolution_name(width)
    
    # Inicia a lista de partes do nome do arquivo com o Título principal
    parts = [title]
    # Se encontrou o ano de lançamento
    if year:
        # Adiciona o ano à lista de partes
        parts.append(str(year))
        
    # Tratamento para Séries (Quando há uma temporada detectada)
    if season is not None:
        # Se a temporada for uma lista (várias detectadas), pega apenas a primeira
        if isinstance(season, list): season = season[0]
        # Formata a string de temporada no formato 'S01' (S acompanhado de número com 2 dígitos)
        s_str = f"S{int(season):02d}"
        # Se houver episódio correspondente
        if episode is not None:
            # Se for uma lista de episódios, pega apenas o primeiro
            if isinstance(episode, list): episode = episode[0]
            # Concatena o número do episódio ao padrão, gerando ex: 'S01E02'
            s_str += f"E{int(episode):02d}"
        # Adiciona o bloco Temporada/Episódio nas partes do nome
        parts.append(s_str)
    # Tratamento alternativo caso haja episódio mas nenhuma temporada (ex: Anime onde só enumera o eps)
    elif episode is not None:
        # Pega o primeiro se for lista
        if isinstance(episode, list): episode = episode[0]
        # Adiciona apenas o episódio na string (ex: 'E02')
        parts.append(f"E{int(episode):02d}")
        
    # Se a análise detectou um nome específico para o episódio da série
    if episode_title:
        # Pega o primeiro se for lista
        if isinstance(episode_title, list): episode_title = episode_title[0]
        # Limpa o título do episódio com a função de sanitização e adiciona à lista
        parts.append(sanitize_title(episode_title))
        
    # Se existe uma resolução (detectada pelo guessit ou calculada pela largura)
    if resolution and resolution != "Unknown":
        # Adiciona a resolução (ex: 1080p) às partes
        parts.append(str(resolution))
        
    # Adiciona sempre a tag H265 no final do arquivo, já que esse será o formato de saída
    parts.append("H265")
    
    # Junta todas as partes da lista com ponto (ex: Título.Ano.S01E01.1080p.H265) e adiciona a extensão original (ex: .mkv)
    return ".".join(parts) + original_path.suffix

# Função para extrair os metadados técnicos do vídeo usando ffprobe
def get_video_metadata(file_path):
    # Monta a linha de comando do ffprobe formatando a saída para JSON de modo silencioso (quiet)
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    # Inicia o bloco de tentativa de execução
    try:
        # Decodificação manual para evitar erros de encodings do Windows PowerShell com CP1252
        # Executa o subprocesso, captura a saída no stdout e checa por falhas
        result = subprocess.run(cmd, capture_output=True, check=True)
        # Decodifica o resultado UTF-8, substituindo erros, e converte de string JSON para Dicionário Python
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
    # Se houver erro de execução do ffprobe ou erro lendo o JSON, captura a exceção
    except Exception:
        # Retorna None indicando que houve falha para processar o vídeo
        return None, False, None
    
    # Inicializa variável para largura da resolução
    width = None
    # Inicializa variável para checar se o formato já é H.265
    is_hevc = False
    # Itera sobre todas as streams (faixas de vídeo, áudio, legendas) no JSON gerado pelo ffprobe
    for stream in data.get('streams', []):
        # Procura a stream que seja do tipo "video" e não a de áudio
        if stream.get('codec_type') == 'video':
            # Obtém a largura da faixa de vídeo e guarda na variável
            width = stream.get('width')
            # Checagem contra codecs de altíssima compactação (HEVC e nova geração)
            codec_name = stream.get('codec_name')
            if codec_name in ("hevc", "h265", "x265", "av1", "vp9"):
                # Marca a flag indicando que o vídeo já está comprimido no formato ideal
                is_hevc = True
            # Encerra o laço pois achou o vídeo (ignora outros possíveis streams de imagem extras)
            break
            
    # Inicializa a variável duração para guardar o tempo
    duration = None
    # Tentativa de extrair a duração global do arquivo do container format
    try:
        # Verifica se as chaves existem na estrutura do JSON retornado
        if 'format' in data and 'duration' in data['format']:
            # Converte a string de duração (ex: '3600.000') para número com casa decimal (float)
            duration = float(data['format']['duration'])
    # Se falhar (metadado ausente ou corrompido), ignora silenciosamente
    except Exception:
        pass
            
    # Retorna as métricas essenciais extraídas: Largura em pixels, se é H.265 e a duração em segundos
    return width, is_hevc, duration

# Função para codificar (converter) o vídeo usando FFmpeg com aceleração de hardware (GPU)
def encode_video(input_path, output_path, gpu, duration_secs):
    # Define o início do comando chamando o executável e a flag -y para sobrescrever o arquivo de saída sem perguntar no console
    command = ["ffmpeg", "-y"]
    
    # Define a decodificação por hardware (Leitura do vídeo original mais rápida)
    # Se o sistema informou uso de hardware NVIDIA
    if gpu == "nvidia":
        # Adiciona a flag de aceleração via CUDA para decodificação pela placa
        command.extend(["-hwaccel", "cuda"])
    # Se o sistema informou uso de hardware AMD
    elif gpu == "amd":
        # Adiciona a flag de aceleração DXVA2 (padrão antigo/estável do Windows) para decodificação
        command.extend(["-hwaccel", "dxva2"])
        
    # SILENCE FFMPEG SPAM AND ENABLE PROGRESS OUTPUT TO STDOUT
    # Suprime mensagens comuns poluentes e força o status de progresso do ffmpeg para o stdout (onde possamos ler em texto)
    command.extend(["-v", "error", "-nostats", "-progress", "-"])
        
    # Declara o parâmetro de entrada `-i` seguido do caminho do arquivo de origem que vamos converter
    command.extend(["-i", str(input_path)])
    
    # Bloco de Encoding de Destino NVIDIA
    if gpu == "nvidia":
        # Argumentos do encoder para placas da Nvidia
        command.extend([
            "-c:v", "hevc_nvenc",    # Codec de vídeo H.265 executado 100% no hardware da NVIDIA
            "-cq", "27",             # Parâmetro Constant Quality (nível 27 = bom equilíbrio peso/imagem)
            "-preset", "p4"          # Predefinição média de qualidade/velocidade da API nvenc (P4)
        ])
    # Bloco de Encoding de Destino AMD
    elif gpu == "amd":
        # Argumentos do encoder para placas da AMD (AMF)
        command.extend([
            "-c:v", "hevc_amf",      # Codec de vídeo H.265 executado no hardware da AMD
            "-rc", "cqp",            # Parâmetro Constant QP (Constant Quality via hardware)
            "-qp_i", "26",           # Fator de compressão QP para os I-frames originais
            "-qp_p", "26",           # Fator de compressão QP para os P-frames previstos
            "-vbaq", "false"         # Desativa Variance Based Activity Queuing (evita bugs no encoder da AMD e frames verdes)
        ])
    # Bloco de Encoding de Software (Fallback)
    else:
        # Argumentos de codificação usando o processador (CPU) - Bastante lento
        command.extend([
            "-c:v", "libx265",       # Codec oficial em software puro para h265
            "-crf", "26",            # Fator CRF de qualidade (Constant Rate Factor, quanto menor, melhor mas mais pesado)
            "-preset", "fast"        # Velocidade rápida de processamento para não gargalar a CPU infinitamente
        ])
        
    # Parâmetros Universais aplicados independentes de qual hardware está renderizando
    command.extend([
        "-map", "0",                               # Copia de modo cru todos os fluxos do arquivo fonte (todos os vídeos, vários áudios, legendas, anexos)
        "-c:a", "copy",                            # Copia o codec de áudio 1:1 exatamente como está (sem reconverter ou perder qualidade do som)
        "-c:s", "copy",                            # Copia as legendas (SRT, ASS) da mesma forma 1:1 sem renderizar na imagem
        "-disposition:s", "0",                     # Desliga as flags e zera todos os sinalizadores de "Legenda Padrão/Forçada" preexistentes
        "-disposition:s:m:language:por", "default",# Reassinala e define qualquer faixa de legenda marcada como Português para "Default" forçado
        str(output_path)                           # No final do comando inteiro, entrega o caminho absoluto do arquivo de saída (Output)
    ])
    
    # Inicia o bloco try para a execução do conversor ffmpeg sem dar crash geral
    try:
        # Inicia o processo do ffmpeg passando a lista de comandos via subprocess.
        # bufsize=1 cria buffering em linha, stdout/err redirecionados para conseguirmos capturar o log em tempo real sem engasgos de bytes
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, encoding='utf-8', errors='replace')
        
        # Inicia o valor de última porcentagem relatada com margem folgada negativa para printar instantaneamente o início
        last_report_pct = -10
        # Armazena o tempo (hora atual) do último log de relatório gerado
        last_report_time = time.time()
        # Inicializa a velocidade em quadros por segundo da conversão em string 0
        current_fps = "0"
        
        # Inicia o laço contínuo lendo iterativamente cada nova linha sendo cuspida pelo log texto do ffmpeg
        for line in process.stdout:
            # Se a linha produzida informar os Frames per Second atuais
            if line.startswith("fps="):
                # Isola e armazena o valor numérico limpo para uso posterior (ex: "fps=144" virá "144")
                current_fps = line.split("=")[1].strip()
            # Se a linha informar o tempo codificado até agora (representado em microsegundos)
            elif line.startswith("out_time_us="):
                # Inicia try interno para conversões matemáticas
                try:
                    # Captura o valor após o símbolo de igual na linha lida
                    val = line.split("=")[1].strip()
                    # Verifica se o valor é um número válido (ignorando valores bugados, negativos aleatórios e literais soltos pelo FFmpeg no boot)
                    if val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
                        # Converte a string limpa para inteiro matemático
                        out_time_us = int(val)
                        # Se conseguimos mapear a duração total do filme na função anterior, permitindo o cálculo de porcentagem
                        if duration_secs and duration_secs > 0:
                            # Calcula a porcentagem atual do progresso: divide por 1mi pra virar segundos e por duração pra virar fração, vezes 100
                            pct = (out_time_us / 1_000_000) / duration_secs * 100
                            # Filtro anti-spam: Imprime a cada incremento de 5% concluído ou após aguardar silenciosamente por 5 minutos (300 segs)
                            if (pct - last_report_pct >= 5) or (time.time() - last_report_time > 300):
                                # Mostra o andamento na tela do console, injetando FPS armazenado
                                print(f"    -> Progresso: {pct:.1f}% | Taxa: {current_fps} fps")
                                # Atualiza o registro visual marcando este percentual como o último relatado
                                last_report_pct = pct
                                # Marca no relógio a hora exata deste log que acabou de ser cuspido
                                last_report_time = time.time()
                                # Força o descarregamento da string no console (essencial quando rodando via systemd ou serviços de fundo)
                                sys.stdout.flush()
                # Ignora erros caso o valor lido do pipe não pudesse ser convertido para Inteiro (ex: string nula ou 'N/A' gerado por codecs soltos)
                except ValueError:
                    # Passagem silenciosa para manter a renderização rodando sem interrupções triviais
                    pass
                    
        # Ao término de todo o processo de encoding, espera o processo fechar por completo e extrai o log residual de erros stderr
        _, stderr = process.communicate()
        # Se o código de retorno do sistema do binário (returncode) for diferente de zero (zero = sucesso final)
        if process.returncode != 0:
            # Exibe erro genérico notificando o status code para o usuário debuggar
            print(f"  [ERRO] FFmpeg falhou com código {process.returncode}")
            # Se a saída de erro não estiver vazia no log
            if stderr.strip():
                # Imprime os detalhes profundos embutidos
                print(f"  [ERRO DETALHES] {stderr.strip()}")
            # Retorna Falso avisando à função pai que o arquivo quebrou na geração
            return False
        # Se sobreviveu a tudo sem quebrar, retorna Verdadeiro. O arquivo foi escrito com sucesso no HD.
        return True
    # Captura possíveis exceções de sistema (ex: Executável do FFmpeg ausente, driver crashado, permissão negada)
    except Exception as e:
        # Exibe o erro legível
        print(f"  [ERRO] Falha ao executar FFmpeg: {e}")
        # Notifica falha catastrófica ao chamador
        return False

# Função central que gerencia todo o ciclo de vida e orquestração do arquivo: Análise, Nomenclatura, Bloqueio de Cluster e chamada de Conversão.
def process_file(file_path, delete_original, os_name, gpu, index, total):
    # Gera virtualmente um caminho idêntico ao do vídeo mas finalizado em ".lock" (ex: filme.mkv.lock)
    lock_file = file_path.with_suffix(file_path.suffix + ".lock")
    
    # 1. VERIFICAÇÃO DE LOCK (CONCORRÊNCIA EM AMBIENTES DE CLUSTER / SWARM)
    # Verifica de antemão se o arquivo `.lock` físico já existe nesta exata pasta no NAS
    if lock_file.exists():
        # Informa que pulou e aborta a função (Isso previne que a máquina 1 e máquina 2 peguem a linha 1 do CSV ao mesmo tempo)
        print(f"\n[{index}/{total}] [{file_path.name}] [LOCK] Outra máquina está processando. Pulando...")
        # Atualiza a interface
        sys.stdout.flush()
        # Aborta silenciosamente entregando 0 de contagem de Megabytes de economia
        return 0, 0
        
    # 2. TENTA CRIAR O LOCK (Exclusão Mútua contra Race Conditions via Sistema Operacional)
    try:
        # Tenta criar um arquivo minúsculo vazio no caminho do `.lock`. O parâmetro exist_ok=False diz ao Kernel para disparar exceção se já existir.
        lock_file.touch(exist_ok=False)
    # Captura a falha de race condition segura (Duas máquinas tocaram no mesmo arquivo no exato mesmo milissegundo de diferença)
    except FileExistsError:
        # Previne perda de dados e avisa quem perdeu a corrida
        print(f"\n[{index}/{total}] [{file_path.name}] [LOCK] Outra máquina pegou no mesmo milissegundo. Pulando...")
        sys.stdout.flush()
        return 0, 0
    # Caso não tenha permissão de escrita, rede sem fio caia ou a pasta do samba tenha reiniciado e desvinculado a unidade
    except Exception as e:
        # Exibe que ocorreu erro bizarro gerando o lock
        print(f"\n[{index}/{total}] [{file_path.name}] Erro ao criar lock: {e}")
        sys.stdout.flush()
        return 0, 0

    # Inicia o bloco de orquestração em si. Envolvido em try/finally para garantir de vida e morte que o arquivo de trava (.lock) irá sumir da rede caso haja falha severa (ex: queda de luz do pc)
    try:
        # Checa e calcula o tamanho atualizado em disco do arquivo original em Megabytes se ele for rastreável e não-nulo
        orig_mb = file_path.stat().st_size / (1024 * 1024) if file_path.exists() else 0
        
        # Puxa a string com horário do sistema e formata para leitura visual confortável na tela preta
        start_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Imprime o banner estético no console marcando que o arquivo começou oficialmente
        print(f"\n=======================================================")
        print(f"[{start_time_str}] [{index}/{total}] Iniciando processamento ({os_name}):")
        sys.stdout.flush()
        
        # Chama a função que lê as especificações com ffprobe e armazena os metadados gerados (Largura, Tipo atual, Duração)
        width, is_hevc, duration = get_video_metadata(file_path)
        
        # Se os metadados falharem (width não preenchido), é porque o FFprobe bateu contra a parede num vídeo ilegível
        if width is None:
            # Avisa o usuário sobre corrompimento
            print("  [ERRO] Não foi possível ler metadados. Vídeo corrompido?")
            # Devolve valores idênticos anulando economias e partindo pra outra sem dar lock de processador
            return orig_mb, orig_mb
            
        # Pede para a IA de Nomenclatura (Guessit) gerar o nome padronizado oficial e enxertar o nome embutido nele, já projetando H265
        new_name = generate_new_name(file_path, width)
        # Cria o objeto pathlib (Destino final) juntando e mapeando virtualmente na mesma pasta de origem usando apenas o nome elegante projetado
        final_dest = file_path.parent / new_name
        
        # Printa estatísticas de operação de mudança
        print(f"  -> Entrada: {file_path}")
        print(f"  -> Saída:   {final_dest}")
        # Se a duração pôde ser lida no container e é confiável
        if duration:
            # Extrai o quociente e resto dividindo a duração bruta do filme em Minutos limpos e Segundos remanescentes
            mins, secs = divmod(duration, 60)
            # Imprime estimativas completas do vídeo na tela, servindo de log para análise temporal e volumétrica
            print(f"  -> Duração: {int(mins)}m {int(secs)}s | Tamanho: {orig_mb:.1f} MB")
        # Força print
        sys.stdout.flush()
        
        # Recria e reforça as varíaveis de destino novamente para validações lógicas rigorosas de bypassing
        final_dest = file_path.parent / new_name
        # Cria um destino secundário hipotético caso o arquivo recebesse o nome final padronizado MAS com final H264 (fallback pro anti-inchaço)
        final_dest_h264 = file_path.parent / new_name.replace("H265", "H264")
        
        # Primeira Condição de Bypass: Se o arquivo lindo final H265 já existir na pasta OU o próprio arquivo velho e original mal-nomeado já possuir formato e nome embutido idêntico ao H265 final esperado. (Economiza processamento duplo de quem rodar o script sem querer)
        if final_dest.exists() or (file_path.name == new_name and is_hevc):
            # Loga
            print("  -> O arquivo final já existe ou já está no padrão. Pulando.")
            # Se a linha de comando foi chamada com flag `--delete` explícita, o usuário quer eliminar rastros desorganizados. 
            # A checagem confirma se o arquivo original avaliado tem de fato nome ou formato diferente do destino padronizado para só então apagá-lo.
            if delete_original and file_path.name != new_name and file_path.exists():
                print("  -> Deletando original obsoleto...")
                # Apaga o arquivo desnecessário fisicamente no disco e no NAS
                file_path.unlink()
            # Avalia se a deleção limpou o HD para enviar pro calculo. Caso sim, calcula MBs finais lendo do disco.
            final_mb = final_dest.stat().st_size / (1024*1024) if final_dest.exists() else orig_mb
            # Retorna estatísticas reais
            return orig_mb, final_mb
            
        # Nova Condição de Bypass Rápido: Se o arquivo já está em formato perfeito (AV1/HEVC/VP9), mas apenas com o nome despadronizado
        elif is_hevc and not final_dest.exists():
            print("  -> O vídeo já possui codec de altíssima compactação (AV1/HEVC).")
            print("  -> O nome original está fora do padrão. Efetuando renomeio físico instântaneo...")
            import shutil
            shutil.move(str(file_path), str(final_dest))
            final_mb = final_dest.stat().st_size / (1024*1024)
            return orig_mb, final_mb
            
        # Segunda Condição de Bypass: O arquivo tentou ser convertido dias atrás e foi rejeitado pelo limitador de tamanho por ficar ruim/estourado (Foi salvo sob o nome H264 elegante e mantido no sistema, devendo ser ignorado por ser intratável sem loss massivo)
        if final_dest_h264.exists() or (file_path.name == final_dest_h264.name and not is_hevc):
            print("  -> Arquivo padronizado em H264 já existe (foi descartado pelo anti-inchaço). Pulando.")
            # Mesma lógica para limpar se ele estiver obsoleto na flag delete. Útil se o usuário colocar lixo renomeado na pasta para o csv pegar de propósito.
            if delete_original and file_path.name != final_dest_h264.name and file_path.exists():
                print("  -> Deletando original obsoleto...")
                # Deleta
                file_path.unlink()
            # Extrai tamanho estático
            final_mb = final_dest_h264.stat().st_size / (1024*1024) if final_dest_h264.exists() else orig_mb
            return orig_mb, final_mb
            
        # Cria e constroi o nome de caminho abstrato para o arquivo temporário ser usado em background na pasta atual durante o processamento de horas.
        # Usa um prefixo de "_part_" e mantem a extensão mkv/mp4 intacta no sufixo para o multiplexador do FFmpeg não enlouquecer e não engasgar formatos (ex: _part_Filme.mkv)
        encoded_temp = file_path.parent / f"_part_{new_name}"
        
        # Informa qual hardware está ativamente processando e iniciando a tortura de silício
        print(f"  -> Convertendo para HEVC ({gpu.upper()}) pela rede...")
        sys.stdout.flush()
        # Marca um carimbo de tempo Epoch da largada da conversão
        start_time = time.time()
        # Delega e despacha a requisição de encoding (síncrona), trancando e aguardando enquanto assiste o retorno de dados pela rede até findar.
        success = encode_video(file_path, encoded_temp, gpu, duration)
        # Calcula quantos segundos inteiros de demora transcorreram entre a largada e a conclusão
        elapsed = time.time() - start_time
        
        # Tratamento de catástrofe: Se a conversão explodiu por falta de VRAM, RAM, timeout, ou o arquivo sumiu na compilação.
        if not success or not encoded_temp.exists():
            print("  [ERRO] A conversão falhou!")
            # Tenta ser limpo e deletar o lixo fragmentado estragado ("_part_...") se ele sobrou poluindo o disco de quem hospeda.
            if encoded_temp.exists(): encoded_temp.unlink()
            # Informa que o arquivo rendeu 0 megas de lucro
            return orig_mb, orig_mb
            
        # 3. VERIFICAÇÃO ANTI-INCHAÇO (Prevenção heurística contra bitrates estourados, grainy films, noise em excesso ou perfis de VMAF desajustados da GPU)
        # Pega o tamanho real do arquivo temporário recém gerado (que acabou de ser parido) convertendo o ST_SIZE em formato Megabytes puros.
        new_mb = encoded_temp.stat().st_size / (1024*1024)
        
        # AVALIAÇÃO DE RESULTADOS: O H265 é um formato criado ESTRITAMENTE para compressão (Metade do tamanho do H264 com a mesma qualidade de pixel).
        # Se um encoder mal regulado ou com Constant Quality muito rígida fizer o novo arquivo ficar GORDO (maior) do que o antigo arquivo que já era lixo, a conversão falhou moral e logisticamente.
        if new_mb >= orig_mb:
            # Notifica que ativou o trigger limitador de espaço em disco
            print("  -> [ANTI-INCHAÇO] Arquivo novo ficou MAIOR que o original H264!")
            print("  -> Descartando a conversão para economizar espaço.")
            # Apaga rudemente o arquivo recém-gerado que custou horas de GPU porque a troca de disco não é um bom investimento de vida no NAS limitadíssimo do usuário.
            encoded_temp.unlink()
            
            # Reconhece que, ainda assim, seria bom aproveitar algo dessa máquina. Gera mentalmente a string padronizada belíssima do arquivo, apenas substituindo e marcando embutido de que "esse filme restará como sendo H264 pra sempre."
            new_name_h264 = new_name.replace("H265", "H264")
            # Verifica se o arquivo original base desorganizado (que foi mantido vivo na checagem acima) possuía um nome muito sujo
            if file_path.name != new_name_h264 and file_path.exists():
                print(f"  -> Padronizando original para evitar retrabalho futuro: {new_name_h264}")
                # Envolve em tratamento de erro de leitura IO
                try:
                    # Aplica a string sanitizada H264 ao arquivo raiz mal-criado.
                    # Isso garante uma pequena vitória de estética ao NAS (Filme antes `Jumanji_.XviD_LOL` vira `Jumanji.1080p.H264` limpo). A segunda checagem de Bypass garante que esse filme jamais será tocado nas próximas semanas pra perder tempo em GPUs caso varrido de novo.
                    file_path.rename(file_path.parent / new_name_h264)
                except Exception as e:
                    # Registra se falhar, comum em discos montados readonly ou permissões ACLs do Windows (NTSF Access denied).
                    print(f"  [ERRO] Falha ao renomear: {e}")
                    
            # Calcula o tempo total em minutos e segundos perdidos
            mins, secs = divmod(elapsed, 60)
            # Pega log de hora final
            end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Registra no log abertamente que essa conversão específica não rendeu lucro e foi descartada com perdas de X para Y para auditorias de sistema futuras
            print(f"  [{end_time_str}] [DESCARTADO] Tempo desperdiçado: {int(mins)}m {int(secs)}s | {orig_mb:.1f}MB -> {new_mb:.1f}MB")
            # Devolve megabytes intocados originais sem lucros
            return orig_mb, orig_mb
            
        # O arquivo novo conseguiu ser perfeitamente otimizado (Pesou menos sem estragar).
        print("  -> Finalizando...")
        # Renomeia fisicamente o arquivo temporário da lixeira "part" e o consagra definitivamente como o formato oficial finalizado na biblioteca do cliente.
        encoded_temp.rename(final_dest)
        
        # Se o usuário ordenou a destruição das fitas raízes
        if delete_original:
            print("  -> Excluindo arquivo original no NAS...")
            # Limpa o arquivo de 10GB que foi transformado perfeitamente em 2GB (Economia líquida real pra conta final)
            file_path.unlink()
        # Se omitido (Cenário seguro para primeira testagem ou backups de segurança)
        else:
            # Confirma
            print("  -> Mantendo original no NAS (Fase 1 - QA).")
            
        # Calcula e converte o tempo de andamento vitorioso
        mins, secs = divmod(elapsed, 60)
        end_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Imprime orgulhosamente a estatística de sucesso com contadores
        print(f"  [{end_time_str}] [CONCLUÍDO] Tempo Total: {int(mins)}m {int(secs)}s | {orig_mb:.1f}MB -> {new_mb:.1f}MB")
        
        # Devolve a margem exata e fidedigna de ganhos da compressão a nível de byte pro chamador principal
        return orig_mb, new_mb
        
    # Cláusula infalível embutida em interpretadores de baixo nível do Python para limpeza IO
    finally:
        # GARANTIA DE LIMPEZA: Sempre deleta o arquivo de trava sem exceção para evitar travar toda a esteira do cluster infinitamente após um crash inesperado da maquina operante local
        if lock_file.exists():
            lock_file.unlink()

# Bloco de chamada principal inicial (Routine starter function do script)
def main():
    # Prevenção rigorosa de quebras de log ao jogar acentos e caracteres UTF8 na tela arcaica de terminais Windows não-modernos (ex: cmd/powershell clássico sem chcp 65001)
    if sys.platform == "win32":
        # Força o fluxo de saída text pro formato internacional UTF-8 (impede erro UnicodeEncodeError em nomes de filmes gringos e chineses)
        sys.stdout.reconfigure(encoding='utf-8')
        
    # Inicializa e configura o parser de linha de comando gerando um --help explicativo com a descrição da ferramenta
    parser = argparse.ArgumentParser(description="Conversor Universal (Cluster Ready)")
    # Registra o argumento obrigatório para injetar a string literal com o caminho do .CSV gerado
    parser.add_argument("--csv", help="Caminho para o arquivo CSV de lista")
    # Registra flag booliana (true/false) que executa a diretiva ALL, varrendo em peso independente do CSV
    parser.add_argument("--all", action="store_true", help="Processa toda a biblioteca em vez de só o piloto")
    # Registra flag booliana destrutiva (true/false) avisando para destruir lixo
    parser.add_argument("--delete", action="store_true", help="Deleta o arquivo original após converter")
    
    # Executa a compilação cruzando argumentos passados via terminal e mapeando nos objetos programados
    args = parser.parse_args()
    
    # Valida rigidamente se o usuário esqueceu de prover pelo menos a lista de tarefas base
    if not args.csv:
        # Imprime na tela o texto instrucional de autoajuda formatado
        parser.print_help()
        # Mata a aplicação informando código de interrupção 1 (Erro do usuário)
        sys.exit(1)
        
    # Orquestra e obtém variáveis de ambiente do ambiente atual operando e o hardware injetável selecionado pro ffmpeg
    os_name, gpu = detect_environment()
        
    # Bloco try amplo focado em proteger de falhas brutas de leitura e parsing do formato CSV que o usuário jogar aqui dentro
    try:
        # Abre o arquivo CSV com suporte especial ao formato Microsoft Excel (utf-8-sig ignora o BOM invisivel chato no começo do texto) em modo leitura textual
        with open(args.csv, newline='', encoding='utf-8-sig') as f:
            # Inicializa a leitura em formato de Dicionário Python, reconhecendo ; como delimitador de coluna padrão do office
            reader = csv.DictReader(f, delimiter=';')
            # Fila de processamento a ser recheada (Array vazio)
            to_process = []
            # Acumulador virtual de megabytes extraídos apenas visualmente das anotações das células do Excel
            initial_mb = 0
            # Varre e perfura cada uma das linhas contendo vídeos anotados na lista
            for row in reader:
                # Regra de Inclusão: Se flag --all for True ignoramos a regra seletiva, senão (se False) caçamos manualmente as linhas contendo a string mágica 'SIM' em Lote Piloto
                if args.all or row.get('Lote_Piloto') == 'SIM':
                    # Recupera de dentro da célula da planilha a string gigantesca com o caminho de rede UNC exato daquele filme
                    path_str = row['Caminho_Completo_Original']
                    # Encapsula na função de tradução multi-kernel (Transforma barras e mounts entre Windows e Linux para universalizar)
                    path_str = translate_path(path_str, os_name)
                    # Dá um append do filme finalmente validado na fila em memória do Python
                    to_process.append(path_str)
                    
                    # Try catch isolado meramente para contabilidade estética do peso (Evita quebrar o laço inteiro só por 1 célula preenchida errada com letras e que não parseia em Float)
                    try:
                        # Pega na célula o tamanho em string do vídeo listado, e dá overwrite rápido em vírgulas pra ponto (Padrão PT-BR decimal fix) 
                        size_str = row.get('Tamanho_MB', '0').replace(',', '.')
                        # Floatiza e engorda a fila
                        initial_mb += float(size_str)
                    # Em caso de crash matemático com dados corrompidos (Ex: Vazio " ", ou Not Available "N/A"), ignora com maestria e não altera os gigabytes somados ate entao
                    except:
                        pass
                        
        # Finalizada a varredura do excel, converte o somatório estimado bruto estático lido das colunas para GB
        initial_gb = initial_mb / 1024
        
        # Gera o banner de entrada com hora pontual gravada
        batch_start_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Imprime que a esteira da linha de produção mapeou com êxito
        print(f"\n[{batch_start_str}] Encontrados {len(to_process)} vídeos para conversão paralela.")
        # E demonstra o limite do que a máquina passará processando pelas proximas semanas baseando-se no arquivo estático provido
        print(f"-> Volume Total Inicial da Fila: {initial_gb:.2f} GB")
        # Flush de tela
        sys.stdout.flush()
        
        # Variáveis de monitoramento contínuo final que contam verdadeiramente os dados processados em tempo real na máquina e não do Excel
        total_videos = len(to_process) # Contagem do Array
        total_orig_mb = 0 # Balanço Entrada real em disco
        total_new_mb = 0 # Balanço Saida real em disco
        
        # Executa o loop principal, alimentando o índice real matemático, lendo de 1 em diante da fila enclausurada processada out-of-order 
        for i, path_str in enumerate(to_process, start=1):
            # Bloqueio síncrono. Envia os dados pra esteira, e cruza os braços aguardando retorno final que destravam e dão as metricas consolidadas
            o_mb, n_mb = process_file(Path(path_str), args.delete, os_name, gpu, i, total_videos)
            # Acumula semestralmente o tamanho do disco lido que passou por esta rotina individualmente (seja ele H265 convertido ou arquivo esquivado do anti-inchaço e descartado)
            total_orig_mb += o_mb
            # Acumula semestralmente o novo tamanho do disco enxuto devolvido
            total_new_mb += n_mb
            
        # Puxa o horário cravado final exato em que tudo e todos foram computados com sucesso
        batch_end_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Divide todos os acúmulos por 1024 e engloba tudo em valores práticos para tela de encerramento em modo real
        total_orig_gb = total_orig_mb / 1024
        total_new_gb = total_new_mb / 1024
        # A Métrica Diamante (Lucro Absoluto de Terabytes da Operação): Entrada menos Saída
        economia_gb = total_orig_gb - total_new_gb
        
        # Gera o painel de estatísticas conclusivas da sessão
        print("\n=======================================================")
        print(f"[{batch_end_str}] Processamento em lote concluído!")
        print(f"-> Volume Inicial Total (Processado): {total_orig_gb:.2f} GB") # O quanto nós comemos da maquina
        print(f"-> Volume Final Total   (Processado): {total_new_gb:.2f} GB") # O quanto repusemos na maquina
        print(f"-> Espaço Economizado               : {economia_gb:.2f} GB") # Diferença monetária tangível
        # Flush mandatório
        sys.stdout.flush()
            
    # Clausula salvadora captadora de pane ao abrir, ou ler partes brutas, ou encerramento precipitado da permissão IO do arquivo text/csv.
    except Exception as e:
        # Notificação amigável impedindo display vermelho gigante que assusta operadores
        print(f"Erro ao ler CSV: {e}")

# Sentinela idiomática mágica do Python. Impede invasões (Se este arquivo for chamado por 'import my_script', seu __name__ será 'my_script', e o bloco não executa, prevenindo comportamento de código macarrônico em livrarias importadas acidentalmente)
if __name__ == "__main__":
    # Evoca o laço inicial com autorização do Kernel validada
    main()
