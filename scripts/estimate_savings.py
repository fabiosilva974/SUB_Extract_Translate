#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: estimate_savings.py
#
# Objetivo:
#   Ler o arquivo CSV mapeado de animes e cruzar com os dados atuais do disco
#   (pasta U:\Anime-Cartoon) para checar a taxa de sucesso de compressão H.265.
#   Calcula quanto espaço foi economizado (em GB) e a média de MB ganha por arquivo,
#   gerando em seguida um novo CSV apenas com os arquivos que restaram.
#
# Lógica Principal:
#   Cruza os paths do arquivo Linux (/mnt/Media/Anime-Cartoon/) para o path
#   Windows mapeado em (U:\). Checa se o arquivo HEVC (.H265.mkv) já foi gravado
#   pelo conversor e faz o comparativo de peso usando a biblioteca os (getsize).
#
# Dependências Externas:
#   Nenhuma
# ==============================================================================
# Módulo de manipulação de planilhas
import csv
# Módulo para interação com o SO (ler propriedades e peso do disco)
import os
# Módulo para navegação abstraída de pastas, unificando barras e diretórios
from pathlib import Path

# Arquivo base inteiro criado antes da conversão
csv_path = r"E:\Traducao\planos\mapa_animes_renomeio.csv"
# Arquivo novo a ser gerado descontando o progresso finalizado
new_csv_path = r"E:\Traducao\planos\mapa_animes_renomeio_novo.csv"

# Array para enfileirar as fitas que ainda precisam de processamento FFmpeg
linhas_restantes = []
# Variavel cumulativa matematica
total_ganho_mb = 0
# Contador de vitórias
arquivos_comprimidos = 0

# UI
print("Analisando arquivos já concluídos...")

# Abertura no modo Leitura (Read) com suporte a formatação estranha do excel (BOM)
with open(csv_path, newline='', encoding='utf-8-sig') as f:
    # Chama o empacotador nativo dividindo as colunas usando Ponto-e-Vírgula
    reader = csv.DictReader(f, delimiter=';')
    
    # Roda linha a linha do CSV original
    for row in reader:
        # Pega a string gravada (normalmente no padrao UNIX do Linux)
        caminho_linux = row['Caminho_Completo_Original']
        # Faz a gambiarra de cross-platform, checando o hardcoded mount
        if caminho_linux.startswith('/mnt/Media/Anime-Cartoon/'):
            # Remove a rota do servidor linux
            caminho_relativo = caminho_linux[len('/mnt/Media/Anime-Cartoon/'):]
            # Adiciona a letra de rede local mapeada do Servidor Samba/NFS no Windows 
            caminho_windows = Path(r"U:\Anime-Cartoon") / caminho_relativo
        else:
            # Assuma Windows nativo
            caminho_windows = Path(row['Caminho_Completo_Original'])
            
        # Flutua a string, alterando virgula brasileira para ponto universal de computação
        tamanho_antigo_mb = float(row['Tamanho_MB'].replace(',', '.'))
        # Captura o texto sugerido pra ser gravado 
        novo_nome = row['Novo_Nome_Padronizado']
        
        # Junta a raiz da pasta com o nome padronizado (Ex: U:\Anime\ + Episodio01.H265.mkv)
        novo_caminho = caminho_windows.parent / novo_nome
        
        # IO Disk check: O ffmpeg já cuspiu esse H265?
        if novo_caminho.exists():
            # Captura megabytes puros e duplamente divide (byte > kbyte > mb)
            tamanho_novo_mb = os.path.getsize(novo_caminho) / (1024 * 1024)
            # Aritmética básica pra saber se inchou ou salvou espaco 
            ganho_mb = tamanho_antigo_mb - tamanho_novo_mb
            # Incrementa o pool mestre (Apenas MB, nada de GIGAS)
            total_ganho_mb += ganho_mb
            # Conta ponto 
            arquivos_comprimidos += 1
        # Se a conversão não ocorreu ainda (Pendências)
        else:
            # Empilha na montanha de pendencias que vão ser jogadas no novo arquivo 
            linhas_restantes.append(row)

# Impressoes de quebra de linha CLI
print("="*40)
# Mostra ao humano 
print(f"Arquivos concluídos (H265 encontrados): {arquivos_comprimidos}")

# Matematica segura (evitando divisao por 0 caso o array retorne nulo)
if arquivos_comprimidos > 0:
    # Rate medio basico 
    media_ganho = total_ganho_mb / arquivos_comprimidos
    # / 1024 para mostrar GIGAS
    print(f"Ganho total de espaço: {total_ganho_mb/1024:.2f} GB")
    print(f"Média de ganho por arquivo: {media_ganho:.2f} MB")
# Mensagem pessimista caso nenhuma fita tenha salvo 
else:
    print("Nenhum arquivo convertido encontrado com o novo nome H265 ainda.")
print("="*40)

# Informa local da nova base 
print(f"Gerando novo CSV ({new_csv_path}) com os {len(linhas_restantes)} arquivos restantes...")

# Cria planilha CSV (Mode = Write)
with open(new_csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
    # Instancia o esqueleto com os cabecalhos engessados da planilha original 
    writer = csv.DictWriter(f, fieldnames=['Lote_Piloto', 'Tamanho_MB', 'Nome_Original', 'Novo_Nome_Padronizado', 'Pasta_Pai', 'Caminho_Completo_Original'], delimiter=';')
    # Preenche primeira linha (Bold Excel Titles)
    writer.writeheader()
    # Despeja as milhares de linhas restantes de forma binaria super rapida
    writer.writerows(linhas_restantes)

# UI final 
print("Finalizado!")
