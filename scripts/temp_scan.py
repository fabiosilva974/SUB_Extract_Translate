# ==============================================================================
# Script: temp_scan.py
#
# Objetivo:
#   Script temporário para varrer a unidade V:\ em busca de arquivos de vídeo
#   e avaliar a quantidade de espaço desperdiçado por não estarem em HEVC/H.265.
#
# Lógica Principal:
#   Usa os.walk no drive, checa a terminação dos arquivos e tenta buscar
#   as tags 'hevc' ou 'x265' no nome. Se não tiver, soma o peso e lista 
#   as piores pastas no console.
#
# Dependências Externas:
#   Nenhuma
# ==============================================================================
# Importação da biblioteca nativa de Sistema Operacional (Pastas, Arquivos, Variáveis)
import os

# Define fixo a unidade de disco a ser prospectada (Disco V)
v_drive = "V:\\"
# Inicia array vazio que receberá o catálogo de todos os arquivos suspeitos achados no disco
candidates = []

# Laço mestre recursivo que esburaca toda a arvore de pastas de V:\ do topo ao fundo
for root, dirs, files in os.walk(v_drive):
    # Passa pelos arquivos da pasta da vez
    for f in files:
        # Se for um nome que termina nas extensões de vídeo padrão (Ignorando NFOs, JPGs e legendas)
        if f.lower().endswith(('.mkv', '.mp4')):
            # Monta o endereço absoluto completo ex: V:\Filmes\Avatar.mkv
            full_path = os.path.join(root, f)
            # Tenta puxar propriedades bloqueadas
            try:
                # Usa biblioteca do OS para pegar o peso real no SSD em bytes e converte p/ Megabytes (Divisão Dupla)
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
            # Em caso de pasta sistema trancada
            except Exception:
                # Pula arquivo
                continue
                
            # Força o nome original pro minúsculo para a inteligência buscar as palavras-chave
            name_lower = f.lower()
            # Avaliação (True/False) verificando se alguma das tags the-scene consta no titulo batizado
            is_hevc = any(x in name_lower for x in ['hevc', 'x265', 'h265'])
            
            # Registra tupla (dicionario) dentro do array mestre de candidatos
            candidates.append({
                'path': full_path,     # Caminho inteiro original
                'name': f,             # Nome com extensao
                'size_mb': size_mb,    # Peso matematico
                'is_hevc': is_hevc,    # Status visual
                'folder': root         # Pai organizador
            })

# Dict vazio para consolidaçao das estatisticas por pasta
folders = {}
# Despeja a lista de candidatos achados 
for c in candidates:
    # Captura nome da pasta 
    fld = c['folder']
    # Se a pasta é virgem no contador
    if fld not in folders:
        # Cadastra ela zerada para iniciar contagem
        folders[fld] = {'avc_size_mb': 0, 'files': 0, 'hevc_files': 0}
    
    # Acrescenta 1 no numero total de arquivos da pasta 
    folders[fld]['files'] += 1
    # Se ele testou positivo p/ Eficiente
    if c['is_hevc']:
        # Pontua em video bom 
        folders[fld]['hevc_files'] += 1
    # Se reprovou (AVC/H264 Velho)
    else:
        # Acumula o prejuízo matemático no pote 
        folders[fld]['avc_size_mb'] += c['size_mb']

# Gera uma lista ordenada da Pior (Maior Prejuízo) para a Melhor Pasta, usando expressao lambda
sorted_folders = sorted(folders.items(), key=lambda x: x[1]['avc_size_mb'], reverse=True)

# Imprime APENAS o top 20 para o terminal humano conseguir ler
for fld, data in sorted_folders[:20]:
    # Se efetivamente tem espaço a ganhar 
    if data['avc_size_mb'] > 0:
        # Escreve nome, Gigabytes perdidos e status da migração 
        print(f"[{fld}] - Oportunidade: {data['avc_size_mb']/1024:.2f} GB ({data['files'] - data['hevc_files']} de {data['files']} arquivos não são HEVC)")
