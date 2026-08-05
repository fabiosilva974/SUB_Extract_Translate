#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# Script: translate_srt_google.py
#
# Objetivo:
#   Processa arquivos de legenda no formato SRT, identifica os blocos de texto
#   e os envia em lotes para tradução via Google Translate (API não oficial).
#
# Lógica Principal:
#   O arquivo é lido e analisado por Expressão Regular (Regex) que divide
#   cada bloco em índice, timestamps e texto. O texto é isolado, processado 
#   pela biblioteca deep-translator em lotes (batch) e, por fim, o arquivo 
#   SRT é reconstruído e gravado com o sufixo '.pt.srt'.
#
# Dependências Externas:
#   deep-translator
# ==============================================================================
# Importa o módulo para interações com o sistema operacional (caminhos, pastas)
import os
# Importa o módulo para expressões regulares (usado para identificar blocos SRT)
import re
# Importa o módulo para interações com o interpretador Python (parâmetros de sistema)
import sys
# Importa o módulo para criar interfaces de linha de comando robustas
import argparse
# Importa o módulo para expansão de curingas/wildcards (ex: *.srt no Windows)
import glob
# Importa a classe Path para manipulação moderna e multiplataforma de caminhos
from pathlib import Path
# Importa a classe principal de tradução do Google da biblioteca deep-translator
from deep_translator import GoogleTranslator

# ── CONFIGURAÇÃO ──────────────────────────────────────────────────────────────
# Define quantos blocos de legenda serão enviados por vez para o Google
BATCH_SIZE = 30

# Expressão regular para identificar e separar os componentes de um bloco SRT padrão
ENTRY_RE = re.compile(
    r"(\d+)\r?\n"                          # Captura o índice (número da legenda)
    r"([\d:,]+ --> [\d:,]+)\r?\n"          # Captura o intervalo de tempo (timecode)
    r"([\s\S]*?)(?=\n\n|\Z)",              # Captura o texto do diálogo até o fim do bloco
    re.MULTILINE,                          # Habilita o modo multilinhas para o regex
)

# Função que converte o texto bruto de um arquivo SRT em uma lista de dicionários
def parse_srt(text: str) -> list[dict]:
    # Inicializa a lista que guardará os objetos de legenda
    entries = []
    # Itera sobre todas as ocorrências encontradas pelo regex no texto original
    for m in ENTRY_RE.finditer(text.strip()):
        # Adiciona um dicionário com os dados limpos de cada bloco à lista
        entries.append({
            "index":    m.group(1),          # O número sequencial da legenda
            "timecode": m.group(2),          # O tempo de entrada e saída
            "text":     m.group(3).strip(),  # O conteúdo textual limpo
        })
    # Retorna a lista completa de blocos processados
    return entries

# Função que reconstrói a estrutura do arquivo SRT a partir dos dados traduzidos
def build_srt(entries: list[dict]) -> str:
    # Inicializa a lista de blocos formatados em string
    blocks = []
    # Itera sobre cada entrada traduzida
    for e in entries:
        # Monta a string no padrão SRT: índice, timecode e texto
        blocks.append(f"{e['index']}\n{e['timecode']}\n{e['text']}\n")
    # Une todos os blocos usando uma quebra de linha como separador
    return "\n".join(blocks)

# Função que realiza a tradução de uma lista de textos de uma só vez
def translate_batch(lines: list[str], source_lang: str = "auto", target_lang: str = "pt") -> list[str]:
    # Tenta executar a operação de tradução
    try:
        # Instancia o tradutor configurando origem e o destino padrão
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        # Envia a lista de linhas para o tradutor e aguarda o retorno
        return translator.translate_batch(lines)
    # Em caso de falha (conexão, limite de caracteres, etc)
    except Exception as e:
        # Exibe a mensagem de erro no console para diagnóstico
        print(f"  [erro na tradução] {e}")
        # Retorna as linhas originais para evitar perda de dados no arquivo final
        return lines

# Função que gerencia o fluxo de tradução de todas as legendas em pequenos grupos
def translate_entries(entries: list[dict], source_lang: str = "auto", target_lang: str = "pt") -> list[dict]:
    # Extrai apenas o texto de diálogo de cada objeto da lista original
    texts = [e["text"] for e in entries]
    # Armazena a contagem total de blocos para exibir o progresso
    total = len(texts)
    # Inicializa a lista que guardará os textos convertidos para português
    translated_texts = []
    # Divide a tradução em fatias (lotes) baseadas no BATCH_SIZE definido
    for start in range(0, total, BATCH_SIZE):
        # Define o ponto final da fatia atual
        end = min(start + BATCH_SIZE, total)
        # Exibe a porcentagem de conclusão no terminal
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({int(end/total*100)}%)…")
        # Traduz a fatia atual e adiciona os resultados à lista acumuladora
        translated_texts.extend(translate_batch(texts[start:end], source_lang, target_lang))
    # Reconstrói a lista de dicionários mantendo os metadados mas trocando o texto pelo traduzido
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

