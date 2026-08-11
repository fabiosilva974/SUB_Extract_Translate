# ==============================================================================
# Script: batch_process_linux.py
#
# Objetivo:
#   Processar em lote vídeos a partir de uma lista CSV ou arquivo único,
#   convertendo-os nativamente para H.265 usando hardware NVIDIA (NVENC) no Linux.
#
# Lógica Principal:
#   Extrai metadados, formata e higieniza nomes de arquivos. Tenta conversão
#   por hardware NVIDIA; descarta os arquivos se ficarem maiores que o original.
#
# Dependências Externas:
#   guessit (requer instalação via pip)
#   FFmpeg e FFprobe (devem estar instalados e no PATH do sistema)
# ==============================================================================
# Importação do módulo de interações com o sistema operacional
import os
# Importação do módulo para funções e variáveis do sistema (ex: sair do script)
import sys
# Importação do módulo para trabalhar com tempo e delays
import time
# Importação do módulo para parsear dados no formato JSON
import json
# Importação do módulo para manipulação de arquivos (ex: mover, copiar)
import shutil
# Importação do módulo para execução de comandos externos no terminal
import subprocess
# Importação do módulo para parsear argumentos de linha de comando
import argparse
# Importação da classe Path para lidar com caminhos de forma orientada a objetos
from pathlib import Path

# Bloco try-except para tentar importar a biblioteca 'guessit'
try:
    # Importa guessit, que extrai dados úteis de nomes de arquivos
    from guessit import guessit
# Captura o erro caso não esteja instalada
except ImportError:
    # Mostra mensagem de erro
    print("ERRO: Biblioteca 'guessit' não encontrada. Rode: pip install guessit")
    # Encerra o script
    exit(1)

# Função para extrair metadados do vídeo via FFprobe
def get_video_metadata(file_path):
    # Monta a string do comando FFprobe formatado para JSON
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    # Bloco try
    try:
        # Executa o subprocesso, travando até terminar e capturando a saída
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Parseia o JSON recebido da saída (stdout)
        data = json.loads(result.stdout)
    # Se falhar
    except Exception:
        # Retorna valores nulos informando falha
        return None, False
    # Inicializa a largura como None
    width = None
    # Inicializa a flag de codec HEVC como Falsa
    is_hevc = False
    # Itera pelas faixas (streams) encontradas no JSON
    for stream in data.get("streams", []):
        # Lê o nome do codec de forma segura (minúsculo)
        codec = stream.get("codec_name", "").lower()
        # Se for uma faixa de vídeo
        if stream.get("codec_type") == "video":
            # Extrai a largura da primeira faixa de vídeo encontrada
            if not width: width = stream.get("width")
            # Verifica se o codec bate com as nomenclaturas conhecidas do HEVC/H.265 ou os modernos AV1/VP9
            if codec in ("hevc", "h265", "x265", "av1", "vp9"): is_hevc = True
    # Retorna largura e status do codec
    return width, is_hevc

# Função para higienizar o título do vídeo
def sanitize_title(title):
    # Substitui aspas e aspas estilizadas por sublinhados, e espaços por pontos
    title = title.replace("'", "_").replace("’", "_").replace(" ", ".")
    # Enquanto houver duplo ponto, substitui por um ponto só
    while ".." in title: title = title.replace("..", ".")
    # Retorna o título higienizado
    return title

# Função para padronizar o nome da resolução baseada na largura (pixels)
def get_resolution_name(width):
    # Converte para int
    w = int(width) if width else 0
    # Retorna as strings baseadas em limiares
    if w >= 3800: return "2160p"
    elif w >= 1900: return "1080p"
    elif w >= 1200: return "720p"
    else: return "480p"

