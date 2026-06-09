#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: translate_subtitles_google_win.py
Objetivo: Versão dedicada e robusta para Windows, que embute caminhos fixos de 
          executáveis (FFmpeg e MKVToolNix) para extrair, transcodificar e traduzir 
          legendas via Google Translate sem depender do PATH do sistema.
"""
# Importa o módulo 'os' para interagir com o sistema operacional e caminhos de arquivo
import os
# Importa 're' para usar expressões regulares (regex) na leitura do texto da legenda
import re
# Importa 'sys' para funções de sistema, como encerrar a execução do script (sys.exit)
import sys
# Importa 'json' para fazer o parse (leitura) do output JSON gerado pelo comando mkvmerge
import json
# Importa 'argparse' para criar a interface de linha de comando e receber argumentos
import argparse
# Importa 'subprocess' para executar programas externos como ffmpeg, mkvmerge e mkvextract
import subprocess
# Importa 'tempfile' para criar diretórios e arquivos temporários seguros durante o processamento
import tempfile
# Importa 'glob' para lidar com expansão de curingas (ex: *.mkv) no Windows
import glob
# Importa 'shutil' para operações de manipulação de arquivos como copiar e mover
import shutil
# Importa 'Path' de 'pathlib' para uma manipulação mais moderna de caminhos de arquivo
from pathlib import Path
# Importa a classe 'GoogleTranslator' da biblioteca 'deep_translator' para realizar a tradução
from deep_translator import GoogleTranslator

# ── CONFIGURAÇÃO DE CAMINHOS LOCAIS (WINDOWS) ──────────────────────────────────
# Define o caminho de instalação do MKVToolNix onde estão os executáveis de extração
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
# Define o caminho do executável do ffmpeg
FFMPEG_BIN     = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin\ffmpeg.exe"

# Cria um dicionário associando o nome da ferramenta ao seu caminho completo
TOOLS = {
    # Mapeia o comando 'mkvmerge' para o seu executável no diretório do MKVToolNix
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    # Mapeia o comando 'mkvextract' para o seu executável
    "mkvextract": os.path.join(MKVTOOLNIX_DIR, "mkvextract.exe"),
    # Mapeia o comando 'ffmpeg' para o seu executável
    "ffmpeg":     FFMPEG_BIN
}

# Define o tamanho do lote de tradução para enviar ao Google (30 blocos de legenda por vez)
BATCH_SIZE = 30
# Define a linguagem alvo para a tradução como Português ('pt')
TARGET_LANG = "pt"

# Função utilitária para rodar comandos de sistema usando subprocess
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    """Wrapper para rodar comandos de sistema. Faz um override dinâmico se o executável estiver no dicionário TOOLS."""
    # Se o primeiro argumento do comando (o nome do programa) estiver no dicionário TOOLS
    if cmd[0] in TOOLS:
        # Substitui o nome do programa pelo caminho completo mapeado no dicionário
        cmd[0] = TOOLS[cmd[0]]
    # Executa o comando, capturando a saída em texto e lidando com a codificação utf-8
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")

# Função que checa a existência da ferramenta necessária antes de continuar
def require_tool(name: str):
    # Pega o caminho mapeado no dicionário ou usa o nome direto caso não exista
    path = TOOLS.get(name, name)
    # Se o caminho/arquivo não existir fisicamente no disco
    if not os.path.exists(path):
        # Exibe mensagem de erro na tela
        print(f"[ERRO] Ferramenta '{name}' não encontrada em: {path}")
        # Encerra o script retornando o código de erro 1
        sys.exit(1)

# Função para listar as faixas (tracks) contidas em um arquivo mkv
def list_tracks(mkv_path: str) -> list[dict]:
    # Executa o mkvmerge pedindo a saída em formato JSON (-J) para o arquivo especificado
    result = run(["mkvmerge", "-J", mkv_path])
    # Interpreta (faz o parse) do texto JSON devolvido pela ferramenta
    info = json.loads(result.stdout)
    # Inicializa lista vazia para armazenar informações sobre as faixas de legenda
    tracks = []
    # Itera sobre todas as faixas encontradas no JSON
    for t in info.get("tracks", []):
        # Filtra para processar apenas faixas que são legendas (subtitles)
        if t["type"] == "subtitles":
            # Extrai as propriedades extras da faixa, com dicionário vazio como fallback
            props = t.get("properties", {})
            # Adiciona informações relevantes da faixa na lista
            tracks.append({
                "id":       t["id"], # ID da faixa no arquivo MKV
                "codec":    t.get("codec", ""), # Formato/codec da legenda (ex: SubRip, ASS)
                "language": props.get("language", "und"), # Idioma da legenda, 'und' se indefinido
                "name":     props.get("track_name", ""), # Nome da faixa, se possuir
            })
    # Retorna a lista de legendas detectadas
    return tracks

# Função para extrair uma faixa de legenda específica usando mkvextract
def extract_subtitle(mkv_path: str, track_id: int, out_path: str):
    # Roda o mkvextract informando para extrair a 'track_id' e salvar em 'out_path'
    run(["mkvextract", "tracks", mkv_path, f"{track_id}:{out_path}"])

# Função que escolhe qual legenda extrair com base na preferência do usuário
def pick_track(tracks: list[dict], prefer_lang: str) -> dict | None:
    """
    Função de fallback. Tenta encontrar a linguagem preferida. Se não achar, 
    busca a faixa em inglês (eng). Como último recurso, retorna a primeira faixa.
    """
    # Primeiro loop: tenta achar uma faixa cujo idioma seja exatamente a preferência fornecida
    for t in tracks:
        if t["language"] == prefer_lang: return t
    # Segundo loop (fallback): caso a preferência não exista, procura a primeira legenda em inglês ('eng')
    for t in tracks:
        if t["language"] == "eng": return t
    # Último recurso: retorna a primeira legenda da lista, se houver alguma, senão retorna None
    return tracks[0] if tracks else None

# Regex compilada que captura: 1) o índice da legenda, 2) os tempos (timecode) e 3) o texto propriamente dito
ENTRY_RE = re.compile(r"(\d+)\r?\n([\d:,]+ --> [\d:,]+)\r?\n([\s\S]*?)(?=\n\n|\Z)", re.MULTILINE)

# Função para transformar o texto de um arquivo SRT em uma lista de dicionários (parsing)
def parse_srt(text: str) -> list[dict]:
    # Cria uma lista vazia para armazenar cada bloco da legenda
    entries = []
    # Itera sobre todas as correspondências da regex 'ENTRY_RE' no texto
    for m in ENTRY_RE.finditer(text.strip()):
        # Para cada correspondência, agrupa em um dicionário o índice, timecode e texto
        entries.append({"index": m.group(1), "timecode": m.group(2), "text": m.group(3).strip()})
    # Retorna a lista de blocos estruturada
    return entries

# Função para recriar o texto do arquivo SRT a partir da lista de dicionários
def build_srt(entries: list[dict]) -> str:
    # Junta todas as linhas, formatando cada bloco: "índice \n tempo \n texto \n" com uma quebra final
    return "\n".join([f"{e['index']}\n{e['timecode']}\n{e['text']}\n" for e in entries])

# Função que traduz uma lista de linhas de texto usando a API do Google Translate
def translate_batch(lines: list[str], source_lang: str = "auto") -> list[str]:
    try:
        # Inicializa o objeto do tradutor configurando idioma de origem e idioma de destino
        translator = GoogleTranslator(source=source_lang, target=TARGET_LANG)
        # Realiza a tradução em lote passando a lista de strings
        return translator.translate_batch(lines)
    except Exception as e:
        # Caso ocorra falha (erro de conexão, timeout, etc), imprime o erro
        print(f"  [erro na tradução] {e}")
        # Retorna o texto original sem tradução como forma de segurança para não perder o texto
        return lines

# Função que recebe os blocos formatados de legenda e gerencia o processo de tradução
def translate_entries(entries: list[dict], source_lang: str = "auto") -> list[dict]:
    # Extrai somente o campo "text" de cada dicionário, formando uma lista só de strings a traduzir
    texts = [e["text"] for e in entries]
    # Conta a quantidade total de blocos/textos
    total = len(texts)
    # Inicializa a lista final que armazenará os textos traduzidos
    translated_texts = []
    # Itera de 0 até o final da lista em passos do tamanho configurado em BATCH_SIZE (ex: 30)
    for start in range(0, total, BATCH_SIZE):
        # Calcula o índice final do lote (limitado ao total de textos para não dar erro)
        end = min(start + BATCH_SIZE, total)
        # Imprime o progresso em porcentagem na tela do usuário
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({int(end/total*100)}%)…")
        # Envia a fatia 'start:end' da lista de textos e adiciona o resultado à lista final
        translated_texts.extend(translate_batch(texts[start:end], source_lang))
    # Reconstrói os dicionários fundindo o original '{**e}' com a chave "text" atualizada para o valor traduzido
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

# Função para converter arquivos de legenda usando ffmpeg (ex: de ASS para SRT e vice-versa)
def convert_subtitle(input_path: str, output_path: str) -> bool:
    """Converte legenda de qualquer formato para o desejado usando ffmpeg."""
    # Se a extensão e os caminhos de entrada/saída forem iguais, não faz nada
    if input_path == output_path: return True
    # Roda o ffmpeg: "-y" para sobrescrever se já existir, "-i" para especificar a entrada
    result = run(["ffmpeg", "-y", "-i", input_path, output_path], check=False)
    # Retorna True se o comando obteve sucesso (returncode 0) e o arquivo final de fato existe no disco
    return result.returncode == 0 and Path(output_path).exists()

# Função principal do script que fará o parsing dos argumentos de CLI e rodará a lógica
def main():
    # Inicializa o parser para receber os parâmetros pela linha de comando
    parser = argparse.ArgumentParser(description="Tradutor MKV (Versão Windows Otimizada)")
    # Argumento obrigatório: os caminhos dos arquivos MKV ou padrões (ex: *.mkv)
    parser.add_argument("mkv", nargs='+', help="Arquivo(s) .mkv ou padrão (ex: *.mkv)")
    # Argumento opcional para a preferência de idioma da legenda (padrão é "eng")
    parser.add_argument("--lang", default="eng", help="Idioma da faixa a extrair (padrão: eng)")
    # Argumento opcional de qual formato deverá ser gerado no fim (ass ou srt)
    parser.add_argument("--format", choices=["srt", "ass"], default="srt", help="Formato de saída (padrão: srt)")
    # Argumento opcional para definir manualmente o idioma de origem caso 'auto' falhe
    parser.add_argument("--source-lang", default="auto", help="Origem da tradução (ex: en, ja)")
    # Argumento opcional para sobrepor o nome final do arquivo que será exportado
    parser.add_argument("--output", default=None, help="Saída personalizada")
    # Argumento tipo flag (boolean) que faz o script apenas listar as faixas e encerrar
    parser.add_argument("--list-tracks", action="store_true", help="Lista faixas e sai")
    # Argumento tipo flag que extrai a legenda original mas pula a fase de tradução
    parser.add_argument("--extract-only", action="store_true", help="Apenas extrai a legenda original sem traduzir")
    # Pega os argumentos da linha de comando
    args = parser.parse_args()

    # Inicializa lista de arquivos que de fato vão ser lidos
    mkv_files = []
    # Itera sobre o(s) argumento(s) mkv passado(s)
    for pattern in args.mkv:
        # Usa o glob para expandir casos onde foi digitado algo como "*.mkv" no terminal
        matches = glob.glob(pattern)
        # Se houve expansão (achou arquivos), adiciona eles. Se não (pode ser arquivo específico sem curinga), adiciona diretamente
        mkv_files.extend(matches) if matches else mkv_files.append(pattern)

    # Verifica proativamente se as três ferramentas externas obrigatórias estão disponíveis
    require_tool("mkvmerge")
    require_tool("mkvextract")
    require_tool("ffmpeg")

    # Inicia o laço de repetição processando cada arquivo MKV da lista de forma individual
    for mkv_path in mkv_files:
        # Imprime um cabeçalho bonitinho para separar a visualização dos logs no console
        print(f"\n{'='*60}\n Processando: {mkv_path}\n{'='*60}")
        # Valida se o arquivo informado de fato existe
        if not Path(mkv_path).exists():
            # Se não existir, avisa e vai para o próximo do loop
            print(f"[ERRO] Arquivo não encontrado: {mkv_path}")
            continue

        # Lista todas as propriedades das faixas do MKV
        tracks = list_tracks(mkv_path)
        # Se não achou nenhuma faixa (ou seja, se a lista for vazia), pula pro próximo
        if not tracks: continue

        # Caso o usuário tenha passado a flag para apenas listar as faixas
        if args.list_tracks:
            # Imprime o cabeçalho das colunas
            print(f"{'ID':>4}  {'Idioma':<8}  {'Codec':<20}")
            # Itera sobre todas as faixas e as exibe alinhadas
            for t in tracks: print(f"{t['id']:>4}  {t['language']:<8}  {t['codec']:<20}")
            # Pula para o próximo arquivo, já que o comando era apenas para listagem
            continue

        # A partir das faixas, escolhe aquela que melhor se encaixa no idioma pedido em '--lang'
        track = pick_track(tracks, args.lang)
        # Avisa ao usuário qual trilha foi selecionada pelo processo de fallback/escolha
        print(f"\nUsando faixa ID={track['id']} ({track['language']}) codec={track['codec']}")

        # Cria uma pasta temporária pelo sistema que será autolimpada ao sair deste bloco "with"
        with tempfile.TemporaryDirectory() as tmp:
            # Define se a extensão para extração primária deve ser '.ass' ou '.srt' verificando o nome do codec
            orig_ext = "ass" if "ass" in track["codec"].lower() else "srt"
            # Define caminho do arquivo temporário onde a legenda bruta recém extraída será gravada
            raw_path = os.path.join(tmp, f"sub_orig.{orig_ext}")
            
            # Avisa na tela
            print(f"  Extraindo legenda ({track['codec']})...")
            # Extrai o arquivo bruto pelo 'mkvextract'
            extract_subtitle(mkv_path, track["id"], raw_path)
            
            # Checa a flag se o usuário quer apenas a legenda e não deseja traduzi-la
            if args.extract_only:
                # Pega a extensão solicitada pelo usuário no CLI (padrão é .srt)
                final_ext = f".{args.format}"
                # Define o destino com base no parâmetro '--output' ou cria um novo nome mantendo base do MKV
                dest_path = args.output or Path(mkv_path).with_suffix(final_ext)
                # Tenta converter a legenda recém extraída para o formato desejado, se não puder faz uma cópia apenas
                if convert_subtitle(raw_path, str(dest_path)):
                    print(f"\n✅ Extração concluída no formato {args.format.upper()}: {dest_path}")
                else:
                    print(f"\n[ERRO] Falha ao converter para {args.format.upper()}")
                # Como foi apenas extração, pula pro próximo arquivo MKV
                continue

            # Início do bloco de tradução; primeiro é preciso normalizar a legenda extraída para SRT
            srt_internal = os.path.join(tmp, "internal.srt")
            # Tenta converter para SRT usando ffmpeg, caso falhe exibe erro e pula
            if not convert_subtitle(raw_path, srt_internal):
                print(f"[ERRO] Falha ao normalizar legenda.")
                continue

            # Abre o arquivo SRT temporário recém-convertido para leitura de texto
            with open(srt_internal, encoding="utf-8", errors="replace") as f: 
                # Lê o conteúdo em sua totalidade
                srt_text = f.read()

            # Chama a função que destrincha a string do SRT em blocos (índice, tempo, texto)
            entries = parse_srt(srt_text)
            # Se a legenda gerou 0 blocos (talvez esteja vazia ou corrompida), ignora e vai ao próximo MKV
            if not entries: continue

            # Exibe na tela quantos blocos achou
            print(f"  Blocos encontrados: {len(entries)}")
            # Envia a lista para tradução, que dividirá os envios usando BATCH_SIZE (30)
            translated_entries_list = translate_entries(entries, source_lang=args.source_lang)
            
            # Define o caminho do arquivo temporário onde será jogada a legenda final já traduzida em SRT
            translated_srt = os.path.join(tmp, "translated.srt")
            # Abre para gravação de texto, assumindo codificação utf-8
            with open(translated_srt, "w", encoding="utf-8") as f:
                # Escreve o texto refeito pela função 'build_srt'
                f.write(build_srt(translated_entries_list))
            
            # Monta a extensão do arquivo baseada na sigla 'pt' (português) mais o formato requerido
            final_ext = f".pt.{args.format}"
            # Usa novamente a regra do output personalizado ou nomeia com base no próprio MKV
            out_path = args.output or Path(mkv_path).with_suffix(final_ext)
            
            # Se o usuário especificou formato ASS no destino
            if args.format == "ass":
                # Converte o arquivo SRT temporário que tem as traduções para o formato ASS e avisa resultado
                if convert_subtitle(translated_srt, str(out_path)):
                    print(f"\n✅ Tradução concluída no formato ASS: {out_path}")
                else:
                    print(f"\n[ERRO] Falha ao converter tradução para ASS.")
            else:
                # Se o usuário não pediu ASS, o padrão é SRT, então apenas copia e move o arquivo temporário SRT para o lugar final
                shutil.copy(translated_srt, out_path)
                print(f"\n✅ Tradução concluída no formato SRT: {out_path}")

# Verifica se o script está sendo rodado diretamente (ao invés de ser importado por outro) e invoca a main
if __name__ == "__main__":
    main()
