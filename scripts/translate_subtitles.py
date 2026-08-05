#!/usr/bin/env python3
# ==============================================================================
# Script: translate_subtitles.py
#
# Objetivo:
#   Extrair legenda embutida de um arquivo .mkv e traduzir para português
#   usando a API da Anthropic (Claude).
#
# Lógica Principal:
#   Extrai a legenda SRT do arquivo MKV original usando o FFmpeg. O texto é lido, 
#   os blocos de diálogo identificados por Expressão Regular (Regex) e enviados 
#   para a API do Claude em lotes. O arquivo SRT traduzido é então regerado.
#
# Dependências Externas:
#   FFmpeg, anthropic
# ==============================================================================

# Importa módulo 'os' para interagir com sistema e variáveis de ambiente (como chaves de API)
import os
# Importa módulo 're' para realizar buscas complexas de texto via Expressões Regulares
import re
# Importa módulo 'sys' para controle do fluxo do script em nível de sistema (ex: sys.exit)
import sys
# Importa módulo 'json' para lidar com payloads da API e dados de saída do mkvmerge
import json
# Importa módulo 'argparse' para construção da interface de linha de comando
import argparse
# Importa módulo 'subprocess' para executar as ferramentas cli (ffmpeg, mkvtoolnix)
import subprocess
# Importa módulo 'tempfile' para criar diretórios transitórios seguros
import tempfile
# Importa módulo 'glob' para localizar arquivos a partir de padrões (como *.mkv)
import glob
# Importa módulo 'shutil' para mover, copiar ou remover arquivos e pastas
import shutil
# Importa classe 'Path' para manipular caminhos de forma robusta entre sistemas operacionais
from pathlib import Path

# ── Configuração da API ────────────────────────────────────────────────────────
# Captura a chave de API da variável de ambiente. Se não existir, fica em branco
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
# Define qual versão do modelo Claude será utilizada
MODEL = "claude-sonnet-4-20250514"
# Define o tamanho do pacote de linhas enviadas de uma vez para a IA
BATCH_SIZE = 40
# Define o limite máximo de tokens permitidos como resposta da API
MAX_TOKENS  = 4096

# Função auxiliar para rodar comandos CLI no sistema operacional
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Captura a saída do console, formata como texto (utf-8) e verifica erros se check=True
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

# Função para garantir que executáveis de terceiros estejam instalados
def require_tool(name: str):
    """Verifica se a ferramenta CLI especificada está disponível no PATH do sistema."""
    # Usa 'where' no Windows ('nt') ou 'which' em Linux/Mac para achar a ferramenta
    result = run(["where" if os.name == "nt" else "which", name], check=False)
    # Se retornou algo diferente de 0, o programa falhou ou não existe
    if result.returncode != 0:
        # Avisa ao usuário que a ferramenta requerida não foi encontrada
        print(f"[ERRO] '{name}' não encontrado. Instale o mkvtoolnix.")
        # Encerra o script com status de erro
        sys.exit(1)

# Função para ler a estrutura interna de um arquivo MKV
def list_tracks(mkv_path: str) -> list[dict]:
    # O comando 'mkvmerge -J' imprime os dados do arquivo em formato JSON
    result = run(["mkvmerge", "-J", mkv_path])
    # Faz o parser do JSON retornado pelo mkvmerge para uma estrutura Python nativa
    info = json.loads(result.stdout)
    # Inicializa uma lista que armazenará somente as faixas que são de legenda
    tracks = []
    # Itera sobre todas as faixas (vídeo, áudio, etc) do MKV
    for t in info.get("tracks", []):
        # Filtra especificamente aquelas marcadas como 'subtitles'
        if t["type"] == "subtitles":
            # Extrai o campo de propriedades, evitando erro se não existir
            props = t.get("properties", {})
            # Adiciona os dados mapeados relevantes da legenda à lista
            tracks.append({
                "id":       t["id"],
                "codec":    t.get("codec", ""),
                "language": props.get("language", "und"),
                "name":     props.get("track_name", ""),
            })
    # Retorna as faixas de legenda encontradas
    return tracks