# Função que formata o novo nome usando 'guessit'
def generate_new_name(original_path, width):
    # Analisa o nome do arquivo original com guessit
    guess = guessit(original_path.name)
    # Tenta puxar o título; se falhar, usa o nome do arquivo raiz
    title = guess.get('title', original_path.stem)
    
    # Extrai o título alternativo se existir
    alt_title = guess.get('alternative_title')
    # Se existir
    if alt_title:
        # Concatena o principal com o alternativo
        title = f"{title}.{alt_title}"
        
    # Extrai metadados adicionais
    year = guess.get('year', '')
    season = guess.get('season')
    episode = guess.get('episode')
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
    
    # Se for anime ou algo sem season/episode, mas tiver título do ep
    if not season and not episode and episode_title:
        # Mescla o título
        title = f"{title}.{episode_title}"
        # Zera a variavel pra não inserir duas vezes
        episode_title = None
        
    # Aplica higienização geral no título
    title = sanitize_title(title)
    
    # Tenta obter a resolução
    resolution = guess.get('screen_size')
    # Se não detectar via texto
    if not resolution:
        # Calcula matematicamente usando a largura lida do arquivo real
        resolution = get_resolution_name(width)
    
    # Lista de pedaços que formarão o nome
    parts = [title]
    # Se houver ano
    if year:
        # Adiciona à lista
        parts.append(str(year))
        
    # Lida com a formatação das Temporadas e Episódios (S00E00)
    if season is not None:
        # Pega a primeira ocorrência
        if isinstance(season, list): season = season[0]
        # Formata S
        s_str = f"S{int(season):02d}"
        if episode is not None:
            # Pega primeira ocorrência
            if isinstance(episode, list): episode = episode[0]
            # Formata E
            s_str += f"E{int(episode):02d}"
        # Adiciona partes
        parts.append(s_str)
    # Se tiver apenas episódio sem temporada (ex: Animes soltos)
    elif episode is not None:
        if isinstance(episode, list): episode = episode[0]
        # Formata
        parts.append(f"E{int(episode):02d}")
        
    # Lida com títulos do episódio
    if episode_title:
        if isinstance(episode_title, list): episode_title = episode_title[0]
        # Adiciona
        parts.append(sanitize_title(episode_title))
        
    # Adiciona resolução
    if resolution and resolution != "Unknown":
        parts.append(str(resolution))
        
    # Etiqueta H.265 final
    parts.append("H265")
    
    # Retorna unindo com pontos e adicionando a extensão original
    return ".".join(parts) + original_path.suffix

# Função para comandar a conversão nativa
def encode_video(input_path, output_path, quality=26):
    # Array de parâmetros do FFmpeg focados em Linux NVIDIA
    cmd = [
        "ffmpeg", "-y",                # Sobrescreve
        "-hwaccel", "cuda",            # Aceleração em CUDA (NVIDIA)
        "-i", str(input_path),         # Input file
        "-map", "0",                   # Copia todos os fluxos
        "-c:v", "hevc_nvenc",          # Codec da placa de video (H.265)
        "-preset", "p7",               # Preset de maxima qualidade nvenc
        "-tune", "hq",                 # Tuning de High Quality
        "-rc", "vbr",                  # Variabel bitrate
        "-cq", str(quality),           # Constant Quality
        "-qmin", str(quality),         # Quantizer mínimo
        "-qmax", str(quality),         # Quantizer máximo
        "-c:a", "copy",                # Copia áudio
        "-c:s", "copy",                # Copia legenda
        "-f", "matroska",              # Saída em container MKV
        str(output_path)               # Caminho final
    ]
    
    # Chama o FFmpeg via pipe para lermos as linhas em tempo real
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    # Prepara lista de logs
    log_output = []
    # Itera linha a linha do log cuspidor do FFmpeg
    for line in process.stdout:
        # Armazena histórico
        log_output.append(line)
        # Se a linha referenciar frame ou tempo
        if "frame=" in line or "time=" in line:
            # Imprime apagando a linha anterior na tela com \r
            print(f"\r{line.strip()}", end="")
    # Aguarda encerramento
    process.wait()
    # Pula uma linha
    print()
    # Se encerrou com erro
    if process.returncode != 0:
        # Mostra bloco de debug
        print("\n=== LOG DE ERRO DO FFMPEG ===")
        # Puxa ultimas 15 linhas
        print("".join(log_output[-15:]))
        print("=============================\n")
    # Retorna Verdadeiro se Sucesso (0), Falso se falha
    return process.returncode == 0

