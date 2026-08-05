# Importa o módulo 'os' para interagir com o sistema operacional e tratar caminhos
import os
# Importa o módulo 'sys' para funções de controle do script (como sys.exit para finalizar)
import sys
# Importa o módulo 'json' para lidar com os dados estruturados devolvidos pelo mkvmerge
import json
# Importa o módulo 'argparse' para lidar com os argumentos de linha de comando
import argparse
# Importa o módulo 'subprocess' para executar comandos e binários externos
import subprocess
# Importa o módulo 're' (Expressões Regulares) para buscar padrões de texto específicos
import re
# Importa 'Path' para trabalhar com caminhos de arquivos de forma orientada a objetos
from pathlib import Path
# Importa 'tempfile' para criar diretórios temporários para despejar arquivos intermediários
import tempfile

# ==============================================================================
# Script: extract_pt_sub.py
#
# Objetivo:
#   Procura a faixa de legenda em Português dentro de um arquivo MKV
#   fazendo uma análise heurística do conteúdo das legendas, sem confiar
#   cegamente nos metadados da faixa, que frequentemente são incorretos.
#
# Lógica Principal:
#   Extrai temporariamente todas as legendas do arquivo e avalia o conteúdo de cada 
#   uma contando a ocorrência de palavras-chave ("não", "você", etc.). A trilha
#   com a pontuação mais alta é exportada permanentemente como .pt.srt.
#
# Dependências Externas:
#   MKVToolNix (mkvmerge), FFmpeg
# ==============================================================================

# Configura o diretório padrão onde o pacote de ferramentas MKVToolNix fica instalado
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
# Configura o diretório exato do executável FFmpeg
FFMPEG_BIN     = r"C:\ffmpeg-2026-04-30-git-cc3ca17127-essentials_build\bin\ffmpeg.exe"

# Cria um dicionário que associa o nome do comando ao caminho exato no Windows
TOOLS = {
    # Mapeia mkvmerge para listar a estrutura do arquivo MKV
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    # Mapeia ffmpeg para fazer a extração propriamente dita das legendas
    "ffmpeg":    FFMPEG_BIN
}

# Wrapper para executar programas pelo console e interceptar sua saída de texto
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Se o nome do programa na lista bater com uma de nossas ferramentas configuradas...
    if cmd[0] in TOOLS:
        # Substituímos o atalho pelo caminho completo
        cmd[0] = TOOLS[cmd[0]]
    # Executa de fato e retorna o output como texto forçado para utf-8
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")

# Função que identifica quais faixas em um arquivo de vídeo são legendas
def list_subtitle_tracks(mkv_path: str) -> list[dict]:
    """Lista todas as faixas de legenda (subtitles) do arquivo MKV."""
    # Chama o mkvmerge em modo de relatório JSON (-J)
    result = run(["mkvmerge", "-J", mkv_path])
    # Converte o bloco de texto JSON que o programa retornou para uma variável Python
    info = json.loads(result.stdout)
    # Inicializa uma lista para guardar as trilhas
    tracks = []
    # Itera sobre todas as trilhas do vídeo
    for t in info.get("tracks", []):
        # Condiciona a pegar SOMENTE se for do tipo legenda ('subtitles')
        if t["type"] == "subtitles":
            # Extrai a propriedade ou retorna um ditado vazio caso não exista
            props = t.get("properties", {})
            # Grava as informações da legenda numa lista de dicionários
            tracks.append({
                "id":       t["id"],
                "codec":    t.get("codec", ""),
                "language": props.get("language", "und"),
                "name":     props.get("track_name", ""),
            })
    # Retorna o que filtrou
    return tracks

# Função fundamental para a heurística: tenta adivinhar se um texto está em Português
def is_portuguese(text: str) -> int:
    """
    Retorna uma pontuação baseada na quantidade de palavras muito comuns 
    na língua portuguesa. Quanto maior a pontuação, maior a chance de ser PT-BR.
    """
    # Lista de "stop words" e palavras do dia a dia da língua portuguesa
    # Usamos o \b no regex para indicar "Word Boundary" (fronteira de palavra), 
    # garantindo que só ache a palavra exata e não trechos de outra palavra
    pt_words = [r"\bnão\b", r"\bvocê\b", r"\bcom\b", r"\bum\b", r"\buma\b", r"\bele\b", r"\bela\b", r"\bisso\b", r"\baqui\b", r"\bquem\b", r"\bmuito\b", r"\btambém\b", r"\bsão\b", r"\bvocês\b", r"\bestá\b", r"\bjá\b"]
    # Zera a pontuação para esta legenda
    score = 0
    # Converte todo o texto extraído para minúsculo para simplificar a busca do regex
    text_lower = text.lower()
    # Para cada padrão de palavra em nossa lista de teste...
    for word_pattern in pt_words:
        # Usa re.findall para encontrar TODAS as ocorrências da palavra e soma a quantidade no score geral
        score += len(re.findall(word_pattern, text_lower))
    # Devolve a pontuação (score) de "quão português" o texto parece
    return score

