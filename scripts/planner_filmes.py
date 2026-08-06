import os
import csv
import json
import subprocess
import argparse
from pathlib import Path

try:
    from guessit import guessit
except ImportError:
    print("ERRO: Biblioteca 'guessit' não encontrada.")
    print("Por favor, instale executando: pip install guessit")
    exit(1)

def get_video_metadata(file_path):
    """
    Usa o ffprobe para descobrir a largura do vídeo e se já é HEVC.
    """
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
    except Exception:
        return None, False

    width = None
    is_hevc = False
    
    for stream in data.get("streams", []):
        codec_name = stream.get("codec_name", "").lower()
        if stream.get("codec_type") == "video":
            if not width:
                width = stream.get("width")
            if codec_name in ("hevc", "h265", "x265"):
                is_hevc = True
                
    return width, is_hevc

def get_resolution_name(width):
    if not width: return "Unknown"
    width = int(width)
    if width >= 3800: return "2160p"
    if width >= 1900: return "1080p"
    if width >= 1200: return "720p"
    return "480p"

def sanitize_title(title):
    # Substituir aspas e apóstrofos por underline
    title = title.replace("'", "_").replace("’", "_")
    # Substituir espaços por pontos
    title = title.replace(" ", ".")
    # Limpar múltiplos pontos (ex: Kiki..s -> Kiki.s)
    while ".." in title:
        title = title.replace("..", ".")
    return title

def generate_new_name(original_path, width):
    """
    Usa o guessit para adivinhar Título, Ano e Resolução e monta no padrão desejado.
    """
    filename = original_path.name
    guess = guessit(filename)
    
    title = guess.get('title', original_path.stem)
    title = sanitize_title(title)
    
    year = guess.get('year', '')
    
    resolution = guess.get('screen_size')
    if not resolution:
        resolution = get_resolution_name(width)
    
    # Monta a estrutura Nome.Ano.Resolucao.H265.mkv
    parts = [title]
    if year:
        parts.append(str(year))
    if resolution and resolution != "Unknown":
        parts.append(str(resolution))
        
    parts.append("H265")
    
    new_name = ".".join(parts) + original_path.suffix
    return new_name

def main():
    parser = argparse.ArgumentParser(description="Mapeia e padroniza nomes de filmes")
    parser.add_argument("--input", required=True, help="Diretório de filmes (Ex: U:\\filmes ou /mnt/Media/filmes)")
    parser.add_argument("--output", default="mapa_filmes_renomeio.csv", help="Caminho do CSV de saída")
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    if not input_dir.exists():
        print(f"Diretório não encontrado: {input_dir}")
        return

    movies = []
    print(f"Mapeando árvore de arquivos em: {input_dir}")
    for root, _, files in os.walk(input_dir):
        for f in files:
            if f.lower().endswith(('.mkv', '.mp4', '.avi')):
                movies.append(Path(root) / f)

    print(f"Encontrados {len(movies)} arquivos de vídeo. Iniciando análise FFprobe e Guessit...")
    
    data = []
    
    for i, path in enumerate(movies):
        print(f"Analisando [{i+1}/{len(movies)}]: {path.name}")
        width, is_hevc = get_video_metadata(path)
        
        # Só queremos processar/mapear o que não é HEVC
        if is_hevc:
            continue
            
        try:
            size_mb = os.path.getsize(path) / (1024 * 1024)
        except Exception:
            size_mb = 0
            
        new_name = generate_new_name(path, width)
        new_path = path.parent / new_name
        
        data.append({
            'old_path': str(path),
            'new_path': str(new_path),
            'old_name': path.name,
            'new_name': new_name,
            'size_mb': size_mb,
            'folder': path.parent.name
        })
        
    # Ordenar por tamanho do arquivo (para pegar o maior ganho)
    data.sort(key=lambda x: x['size_mb'], reverse=True)
    
    targets = []
    hp_added = False
    
    # Seleciona 1 do Harry Potter
    for d in data:
        if "harry" in str(d['old_path']).lower():
            targets.append(d)
            hp_added = True
            break
            
    # Seleciona os Top 20
    count = 0
    for d in data:
        if count >= 20:
            break
        if d not in targets:
            targets.append(d)
            count += 1
            
    out_path = Path(args.output).resolve()
    with open(out_path, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f, delimiter=';')
        writer.writerow(['Lote_Piloto', 'Tamanho_MB', 'Nome_Original', 'Novo_Nome_Padronizado', 'Pasta_Pai', 'Caminho_Completo_Original'])
        
        for d in data:
            is_target = "SIM" if d in targets else "NAO"
            size_str = f"{d['size_mb']:.2f}".replace('.', ',')
            writer.writerow([is_target, size_str, d['old_name'], d['new_name'], d['folder'], d['old_path']])
            
    print(f"\nMapeamento concluído com sucesso!")
    print(f"CSV de Planejamento salvo em: {out_path}")
    print(f"Lote de Teste Cirúrgico isolou {len(targets)} arquivos para a Fase 1.")

if __name__ == '__main__':
    main()