# Função mestre orquestradora
def process_file(file_path, temp_dir, delete_original=False):
    # Valida se arquivo existe
    if not file_path.exists():
        # Informa erro
        print(f"Erro: Arquivo não existe {file_path}")
        # Encerra iteracao
        return False
        
    # Extrai dados do probe
    width, is_hevc = get_video_metadata(file_path)
    # Bypass
    if is_hevc:
        print(f"O arquivo {file_path.name} já é HEVC. Pulando.")
        return True
        
    # Gera novo nome da fita
    new_name = generate_new_name(file_path, width)
    # Define alvo final
    final_dest = file_path.parent / new_name
    
    # Bypass 2
    if final_dest.exists():
        print(f"O destino já existe: {final_dest.name}. Pulando.")
        return True
        
    # Título do processamento
    print(f"\n[{file_path.name}] Iniciando processamento...")
    print(f"  -> Nome final será: {new_name}")
    
    # Nome no disco temporário
    encoded_temp = file_path.parent / (new_name + ".part")
    
    # Tempo de início
    start_time = time.time()
    # Inicia ffmpeg
    print("  -> Lendo do NAS e convertendo para HEVC (NVENC) diretamente na rede...")
    # Executa função pesada
    success = encode_video(file_path, encoded_temp)
    # Mede decorrido
    elapsed = time.time() - start_time
    
    # Trata catástrofe
    if not success or not encoded_temp.exists():
        print("  [ERRO] A conversão falhou!")
        # Limpa arquivo fantasma
        if encoded_temp.exists(): encoded_temp.unlink()
        return False
        
    # Captura MBs das fitas real x virtual
    orig_size = file_path.stat().st_size / (1024*1024)
    new_size = encoded_temp.stat().st_size / (1024*1024)
    
    # Sistema Anti-Inchaço
    if new_size >= orig_size:
        print("  -> [ANTI-INCHAÇO] O arquivo H265 ficou MAIOR que o original H264!")
        print("  -> Descartando a conversão para economizar espaço e mantendo o original intacto.")
        # Lixeira
        encoded_temp.unlink()
        # Matématica de horas perdidas
        mins, secs = divmod(elapsed, 60)
        # Loga desperdício
        print(f"  [DESCARTADO] Tempo desperdiçado: {int(mins)}m {int(secs)}s | Tamanho: {orig_size:.1f}MB -> {new_size:.1f}MB")
        return True

    # Sucesso, batiza permanentemente
    print("  -> Finalizando arquivo convertido...")
    # Retira sufixo ".part"
    encoded_temp.rename(final_dest)
    
    # Avalia ordem de execução
    if delete_original:
        # Avisa deleção
        print("  -> Excluindo arquivo original no NAS...")
        # Lixeira do raiz
        file_path.unlink()
    else:
        # QA Bypass
        print("  -> Mantendo arquivo original no NAS (Fase 1 - QA).")
        
    # Finaliza timer
    mins, secs = divmod(elapsed, 60)
    # Log de vitória
    print(f"  [CONCLUÍDO] Tempo: {int(mins)}m {int(secs)}s | Tamanho: {orig_size:.1f}MB -> {new_size:.1f}MB")
    return True

# Função inicial Main
def main():
    # Helper parser
    parser = argparse.ArgumentParser(description="Conversor Nativo Linux (In-Place)")
    # Argumento input isolado
    parser.add_argument("--input", help="Arquivo de vídeo único para processar")
    # Argumento csv
    parser.add_argument("--csv", help="Caminho para o mapa_filmes_renomeio.csv gerado pelo planner")
    # Flag ALL
    parser.add_argument("--all", action="store_true", help="Processar todos os arquivos do CSV (ignora a flag de Lote Piloto)")
    # Path local
    parser.add_argument("--temp", default="/home/conversor/TEMP", help="Diretório temporário local")
    # Limpeza ativada
    parser.add_argument("--delete", action="store_true", help="Deletar o original após sucesso (Fase 3)")
    # Parseia
    args = parser.parse_args()
    
    # Processa path real
    temp_dir = Path(args.temp).resolve()
    # Força criação da temp local
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Fluxograma Single-File
    if args.input:
        # Resolve Input
        input_path = Path(args.input).resolve()
        # Valida ficheiro
        if input_path.is_file():
            # Inicia rotina isolada
            process_file(input_path, temp_dir, args.delete)
        else:
            # Rejeita pasta
            print("Para --input, passe o caminho exato do arquivo .mkv")
    
    # Fluxograma Mass-File
    elif args.csv:
        # Resolve Path do CSV
        csv_path = Path(args.csv).resolve()
        # Valida existencia
        if not csv_path.exists():
            print(f"Erro: CSV não encontrado em {csv_path}")
            return
            
        # Puxa biblio local pra CSV
        import csv as csv_lib
        # Fila vazia
        to_process = []
        # Tenta abrir lendo ignorando encoding BOM nativo do MS DOS/Excel
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            # Mapeia colunas
            reader = csv_lib.DictReader(f, delimiter=';')
            # Itera em dados
            for row in reader:
                # Regra de Lote
                if args.all or row.get('Lote_Piloto') == 'SIM':
                    # Apenda
                    to_process.append(row['Caminho_Completo_Original'])
                    
        # Define nomenclatura printada
        desc = "toda a biblioteca de filmes" if args.all else "o Lote Piloto"
        # Printa somatorio total
        print(f"Encontrados {len(to_process)} vídeos para {desc}.")
        # Laco Final
        for path_str in to_process:
            # Universal Path Translator (Windows -> Linux)
            # Substitui caminho rede nativo pro Mount-point da WSL/Linux
            path_str = path_str.replace("\\\\192.168.0.99\\Media\\", "/mnt/Media/")
            # Substitui possivel letra de driver mapeada Z:
            path_str = path_str.replace("U:\\", "/mnt/") # Caso use driver mapeado
            # Limpa barras invertidas para barras UNIX
            path_str = path_str.replace("\\", "/")
            
            # Instancia
            file_path = Path(path_str)
            # Chama Orquestradora
            process_file(file_path, temp_dir, args.delete)
            
        # Imprime termo
        print(f"\nProcessamento concluído para {desc}!")
    # Sem parametros
    else:
        # Ajuda automatica
        parser.print_help()

# Boilerplate default python anti-import loop
if __name__ == "__main__":
    main()
