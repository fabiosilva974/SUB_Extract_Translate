import csv
import os
from pathlib import Path
import re

def translate_path(path_str):
    path_str = path_str.replace("\\\\192.168.0.99\\Media\\", "/mnt/Media/")
    path_str = path_str.replace("U:\\", "/mnt/Media/")
    path_str = path_str.replace("\\", "/")
    return path_str

def sanitize_title(title):
    title = re.sub(r'[\[\]\(\)\'\":!]', '', title)
    title = re.sub(r'[\s\-]+', '.', title)
    title = re.sub(r'\.+', '.', title)
    return title.strip('.')

def main():
    csv_path = "scripts/test_map.csv"
    if not os.path.exists(csv_path):
        print(f"Erro: CSV não encontrado em {csv_path}")
        return

    print("Iniciando limpeza dos originais (Lote Piloto)...")
    apagados = 0

    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            orig_path = Path(translate_path(row['Caminho_Completo_Original']))
            
            new_name = row['Novo_Nome_Padronizado']
            # Usa a mesma regra agressiva de limpeza do H265 do script original
            new_name = sanitize_title(new_name.replace(".mkv", "")) + ".mkv"
            while ".." in new_name: new_name = new_name.replace("..", ".")
            
            conv_path = orig_path.parent / new_name
            
            if conv_path.exists() and orig_path.exists():
                print(f"Apagando: {orig_path.name}")
                try:
                    orig_path.unlink()
                    apagados += 1
                except Exception as e:
                    print(f"Erro ao apagar {orig_path.name}: {e}")
            elif not orig_path.exists():
                print(f"Já apagado ou renomeado: {orig_path.name}")
            else:
                print(f"Ignorando (Convertido não achado): {orig_path.name}")

    print(f"\nLimpeza concluída! {apagados} arquivos originais apagados.")

if __name__ == '__main__':
    main()
