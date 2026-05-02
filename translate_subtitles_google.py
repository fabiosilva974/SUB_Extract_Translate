#!/usr/bin/env python3
# Importa o módulo para interagir com o sistema operacional
import os
# Importa o módulo para expressões regulares (usado no processamento do SRT)
import re
# Importa o módulo para interagir com parâmetros do sistema e saída de erro
import sys
# Importa o módulo para lidar com dados em formato JSON
import json
# Importa o módulo para criação de interface de linha de comando (CLI)
import argparse
# Importa o módulo para execução de comandos externos do sistema
import subprocess
# Importa o módulo para criação de arquivos e diretórios temporários
import tempfile
# Importa a classe Path para manipulação moderna de caminhos de arquivos
from pathlib import Path
# Importa o tradutor do Google da biblioteca deep-translator
from deep_translator import GoogleTranslator

# Define o tamanho do lote de tradução para evitar bloqueios ou lentidão (Google Translate aceita textos longos)
BATCH_SIZE = 30
# Define o idioma de destino padrão como português
TARGET_LANG = "pt"

# Função para executar comandos no terminal e capturar a saída
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Executa o comando, captura stdout/stderr e retorna o resultado
    return subprocess.run(cmd, capture_output=True, text=True, check=check)

# Função para verificar se uma ferramenta necessária está instalada no sistema
def require_tool(name: str):
    # Tenta encontrar o caminho do executável da ferramenta
    result = run(["where" if os.name == "nt" else "which", name], check=False)
    # Se não encontrar (código de retorno diferente de 0), exibe erro e encerra
    if result.returncode != 0:
        # Exibe mensagem de erro informando a ferramenta ausente
        print(f"[ERRO] '{name}' não encontrado. Instale o mkvtoolnix e ffmpeg.")
        # Encerra o script com código de erro
        sys.exit(1)

# Função que lista as faixas de legenda dentro de um arquivo MKV
def list_tracks(mkv_path: str) -> list[dict]:
    # Usa o mkvmerge para obter informações do arquivo em formato JSON
    result = run(["mkvmerge", "-J", mkv_path])
    # Converte a string JSON da saída para um dicionário Python
    info = json.loads(result.stdout)
    # Inicializa a lista que guardará as informações das faixas
    tracks = []
    # Itera sobre todas as faixas encontradas no arquivo
    for t in info.get("tracks", []):
        # Filtra apenas faixas que sejam do tipo legenda (subtitles)
        if t["type"] == "subtitles":
            # Obtém as propriedades específicas da faixa
            props = t.get("properties", {})
            # Adiciona um dicionário simplificado com os dados relevantes da faixa
            tracks.append({
                "id":       t["id"], # ID da faixa para extração
                "codec":    t.get("codec", ""), # Codec da legenda (ex: SubRip, HDMV PGS)
                "language": props.get("language", "und"), # Idioma (ou 'und' se não definido)
                "name":     props.get("track_name", ""), # Nome da faixa dado pelo autor
            })
    # Retorna a lista de faixas de legenda encontradas
    return tracks

# Função que extrai uma faixa específica de legenda do MKV para um arquivo
def extract_subtitle(mkv_path: str, track_id: int, out_path: str):
    # Executa o mkvextract especificando o arquivo, a operação 'tracks' e o mapeamento ID:Caminho
    run(["mkvextract", "tracks", mkv_path, f"{track_id}:{out_path}"])

# Função que decide qual faixa de legenda usar com base na preferência de idioma
def pick_track(tracks: list[dict], prefer_lang: str) -> dict | None:
    # Primeiro, tenta encontrar a faixa com o idioma solicitado pelo usuário
    for t in tracks:
        # Verifica se o idioma da faixa coincide com o preferido
        if t["language"] == prefer_lang:
            # Retorna a faixa correspondente
            return t
    # Se não achar a preferida, tenta encontrar uma faixa em inglês ('eng')
    for t in tracks:
        # Verifica se o idioma é inglês
        if t["language"] == "eng":
            # Retorna a faixa em inglês
            return t
    # Se não houver inglês nem a preferida, retorna a primeira faixa de legenda disponível
    return tracks[0] if tracks else None

# Expressão regular para identificar os blocos de um arquivo SRT
ENTRY_RE = re.compile(
    r"(\d+)\r?\n"                          # Captura o índice/número do bloco
    r"([\d:,]+ --> [\d:,]+)\r?\n"          # Captura o intervalo de tempo (timecode)
    r"([\s\S]*?)(?=\n\n|\Z)",              # Captura o texto do diálogo até o próximo bloco
    re.MULTILINE,                          # Modo multilinhas para processar o texto corretamente
)

# Função que transforma o texto bruto de um SRT em uma lista de dicionários
def parse_srt(text: str) -> list[dict]:
    # Inicializa a lista de entradas
    entries = []
    # Itera sobre todos os padrões encontrados pela expressão regular
    for m in ENTRY_RE.finditer(text.strip()):
        # Adiciona os dados capturados à lista
        entries.append({
            "index":    m.group(1), # Índice do bloco
            "timecode": m.group(2), # Tempo de exibição
            "text":     m.group(3).strip(), # Conteúdo do diálogo limpo
        })
    # Retorna a lista de objetos de legenda
    return entries

