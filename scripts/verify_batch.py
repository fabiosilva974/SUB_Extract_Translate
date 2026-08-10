import csv
import sys
import subprocess
from pathlib import Path

def verify_file(orig, conv):
    cmd = ["python", r"E:\Traducao\scripts\compare_media_tracks.py", orig, conv]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stdout

def main():
    csv_path = r"E:\Traducao\scripts\test_map.csv"
    print("Verificando os primeiros 10 arquivos concluídos...")
    
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f, delimiter=';')
        count = 0
        success_count = 0
        error_count = 0
        
        for row in reader:
            orig = Path(row['Caminho_Completo_Original'])
            new_name = row['Novo_Nome_Padronizado'].replace('!', '')
            while '..' in new_name: new_name = new_name.replace('..', '.')
            conv = orig.parent / new_name
            
            if not conv.exists():
                print(f"[{count+1}/10] IGNORADO: Arquivo convertido não encontrado: {conv.name}")
                count += 1
                continue
                
            print(f"[{count+1}/10] Verificando: {orig.name} ... ", end="")
            sys.stdout.flush()
            
            is_ok, out = verify_file(str(orig), str(conv))
            if is_ok:
                print("OK (Trilhas Identicas)")
                success_count += 1
            else:
                print("ERRO")
                print("Detalhes do erro:")
                print(out)
                error_count += 1
                
            count += 1
            
        print("\n" + "="*30)
        print("--- RESUMO DA VERIFICAÇÃO ---")
        print(f"Total testados: {success_count + error_count}")
        print(f"Preservados perfeitamente: {success_count}")
        print(f"Com divergências (FALHA): {error_count}")
        print("="*30)

if __name__ == '__main__':
    main()
