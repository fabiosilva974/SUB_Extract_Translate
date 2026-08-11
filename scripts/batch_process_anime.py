# ==============================================================================
# Script: batch_process_anime.py
#
# Objetivo:
#   Processar em lote (e recursivamente) vídeos de uma biblioteca de rede.
#   Copia localmente, sanitiza pastas/arquivos, converte para HEVC,
#   configura legenda PT como padrão e gera log CSV detalhado.
#
# Lógica Principal:
#   Cria uma estrutura de diretórios espelho em "Convertidos" na raiz do disco,
#   com todos os nomes sanitizados (sem espaços). 
#   Pula arquivos já codificados em HEVC para economizar tempo.
#
# Dependências Externas:
#   FFmpeg (deve estar instalado e no PATH do sistema)
# ==============================================================================
# Importação do módulo de interações com o sistema operacional e caminhos de arquivo
import os
# Importação do módulo para funções específicas do interpretador Python (ex: sys.exit)
import sys
# Importação do módulo para operações de alto nível em arquivos, como cópia e movimentação
import shutil
# Importação do módulo para criação e gerenciamento de subprocessos (ex: rodar FFmpeg)
import subprocess
# Importação do módulo para parsing amigável de argumentos de linha de comando
import argparse
# Importação do módulo de medição de tempo, para calcular a duração das tarefas
import time
# Importação do módulo de expressões regulares para sanitização de strings (Regex)
import re
# Importação do módulo para decodificar saídas formatadas em JSON do FFprobe
import json
# Importação do módulo para escrita de relatórios/logs estruturados em CSV
import csv
# Importação do módulo para detectar a arquitetura e sistema operacional atual
import platform
# Importação da classe moderna Path para facilitar manipulação multiplataforma de caminhos
from pathlib import Path

# Função responsável por tentar descobrir a marca da placa de vídeo presente no PC
def get_gpu_vendor():
    # Inicia um bloco de tentativa para comandos de baixo nível no SO
    try:
        # Se o sistema operacional for identificado como Windows
        if platform.system() == "Windows":
            # Invoca o WMIC para listar o nome do controlador de vídeo e converte pra minúsculo
            output = subprocess.check_output(
                "wmic path win32_VideoController get name", shell=True, text=True
            ).lower()
        # Se for Linux ou outro derivado Unix
        else:
            # Usa o lspci em conjunto com o grep para achar a placa gráfica ativa no kernel
            output = subprocess.check_output("lspci | grep -i vga", shell=True, text=True).lower()
            
        # Se a string contiver "nvidia", retorna a marca correspondente
        if "nvidia" in output: return "nvidia"
        # Se possuir "amd" ou "radeon", conclui ser placa da AMD
        elif "amd" in output or "radeon" in output: return "amd"
        # Se possuir "intel", provavelmente é a placa integrada do processador
        elif "intel" in output: return "intel"
    # Captura caso o comando do SO não seja reconhecido ou estoure permissões
    except Exception as e:
        # Avisa que a varredura falhou
        print(f"Não foi possível detectar a GPU: {e}")
    # Caso tudo falhe, rebaixa para renderização forçada por processador (CPU)
    return "cpu"

# Função que extrai do arquivo de vídeo qual é o seu codec visual atual
def get_video_codec(file_path):
    # Inicia o bloco de extração de metadados
    try:
        # Cria a string de comando pro FFprobe retornar via JSON apenas dados do Stream V:0 (Video 0)
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-select_streams", "v:0", file_path
        ]
        # Executa sincronamente capturando o log da tela
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Transforma o log textual puro numa árvore (dicionário) JSON legível para o Python
        data = json.loads(result.stdout)
        # Verifica se o FFprobe identificou pelo menos uma faixa visual chamada 'streams'
        if "streams" in data and len(data["streams"]) > 0:
            # Retorna o nome do Codec registrado na faixa zero em letras minúsculas (ex: 'hevc', 'h264')
            return data["streams"][0].get("codec_name", "").lower()
    # Pula silenciosamente erros severos (arquivo inacessível ou criptografado)
    except Exception:
        pass
    # Se falhou, retorna vazio para não atrapalhar o fluxo
    return ""