# Função que reconstrói o arquivo SRT a partir da lista de dicionários
def build_srt(entries: list[dict]) -> str:
    # Inicializa a lista que guardará os blocos formatados
    blocks = []
    # Itera sobre cada entrada da legenda
    for e in entries:
        # Formata o bloco seguindo o padrão SRT (Índice, Tempo, Texto)
        blocks.append(f"{e['index']}\n{e['timecode']}\n{e['text']}\n")
    # Une todos os blocos com uma quebra de linha entre eles
    return "\n".join(blocks)

# Função que realiza a tradução de uma lista de textos usando o Google Translate
def translate_batch(lines: list[str], source_lang: str = "auto") -> list[str]:
    # Tenta realizar a tradução
    try:
        # Instancia o tradutor configurando origem (automática ou definida) e destino (português)
        translator = GoogleTranslator(source=source_lang, target=TARGET_LANG)
        # Traduz a lista de textos de uma vez (a biblioteca lida com a concatenação interna se necessário)
        translated = translator.translate_batch(lines)
        # Retorna a lista de textos traduzidos
        return translated
    # Caso ocorra algum erro na tradução (ex: rede, limite de caracteres)
    except Exception as e:
        # Exibe o erro no console
        print(f"  [erro na tradução] {e}")
        # Retorna as linhas originais para não perder o fluxo do script
        return lines

# Função que coordena a tradução de todas as entradas da legenda em lotes
def translate_entries(entries: list[dict], source_lang: str = "auto") -> list[dict]:
    # Extrai apenas o texto de cada entrada da legenda
    texts = [e["text"] for e in entries]
    # Conta o total de blocos para exibição de progresso
    total = len(texts)
    # Inicializa a lista para armazenar os textos traduzidos
    translated_texts = []
    # Itera sobre os textos em pedaços (lotes) definidos pelo BATCH_SIZE
    for start in range(0, total, BATCH_SIZE):
        # Define o fim do lote atual
        end = min(start + BATCH_SIZE, total)
        # Separa o lote de textos
        batch = texts[start:end]
        # Calcula a porcentagem de conclusão
        pct = int(end / total * 100)
        # Exibe o progresso atual no terminal
        print(f"  Traduzindo blocos {start+1}–{end} de {total} ({pct}%) via Google Translate…")
        # Traduz o lote e adiciona à lista final
        translated_texts.extend(translate_batch(batch, source_lang))
    # Retorna uma nova lista de entradas mantendo os metadados mas com o texto traduzido
    return [
        {**e, "text": t} # Desempacota o original e sobrescreve a chave 'text'
        for e, t in zip(entries, translated_texts) # Pareia a entrada original com sua tradução
    ]

# Função que converte formatos de legenda (como ASS/SSA) para SRT se necessário
def convert_to_srt_if_needed(raw_path: str, codec: str) -> str:
    # Converte o nome do codec para minúsculas para facilitar a comparação
    codec_lower = codec.lower()
    # Se o codec já for SRT (SubRip), não precisa de conversão
    if "subrip" in codec_lower or "srt" in codec_lower:
        # Retorna o caminho original
        return raw_path
    # Define o novo caminho para o arquivo SRT convertido
    srt_path = raw_path + ".srt"
    # Executa o ffmpeg para converter o arquivo de legenda extraído para o padrão SRT
    result = run(["ffmpeg", "-y", "-i", raw_path, srt_path], check=False)
    # Se o ffmpeg executou com sucesso e o arquivo foi criado
    if result.returncode == 0 and Path(srt_path).exists():
        # Informa o usuário sobre a conversão realizada
        print(f"  Convertido de {codec} para SRT via ffmpeg.")
        # Retorna o caminho do novo arquivo
        return srt_path
    # Se falhar, avisa o usuário sobre a necessidade da ferramenta ou conversão manual
    print(f"  [aviso] Não foi possível converter o codec '{codec}' automaticamente.")
    # Sugere a instalação do ffmpeg
    print("          Instale o ffmpeg para suporte a conversão de legendas PGS/ASS.")
    # Encerra o script por impossibilidade técnica de processar o formato atual
    sys.exit(1)

