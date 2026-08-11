# ==============================================================================
# Script: generate_test_map.py
#
# Objetivo:
#   Gera um arquivo CSV mapeando vídeos para uma conversão piloto.
#   Identifica os 5 maiores arquivos não-HEVC de pastas específicas para
#   testar o workflow de padronização e compressão.
#
# Lógica Principal:
#   Usa guessit para padronizar os nomes de acordo com o padrão do projeto.
#   Usa ffprobe para detectar se o arquivo já é H.265/HEVC.
#   Gera test_map.csv com colunas para orquestrar a renomeação/conversão.
#
# Dependências Externas:
#   guessit, FFprobe (FFmpeg)
# ==============================================================================
# Importação da biblioteca base do OS
import os
# Importação para manipulação de arquivos de planilha
import csv
# Importação para consumir logs em formato JSON
import json
# Importação para disparar chamadas shell
import subprocess
# Importação para lidar elegantemente com paths no Windows e Linux
from pathlib import Path

# Protege contra a ausência da biblioteca na máquina do cliente
try:
    # Biblioteca de parser de metadados em nomes piratas
    from guessit import guessit
# Caso não ache
except ImportError:
    # Silencia o erro, mas algumas funções podem falhar mais tarde
    pass

# Função que descobre se o vídeo é HEVC e sua resolução
def get_video_metadata(file_path):
    # Comando FFprobe filtrando streams de vídeo apenas para JSON
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    # Tenta rodar a análise
    try:
        # Atraca o processo e puxa log
        result = subprocess.run(cmd, capture_output=True, check=True)
        # Decodifica de bytes pra str ignorando encodings com falha (caracteres japoneses no path etc)
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
    # Falhas variadas
    except Exception:
        # Falhou
        return None, False
    # Var Largura vazia
    width = None
    # Var Booleana
    is_hevc = False
    # Itera streams capturadas
    for stream in data.get("streams", []):
        # Caixa baixa do nome de codec
        codec_name = stream.get("codec_name", "").lower()
        # Isolamento do tipo visual
        if stream.get("codec_type") == "video":
            # Guarda se for a primeira trilha de vídeo
            if not width: width = stream.get("width")
            # Avalia se a flag de codec e a desejada ou nova geracao
            if codec_name in ("hevc", "h265", "x265", "av1", "vp9"): is_hevc = True
    # Retorna dimensoes e flag
    return width, is_hevc

# Limpeza pesada contra caracteres feios de torrent
def sanitize_title(title):
    # Substitui aspas por _ 
    title = title.replace("'", "_").replace("’", "_")
    # Substitui espaços por pontos (estética scene)
    title = title.replace(" ", ".")
    # Limpa reincidências de falhas no loop
    while ".." in title: title = title.replace("..", ".")
    # Retorna polido
    return title

# Montador do Novo Nome Perfeito
def generate_new_name(original_path, width):
    # Joga nome original cru pra inteligencia
    guess = guessit(original_path.name)
    # Extrai tag título
    title = guess.get('title', original_path.stem)
    # Extrai tag título alternativo
    alt_title = guess.get('alternative_title')
    # Se tiver alternativo, funde os dois
    if alt_title: title = f"{title}.{alt_title}"
    # Puxa ano de lançamento
    year = guess.get('year', '')
    # Puxa temporada 
    season = guess.get('season')
    # Puxa episodio numero
    episode = guess.get('episode')
    # Puxa titulo do episodio (Animes tem)
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
    # Se for tipo de midia avulsa sem temporada
    if not season and not episode and episode_title:
        # Gruda no titulo raiz
        title = f"{title}.{episode_title}"
        # Reseta 
        episode_title = None
    # Roda nossa sanitização manual
    title = sanitize_title(title)
    
    # Puxa resolução lida pelo guessit 
    resolution = guess.get('screen_size')
    # Se guessit falhou na string
    if not resolution:
        # Usa matemática provinda do metadado real do FFprobe width
        w = int(width) if width else 0
        # Regras dimensionais
        if w >= 3800: resolution = "2160p"
        elif w >= 1900: resolution = "1080p"
        elif w >= 1200: resolution = "720p"
        else: resolution = "480p"
    
    # Inicia array de fragmentos 
    parts = [title]
    # Apenda se não nulo
    if year: parts.append(str(year))
    # Avalia Season 
    if season is not None:
        # As vezes a biblioteca retorna array em duplos episodios
        if isinstance(season, list): season = season[0]
        # Padroniza S01
        s_str = f"S{int(season):02d}"
        # Mescla com Ep se houver
        if episode is not None:
            # Array check
            if isinstance(episode, list): episode = episode[0]
            # Adiciona E01 (Ficando S01E01)
            s_str += f"E{int(episode):02d}"
        # Gruda
        parts.append(s_str)
    # Animes de episodio apenas longo sem season
    elif episode is not None:
        # Valida lista
        if isinstance(episode, list): episode = episode[0]
        # Apenda apenas Episodio 
        parts.append(f"E{int(episode):02d}")
    # Titulos nominais de episódio ("The Begining")
    if episode_title:
        # Lista 
        if isinstance(episode_title, list): episode_title = episode_title[0]
        # Apenda 
        parts.append(sanitize_title(episode_title))
    # Resolução (1080p)
    if resolution and resolution != "Unknown": parts.append(str(resolution))
    # Tag Forçada
    parts.append("H265")
    # Une array inteira por "." e junta a extensao MKV
    return ".".join(parts) + original_path.suffix