# Função encarregada de limpar caracteres feios e problemáticos de nomes de pastas/arquivos
def sanitize_name(name):
    # Docstring documentando o Regex de limpeza
    """Remove colchetes, aspas e substitui espaços/hífens por underline."""
    # Regex varre removendo chaves, aspas simples, aspas duplas, colchetes, brackets sem deixar rastro
    name = re.sub(r'[\[\]\'\"‘’“”]', '', name)
    # Regex converte qualquer espaçamento vazio (tab, espaço) ou hifens num caractere Sublinhado (_)
    name = re.sub(r'[\s\-]+', '_', name)
    # Regex achata duplos/triplos underlines em apenas um, evitando duplo sublinhado
    name = re.sub(r'_+', '_', name)
    # Entrega a string retornando sem underscores perdidos nas laterais
    return name.strip('_')

# Função que checa o tamanho em megabytes reais ocupados em disco
def get_file_size_mb(path):
    # Inicia bloco de tentativa de medição
    try:
        # Usa função getsize nativa para pegar bytes absolutos e divide por 1024 duas vezes (KB, MB)
        return os.path.getsize(path) / (1024 * 1024)
    # Captura caso o disco caia
    except Exception:
        # Se não der pra ler, devolve peso zero seguro flutuante
        return 0.0

