#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: map_drive_opportunities.py
#
# Objetivo:
#   Varrer recursivamente um disco ou pasta, calcular o tamanho de vídeos não-HEVC,
#   e exportar um relatório (CSV/TXT) classificando as pastas (séries/temporadas)
#   que possuem as maiores oportunidades de compressão.
#
# Lógica Principal:
#   Realiza o scanning no disco via os.walk. Se o vídeo NÃO tiver tags "HEVC" / "H265"
#   no nome do arquivo, ele é marcado como H264/AVC (Desperdício de espaço).
#   Consolida o tamanho total de bytes por subdiretório e gera relatórios.
#
# Dependências Externas:
#   Nenhuma
# ==============================================================================
# Módulo de sistema (Disco, arquivos)
import os
# Módulo de flags cmd (CLI)
import argparse
# Módulo exportador de planilhas Excel CSV
import csv
# Pathing universal Win/Lin
from pathlib import Path

# Main Flow Start
def main():
    # Cria o avaliador lógico
    parser = argparse.ArgumentParser(description="Mapeia oportunidades de compressão de vídeo em um diretório.")
    # Exige flag input indicando a pasta raiz
    parser.add_argument("--input", required=True, help="Diretório alvo (ex: U:\\ ou E:\\Traducao\\)")
    # Permite alterar o destino do CSV
    parser.add_argument("--output", default="mapeamento_oportunidades.csv", help="Nome do arquivo de saída (ex: map.csv ou map.txt)")
    # Lê as inputs
    args = parser.parse_args()

    # Formata a string em objeto absoluto sem symlinks
    input_dir = Path(args.input).resolve()
    # Verifica validade no HD
    if not input_dir.exists():
        # Crash seguro
        print(f"Erro: O caminho {input_dir} não existe.")
        return

    # Visual 
    print(f"Iniciando varredura em {input_dir}...")
    # Array agregadora
    candidates = []

    # Faz o scan profundo e complexo do diretório e filhos
    for root, dirs, files in os.walk(input_dir):
        # Percorre as fitas 
        for f in files:
            # Filtro ignorando lixos, fotos, zips 
            if f.lower().endswith(('.mkv', '.mp4', '.avi')):
                # Junta o caminho absoluto 
                full_path = os.path.join(root, f)
                # Tenta IO
                try:
                    # Captura megabytes matematicos 
                    size_mb = os.path.getsize(full_path) / (1024 * 1024)
                # IO Fail
                except Exception:
                    # Silencia
                    continue
                    
                # Força lower case para regex manual primitivo
                name_lower = f.lower()
                # Verifica tags que denunciam se a fita já é pequena o suficiente
                is_hevc = any(x in name_lower for x in ['hevc', 'x265', 'h265'])
                
                # Despeja as anomalias ou sucessos
                candidates.append({
                    'size_mb': size_mb, # Peso exato 
                    'is_hevc': is_hevc, # Booleano
                    'folder': root      # Pasta pai para agrupar depois
                })

    # Imprime sucesso no crawl do disco
    print(f"Total de {len(candidates)} vídeos encontrados. Processando métricas...")

    # Dict pra agrupar por pasta/temporada (Ex: Folder 1 -> 5 arquivos)
    folders = {}
    # Itera todos os arquivos achados no disco 
    for c in candidates:
        # Puxa key 
        fld = c['folder']
        # Se a pasta não existe no agregador 
        if fld not in folders:
            # Instancia o template dela vazio (Zera cronometros)
            folders[fld] = {'avc_size_mb': 0, 'total_size_mb': 0, 'files': 0, 'hevc_files': 0}
        
        # Acrescenta 1 ao numero de midias
        folders[fld]['files'] += 1
        # Acrescenta o peso 
        folders[fld]['total_size_mb'] += c['size_mb']
        # Se for eficiente 
        if c['is_hevc']:
            # Ponto pra eficiencia
            folders[fld]['hevc_files'] += 1
        # Se for ineficiente (AVC Velho)
        else:
            # Acumula o peso desperdiçado
            folders[fld]['avc_size_mb'] += c['size_mb']

    # Ordena as pastas alvo da pior para a melhor (A pior deve ser convertida primeiro pelo motor ffmpeg)
    sorted_folders = sorted(folders.items(), key=lambda x: x[1]['avc_size_mb'], reverse=True)

    # Escreve o output (CSV ou TXT ou MD) 
    out_path = Path(args.output)
    # Define se é csv 
    is_csv = out_path.suffix.lower() == '.csv'
    # Define se é MD
    is_md = out_path.suffix.lower() == '.md'
    # IO Master
    with open(out_path, mode='w', newline='', encoding='utf-8-sig') as f:
        # Modo Planilha
        if is_csv:
            # Chama pacote 
            writer = csv.writer(f)
            # Colunas
            writer.writerow(['Diretorio', 'Arquivos Total', 'Arquivos HEVC', 'Arquivos Para Comprimir', 'Tamanho Oportunidade (GB)'])
            # Itera agregador 
            for fld, data in sorted_folders:
                # Se tem pelo menos 1 lixo H264 lá dentro
                if data['avc_size_mb'] > 0:
                    # Calculo de deficit
                    to_compress = data['files'] - data['hevc_files']
                    # MB para GB
                    gb_size = data['avc_size_mb'] / 1024
                    # Grava linha 
                    writer.writerow([fld, data['files'], data['hevc_files'], to_compress, f"{gb_size:.2f}"])
        # Modo Viewer Github 
        elif is_md:
            # Calcula peso total de TODOS os arquivos podres 
            total_gb = sum(data['avc_size_mb'] for data in folders.values()) / 1024
            # Imprime header 
            f.write(f"# Relatório de Oportunidades em {input_dir}\n\n")
            f.write(f"> [!IMPORTANT]\n> 🚀 **Oportunidade Total de Ganho de Espaço: {total_gb:.2f} GB**\n\n")
            f.write("Abaixo estão as subpastas ordenadas pela maior oportunidade de compressão (tamanho desperdiçado).\n\n")
            # Lista ranking
            for fld, data in sorted_folders:
                # Se tem lixo
                if data['avc_size_mb'] > 0:
                    # Matematica 
                    to_compress = data['files'] - data['hevc_files']
                    gb_size = data['avc_size_mb'] / 1024
                    # Bloco
                    f.write(f"## 📁 `{fld}`\n")
                    f.write(f"- **Oportunidade:** **{gb_size:.2f} GB**\n")
                    f.write(f"- **Vídeos Pendentes:** {to_compress} de {data['files']} arquivos NÃO estão em HEVC.\n\n")
        # Modo legadão .TXT 
        else:
            # Escreve padrao 
            f.write(f"Relatório de Oportunidades em {input_dir}\n")
            f.write("=" * 60 + "\n\n")
            # Loop rankeado 
            for fld, data in sorted_folders:
                if data['avc_size_mb'] > 0:
                    # Matematica
                    to_compress = data['files'] - data['hevc_files']
                    gb_size = data['avc_size_mb'] / 1024
                    # Print cru 
                    f.write(f"[{fld}]\n")
                    f.write(f"  -> Oportunidade: {gb_size:.2f} GB\n")
                    f.write(f"  -> Status: {to_compress} de {data['files']} arquivos NÃO estão em HEVC.\n\n")

    # Sucesso 
    print(f"Relatório gerado com sucesso em: {out_path.resolve()}")

# Protection shell 
if __name__ == "__main__":
    main()