# Array hardcoded das raizes que devem ser prospectadas (Nas do lab)
paths = [
    # Anime A Certain
    r"U:\Anime-Cartoon\A Certain",
    # Anime Legend
    r"U:\Anime-Cartoon\LegendoftheGalacticHeroes-GingaEiyuuDensetsu",
    # Anime Haikyuu
    r"U:\Anime-Cartoon\Haikyuu!!"
]

# Array placeholder p/ os dicts a serem jogados no Excel
data = []

# Status visual
print("Mapeando arquivos e metadados...")
# Loop de pastas alvo
for p in paths:
    # Obj instanciado
    d = Path(p)
    # Pula pasta fantasma
    if not d.exists(): continue
    # Zera cache local de fitas
    files = []
    # Roda OS walk pra furar subpastas
    for root, _, fs in os.walk(d):
        # Lista as fitas na branch
        for f in fs:
            # Se a midia bate no regex simplorio
            if f.lower().endswith(('.mkv', '.mp4', '.avi')):
                # Junta o caminho absoluto
                fp = Path(root) / f
                # Tenta IO
                try:
                    # Captura peso absoluto da midia
                    size = os.path.getsize(fp)
                    # Guarda a Tupla
                    files.append((fp, size))
                # Falhas
                except:
                    # Passa panos
                    pass
    # Organiza a array da pasta decrescentemente (Fitas mais gordas primeiro, pois queremos testar compressao agressiva nelas)
    files.sort(key=lambda x: x[1], reverse=True)
    # Lote de apenas N por diretório
    count = 0
    # Percorre Tupla Rankeada
    for fp, size in files:
        # Limitador batch piloto = 5 arquivos estritamente
        if count >= 5:
            # Para e vai pra proxima pasta
            break
        # Probe na fita 
        width, is_hevc = get_video_metadata(fp)
        # Se infelizmente já estava H.265 (Fita já convertida no passado)
        if is_hevc:
            # Ignora e pula iteracao sem contar 1 
            continue
        # Gera o nome mágico idealizado do futuro
        new_name = generate_new_name(fp, width)
        # Matemátic MB
        size_mb = size / (1024 * 1024)
        # Preenche a listona que vai pro csv excel
        data.append({
            'old_path': str(fp),         # Absoluto velho
            'new_name': new_name,        # Nome novo limpo
            'old_name': fp.name,         # Nome velho sujo
            'size_mb': size_mb,          # Peso local
            'folder': fp.parent.name     # Nome da Season/Pasta base
        })
        # Registra sucesso
        count += 1

# Determina path de desova do banco de dados na raiz E
out_path = Path(r"E:\Traducao\scripts\test_map.csv")
# Abre o documento gravador com BOM para Excel BR não bugar acentos 
with open(out_path, mode='w', newline='', encoding='utf-8-sig') as f:
    # Seta limitador ";" BR
    writer = csv.writer(f, delimiter=';')
    # Cabeçalhos do planner
    writer.writerow(['Lote_Piloto', 'Tamanho_MB', 'Nome_Original', 'Novo_Nome_Padronizado', 'Pasta_Pai', 'Caminho_Completo_Original'])
    # Despeja as chaves
    for d in data:
        # Troca ponto decimal padrao USA pela virgula de moeda PT-BR (1.00 -> 1,00)
        size_str = f"{d['size_mb']:.2f}".replace('.', ',')
        # Escreve a Row no Excel 
        writer.writerow(["SIM", size_str, d['old_name'], d['new_name'], d['folder'], d['old_path']])

# Termo 
print(f"CSV de mapeamento gerado com {len(data)} arquivos: {out_path}")