# Central de Processamento. Recebe arquivo, pastas raízes temporárias, metadados extras de hardware e invoca a conversão.
def process_file(file_path, input_anchor, temp_dir, gpu, quality, log_csv_path, force_cpu=False):
    # Subtrai a letra da unidade/raiz abstrata para obter o caminho complementar relativo
    rel_path = file_path.relative_to(input_anchor)
    # Roda a função de limpar caracteres ruins em todas as pastas pais da árvore para preparar o espelhamento
    clean_parts = [sanitize_name(p) for p in rel_path.parent.parts]
    # Determina o nome do arquivo mkv em si finalizado já sem caracteres ruins
    clean_filename = f"{sanitize_name(file_path.stem)}.mkv"
    
    # Validações operacionais cross-plataforma para criar a pasta base Convertidos do espelho
    if platform.system() == "Windows":
        # Se Windows, joga a pasta na própria raiz mapeada (ex: V:\Convertidos)
        base_out = input_anchor / "Convertidos"
    else:
        # Se Linux, salva no Home Directory do usuário atual que rodou o processo
        base_out = Path.home() / "Convertidos"
        
    # Combina a raiz escolhida com a árvore de diretórios subjacente recriada perfeitamente e sanitizada
    out_dir = base_out / Path(*clean_parts)
    # Força a criação proativa das pastas e subpastas caso elas ainda não existam naquele disco
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Registra e guarda o objeto do alvo final para checagem rápida de bypass (economizar horas pulando retrabalho)
    final_dest = out_dir / clean_filename
    
    # BYPASS: Avalia heurísticamente se esse arquivo em questão já existe concluído no destino
    if final_dest.exists():
        # Informa via UI e salta
        print(f"[PULANDO] Arquivo já existe no destino: {clean_filename}")
        # Abandona a função sem dor
        return
        
    # Título ilustrativo da tela 
    print(f"\n[{file_path.name}] Iniciando processamento...")
    # Guarda timer de inicialização Epoch absoluto
    start_time = time.time()
    
    # Usa o nome original provisório com prefixo explícito 'temp_' para evitar colisão na memória temporária local
    temp_original = Path(temp_dir) / f"temp_{file_path.name}"
    # Registra também o nome final que o arquivo H265 recém-renderizado herdará na pasta SSD fervente local
    temp_output = Path(temp_dir) / clean_filename
    
    # Capta quantos megabytes o arquivo cru ocupa parado na rede (usado nas estatísticas)
    old_size_mb = get_file_size_mb(file_path)
    
    # 1. Copiar para disco local (Acelera drasticamente I/O de disco e impede buffering caindo/encavalando pela rede)
    print(f"  -> Copiando da rede para temp local...")
    # Bloco tentar
    try:
        # Usa biblioteca universal shutil para puxar 1:1 copiando metadata
        shutil.copy2(file_path, temp_original)
    # Falhas
    except Exception as e:
        # Erro comum se o arquivo original foi trancado agressivamente (lock) pelo seed de um Torrent no instante exato da cópia
        print(f"  [ERRO] Falha ao copiar arquivo da rede: {e}")
        # Abandona o barco pra focar no proximo item do array
        return
    
    # 2. Comando FFmpeg
    print(f"  -> Verificando formato de vídeo...")
    # O FFprobe puxa o formato e codec de vídeo bruto que ele se encontra, H264, MPEG-2 ou afins
    codec = get_video_codec(str(temp_original))
    
    # Flag nula preparatória indicando que não achamos legenda externa de príncipio
    external_sub = None
    # Realiza varredura na pasta inteira parente do arquivo original em busca de legendas piratas avulsas (.srt ou .ass)
    for f in file_path.parent.iterdir():
        # Verifica se de fato é um arquivo listado que não seja o proprio vídeo em si rodando
        if f.is_file() and f.name != file_path.name:
            # Confere por string-match se a legenda compartilha o mesmo nome de titulo principal do anime e termina num sufixo textual
            if f.stem.startswith(file_path.stem) and f.suffix.lower() in ['.srt', '.ass']:
                # Registra o objeto referencial da legenda externa pra podermos puxá-la pro render final
                external_sub = f
                # Sai da varredura, já localizamos com sucesso
                break

    # Transforma variável numérica pra String plana (ex: "26") que a string do CLI do FFmpeg exije (CRF / CQP value)
    qual_str = str(quality)
    
    # Constrói o comando chamando binário do FFmpeg e determinando log de terminal emudecido exceto em Fatal Errors
    command = [
        "ffmpeg", "-y", "-v", "error", "-stats"
    ]
    
    # MUXING E STRIP: Se de fato existe uma legenda externa isolada achada no diretório
    if external_sub:
        print(f"  -> Legenda externa detectada: {external_sub.name}")
        # Estende o array nativo de comandos incrementando
        command.extend([
            "-i", str(temp_original),          # Puxa Vídeo e dados gerais cruamente do temp em disco NVME/SSD
            "-i", str(external_sub),           # Puxa Legenda externa apontando de fato pra própria Rede
            "-map", "0:v:0",                   # Exige apenas o vídeo principal do arquivo primario, ignorando lixos/thumbnails inseridos indevidamente
            "-map", "0:a",                     # Puxa irrestritamente todos os fluxos de Áudio (JP/EN) originais inteiros
            "-map", "1:s:0",                   # Puxa forçosamente e mapeia o stream textual index 0 (a legenda que lemos isolada)
            "-map", "0:s?",                    # Opcional, importa todas legendas originais perdidas do vídeo base, sem dar crash (sinal interrogação) se vazias
            "-map", "0:t?",                    # Opcional, importa anexos nativos ricos (como fontes TrueType do formato ASS ou tags)
            "-c:a", "copy",                    # Copia todo o áudio bruto instantaneamente e sem perda (bitstream transfer)
            "-c:s", "srt" if (file_path.suffix.lower() == '.mp4' or external_sub.suffix.lower() == '.srt') else "copy", # Converte texto pra SRT forçado caso o vídeo seja engessado MP4, senao deixa copy.
            "-c:t", "copy",                    # Attachments transferidos 1:1
            "-disposition:s", "0",               # Limpa sinalizadores forçados das originais que os Fansubbers embutiram hardcoded
            "-disposition:s:0", "default",       # A legenda externa que nós empurramos (agora ela assumiu a posição index 0) vira a Default/Padrão
            "-metadata:s:s:0", "language=por"    # Força a metadata tag "PT-BR" na legenda externa caso o nome do arquivo avulso ocultasse sua língua original
        ])
    # MUXING FLUXO 2: (Não encontrou arquivo nenhum solto no NAS) - Processa normalmente confiando apenas nas trilhas de fábrica 
    else:
        # Estende
        command.extend([
            "-i", str(temp_original),            # Puxa Video e fontes diretos do temp
            "-map", "0:v:0",                     # Mapeia main Video track estritamente
            "-map", "0:a?",                      # Mapeia Audio (interrogação segura crash)
            "-map", "0:s?",                      # Mapeia legendas 
            "-map", "0:t?",                      # Mapeia Attachments 
            "-c:a", "copy",                      # Manda Audio bit-perfect
            "-c:s", "srt" if file_path.suffix.lower() == '.mp4' else "copy",  # MP4 precisa sub SRT convertida para suportar Mux interno
            "-c:t", "copy",                      # Copy Fonts
            "-disposition:s", "0",               # Expurga defaults malvados que vieram do encoder japonês/russo original e quebram reprodutores
            "-disposition:s:m:language:por", "default" # Tenta astutamente aplicar default flag de reprodução apenas na legenda interna que por sorte venha rotulada "por/pt"
        ])
    
    # Lógica de Encoding Visuo-Mecânico. Prevenção de queima de disco e tempo.
    if codec == "hevc":
        # Se a origem nativa do NAS já se encontra incrivelmente comprimida, ele alerta
        print(f"  -> Vídeo já está em HEVC! Apenas ajustando legendas e nome...")
        # Copia frame-a-frame de imagem de forma passiva (Instantâneo) sem ferver os CUDA-cores
        command.extend(["-c:v", "copy"])
    # Caso precise converter massivamente, o motor esquenta
    else:
        # Define o nome legível no terminal do Codec atual sendo trucidado
        codec_name = codec.upper() if codec else "Desconhecido"
        print(f"  -> Codificando vídeo de {codec_name} para HEVC e configurando legenda PT...")
        
        # Seleção Dinâmica de API e Aceleração Baseada no Chipset
        if force_cpu:
            # CPU forçada pelo User (Software Encoding LibX265 - Extremamente lento, mas perfeito aos puristas)
            command.extend(["-c:v", "libx265", "-crf", qual_str, "-preset", "fast"])
        elif gpu == "nvidia":
            # API NVENC da Nvidia (Rápido, Constant Quality param)
            command.extend(["-c:v", "hevc_nvenc", "-cq", qual_str, "-preset", "p4"]) 
        elif gpu == "amd":
            # API AMF da Radeon/AMD (Rapidez, Constant Quantization param sem pre-análise VBAQ para previnir artefatos)
            command.extend(["-c:v", "hevc_amf", "-rc", "cqp", "-qp_i", qual_str, "-qp_p", qual_str, "-vbaq", "false"]) 
        elif gpu == "intel":
            # API QSV (QuickSync) dos gráficos Intel (Eficiente, Global Quality ICQ)
            command.extend(["-c:v", "hevc_qsv", "-global_quality", qual_str]) 
        else:
            # Fallback Universal. A máquina não forneceu chip e rodará na marra o padrão de segurança
            command.extend(["-c:v", "libx265", "-crf", qual_str, "-preset", "fast"])

    # Engata a string do destino final absoluto no último parâmetro da cauda do FFmpeg
    command.append(str(temp_output))
    
    # Try mestre da chamada
    try:
        # Roda o FFmpeg montado trancando a main thread. O Check=True estoura uma Exception violenta caso haja Kernel Panic ou Error!==0
        subprocess.run(command, check=True)
    # Trata crashs
    except subprocess.CalledProcessError as e:
        # Avisa que quebrou
        print(f"  [ERRO] Falha no FFmpeg: {e}")
        # Realiza cleardown higienizador na temp. Pra nao lotar eternamente e travar o disco C: da máquina hospedadora com sobras e corrupções.
        if temp_original.exists(): temp_original.unlink()
        if temp_output.exists(): temp_output.unlink()
        # Aborta silencioso sem travar o Loop pai de processamentos que o chamou
        return

    # 3. Mover de volta para rede (Fase final de I/O)
    print(f"  -> Movendo arquivo finalizado para: {final_dest}")
    # Try da subida ao Servidor
    try:
        # Corta a fita enviando a remessa pronta e perfeita 100% da temp (shutil envia byte-a-byte) de volta para o espelho UNC Remoto NAS
        shutil.move(str(temp_output), str(final_dest))
    except Exception as e:
        # Se cair a placa de rede no ato da transferência SMB/CIFS, quebra brando sem travar script pai
        print(f"  [ERRO] Falha ao mover arquivo para a rede: {e}")
    
    # 4. Limpeza mandatória local de Segurança Final
    if temp_original.exists(): temp_original.unlink()
        
    # Análise Matemática e Analítica da Tarefa do arquivo
    end_time = time.time()
    # Calcula total líquido consumido subtraindo
    elapsed = end_time - start_time
    # Divmod gera uma Tuple separando cravado em 2 variávies Min e Seg extraídas dos segundos brutos
    mins, secs = divmod(elapsed, 60)
    
    # Extrai quantos Megabytes exatos gerou o arquivo no destino remotamente
    new_size_mb = get_file_size_mb(final_dest)
    
    # Var pra Print formatada
    time_str = f"{int(mins)}m {int(secs)}s"
    # Imprime saldo final contábil
    print(f"  [CONCLUÍDO] Tempo: {time_str} | Tamanho: {old_size_mb:.1f}MB -> {new_size_mb:.1f}MB")
    
    # Fase de Gravação no Log CSV Estatístico central
    file_exists = os.path.isfile(log_csv_path)
    # Abre ou cria o log em modo de Apendice contínuo com prefixo BOM Universal para MS Excel ignorando encodings asiaticos antigos
    with open(log_csv_path, mode='a', newline='', encoding='utf-8-sig') as csvfile:
        # Inicializa componente
        writer = csv.writer(csvfile)
        # Se na varredura passada foi provado que a planilha estava oca e nunca existira antes
        if not file_exists:
            # Monta cabecalho mestre estrutural com as colunas base
            writer.writerow(['Caminho Original', 'Nome Original', 'Tamanho Antigo (MB)', 'Tempo Conversão', 'Novo Nome', 'Novo Tamanho (MB)'])
        # Grava 100% dos dados lineares obtidos num registro individual da tabela
        writer.writerow([str(file_path), file_path.name, f"{old_size_mb:.2f}", time_str, clean_filename, f"{new_size_mb:.2f}"])