# Função principal que orquestra a execução do script
def main():
    # Configura o gerenciador de argumentos da linha de comando
    parser = argparse.ArgumentParser(description="Tradutor independente de arquivos SRT via Google Translate.")
    # Adiciona o argumento para receber um ou mais arquivos (ou padrões *.srt)
    parser.add_argument("srt", nargs='+', help="Arquivo(s) .srt ou padrão (ex: *.srt)")
    # Adiciona a opção para definir o idioma de origem (padrão 'auto')
    parser.add_argument("--source-lang", default="auto", help="Idioma de origem (ex: en, ja, es)")
    parser.add_argument("--target-lang", default="pt", help="Idioma de destino (ex: pt, en, es)")
    # Adiciona a opção para definir um nome fixo para o arquivo de saída
    parser.add_argument("--output", default=None, help="Arquivo de saída (opcional)")
    # Processa os argumentos passados pelo usuário ao chamar o script
    args = parser.parse_args()

    # Cria a lista final de caminhos de arquivos expandindo curingas (especialmente útil no Windows)
    srt_files = []
    for pattern in args.srt:
        # Usa o glob para encontrar arquivos que batem com o padrão informado
        matches = glob.glob(pattern)
        # Se encontrar arquivos, adiciona todos à lista; senão, adiciona o nome original para tratar o erro depois
        if matches:
            srt_files.extend(matches)
        else:
            srt_files.append(pattern)

    # Itera sobre cada arquivo SRT identificado para processamento individual
    for srt_path in srt_files:
        # Desenha um cabeçalho visual no terminal para o arquivo atual
        print(f"\n{'='*60}\n Traduzindo: {srt_path}\n{'='*60}")
        
        # Verifica se o arquivo físico realmente existe no caminho informado
        if not Path(srt_path).exists():
            # Exibe erro e pula para o próximo arquivo se este não existir
            print(f"[ERRO] Arquivo não encontrado: {srt_path}")
            continue

        # Tenta realizar o ciclo de tradução completo para o arquivo atual
        try:
            # Abre o arquivo para leitura em modo UTF-8, substituindo caracteres inválidos para evitar erros
            with open(srt_path, "r", encoding="utf-8", errors="replace") as f:
                # Lê o conteúdo completo do arquivo para a memória
                srt_text = f.read()
            
            # Converte a string bruta do arquivo em uma lista estruturada de objetos Python
            entries = parse_srt(srt_text)
            # Verifica se o arquivo continha blocos de legenda válidos após o processamento
            if not entries:
                # Exibe erro se o arquivo estiver vazio ou fora do padrão esperado
                print(f"[ERRO] Não foi possível encontrar blocos válidos em {srt_path}")
                continue

            # Informa ao usuário a quantidade de legendas identificadas no arquivo
            print(f"  Blocos encontrados: {len(entries)}")
            
            # Chama a função que coordena a tradução em lote para português
            translated = translate_entries(entries, source_lang=args.source_lang, target_lang=args.target_lang)
            
            # Define o nome do arquivo final (usa o informado em --output ou gera um automático .pt.srt)
            out_path = args.output or Path(srt_path).with_suffix(".pt.srt")
            
            # Abre o arquivo de destino para gravação em formato UTF-8
            with open(out_path, "w", encoding="utf-8") as f:
                # Transforma a lista de objetos traduzidos de volta em texto SRT e salva no disco
                f.write(build_srt(translated))
            
            # Confirma o sucesso da operação e informa o local do novo arquivo
            print(f"\n✅ Tradução salva em: {out_path}")

        # Captura qualquer erro inesperado durante o processamento do arquivo específico
        except Exception as e:
            # Exibe a falha sem interromper o processamento dos arquivos restantes na fila
            print(f"[ERRO CRÍTICO] Falha ao processar {srt_path}: {e}")

# Ponto de entrada padrão do Python para execução direta do script
if __name__ == "__main__":
    # Chama a função principal de orquestração
    main()
