# ==============================================================================
# Script: planner_filmes.py
#
# Objetivo:
#   Mapear e padronizar metadados de filmes/séries que necessitam de re-encoding.
#   Identifica se as mídias já são H265/HEVC e gera um CSV formatado para planilhas.
#
# Lógica Principal:
#   Varre a pasta apontada, usa FFProbe para checar os codecs físicos e extrair dimensão.
#   Depois, utiliza o módulo `guessit` para formatar e limpar os títulos de filmes 
#   seguindo o padrão The Scene. Exporta relatórios.
#
# Dependências Externas:
#   FFmpeg (ffprobe), guessit (pip)
# ==============================================================================
# OS
import os
# Planilha
import csv
# Parser string de sistema
import json
# Disparo commandos cmd bat
import subprocess
# Parser cli flags
import argparse
# Paths multiplataforma
from pathlib import Path

# Protecao Try Catch para bibliotecas dificeis 
try:
    # A biblioteca que adivinha infos por nome de torresmos
    from guessit import guessit
# Nao achou 
except ImportError:
    # Aviso explicito de erro 
    print("ERRO: Biblioteca 'guessit' não encontrada.")
    print("Por favor, instale executando: pip install guessit")
    exit(1)

# Descobre peso e dimensoes 
def get_video_metadata(file_path):
    """
    Usa o ffprobe para descobrir a largura do vídeo e se já é HEVC.
    """
    # Monta matriz sem arrays de espaco 
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    # Try io
    try:
        # Roda trancando cpu 
        result = subprocess.run(cmd, capture_output=True, check=True)
        # Extrai logs ignorando bugs de codificacao
        stdout_str = result.stdout.decode('utf-8', errors='replace')
        # Cria variaveis dinâmicas
        data = json.loads(stdout_str)
    # Se der fatal
    except Exception:
        # Cai vazio 
        return None, False

    # Zera cache resoluçao
    width = None
    # Zera eficiencia 
    is_hevc = False
    
    # Percorre camadas
    for stream in data.get("streams", []):
        # Valida caixa
        codec_name = stream.get("codec_name", "").lower()
        # So visual
        if stream.get("codec_type") == "video":
            # Guarda se o motor falhou em trazer (nao regrava em cima de stream secundario como miniatura)
            if not width:
                width = stream.get("width")
            # Detecta nomeclaturas variantes de H.265, H265, HEVC ou nova geração
            if codec_name in ("hevc", "h265", "x265", "av1", "vp9"):
                is_hevc = True
                
    # Return Tupla
    return width, is_hevc

# Nomeador de resolucao a partir de valor quebrado
def get_resolution_name(width):
    # Null check
    if not width: return "Unknown"
    # Força numero int
    width = int(width)
    # Matemática de proporcao p/ aproximar (4K)
    if width >= 3800: return "2160p"
    # 1080p ou 1920 
    if width >= 1900: return "1080p"
    # 720p 
    if width >= 1200: return "720p"
    # DVD Velhos
    return "480p"

# Higienizacao anti Torrent Lixo
def sanitize_title(title):
    # Substituir aspas e apóstrofos por underline
    title = title.replace("'", "_").replace("’", "_")
    # Substituir espaços por pontos (Formato The Scene)
    title = title.replace(" ", ".")
    # Limpar múltiplos pontos remanescentes (ex: Kiki..s -> Kiki.s)
    while ".." in title:
        title = title.replace("..", ".")
    # Return string polida
    return title

# Funcao Mestre geradora da Padronizacao Oficial 
def generate_new_name(original_path, width):
    """
    Usa o guessit para adivinhar Título, Ano, Resolução, Temporada e Episódio e monta no padrão desejado.
    """
    # Isola .mkv
    filename = original_path.name
    # Passa no motor
    guess = guessit(filename)
    
    # Saca o root
    title = guess.get('title', original_path.stem)
    
    # Saca sub root
    alt_title = guess.get('alternative_title')
    # Mergea
    if alt_title:
        title = f"{title}.{alt_title}"
        
    # Puxa anos
    year = guess.get('year', '')
    # Puxa season S01
    season = guess.get('season')
    # Puxa Episodio E01
    episode = guess.get('episode')
    # Puxa Ep Name 
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
    
    # Se não houver temporada nem episódio, mas houver titulo de episódio (comum em filmes avulsos de anime longos)
    if not season and not episode and episode_title:
        # Cola
        title = f"{title}.{episode_title}"
        # Destroi sub para nao apendar denovo
        episode_title = None 
        
    # Higieniza regex
    title = sanitize_title(title)
    
    # Captura string the 1080p da IA 
    resolution = guess.get('screen_size')
    # IA Falhou miseravelmente
    if not resolution:
        # Usa fisica hard matematica feita por nós
        resolution = get_resolution_name(width)
    
    # Array de blocos construtores the string
    parts = [title]
    # Se ter 
    if year:
        # Gruda
        parts.append(str(year))
        
    # Lógica customizada para Séries e Animes (S01E01 ou apenas E01 solto)
    if season is not None:
        # Limpa array bugs do pacote
        if isinstance(season, list): season = season[0]
        # Aplica S zero padded (S02)
        s_str = f"S{int(season):02d}"
        # Se tem ep
        if episode is not None:
            # Lista chk 
            if isinstance(episode, list): episode = episode[0]
            # S02E03
            s_str += f"E{int(episode):02d}"
        # Acopla a parte 
        parts.append(s_str)
    # Só eps isolados sem season 
    elif episode is not None:
        # List bug chk
        if isinstance(episode, list): episode = episode[0]
        # Acopla
        parts.append(f"E{int(episode):02d}")
        
    # Se existir subtitulo
    if episode_title:
        # Limpa array 
        if isinstance(episode_title, list): episode_title = episode_title[0]
        # Higieniza pontos e limpa acentos se rolar 
        parts.append(sanitize_title(episode_title))
        
    # Se teve resolucao achada 
    if resolution and resolution != "Unknown":
        # Bota no array 
        parts.append(str(resolution))
        
    # Assinatura de projeto oficial 
    parts.append("H265")
    
    # Montador The Scene Universal: title.S01E02.name.1080p.H265.mkv
    new_name = ".".join(parts) + original_path.suffix
    return new_name