# Função principal que agrupa todo o fluxo
def main():
    # Cria o avaliador de argumentos de linha de comando
    parser = argparse.ArgumentParser(description="Procura e extrai a faixa de legenda em Português de um MKV, identificando pelo conteúdo.")
    # Exige que seja passado obrigatoriamente um arquivo mkv
    parser.add_argument("mkv", help="Arquivo .mkv de entrada")
    args = parser.parse_args()

    # Formata a string do arquivo para Path Object
    input_file = Path(args.mkv)
    # Proteção: verifica se o MKV existe para não dar crash depois
    if not input_file.exists():
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        sys.exit(1)

    # Informa início de processo
    print(f"Listando faixas de '{input_file.name}'...")
    # Executa a função que lê do arquivo de vídeo só as faixas que são legendas
    tracks = list_subtitle_tracks(str(input_file))
    
    # Se retornou vazio (não tem legenda no vídeo)
    if not tracks:
        print("[ERRO] Nenhuma faixa de legenda encontrada no arquivo.")
        sys.exit(1)
        
    print(f"Encontradas {len(tracks)} faixas de legenda. Extraindo para análise...")
    
    # Prepara as variáveis de histórico para o algoritmo de "O maior vence"
    best_track = None
    best_score = 0
    best_text = ""
    
    # Cria uma pasta temporária (tmpdir) que vai sumir do PC quando terminar o bloco
    with tempfile.TemporaryDirectory() as tmpdir:
        # Array onde colocaremos os argumentos de -map pro ffmpeg
        maps = []
        # Dicionário que mapeará o ID da legenda ao seu arquivo gerado na pasta temporária
        track_files = {}
        # Prepara a instrução para retirar todas as legendas do vídeo simultaneamente
        for t in tracks:
            # Caminho de onde vai salvar a legenda da vez
            tmp_srt = Path(tmpdir) / f"{t['id']}.srt"
            # Salva o rastreio daquela ID
            track_files[t['id']] = tmp_srt
            # Informa no formato do ffmpeg: -map 0:ID arquivo.srt
            maps.extend(["-map", f"0:{t['id']}", str(tmp_srt)])
        
        # Junta a base de instrução com o mapeamento criado acima
        # Essa manobra tira todas as faixas usando uma única leitura do vídeo (super rápido)
        cmd = [TOOLS["ffmpeg"], "-y", "-i", str(input_file)] + maps
        # Roda o ffmpeg ocultando saídas para não encher a tela
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        print("Analisando o idioma das legendas...")
        # Percorre os IDs novamente, agora que os arquivos já foram gerados na pasta temp
        for t in tracks:
            tmp_srt = track_files[t['id']]
            # Se o arquivo temporário dela foi salvo mesmo pelo ffmpeg...
            if tmp_srt.exists():
                try:
                    # Tenta ler o conteúdo de texto da legenda usando formato unicode normal
                    text = tmp_srt.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    try:
                        # Se não conseguir ler em utf-8, tenta pelo formato antigo latin-1
                        text = tmp_srt.read_text(encoding="latin-1")
                    except:
                        # Se também der falha, ignora e pula pra próxima
                        continue
                
                # Joga o bloco de texto massivo que o ffmpeg extraiu na função pontuadora de PT-BR
                score = is_portuguese(text)
                # O clássico algoritmo para pegar a "melhor nota": se é maior que a atual, substitui
                if score > best_score:
                    best_score = score
                    best_track = t
                    best_text = text

    # Avaliação final: Achou alguma e teve score superior a 10?
    if best_track and best_score > 10:  # Mínimo de ocorrências para evitar falsos positivos
        print(f"\n[SUCESSO] Faixa de legenda em Português identificada!")
        print(f" - ID da faixa original: {best_track['id']}")
        print(f" - Pontuação de similaridade com PT: {best_score}")
        
        # Monta o nome base trocando a extensão final
        output_srt = input_file.with_suffix(".pt.srt")
        # Escreve fisicamente o texto do ganhador na mesma pasta que o MKV original
        output_srt.write_text(best_text, encoding="utf-8")
        print(f"Legenda salva em: {output_srt}")
    else:
        # Informa caso o placar de nenhuma chegou a passar de 10
        print("\n[ERRO] Não foi possível identificar com confiança uma faixa de legenda em Português.")

# Executa o block main() caso não seja um import via module
if __name__ == "__main__":
    main()