# Função para extrair uma faixa de legenda de dentro do MKV para o disco local
def extract_subtitle(mkv_path: str, track_id: int, out_path: str):
    # 'mkvextract tracks arquivo.mkv id:destino.srt' efetua a extração física
    run(["mkvextract", "tracks", mkv_path, f"{track_id}:{out_path}"])

# Função que seleciona automaticamente qual trilha de legenda usar
def pick_track(tracks: list[dict], prefer_lang: str) -> dict | None:
    # 1º Passo: tenta achar uma faixa cujo idioma corresponda exatamente à preferência
    for t in tracks:
        if t["language"] == prefer_lang: return t
    # 2º Passo (Fallback): se não achar a preferida, tenta inglês ('eng')
    for t in tracks:
        if t["language"] == "eng": return t
    # 3º Passo (Fallback): não achou nenhuma das anteriores, usa a primeira que encontrar
    return tracks[0] if tracks else None

# Regex compilada para bater com a estrutura fixa de arquivos '.srt' (SubRip)
# Pega o 1) índice, 2) o tempo de entrada/saída, 3) o texto propriamente dito
ENTRY_RE = re.compile(r"(\d+)\r?\n([\d:,]+ --> [\d:,]+)\r?\n([\s\S]*?)(?=\n\n|\Z)", re.MULTILINE)

# Função que converte o texto integral do arquivo SRT numa lista de dicionários
def parse_srt(text: str) -> list[dict]:
    """Usa Regex para processar o texto do arquivo SRT e retornar uma lista de blocos (index, timecode, text)."""
    # Inicializa a lista de dicionários
    entries = []
    # Busca todas as ocorrências de blocos SubRip no texto
    for m in ENTRY_RE.finditer(text.strip()):
        # Para cada ocorrência, guarda as 3 partes capturadas de forma estruturada
        entries.append({"index": m.group(1), "timecode": m.group(2), "text": m.group(3).strip()})
    # Retorna o modelo de dados gerado
    return entries

# Função inversa ao 'parse_srt', reconstrói o texto do arquivo usando a lista
def build_srt(entries: list[dict]) -> str:
    # Junta índice, tempo e texto separados por quebra de linha usando a lista comprehensions
    return "\n".join([f"{e['index']}\n{e['timecode']}\n{e['text']}\n" for e in entries])

