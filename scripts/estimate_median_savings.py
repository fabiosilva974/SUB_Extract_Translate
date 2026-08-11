#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: estimate_median_savings.py
#
# Objetivo:
#   Ler o arquivo CSV mapeado de animes e os dados atuais do disco para
#   calcular a **mediana percentual** de redução de tamanho, que é uma 
#   métrica muito mais realista que a média bruta em MB, visto que arquivos
#   menores economizam menos MB mas podem ter a mesma % de compressão.
# ==============================================================================
import csv
import os
import statistics
from pathlib import Path

csv_path = r"E:\Traducao\planos\mapa_animes_renomeio.csv"
target_dir = Path(r"U:\Anime-Cartoon")

arquivos_comprimidos = 0
tamanho_total_antigo = 0
tamanho_total_novo = 0
porcentagens_ganho = []

tamanho_pendente_total = 0
arquivos_pendentes = 0

print("Lendo arquivos concluídos e analisando % de ganho de cada um...")

with open(csv_path, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    
    for row in reader:
        caminho_linux = row['Caminho_Completo_Original']
        if caminho_linux.startswith('/mnt/Media/Anime-Cartoon/'):
            caminho_relativo = caminho_linux[len('/mnt/Media/Anime-Cartoon/'):]
            caminho_windows = target_dir / caminho_relativo
        else:
            caminho_windows = Path(row['Caminho_Completo_Original'])
            
        tamanho_antigo_mb = float(row['Tamanho_MB'].replace(',', '.'))
        novo_nome = row['Novo_Nome_Padronizado']
        caminho_novo = caminho_windows.parent / novo_nome
        
        # Verifica se o arquivo H265 existe
        if caminho_novo.exists():
            tamanho_novo_mb = os.path.getsize(caminho_novo) / (1024 * 1024)
            ganho_mb = tamanho_antigo_mb - tamanho_novo_mb
            
            # Anti-inchaço (se ficou maior, o ganho é zero ou ignoramos? O script Linux deleta e mantém o original)
            if tamanho_novo_mb >= tamanho_antigo_mb:
                continue # Foi descartado pelo anti-inchaço
                
            porcentagem = ganho_mb / tamanho_antigo_mb
            porcentagens_ganho.append(porcentagem)
            
            tamanho_total_antigo += tamanho_antigo_mb
            tamanho_total_novo += tamanho_novo_mb
            arquivos_comprimidos += 1
        else:
            tamanho_pendente_total += tamanho_antigo_mb
            arquivos_pendentes += 1

print("="*50)
print(f"Arquivos H265 analisados: {arquivos_comprimidos}")

if arquivos_comprimidos > 0:
    mediana_pct = statistics.median(porcentagens_ganho) * 100
    media_pct = statistics.mean(porcentagens_ganho) * 100
    
    print(f"Média de compressão: {media_pct:.2f}% de redução por arquivo")
    print(f"MEDIANA de compressão: {mediana_pct:.2f}% de redução por arquivo (Mais preciso!)")
    print("-" * 50)
    print(f"Arquivos ainda pendentes: {arquivos_pendentes}")
    print(f"Peso total pendente estimado (H264): {tamanho_pendente_total/1024:.2f} GB")
    
    estimativa_ganho_futuro = (tamanho_pendente_total * (mediana_pct / 100)) / 1024
    estimativa_tamanho_futuro = (tamanho_pendente_total * (1 - (mediana_pct / 100))) / 1024
    
    print("-" * 50)
    print(f"PROJEÇÃO FINAL USANDO A MEDIANA ({mediana_pct:.2f}%):")
    print(f" -> Espaço extra a ser salvo: ~{estimativa_ganho_futuro:.2f} GB")
    print(f" -> Peso final estimado da fila: ~{estimativa_tamanho_futuro:.2f} GB")
else:
    print("Nenhum arquivo convertido encontrado com o novo nome H265 ainda.")
print("="*50)
