#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: map_drive_opportunities.py
#
# Objetivo:
#   Varrer recursivamente um disco ou pasta, calcular o tamanho de vídeos não-HEVC,
#   e exportar um relatório (CSV/TXT) classificando as pastas (séries/temporadas)
#   que possuem as maiores oportunidades de compressão.
# ==============================================================================
import os
import argparse
import csv
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Mapeia oportunidades de compressão de vídeo em um diretório.")
    parser.add_argument("--input", required=True, help="Diretório alvo (ex: U:\\ ou E:\\Traducao\\)")
    parser.add_argument("--output", default="mapeamento_oportunidades.csv", help="Nome do arquivo de saída (ex: map.csv ou map.txt)")
    args = parser.parse_args()

    input_dir = Path(args.input).resolve()
    if not input_dir.exists():
        print(f"Erro: O caminho {input_dir} não existe.")
        return

    print(f"Iniciando varredura em {input_dir}...")
    candidates = []

    # Faz o scan do diretório
    for root, dirs, files in os.walk(input_dir):
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

    print(f"Total de {len(candidates)} vídeos encontrados. Processando métricas...")

    # Agrupa por pasta
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

    # Ordena pelo tamanho potencial (AVC) decrescente
    sorted_folders = sorted(folders.items(), key=lambda x: x[1]['avc_size_mb'], reverse=True)

    # Escreve o output (CSV ou TXT)
    out_path = Path(args.output)
    is_csv = out_path.suffix.lower() == '.csv'
    is_md = out_path.suffix.lower() == '.md'
    with open(out_path, mode='w', newline='', encoding='utf-8-sig') as f:
        if is_csv:
            writer = csv.writer(f)
            writer.writerow(['Diretorio', 'Arquivos Total', 'Arquivos HEVC', 'Arquivos Para Comprimir', 'Tamanho Oportunidade (GB)'])
            for fld, data in sorted_folders:
                if data['avc_size_mb'] > 0:
                    to_compress = data['files'] - data['hevc_files']
                    gb_size = data['avc_size_mb'] / 1024
                    writer.writerow([fld, data['files'], data['hevc_files'], to_compress, f"{gb_size:.2f}"])
        elif is_md:
            f.write(f"# Relatório de Oportunidades em {input_dir}\n\n")
            f.write("Abaixo estão as subpastas ordenadas pela maior oportunidade de compressão (tamanho desperdiçado).\n\n")
            for fld, data in sorted_folders:
                if data['avc_size_mb'] > 0:
                    to_compress = data['files'] - data['hevc_files']
                    gb_size = data['avc_size_mb'] / 1024
                    f.write(f"## 📁 `{fld}`\n")
                    f.write(f"- **Oportunidade:** **{gb_size:.2f} GB**\n")
                    f.write(f"- **Vídeos Pendentes:** {to_compress} de {data['files']} arquivos NÃO estão em HEVC.\n\n")
        else:
            f.write(f"Relatório de Oportunidades em {input_dir}\n")
            f.write("=" * 60 + "\n\n")
            for fld, data in sorted_folders:
                if data['avc_size_mb'] > 0:
                    to_compress = data['files'] - data['hevc_files']
                    gb_size = data['avc_size_mb'] / 1024
                    f.write(f"[{fld}]\n")
                    f.write(f"  -> Oportunidade: {gb_size:.2f} GB\n")
                    f.write(f"  -> Status: {to_compress} de {data['files']} arquivos NÃO estão em HEVC.\n\n")

    print(f"Relatório gerado com sucesso em: {out_path.resolve()}")

if __name__ == "__main__":
    main()
