import os

u_drive = "U:\\"
candidates = []

if not os.path.exists(u_drive):
    print(f"Drive {u_drive} não encontrado.")
    exit(1)

for root, dirs, files in os.walk(u_drive):
    for f in files:
        if f.lower().endswith(('.mkv', '.mp4', '.avi')):
            full_path = os.path.join(root, f)
            try:
                size_mb = os.path.getsize(full_path) / (1024 * 1024)
            except Exception:
                continue
                
            name_lower = f.lower()
            is_hevc = any(x in name_lower for x in ['hevc', 'x265', 'h265'])
            
            candidates.append({
                'size_mb': size_mb,
                'is_hevc': is_hevc,
                'folder': root
            })

folders = {}
for c in candidates:
    fld = c['folder']
    if fld not in folders:
        folders[fld] = {'avc_size_mb': 0, 'total_size_mb': 0, 'files': 0, 'hevc_files': 0}
    folders[fld]['files'] += 1
    folders[fld]['total_size_mb'] += c['size_mb']
    if c['is_hevc']:
        folders[fld]['hevc_files'] += 1
    else:
        folders[fld]['avc_size_mb'] += c['size_mb']

sorted_folders = sorted(folders.items(), key=lambda x: x[1]['avc_size_mb'], reverse=True)

print(f"Total de arquivos encontrados: {len(candidates)}")
for fld, data in sorted_folders[:15]:
    if data['avc_size_mb'] > 0:
        print(f"[{fld}] - Oportunidade: {data['avc_size_mb']/1024:.2f} GB ({data['files'] - data['hevc_files']} de {data['files']} arquivos não são HEVC)")
