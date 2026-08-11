#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: find_conversion_anomalies.py
#
# Objetivo:
#   Rastrear o disco rígido (ou partição de rede montada) buscando por lixo e
#   ressalvas gerados pela interrupção súbita do motor do FFmpeg (part files).
#   Busca também detectar arquivos H.264 antigos que não foram apagados porque a
#   etapa de limpeza (QA/Fase 3) não foi autorizada.
#
# Lógica Principal:
#   Escaneia tudo recursivamente achando as sub-extensões .part e .lock, armazenando-as.
#   Depois itera sob a lista matriz de intenções (CSV) garantindo que, se houver o 
#   arquivo Original E TAMBÉM houver a versão nova batizada de H265, é caracterizado
#   como lixo Duplicado, preenchendo um relatório em texto TXT legível.
#
# Dependências Externas:
#   Nenhuma
# ==============================================================================
# Módulo de planilhas nativo do Python 
import csv
# Módulo de SO e Arquivos 
import os
# Abstrator universal de pastas Win/UNIX 
from pathlib import Path

# Aponta pro livro de registros completo do banco da biblioteca de Animes 
csv_path = r"E:\Traducao\planos\mapa_animes_renomeio.csv"
# Caminho físico de prospecção alvo 
target_dir = Path(r"U:\Anime-Cartoon")
# Endereço de Output do Bloco de Notas gerado 
output_report = r"E:\Traducao\planos\relatorio_anomalias.txt"

# Vazio: Registros de pastas onde o Velho e Novo coexistem desnecessariamente
duplicados = []
# Vazio: Restos mortais e crasheados do FFmpeg / NVENC
arquivos_part = []
# Vazio: Sistema travado por acesso paralelo e rede 
arquivos_lock = []
# Vazio: Lista onde apenas o Velho existe (Orfãos intocados)
arquivos_orfaos_originais = []

# Terminal start 
print(f"Iniciando varredura em {target_dir}...")

# 1. Varredura profunda no disco rígido buscando os fantasmas
for root, dirs, files in os.walk(target_dir):
    # Passa pelos arquivos da pasta
    for f in files:
        # Se na extensao encontrar PART 
        if f.lower().endswith('.part'):
            # Acopla raiz + nome do arquivo corrompido 
            arquivos_part.append(os.path.join(root, f))
        # Se na extensao achar lock
        elif f.lower().endswith('.lock'):
            # Grava pra limpeza futura
            arquivos_lock.append(os.path.join(root, f))

# 2. Verificação logica do CSV cruzada 
print("Verificando status dos arquivos mapeados no CSV...")
# Controle de quebra 
try:
    # Abertura modo Read
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        # Define os tokens de separacao 
        reader = csv.DictReader(f, delimiter=';')
        
        # Lê 
        for row in reader:
            # Tratamento de caminho bruto pro cross platform
            caminho_linux = row['Caminho_Completo_Original']
            # Se vier da planilha feita no linux server 
            if caminho_linux.startswith('/mnt/Media/Anime-Cartoon/'):
                # Corta a rota do Linux (Trunca a string a partir do index 27)
                caminho_relativo = caminho_linux[len('/mnt/Media/Anime-Cartoon/'):]
                # Insere o mount point padrao the windows home server (U:)
                caminho_original = target_dir / caminho_relativo
            # Se nao usar padroes the windows puros
            else:
                caminho_original = Path(row['Caminho_Completo_Original'])
                
            # Saca Nome 
            novo_nome = row['Novo_Nome_Padronizado']
            # Aponta nome H265 alvo  
            caminho_novo = caminho_original.parent / novo_nome
            
            # Condição lógica: Se os dois arquivos moram na mesma pasta, ocupando disco (1.8gb + 800mb por ex)
            if caminho_original.exists() and caminho_novo.exists():
                # Gera matriz dupla no array de vitimas a deletar (tupla contendo velho e novo)
                duplicados.append((str(caminho_original), str(caminho_novo)))
            # Condição: Se só tem o velho original lá parado (H264/AVC)
            elif caminho_original.exists() and not caminho_novo.exists():
                # O original está lá e a conversão não terminou ou falhou ou sequer começou 
                arquivos_orfaos_originais.append(str(caminho_original))
# Em caso the falha the sintaxe CSV 
except Exception as e:
    # Cuspir pra tela
    print(f"Erro ao ler o CSV: {e}")

# Gera o Relatório Visual na UI Preta 
print("="*50)
print(f"Anomalias Encontradas:")
# Conta os arrays de problemas 
print(f" - Arquivos Temporários Incompletos (.part): {len(arquivos_part)}")
print(f" - Arquivos de Trava (.lock): {len(arquivos_lock)}")
print(f" - Arquivos Duplicados (Original + H265): {len(duplicados)}")
print("="*50)

# Informa ao usuario 
print(f"Gerando relatório detalhado em: {output_report}")

# Prepara arquivo de texto gigante cru pra listagem (Ideal pra mandar pro ChatGPT limpar)
with open(output_report, 'w', encoding='utf-8') as f:
    # Header format 
    f.write("RELATÓRIO DE ANOMALIAS E ARQUIVOS PERDIDOS\n")
    f.write("="*50 + "\n\n")
    
    # Bloco dos corrompidos 
    f.write(f"1. ARQUIVOS TEMPORÁRIOS INCOMPLETOS (.part) - {len(arquivos_part)} encontrados\n")
    f.write("Geralmente conversões que foram interrompidas ou travaram no meio.\n")
    # For
    for part in arquivos_part:
        # Item bullet list
        f.write(f" - {part}\n")
    # Espaçamento de pular linha final 
    f.write("\n")
    
    # Bloco dos travados 
    f.write(f"2. ARQUIVOS DE TRAVA (.lock) - {len(arquivos_lock)} encontrados\n")
    for lock in arquivos_lock:
        f.write(f" - {lock}\n")
    f.write("\n")
    
    # Bloco the desperdicio de Disco Rigido 
    f.write(f"3. ARQUIVOS DUPLICADOS (Fase 1 Não-Deletada) - {len(duplicados)} encontrados\n")
    f.write("Você possui a versão original e a versão H265 ocupando espaço ao mesmo tempo na pasta.\n")
    # Usa a matrix tupla de cruzamento
    for orig, novo in duplicados:
        # Mostra o Inimigo Original Velho
        f.write(f" - ORIGINAL: {orig}\n")
        # Mostra o Amigo HEVC eficiente
        f.write(f"   CONVERTIDO: {novo}\n\n")

# Despedida the shell script 
print("Varredura de anomalias concluída! Você pode consultar o relatório para fazer a limpeza.")