# Função pai de Bootstrap principal (Orquestradora Geral da Sessão)
def main():
    # Inicia documentação descritiva do script na interface do usuário (CLI Help)
    parser = argparse.ArgumentParser(description="Processa vídeos em lote recursivamente.")
    # Flag Obrigatoria '--input'. Exige caminho montado abstrato contendo tudo (Ex: V:\\Animes.P01)
    parser.add_argument("--input", required=True, help="Pasta de origem (ex: V:\\Banksters.S01)")
    # Oferece ao usuario escolha override de onde o SSD local mais veloz está alocado pra montar temps
    parser.add_argument("--temp", default=r"E:\Traducao\TEMP", help="Pasta local temporária")
    # Qualidade param (26 pra anime é o sweet spot em H265 que detona compressão mantendo edges)
    parser.add_argument("--quality", type=int, default=26, help="Nível de qualidade (CQ/CRF)")
    # Flag recursiva boolean que expande os limites horizontais e faz o walk penetrar no fundo das subpastas
    parser.add_argument("--recursive", action="store_true", help="Varrer subpastas recursivamente (OS.Walk)")
    # Flag Boolean p/ forçar máquina virtual/docker capado a rodar na raça. 
    parser.add_argument("--cpu", action="store_true", help="Forçar a codificação via CPU (libx265)")
    # Parseia todas as strings supracitadas que injetaram
    args = parser.parse_args()

    # Valida paths localmente resolvendo possiveis symlinks virtuais e limpando barras estranhas do shell
    input_path = Path(args.input).resolve()
    temp_dir = Path(args.temp)
    # Cast variables param
    quality = args.quality
    recursive = args.recursive
    force_cpu = args.cpu
    
    # Aborta operação mestre se NAS/Server host original estiver offline para consulta (ou disco desmontado)
    if not input_path.exists():
        print(f"Erro: Pasta de origem não existe: {input_path}")
        return
        
    # Isola o Root node do path fornecido de entrada 'C:\' pra usar de ancora estática de navegação no espelhamento 
    input_anchor = Path(input_path.anchor) # e.g. "V:\"
    # Instancia onde o Relatório consolidado final irá morar. (Salva sempre na âncora/raiz com nome referenciando o batch processado)
    log_csv_path = input_anchor / f"compression_log_{input_path.name}.csv"
    
    # Assegura a integridade do disco local Temp
    temp_dir.mkdir(parents=True, exist_ok=True)
    # Detecta GPU e define string condutora
    gpu = get_gpu_vendor()
    
    # Array Vazia receptiva (Fila/Queue Array)
    files_to_process = []
    
    # Processo de Mapeamento Inicial do OS e Sistema de Ficheiros
    print("Mapeando arquivos...")
    # Condicao Específica 1: Acidentalmente (ou de propósito) o input se trata de arquivo MKV único pra converter isoladamente? 
    if input_path.is_file():
        # Extensao e formato check
        if input_path.suffix.lower() in ('.mkv', '.mp4'):
            # Apenda único video na lista do Array e prossegue engatilhando
            files_to_process.append(input_path)
        # Nao-suportado por design (Avisos MP3 etc)
        else:
            print(f"Erro: O arquivo não é um vídeo suportado (.mkv, .mp4): {input_path}")
            # Fim
            return
    # Condicao Generalizada 2: Input passado é a Root de Fato de centenas de pastas / subpastas?
    else:
        # Condicao Varredura Profunda (Flag True) 
        if recursive:
            # Walk destrinchador percorre todas as arvorezinhas e galhos de dentro pra fora do InputPath
            for root, _, files in os.walk(input_path):
                # Para todo documento textual achado em cada pasta
                for f in files:
                    # Filtro final extensões suportadas
                    if f.lower().endswith(('.mkv', '.mp4')):
                        # Apenda no array de Jobs anexando a raiz geratriz dele com nome dele
                        files_to_process.append(Path(root) / f)
        # Varredura Rasa, Reta não-recursiva (Só arquivos avulsos expostos brutalmente juntos numa pasta plana só)
        else:
            # OS Listdir simples não enxerga profundidade
            for f in os.listdir(input_path):
                # Filtra videos
                if f.lower().endswith(('.mkv', '.mp4')):
                    # Popula
                    files_to_process.append(input_path / f)
                
    # Confirmação visual pro Cliente pra ele ter noçao mental do ETA
    print(f"Encontrados {len(files_to_process)} vídeos para processar.")
    
    # Laço Iterador Mestre (Queue processor) 
    for f_path in files_to_process:
        # Envia e Orquestra individualmente a extração e log de cada video (Pausa Thread ate terminar a promisse implícita)
        process_file(f_path, input_anchor, temp_dir, gpu, quality, log_csv_path, force_cpu)
        
    # Anuncia sem alarmismo fim das transações do Lote
    print("\nProcessamento em lote finalizado!")

# Cláusula padrão boilerplate anti importação. Impede que o interpretador dispare este script isoladamente se alguem "importar" ele sem querer em scripts paralelos alheios
if __name__ == "__main__":
    # Arranca Thread principal 
    main()
