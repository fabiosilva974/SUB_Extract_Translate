# ==============================================================================
# Script: verify_batch.py
#
# Objetivo:
#   Script de validação que lê um CSV de lote piloto e usa uma ferramenta externa 
#   para checar se os arquivos de vídeo convertidos e originais mantiveram todas
#   as trilhas e qualidades desejadas idênticas.
#
# Lógica Principal:
#   Abre o CSV (test_map.csv), isola o caminho da versão original e projeta qual
#   foi o nome gerado pelo batch de encoding. Em seguida, roda o script
#   compare_media_tracks.py e contabiliza os acertos e falhas.
#
# Dependências Externas:
#   compare_media_tracks.py, Python 3
# ==============================================================================
# Módulo para parser de planilhas CSV 
import csv
# Módulo de sistema para acesso ao standard out e err
import sys
# Módulo para rodar scripts paralelos e capturar o terminal
import subprocess
# Pacote Pathlib para lidar com caminhos independente do OS 
from pathlib import Path

# Orquestrador de invocação remota 
def verify_file(orig, conv):
    # Constrói comando CLI via Python isolado para comparar tracks de mídia 
    cmd = ["python", r"E:\Traducao\scripts\compare_media_tracks.py", orig, conv]
    # Bloco try IO 
    try:
        # Dispara shell trancando o pipeline 
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        # Devolve sucesso e relatorio do log 
        return True, result.stdout
    # Em caso de crash ou reprovação na análise 
    except subprocess.CalledProcessError as e:
        # Devolve fracasso e o motivo 
        return False, e.stdout

# Escopo mestre 
def main():
    # Caminho gravado hardcoded do CSV piloto gerado anteriormente 
    csv_path = r"E:\Traducao\scripts\test_map.csv"
    # User info 
    print("Verificando os primeiros 10 arquivos concluídos...")
    
    # Abre excel
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        # Tabela dit 
        reader = csv.DictReader(f, delimiter=';')
        # Zera total
        count = 0
        # Zera sucessos
        success_count = 0
        # Zera falhas 
        error_count = 0
        
        # Le linhas 
        for row in reader:
            # Saca absolut route
            orig = Path(row['Caminho_Completo_Original'])
            # Saca e trata bugs de exclamacao
            new_name = row['Novo_Nome_Padronizado'].replace('!', '')
            # Saca e trata bugs de pontos multiplos do The Scene 
            while '..' in new_name: new_name = new_name.replace('..', '.')
            # Monta novo endereco
            conv = orig.parent / new_name
            
            # Se não converteu esse arquivo ainda 
            if not conv.exists():
                # Reporta pular e somar cota pra sair logo dos top 10 
                print(f"[{count+1}/10] IGNORADO: Arquivo convertido não encontrado: {conv.name}")
                count += 1
                continue
                
            # Mostra na UI sem pular linha de cara 
            print(f"[{count+1}/10] Verificando: {orig.name} ... ", end="")
            # Empurra o buffer pro terminal no Windows 
            sys.stdout.flush()
            
            # Executa orquestrador chamando modulo 2 
            is_ok, out = verify_file(str(orig), str(conv))
            # Teste logico da integridade
            if is_ok:
                # Positivo
                print("OK (Trilhas Identicas)")
                # Somatoria
                success_count += 1
            # Se sumiu alguma trilha ou legendas (Erro fatal de batch)
            else:
                # Acusa falha 
                print("ERRO")
                print("Detalhes do erro:")
                # Despeja logs tecnicos do ffprobe nativo
                print(out)
                # Soma erro 
                error_count += 1
                
            # Incrementa i 
            count += 1
            
        # Linha separadora UI visual
        print("\n" + "="*30)
        # Assinatura
        print("--- RESUMO DA VERIFICAÇÃO ---")
        # Soma global final report
        print(f"Total testados: {success_count + error_count}")
        # OK final report
        print(f"Preservados perfeitamente: {success_count}")
        # Failures report 
        print(f"Com divergências (FALHA): {error_count}")
        # Fim 
        print("="*30)

# Isolamento global python scope
if __name__ == '__main__':
    main()