# Start
def main():
    # Args obj 
    parser = argparse.ArgumentParser(description="Mapeia e padroniza nomes de filmes")
    # Path
    parser.add_argument("--input", required=True, help="Diretório de filmes (Ex: U:\\filmes ou /mnt/Media/filmes)")
    # Out 
    parser.add_argument("--output", default="mapa_filmes_renomeio.csv", help="Caminho do CSV de saída")
    args = parser.parse_args()

    # Formata input para uso hard 
    input_dir = Path(args.input).resolve()
    # Verifica HD OS 
    if not input_dir.exists():
        print(f"Diretório não encontrado: {input_dir}")
        return

    # Listona de alvos mkv
    movies = []
    # Print UI 
    print(f"Mapeando árvore de arquivos em: {input_dir}")
    # Roda tree recursiva
    for root, _, files in os.walk(input_dir):
        # Valida
        for f in files:
            # Regex lixo limit
            if f.lower().endswith(('.mkv', '.mp4', '.avi')):
                # Empilha 
                movies.append(Path(root) / f)

    # Info quantitativa 
    print(f"Encontrados {len(movies)} arquivos de vídeo. Iniciando análise FFprobe e Guessit...")
    
    # Obj data pra tabela 
    data = []
    
    # Loop UI visual de execucao
    for i, path in enumerate(movies):
        # Informa [1/900]
        print(f"Analisando [{i+1}/{len(movies)}]: {path.name}")
        # Dispara pesadao
        width, is_hevc = get_video_metadata(path)
        
        # Só queremos processar/mapear o que não é HEVC para fins de poupar disco
        if is_hevc:
            # Pula 
            continue
            
        # Puxa Peso 
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
        # Falhas
        except Exception:
            # Vazio 
            size_mb = 0
            
        # Roda GuessIt pesado
        new_name = generate_new_name(path, width)
        # Caminho gerado 
        new_path = path.parent / new_name
        
        # Consolida celulas
        data.append({
            'old_path': str(path),
            'new_path': str(new_path),
            'old_name': path.name,
            'new_name': new_name,
            'size_mb': size_mb,
            'folder': path.parent.name
        })
        
    # Ordenar por tamanho do arquivo absoluto real (para pegar o maior ganho de MB)
    data.sort(key=lambda x: x['size_mb'], reverse=True)
    
    # Limites hardcode de testes piloto 
    targets = []
    # Flag var
    hp_added = False
    
    # Seleciona forçadamente 1 iteracao do Harry Potter p/ laboratório
    for d in data:
        # Se contem harry (filme velho pesado)
        if "harry" in str(d['old_path']).lower():
            # Array piloto append 
            targets.append(d)
            # Acusa true 
            hp_added = True
            # Sai pra nao botar a saga inteira
            break
            
    # Seleciona os Top 20 pesos brutos do disco remanescente para o Lote 1 Piloto
    count = 0
    # Roda array inteira novamente
    for d in data:
        # Se cota lotou 
        if count >= 20:
            break
        # Se não tá repetido com o Harry la de cima 
        if d not in targets:
            # Bota no alvo final 
            targets.append(d)
            # Incrementa indexer 
            count += 1
            
    # Path gravador 
    out_path = Path(args.output).resolve()
    # Abre via UTF Sig pra Excel pt-BR 
    with open(out_path, mode='w', newline='', encoding='utf-8-sig') as f:
        # Obj 
        writer = csv.writer(f, delimiter=';')
        # Print Headers 
        writer.writerow(['Lote_Piloto', 'Tamanho_MB', 'Nome_Original', 'Novo_Nome_Padronizado', 'Pasta_Pai', 'Caminho_Completo_Original'])
        
        # Despeja as milhares de tuplas no excel
        for d in data:
            # Avalia se a flag de piloto bate 
            is_target = "SIM" if d in targets else "NAO"
            # Decimal pt-br stringifier
            size_str = f"{d['size_mb']:.2f}".replace('.', ',')
            # Grava no HD 
            writer.writerow([is_target, size_str, d['old_name'], d['new_name'], d['folder'], d['old_path']])
            
    # Success visual p/ user saber
    print(f"\nMapeamento concluído com sucesso!")
    print(f"CSV de Planejamento salvo em: {out_path}")
    # Acusa cota
    print(f"Lote de Teste Cirúrgico isolou {len(targets)} arquivos para a Fase 1.")

# Bloqueio de Import 
if __name__ == '__main__':
    main()
