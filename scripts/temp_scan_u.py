# ==============================================================================
# Script: temp_scan_u.py
#
# Objetivo:
#   Script temporário para varrer a unidade U:\ em busca de arquivos de vídeo
#   e avaliar a quantidade de espaço desperdiçado por não estarem em HEVC/H.265.
#
# Lógica Principal:
#   Mesma lógica do temp_scan.py mas englobando '.avi' e apontando para a U:\.
#   Lista o top 15 de oportunidades de conversão no terminal.
#
# Dependências Externas:
#   Nenhuma
# ==============================================================================
# Importação da biblioteca nativa do OS
import os

# Root Drive prospectado
u_drive = "U:\\"
# Vazio alocador
candidates = []

# Verifica se o HD plugado ou Network Drive Mapeado existe hoje
if not os.path.exists(u_drive):
    # Ui Error
    print(f"Drive {u_drive} não encontrado.")
    # Exit Crash
    exit(1)

# Crawling 
for root, dirs, files in os.walk(u_drive):
    # Files array
    for f in files:
        # Se extensao compativel
        if f.lower().endswith(('.mkv', '.mp4', '.avi')):
            # Combina 
            full_path = os.path.join(root, f)
            # Try 
            try:
                # Matematica megabytes
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
            # Fail
            except Exception:
                # Pula iter
                continue
                
            # Regex base 
            name_lower = f.lower()
            # Any check
            is_hevc = any(x in name_lower for x in ['hevc', 'x265', 'h265'])
            
            # Grava tupla 
            candidates.append({
                'size_mb': size_mb, # Megas 
                'is_hevc': is_hevc, # Bom ruim
                'folder': root      # Group by key 
            })

# Dict 
folders = {}
# Agrega loop
for c in candidates:
    # Key 
    fld = c['folder']
    # Se not 
    if fld not in folders:
        # Inicia
        folders[fld] = {'avc_size_mb': 0, 'total_size_mb': 0, 'files': 0, 'hevc_files': 0}
    
    # Soma geral quantitativo
    folders[fld]['files'] += 1
    # Soma peso geral 
    folders[fld]['total_size_mb'] += c['size_mb']
    
    # Check H265
    if c['is_hevc']:
        # Incrementa 
        folders[fld]['hevc_files'] += 1
    # Check H264
    else:
        # Soma falhas quantitativas 
        folders[fld]['avc_size_mb'] += c['size_mb']

# Rankeador lambda the piores pastas (Piores pesos de videos velhos)
sorted_folders = sorted(folders.items(), key=lambda x: x[1]['avc_size_mb'], reverse=True)

# Ui Total 
print(f"Total de arquivos encontrados: {len(candidates)}")
# Ui limit top 15 
for fld, data in sorted_folders[:15]:
    # Se pesa real
    if data['avc_size_mb'] > 0:
        # Print gigas (GB = MB/1024) e status 
        print(f"[{fld}] - Oportunidade: {data['avc_size_mb']/1024:.2f} GB ({data['files'] - data['hevc_files']} de {data['files']} arquivos não são HEVC)")