# Função principal de conexão com a IA
def translate_batch(lines: list[str], source_lang: str = "inglês") -> list[str]:
    """
    Envia as frases para a API da Anthropic (Claude) solicitando a tradução.
    Enumera cada linha para garantir que o modelo responda exatamente o mesmo 
    número de frases e seja possível validar a sincronia posteriormente.
    """
    # Importa a biblioteca base do Python que faz requisições HTTP
    import urllib.request
    # Enumera cada linha (ex: "1. Olá", "2. Tudo bem?") para evitar que a IA pule linhas ou misture
    numbered = "\n".join(f"{i+1}. {line}" for i, line in enumerate(lines))
    # Prepara o 'prompt' de sistema dando a persona e a instrução clara à IA
    prompt = (
        f"Você é um tradutor profissional de legendas de {source_lang} para português brasileiro.\n"
        "Traduza cada linha abaixo mantendo tags HTML e mantendo a ordem.\n"
        f"{numbered}"
    )
    # Prepara payload em JSON para a API Rest, convertendo para binário (.encode())
    payload = json.dumps({
        "model": MODEL,
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    # Cria o objeto Request com os headers obrigatórios da API da Anthropic
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    # Efetua a requisição web de forma bloqueante aguardando o processamento do servidor
    with urllib.request.urlopen(req) as resp:
        # Pega a resposta, carrega o JSON retornado
        data = json.loads(resp.read())
    
    # Processa e limpa a resposta do Claude retirando as numerações das linhas traduzidas
    # Navega até o bloco de texto útil retornado pela API
    raw = data["content"][0]["text"].strip()
    # Inicializa uma lista para as linhas limpas
    result_lines = []
    # Itera sobre cada linha devolvida
    for line in raw.splitlines():
        # Usa regex para buscar e capturar o texto que vem depois do número (ex: "1. ")
        m = re.match(r"^\d+\.\s*(.*)", line)
        # Se bater com o padrão de número, adiciona apenas a parte de texto puro na lista
        if m: result_lines.append(m.group(1))
    
    # Mecanismo de segurança (fallback): se o Claude retornar menos falas do que as enviadas, 
    # mantemos original para não quebrar a sincronização do arquivo SRT
    return result_lines if len(result_lines) == len(lines) else lines

# Função para enviar todo o lote de legendas para tradução e reagrupar
def translate_entries(entries: list[dict], source_lang: str = "inglês") -> list[dict]:
    # Separa só o texto original de cada dicionário da lista
    texts = [e["text"] for e in entries]
    # Conta a quantidade total de legendas a traduzir
    total = len(texts)
    # Inicia a lista vazia onde guardaremos o texto em português
    translated_texts = []
    # Itera pelos blocos da lista na proporção fixada por 'BATCH_SIZE'
    for start in range(0, total, BATCH_SIZE):
        # Determina onde o lote atual termina sem passar do limite total
        end = min(start + BATCH_SIZE, total)
        # Imprime no terminal em que faixa de legendas estamos
        print(f"  Traduzindo {start+1}–{end} de {total}…")
        # Estende a lista de resultados jogando a fatia atual na função de tradução Claude
        translated_texts.extend(translate_batch(texts[start:end], source_lang))
    # Refaz a lista de dicionários usando a legenda original, mas com o campo 'text' sendo a tradução
    return [{**e, "text": t} for e, t in zip(entries, translated_texts)]

# Utilitário genérico que aciona o ffmpeg para converter formato de legendas (ex: ASS -> SRT)
def convert_subtitle(input_path: str, output_path: str) -> bool:
    # Se a entrada e saída são os mesmos, não precisa fazer nada
    if input_path == output_path: return True
    # -y sobrescreve sem perguntar, -i especifica a entrada
    result = run(["ffmpeg", "-y", "-i", input_path, output_path], check=False)
    # Retorna True se o processo fechou limpo e se o arquivo final foi efetivamente criado no disco
    return result.returncode == 0 and Path(output_path).exists()

# Função principal (CLI e orquestração)
def main():
    # Prepara os comandos a serem passados pelo console
    parser = argparse.ArgumentParser(description="Extrai e traduz legenda de um arquivo MKV via Claude.")
    # Exige que seja passado um ou mais arquivos mkv/padrões
    parser.add_argument("mkv", nargs='+', help="Arquivo(s) .mkv ou padrão")
    # Qual legenda quero tentar extrair (fallback "eng")
    parser.add_argument("--lang", default="eng", help="Idioma da faixa")
    # Qual formato final de legenda o usuário quer no disco (ass ou srt)
    parser.add_argument("--format", choices=["srt", "ass"], default="srt", help="Formato de saída")
    # Idioma que a IA deve saber que está traduzindo a partir
    parser.add_argument("--source-lang", default="inglês", help="Idioma de origem")
    # Possibilidade de salvar o arquivo em nome exato escolhido pelo usuário
    parser.add_argument("--output", default=None, help="Saída")
    # Flag para apenas ver o que tem dentro do arquivo, sem fazer nada
    parser.add_argument("--list-tracks", action="store_true", help="Lista faixas")
    # Flag para fazer a extração mas não acionar API Claude
    parser.add_argument("--extract-only", action="store_true", help="Apenas extrai")
    # Captura efetivamente os parâmetros da chamada
    args = parser.parse_args()

    # Expansão de caminhos (útil no cmd/powershell do Windows)
    mkv_files = []
    # Itera sobre o(s) valor(es) recebidos do console
    for pattern in args.mkv:
        # glob converte "*.mkv" em "video1.mkv", "video2.mkv"
        matches = glob.glob(pattern)
        # Junta os arquivos identificados, ou se não houver expansão coloca o que foi digitado mesmo
        mkv_files.extend(matches) if matches else mkv_files.append(pattern)

    # Checagens para saber se o programa MKVToolNix existe no sistema
    require_tool("mkvmerge")
    require_tool("mkvextract")

    # Início do loop em cada arquivo
    for mkv_path in mkv_files:
        # Feedback visual
        print(f"\nProcessando: {mkv_path}")
        # Proteção: se o arquivo não existe fisicamente, pula pro próximo
        if not Path(mkv_path).exists(): continue

        # Identifica todas as faixas do MKV
        tracks = list_tracks(mkv_path)
        # Se não tiver faixa, pula também
        if not tracks: continue

        # Tratamento da flag que apenas lista
        if args.list_tracks:
            # Mostra dados rudimentares no console e pula pro próximo vídeo
            for t in tracks: print(f"ID={t['id']} lang={t['language']} codec={t['codec']}")
            continue

        # Seleciona qual legenda retirar do vídeo
        track = pick_track(tracks, args.lang)
        # Inicia sessão que cria diretório temporário
        with tempfile.TemporaryDirectory() as tmp:
            # Averigua se a legenda nativa era ass ou srt baseado no seu codec e cria o caminho com extensão respectiva
            orig_ext = "ass" if "ass" in track["codec"].lower() else "srt"
            # Monta rota onde o extraído ficará provisoriamente
            raw_path = os.path.join(tmp, f"sub_orig.{orig_ext}")
            # Roda a extração em si
            extract_subtitle(mkv_path, track["id"], raw_path)
            
            # Tratamento da flag para extrair e abortar
            if args.extract_only:
                # O formato final desejado via parâmetro (--format)
                final_ext = f".{args.format}"
                # Define pasta final
                dest_path = args.output or Path(mkv_path).with_suffix(final_ext)
                # Converte o extraído para o que foi pedido via ffmpeg
                convert_subtitle(raw_path, str(dest_path))
                # Aviso de sucesso
                print(f"✅ Extraído: {dest_path}")
                # Interrompe o processo desse arquivo e vai pro próximo
                continue

            # Início do ciclo de tradução. Tudo tem que ser SRT internamente para a Regex funcionar bem
            srt_internal = os.path.join(tmp, "internal.srt")
            # Converte usando o ffmpeg de forma silenciosa
            convert_subtitle(raw_path, srt_internal)
            # Lê o conteúdo da nova legenda srt padronizada e salva numa string do python
            with open(srt_internal, encoding="utf-8", errors="replace") as f: srt_text = f.read()

            # Chama o módulo que desmonta a string numa lista baseada em dicionário
            entries = parse_srt(srt_text)
            # Verificação de segurança: sem API configurada a gente deve quebrar agora e não gastar recurso à toa
            if not ANTHROPIC_API_KEY: 
                print("[ERRO] API KEY da Anthropic não está configurada.")
                sys.exit(1)
            # Toca toda a tradução via API
            translated_list = translate_entries(entries, source_lang=args.source_lang)
            
            # Cria a string do nome provisório pós-tradução
            translated_srt = os.path.join(tmp, "translated.srt")
            # Escreve arquivo convertendo dicionário de volta a texto SubRip
            with open(translated_srt, "w", encoding="utf-8") as f:
                f.write(build_srt(translated_list))
            
            # Formata a extensão do arquivo definitivo adicionando ".pt" na frente e respeitando o --format do user
            final_ext = f".pt.{args.format}"
            # Usa o nome passado via prompt ou deduz baseado no MKV
            out_path = args.output or Path(mkv_path).with_suffix(final_ext)
            
            # Se a saída desejada é ASS
            if args.format == "ass":
                # Manda o ffmpeg converter o srt traduzido pra ass jogando direto pro destino final
                convert_subtitle(translated_srt, str(out_path))
            else:
                # Se for srt, é só copiar para o destino
                shutil.copy(translated_srt, out_path)
            
            # Exibe aviso confirmando que finalizou com sucesso
            print(f"✅ Concluído ({args.format.upper()}): {out_path}")

# Gatilho de acionamento do Python padrão para que a 'main' não rode sem intenção via imports
if __name__ == "__main__":
    main()
