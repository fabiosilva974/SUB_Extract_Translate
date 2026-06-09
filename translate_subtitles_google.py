#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script: translate_subtitles_google.py
Objetivo: Extrai legendas encapsuladas de um vídeo (MKV) e traduz para português 
          utilizando o serviço gratuito Google Translate (via deep-translator).
"""
# Importa módulo 'os' para interagir com o sistema operacional (caminhos, variáveis de ambiente)
import os
# Importa módulo 're' (Expressões Regulares) para manipulação avançada de strings e busca de padrões
import re
# Importa módulo 'sys' para interações de nível de sistema (ex: forçar fechamento do script)
import sys
# Importa módulo 'json' para codificar e decodificar os dados retornados pelos executáveis
import json
# Importa módulo 'argparse' para criação fácil e robusta de interfaces de linha de comando
import argparse
# Importa módulo 'subprocess' para acionar os arquivos executáveis do ffmpeg e mkvtoolnix em sub-processos
import subprocess
# Importa módulo 'tempfile' que cria diretórios e arquivos temporários seguros que o SO limpa sozinho
import tempfile
# Importa módulo 'glob' para busca fácil de arquivos através de expressões curinga (ex: *.mkv)
import glob
# Importa módulo 'shutil' para realizar operações de alto nível em arquivos, como mover e copiar
import shutil
# Importa 'Path' para trabalhar com caminhos orientados a objetos (resolve problemas com barras \ e /)
from pathlib import Path
# Importa a biblioteca deep_translator especificamente a classe de conexão com Google
from deep_translator import GoogleTranslator

# Quantidade máxima de linhas de legenda para enviar de cada vez à API
BATCH_SIZE = 30
# Língua padrão de destino da tradução
TARGET_LANG = "pt"

# Wrapper simplificado para executar linha de comando via subprocess
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Retorna o resultado capturando sua saída como string padrão UTF-8
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

# Valida se os programas externos exigidos para o script rodar existem no computador
def require_tool(name: str):
    # Roda o comando nativo que acha caminhos: 'where' no Windows, 'which' em Linux/Mac
    result = run(["where" if os.name == "nt" else "which", name], check=False)
    # Se o retorno der erro, quer dizer que não achou no PATH do sistema
    if result.returncode != 0:
        print(f"[ERRO] '{name}' não encontrado. Instale o mkvtoolnix e ffmpeg.")
        sys.exit(1)

# Extrai os metadados e constrói um resumo das faixas presentes no vídeo
def list_tracks(mkv_path: str) -> list[dict]:
    """Usa o mkvmerge para extrair todas as propriedades de faixas de subtitle (legenda) em formato JSON."""
    # Chama mkvmerge pedindo retorno puramente em formato JSON
    result = run(["mkvmerge", "-J", mkv_path])
    # Converte o JSON string para um Dicionário Python
    info = json.loads(result.stdout)
    # Lista vazia que agrupará as faixas localizadas
    tracks = []
    # Loop em cada "track" do vídeo
    for t in info.get("tracks", []):
        # Interessa-nos unicamente os do tipo 'subtitles'
        if t["type"] == "subtitles":
            # Protege contra falha tentando pegar o sub-dicionário "properties"
            props = t.get("properties", {})
            # Adiciona os detalhes importantes à lista resultante
            tracks.append({
                "id":       t["id"], # O ID é vital para pedir extração depois
                "codec":    t.get("codec", ""), # Codec ajuda a prever o formato original
                "language": props.get("language", "und"), # Idioma flaggado na faixa
                "name":     props.get("track_name", ""), # Nome dado pelo criador do vídeo
            })
    return tracks

# Aciona o executável de extração física da trilha do vídeo para o HD
def extract_subtitle(mkv_path: str, track_id: int, out_path: str):
    # Formato do comando: mkvextract tracks nomedovideo.mkv numeroid:caminhodesaida
    run(["mkvextract", "tracks", mkv_path, f"{track_id}:{out_path}"])

# Algoritmo de escolha da faixa mais apropriada com base na linguagem desejada
def pick_track(tracks: list[dict], prefer_lang: str) -> dict | None:
    # Tenta achar correspondência exata primeiro
    for t in tracks:
        if t["language"] == prefer_lang: return t
    # Tenta achar 'inglês' se não achar o pedido
    for t in tracks:
        if t["language"] == "eng": return t
    # Devolve a primeira disponível ou None caso o vídeo não tenha legenda
    return tracks[0] if tracks else None

# Padrão Regex que mapeia exatamente os três pilares de um arquivo de legenda SRT
ENTRY_RE = re.compile(r"(\d+)\r?\n([\d:,]+ --> [\d:,]+)\r?\n([\s\S]*?)(?=\n\n|\Z)", re.MULTILINE)

# Lê o texto cru do arquivo e divide em pedaços programáticos
def parse_srt(text: str) -> list[dict]:
    entries = []
    # Encontra todas as "casinhas" do texto que correspondem ao padrão Regex
    for m in ENTRY_RE.finditer(text.strip()):
        # Guarda os grupos: grupo 1 é índice, 2 é o tempo, 3 é o texto falado
        entries.append({"index": m.group(1), "timecode": m.group(2), "text": m.group(3).strip()})
    return entries

# Reconstrói a string do arquivo original a partir da lista
def build_srt(entries: list[dict]) -> str:
    # Usando string comprehension, monta "indice \n tempo \n texto \n"
    return "\n".join([f"{e['index']}\n{e['timecode']}\n{e['text']}\n" for e in entries])

# Módulo básico de comunicação com a API de tradução do Google
def translate_batch(lines: list[str], source_lang: str = "auto") -> list[str]:
    """Abre conexão com a API do Google Translate e traduz de uma vez a lista de sentenças enviada."""
    try:
        # Prepara o objeto passando origem (auto-detect) e destino (pt)
        translator = GoogleTranslator(source=source_lang, target=TARGET_LANG)
        # Bate na API de fato e retorna
        return translator.translate_batch(lines)
    except Exception as e:
        # Se ocorrer falha de rede/timeout, avisa e devolve intacto pra não perder o arquivo todo
        print(f"  [erro na tradução] {e}")
        return lines

# Orquestrador da divisão em lotes para evitar que a API negue a conexão
def translate_entries(entries: list[dict], source_lang: str = "auto") -> list[dict]:
    """Orquestra a lógica de envio por pequenos lotes (BATCH_SIZE) para contornar limites da web e timeouts."""
    # Retira apenas a fala crua da estrutura
    texts = [e["text"] for e in entries]
    total = len(texts)
    translated_texts = []
    # Avança pela lista pulando em passos iguais a 'BATCH_SIZE' (ex: 30)
    for start in range(0, total, BATCH_SIZE):
        # Determina o máximo pulo para a fatia
        end = min(start + BATCH_SIZE, total)
        # Mostra o status do carregamento para o usuário final
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({int(end/total*100)}%)…")
        # Anexa o resultado do lote aos textos totais que já foram traduzidos
        translated_texts.extend(translate_batch(texts[start:end], source_lang))
    # Reconstrói a estrutura, mudando somente o valor do texto para o novo idioma
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

# Utiliza o motor FFmpeg para transitar a legenda de um formato a outro livremente
def convert_subtitle(input_path: str, output_path: str) -> bool:
    """Invoca o FFmpeg para transformar de maneira forçada formatos entre si (ex: .ass para .srt e vice-versa)."""
    # Proteção besta pra caso de arquivos iguais
    if input_path == output_path: return True
    # -y força sobrescrever se já existir. Aciona check=False pra não travar script caso dê erro no binário
    result = run(["ffmpeg", "-y", "-i", input_path, output_path], check=False)
    # Tem que retornar exit code 0 e o arquivo tem de existir na pasta destino
    return result.returncode == 0 and Path(output_path).exists()

# Entrypoint do script
def main():
    # Cria a documentação dinâmica que o usuário lê quando usa --help
    parser = argparse.ArgumentParser(description="Extrai e traduz legendas de MKV para português via Google Translate.")
    # Parâmetros CLI que controlam o comportamento
    parser.add_argument("mkv", nargs='+', help="Arquivo(s) .mkv ou padrão (ex: *.mkv)")
    parser.add_argument("--lang", default="eng", help="Idioma da faixa a extrair (padrão: eng)")
    parser.add_argument("--format", choices=["srt", "ass"], default="srt", help="Formato de saída (padrão: srt)")
    parser.add_argument("--source-lang", default="auto", help="Origem da tradução (ex: en, ja)")
    parser.add_argument("--output", default=None, help="Saída personalizada")
    parser.add_argument("--list-tracks", action="store_true", help="Lista faixas e sai")
    parser.add_argument("--extract-only", action="store_true", help="Apenas extrai a legenda original sem traduzir")
    # Lê do cmd
    args = parser.parse_args()

    # Expansão para curingas nativa, pro Windows entender coisas do tipo "*.mkv"
    mkv_files = []
    for pattern in args.mkv:
        matches = glob.glob(pattern)
        mkv_files.extend(matches) if matches else mkv_files.append(pattern)

    # Checa dependências hard no SO inteiro, já que essa versão depende do ambiente global
    require_tool("mkvmerge")
    require_tool("mkvextract")
    require_tool("ffmpeg")

    # Inicia o laço de tratamento por cada vídeo inserido
    for mkv_path in mkv_files:
        # Separação visual
        print(f"\n{'='*60}\n Processando: {mkv_path}\n{'='*60}")
        # Proteção se o arquivo físico não for achado
        if not Path(mkv_path).exists(): continue

        # Identifica o que tem dentro do arquivo atual
        tracks = list_tracks(mkv_path)
        # Se for vídeo seco sem legenda, pula
        if not tracks: continue

        # Tratamento da flag list-tracks que interrompe
        if args.list_tracks:
            for t in tracks: print(f"ID={t['id']} lang={t['language']} codec={t['codec']}")
            continue

        # Realiza a escolha baseado em heurística/fallback
        track = pick_track(tracks, args.lang)
        print(f"\nUsando faixa ID={track['id']} ({track['language']}) codec={track['codec']}")

        # Começa as ações num local do HD que se auto-destruirá ao final
        with tempfile.TemporaryDirectory() as tmp:
            # Assume qual é a extensão base dependendo do nome do codec relatado pelo MKVToolNix
            orig_ext = "ass" if "ass" in track["codec"].lower() else "srt"
            # Define o local do extraído original
            raw_path = os.path.join(tmp, f"sub_orig.{orig_ext}")
            print(f"  Extraindo legenda ({track['codec']})…")
            # Extrai pra pasta temporária
            extract_subtitle(mkv_path, track["id"], raw_path)
            
            # Tratamento da flag extract-only
            if args.extract_only:
                # O formato selecionado no prompt
                final_ext = f".{args.format}"
                # Avalia o output final e substitui a extensão default
                dest_path = args.output or Path(mkv_path).with_suffix(final_ext)
                # Chama ffmpeg para transformar
                convert_subtitle(raw_path, str(dest_path))
                print(f"\n✅ Extração concluída: {dest_path}")
                continue

            # Início da fase de tradução - Primeiro passo é converter pro SRT base, pois usamos o Regex dele
            srt_internal = os.path.join(tmp, "internal.srt")
            if not convert_subtitle(raw_path, srt_internal): continue

            # Ler string pra memória
            with open(srt_internal, encoding="utf-8", errors="replace") as f: srt_text = f.read()

            # Converter pra objetos estruturados
            entries = parse_srt(srt_text)
            if not entries: continue

            print(f"  Blocos encontrados: {len(entries)}")
            # Chamar pipeline de tradução do Google via batches
            translated_list = translate_entries(entries, source_lang=args.source_lang)
            
            # Criar srt traduzido no temp
            translated_srt = os.path.join(tmp, "translated.srt")
            with open(translated_srt, "w", encoding="utf-8") as f:
                f.write(build_srt(translated_list))
            
            # Formatar output final
            final_ext = f".pt.{args.format}"
            out_path = args.output or Path(mkv_path).with_suffix(final_ext)
            
            # Condição final de qual tipo o usuário exigiu no destino final
            if args.format == "ass":
                # Uso do ffmpeg se exigiu formato rico
                convert_subtitle(translated_srt, str(out_path))
            else:
                # Cópia simples se for formato padrão textual
                shutil.copy(translated_srt, out_path)
            
            print(f"\n✅ Concluído ({args.format.upper()}): {out_path}")

# Boa prática pra impedir que o main() rode se eu tiver só importando funções soltas desse script num projeto maior
if __name__ == "__main__":
    main()