# Função principal que orquestra todo o processo do script
def main():
    # Cria o objeto de parser para argumentos da linha de comando
    parser = argparse.ArgumentParser(
        description="Extrai e traduz legenda de um arquivo MKV para português usando Google Translate."
    )
    # Adiciona argumento obrigatório: o caminho do arquivo MKV
    parser.add_argument("mkv",           help="Caminho para o arquivo .mkv")
    # Adiciona opção para definir qual idioma extrair do MKV (padrão 'eng')
    parser.add_argument("--lang",        default="eng",  help="Código de idioma a extrair (padrão: eng)")
    # Adiciona opção para definir o idioma de origem na tradução (padrão 'auto' detectado pelo Google)
    parser.add_argument("--source-lang", default="auto", help="Idioma de origem (ex: 'en', 'es', 'ja'). Use 'auto' para detecção automática.")
    # Adiciona opção para definir o nome do arquivo de saída
    parser.add_argument("--output",      default=None,   help="Arquivo de saída .srt (padrão: mesmo nome do mkv + .pt.srt)")
    # Adiciona flag para apenas listar as faixas de legenda e encerrar
    parser.add_argument("--list-tracks", action="store_true", help="Lista as faixas de legenda e sai")
    # Processa os argumentos passados pelo usuário
    args = parser.parse_args()
    # Armazena o caminho do MKV em uma variável
    mkv_path = args.mkv
    # Verifica se o arquivo MKV realmente existe no caminho informado
    if not Path(mkv_path).exists():
        # Exibe erro se não encontrar o arquivo
        print(f"[ERRO] Arquivo não encontrado: {mkv_path}")
        # Encerra o script
        sys.exit(1)
    # Verifica se as ferramentas essenciais estão disponíveis no sistema
    require_tool("mkvmerge")
    # Verifica se o mkvextract está disponível
    require_tool("mkvextract")
    # Exibe mensagem de início de análise
    print(f"\nAnalisando faixas de legenda em: {mkv_path}")
    # Obtém a lista de faixas de legenda do arquivo MKV
    tracks = list_tracks(mkv_path)
    # Se não houver nenhuma legenda no arquivo
    if not tracks:
        # Informa o erro e encerra
        print("[ERRO] Nenhuma faixa de legenda encontrada no arquivo.")
        # Sai do script
        sys.exit(1)
    # Exibe o cabeçalho da tabela de faixas
    print(f"{'ID':>4}  {'Idioma':<8}  {'Codec':<20}  {'Nome'}")
    # Desenha uma linha separadora
    print("-" * 55)
    # Itera e exibe as informações de cada faixa encontrada
    for t in tracks:
        # Formata e imprime a linha com ID, Idioma, Codec e Nome da faixa
        print(f"{t['id']:>4}  {t['language']:<8}  {t['codec']:<20}  {t['name']}")
    # Se o usuário pediu apenas a listagem das faixas
    if args.list_tracks:
        # Encerra o script com sucesso
        sys.exit(0)
    # Seleciona a melhor faixa de legenda disponível com base nos critérios de idioma
    track = pick_track(tracks, args.lang)
    # Se nenhuma faixa foi selecionada (erro inesperado)
    if track is None:
        # Exibe erro e sai
        print("[ERRO] Nenhuma faixa adequada encontrada.")
        # Encerra o script
        sys.exit(1)
    # Informa qual faixa foi selecionada para o processamento
    print(f"\nUsando faixa ID={track['id']}  lang={track['language']}  codec={track['codec']}")
    # Cria um diretório temporário para trabalhar com os arquivos brutos extraídos
    with tempfile.TemporaryDirectory() as tmp:
        # Define a extensão temporária baseada no codec (ASS se for Advanced Substation, senão SRT)
        ext = "ass" if "ass" in track["codec"].lower() else "srt"
        # Define o caminho completo do arquivo bruto na pasta temporária
        raw_path = os.path.join(tmp, f"sub.{ext}")
        # Informa que a extração vai começar
        print("Extraindo legenda…")
        # Chama a função de extração
        extract_subtitle(mkv_path, track["id"], raw_path)
        # Converte a legenda extraída para o formato SRT caso seja necessário (ex: PGS ou ASS)
        srt_path = convert_to_srt_if_needed(raw_path, track["codec"])
        # Abre o arquivo SRT final para leitura
        with open(srt_path, encoding="utf-8", errors="replace") as f:
            # Lê todo o conteúdo textual da legenda
            srt_text = f.read()
    # Transforma o texto bruto do SRT em objetos Python processáveis
    entries = parse_srt(srt_text)
    # Se não conseguir encontrar blocos de legenda válidos no texto
    if not entries:
        # Exibe erro e encerra
        print("[ERRO] Não foi possível parsear o SRT. Verifique o arquivo.")
        # Sai do script
        sys.exit(1)
    # Exibe a quantidade de blocos que serão traduzidos
    print(f"Blocos de legenda encontrados: {len(entries)}")
    # Inicia o processo de tradução usando o motor do Google
    print(f"\nTraduzindo para português…")
    # Chama a função de tradução em lote passando o idioma de origem configurado
    translated = translate_entries(entries, source_lang=args.source_lang)
    # Define o caminho do arquivo final de saída (usa o informado ou gera um padrão .pt.srt)
    out_path = args.output or Path(mkv_path).with_suffix(".pt.srt")
    # Abre o arquivo de destino para escrita em UTF-8
    with open(out_path, "w", encoding="utf-8") as f:
        # Reconstrói o formato SRT com os textos traduzidos e salva no disco
        f.write(build_srt(translated))
    # Exibe mensagem final de sucesso indicando onde o arquivo foi salvo
    print(f"\n✅ Legenda traduzida salva em: {out_path}")

# Ponto de entrada padrão do Python
if __name__ == "__main__":
    # Chama a função principal
    main()
