#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: translate_ass_google.py
#
# Objetivo:
#   Traduzir blocos de diálogos em arquivos de legenda do formato ASS
#   preservando toda a estrutura, estilo e metadados originais do arquivo.
#
# Lógica Principal:
#   O script lê as linhas do arquivo, identifica as marcações "Dialogue:",
#   extrai o campo de texto bruto, envia lotes de 30 linhas para a API do 
#   Google Translate, e depois re-insere o texto traduzido na linha original.
#
# Dependências Externas:
#   deep-translator
# ==============================================================================
# Importa módulos necessários para manipulação de sistema, argumentos, busca de arquivos e tradução
import os
import sys
import argparse
import glob
from pathlib import Path
from deep_translator import GoogleTranslator

# ── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
# Define a quantidade de linhas de diálogo enviadas por vez ao tradutor
BATCH_SIZE = 30
# Define o idioma de destino padrão como português
TARGET_LANG = "pt"

# Função que realiza a tradução de uma lista de textos suportando múltiplas tentativas
def translate_batch_with_retry(lines: list[str], source_lang: str = "auto", max_retries: int = 3) -> tuple[list[str], bool]:
    import time
    for attempt in range(max_retries):
        try:
            translator = GoogleTranslator(source=source_lang, target=TARGET_LANG)
            results = translator.translate_batch(lines)
            if results and any(r and "Error 500" in r for r in results):
                raise Exception("A API retornou Erro 500 como texto (limite atingido).")
            return results, True
        except Exception as e:
            print(f"  [Aviso] Falha na tradução (tentativa {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep((attempt + 1) * 3)
    print("  [ERRO CRÍTICO] Lote falhou após todas as tentativas. As linhas originais foram mantidas.")
    return lines, False

# Função principal de processamento do arquivo ASS
def translate_ass_file(file_path: str, source_lang: str = "auto", output_path: str = None):
    # Lê todas as linhas do arquivo original preservando o encoding
    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()

    # Listas para rastrear quais linhas são diálogos e qual o texto de cada uma
    dialogue_indices = []
    texts_to_translate = []

    # Itera sobre as linhas do arquivo para encontrar as marcações de diálogo
    for i, line in enumerate(lines):
        # Linhas de diálogo no formato ASS começam com "Dialogue:"
        if line.startswith("Dialogue:"):
            # O formato ASS separa campos por vírgula. O texto é sempre o 10º campo (após a 9ª vírgula)
            parts = line.split(',', 9)
            if len(parts) > 9:
                # Armazena o índice da linha no arquivo original
                dialogue_indices.append(i)
                # Armazena apenas o texto (removendo a quebra de linha final)
                texts_to_translate.append(parts[9].strip())

    total = len(texts_to_translate)
    # Se não houver diálogos no arquivo, encerra o processamento dele
    if total == 0:
        print(f"  [aviso] Nenhum diálogo encontrado em {file_path}")
        return

    # Realiza a tradução dos textos coletados em blocos (batches)
    translated_texts = []
    failed_batches = 0
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({int(end/total*100)}%)…")
        
        batch = texts_to_translate[start:end]
        trans_lines, success = translate_batch_with_retry(batch, source_lang)
        if not success:
            failed_batches += 1
            
        translated_texts.extend(trans_lines)

    if failed_batches > 0:
        print(f"\n  [ALERTA DE INTEGRIDADE] Ocorreram falhas em {failed_batches} lote(s) devido a limites da API.")
        raise RuntimeError("Tradução incompleta. Abortando para evitar geração de arquivo misto.")
        
    print("\n  [SUCESSO] Checagem de integridade concluída. Tradução 100% finalizada.")

    # Substitui os textos originais pelos traduzidos nas linhas correspondentes
    for idx, translated_text in zip(dialogue_indices, translated_texts):
        # Divide a linha original novamente para preservar os campos de tempo e estilo
        parts = lines[idx].split(',', 9)
        # Remonta a linha: prefixo (campos 0-8) + vírgula + texto traduzido + quebra de linha
        lines[idx] = ",".join(parts[:9]) + "," + translated_text + "\n"

    # Define o caminho de saída (usa o informado ou gera um automático .pt.ass)
    out = output_path or Path(file_path).with_suffix(".pt.ass")
    # Grava o novo arquivo ASS com a mesma estrutura original mas textos em português
    with open(out, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n[SUCESSO] Tradução concluída: {out}")

# Ponto de entrada do script via linha de comando
def main():
    # Configura o parser de argumentos
    parser = argparse.ArgumentParser(description="Tradutor independente de arquivos ASS mantendo estilos originais.")
    # Aceita um ou mais arquivos ou padrões (ex: *.ass)
    parser.add_argument("ass", nargs='+', help="Arquivo(s) .ass ou padrão (ex: *.ass)")
    # Idioma de origem configurável
    parser.add_argument("--source-lang", default="auto", help="Idioma de origem (ex: en, ja, es)")
    # Caminho de saída opcional
    parser.add_argument("--output", default=None, help="Arquivo de saída (opcional)")
    args = parser.parse_args()

    # Expande os wildcards (necessário para compatibilidade no Windows)
    ass_files = []
    for pattern in args.ass:
        matches = glob.glob(pattern)
        if matches:
            ass_files.extend(matches)
        else:
            ass_files.append(pattern)

    # Processa cada arquivo da lista sequencialmente
    for file_path in ass_files:
        print(f"\n{'='*60}\n Traduzindo ASS: {file_path}\n{'='*60}")
        
        # Verifica existência do arquivo
        if not Path(file_path).exists():
            print(f"[ERRO] Arquivo não encontrado: {file_path}")
            continue

        # Tenta realizar o ciclo de tradução
        try:
            translate_ass_file(file_path, source_lang=args.source_lang, output_path=args.output)
        except Exception as e:
            print(f"[ERRO CRÍTICO] Falha ao processar {file_path}: {e}")

# Execução padrão do Python
if __name__ == "__main__":
    main()
