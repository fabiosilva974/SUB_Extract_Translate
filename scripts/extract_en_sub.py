# Importa módulo para interagir com o sistema operacional e caminhos
import os
# Importa módulo para funções do sistema, como encerramento
import sys
# Importa módulo para trabalhar com arquivos JSON
import json
# Importa módulo para processar argumentos da linha de comando
import argparse
# Importa módulo para execução de processos e comandos externos
import subprocess
# Importa módulo de Expressões Regulares (Regex) para busca de padrões de texto
import re
# Importa a classe Path para manipulação robusta de caminhos e arquivos
from pathlib import Path
# Importa módulo para criar arquivos e pastas temporárias no sistema
import tempfile
# Importa módulo para expansão de caminhos com curingas (wildcards)
import glob

# ==============================================================================
# Script: extract_en_sub.py
#
# Objetivo:
#   Procura a faixa de legenda em Inglês dentro de um ou mais arquivos MKV
#   fazendo uma análise heurística do conteúdo das legendas, sem confiar
#   cegamente nos metadados da faixa. Suporta arquivos individuais ou diretórios.
#
# Lógica Principal:
#   Extrai temporariamente todas as trilhas de legenda para a memória (ou disco),
#   lê o conteúdo e conta a quantidade de palavras comuns da língua inglesa ("the",
#   "be", "to", etc.). A trilha com a pontuação mais alta é exportada como ".en.srt".
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
    # Mapeia mkvmerge para listar estrutura de MKV
    "mkvmerge":  os.path.join(MKVTOOLNIX_DIR, "mkvmerge.exe"),
    # Mapeia ffmpeg para extrair a legenda
    "ffmpeg":    FFMPEG_BIN
}

# Wrapper para executar programas pelo console e interceptar saída
def run(cmd: list[str], check=True) -> subprocess.CompletedProcess:
    # Substitui os nomes genéricos pelos caminhos absolutos mapeados no dicionário TOOLS
    if cmd[0] in TOOLS:
        # Troca pelo caminho absoluto
        cmd[0] = TOOLS[cmd[0]]
    # Executa o subprocesso de forma segura, decodificando o output para utf-8 ignorando falhas
    return subprocess.run(cmd, capture_output=True, text=True, check=check, encoding="utf-8", errors="replace")

# Função que identifica quais faixas em um arquivo de vídeo são legendas
def list_subtitle_tracks(mkv_path: str) -> list[dict]:
    # Analisa a estrutura do MKV retornando relatório JSON puro usando mkvmerge
    result = run(["mkvmerge", "-J", mkv_path])
    # Converte texto JSON para variáveis Python
    info = json.loads(result.stdout)
    # Inicializa lista de legendas vazia
    tracks = []
    
    # Itera sobre todas as faixas e filtra apenas as que são legendas (subtitles)
    for t in info.get("tracks", []):
        # Valida que o tipo é legenda
        if t["type"] == "subtitles":
            # Extrai dicionário de propriedades ou inicia vazio
            props = t.get("properties", {})
            # Grava dict da legenda atual
            tracks.append({
                "id":       t["id"],
                "codec":    t.get("codec", ""),
                "language": props.get("language", "und"),
                "name":     props.get("track_name", ""),
            })
    # Retorna as legendas
    return tracks

# Heurística para definir se a string dada é de fato idioma inglês
def is_english(text: str) -> int:
    """
    Retorna uma pontuação baseada na quantidade de palavras muito comuns 
    na língua inglesa.
    """
    # Lista das palavras mais frequentes na língua inglesa (usadas como heuristicas de word boundaries)
    en_words = [r"\bthe\b", r"\bbe\b", r"\bto\b", r"\bof\b", r"\band\b", r"\ba\b", 
                r"\bin\b", r"\bthat\b", r"\bhave\b", r"\bi\b", r"\bit\b", r"\bfor\b", 
                r"\bnot\b", r"\bon\b", r"\bwith\b", r"\bhe\b", r"\bas\b", r"\byou\b", 
                r"\bdo\b", r"\bat\b", r"\bthis\b", r"\bbut\b", r"\bhis\b", r"\bby\b", 
                r"\bfrom\b"]
    # Zera placar da legenda atual
    score = 0
    # Padroniza string forçando minúsculas
    text_lower = text.lower()
    
    # Adiciona 1 ponto à variável score para cada ocorrência de uma dessas palavras
    for word_pattern in en_words:
        # Usa regex pra caçar as match de fronteiras (tamanho do array regex) e soma
        score += len(re.findall(word_pattern, text_lower))
    # Devolve peso total da analise
    return score

# Processa um arquivo MKV isolado
def process_mkv(input_file: Path):
    # Banner arquivo da vez
    print(f"\n--- Processando '{input_file.name}' ---")
    # Checa se existe fisicamente
    if not input_file.exists():
        # Informa não encontrado
        print(f"[ERRO] Arquivo não encontrado: {input_file}")
        # Aborta
        return

    # Informa analise metadata
    print(f"Listando faixas de '{input_file.name}'...")
    # Executa identificador
    tracks = list_subtitle_tracks(str(input_file))
    
    # Checa lista gerada vazia
    if not tracks:
        # Aviso na tela
        print("[ERRO] Nenhuma faixa de legenda encontrada no arquivo.")
        # Sai da func
        return
        
    # Relata qtd
    print(f"Encontradas {len(tracks)} faixas de legenda. Extraindo para análise...")
    
    # Variaveis sentinela de resultado ganhador
    best_track = None
    best_score = 0
    best_text = ""
    
    # Inicia e amarra lixo temporário a esse bloco with (destruido ao sair)
    with tempfile.TemporaryDirectory() as tmpdir:
        # Array mapeador ffmpeg
        maps = []
        # Ditado de arquivos temporarios extraidos
        track_files = {}
        # Prepara a extração simultânea de TODAS as faixas de legenda para a pasta temporária
        for t in tracks:
            # Associa Path temp para um SRT com nome base = ID
            tmp_srt = Path(tmpdir) / f"{t['id']}.srt"
            # Registra no index de checagem pós extração
            track_files[t['id']] = tmp_srt
            # Injeta argumentos mapeadores (map streamID pro arquivo out tmp)
            maps.extend(["-map", f"0:{t['id']}", str(tmp_srt)])
        
        # O ffmpeg roda uma única vez e exporta os arquivos para cada '-map' configurado
        cmd = [TOOLS["ffmpeg"], "-y", "-i", str(input_file)] + maps
        # Síncrono oculto (DEVNULL tranca poluição cmd)
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Log da ação de CPU bound regex
        print("Analisando o idioma das legendas...")
        # Iterador em cima dos objetos temporários
        for t in tracks:
            # Saca caminho virtual da vez
            tmp_srt = track_files[t['id']]
            # Valida criação do ffmpeg
            if tmp_srt.exists():
                # Tenta leitura IO
                try:
                    # Carrega chunk total de strings usando padrão web moderno
                    text = tmp_srt.read_text(encoding="utf-8")
                # Exceção por encoding velho americano
                except UnicodeDecodeError:
                    # Fallback Windows nativo legado
                    try:
                        # Lê por bytes simples
                        text = tmp_srt.read_text(encoding="latin-1")
                    # Outra quebra
                    except:
                        # Pula 
                        continue
                
                # Despeja calhamaço de srt pro processador triturar word boundaries e devolve rating EN 
                score = is_english(text)
                # Verifica vencedor parcial
                if score > best_score:
                    # Elege novo vencedor e absorve propriedades
                    best_score = score
                    best_track = t
                    best_text = text

    # Limiar minimo de palavras achadas (Evita falsos positivos em musicas instrumentais soltas)
    if best_track and best_score > 10: 
        # Sucesso
        print(f"[SUCESSO] Faixa de legenda em Inglês identificada!")
        print(f" - ID da faixa original: {best_track['id']}")
        print(f" - Pontuação de similaridade com EN: {best_score}")
        
        # Gera nome final estático anexado ao do filme com sufixo en srt
        output_srt = input_file.with_suffix(".en.srt")
        # Flush de escrita para o HD Real
        output_srt.write_text(best_text, encoding="utf-8")
        # UI
        print(f"Legenda salva em: {output_srt}")
    # Derrota da heurística
    else:
        # Avisa que nenhum atingiu a base
        print("[ERRO] Não foi possível identificar com confiança uma faixa de legenda em Inglês.")

# Executável de entrada terminal
def main():
    # Helper parser descritor
    parser = argparse.ArgumentParser(description="Procura e extrai a faixa de legenda em Inglês de um ou mais arquivos MKV, ou de um diretório.")
    # Exige array de strings ilimitado (nargs +)
    parser.add_argument("paths", nargs="+", help="Arquivo(s) .mkv ou diretório(s) de entrada")
    # Avalia
    args = parser.parse_args()

    # Vazio MKV fila
    mkv_files = []
    
    # Expand paths using glob to handle wildcards passed by terminal
    expanded_paths = []
    # Roda paths passados args
    for path_str in args.paths:
        # Se usuário injetou curingas wildcard shell (* ou ?)
        if "*" in path_str or "?" in path_str:
            # Usa biblioteca de varredura globbing apendizando a lista com resultados desdobrados do OS
            expanded_paths.extend(glob.glob(path_str))
        # Se for um nome direto único normal
        else:
            # Adiciona tal qual injetado
            expanded_paths.append(path_str)
    
    # Validações dos itens do wildcard/passados
    for path_str in expanded_paths:
        # Formata Objeto
        p = Path(path_str)
        # Se for file MKV
        if p.is_file() and p.suffix.lower() == ".mkv":
            # Evita duplicatas na array fila
            if p not in mkv_files:
                mkv_files.append(p)
        # Se for só uma pasta enviada
        elif p.is_dir():
            # Varredura glob de nivel 1 puxando tudo dentro
            for mkv_file in p.glob("*.mkv"):
                # Evita repetecos recursivos da lógica
                if mkv_file not in mkv_files:
                    mkv_files.append(mkv_file)
        # Senão, arquivo bizarro ignorado
        else:
            print(f"[AVISO] Ignorando caminho inválido ou não-mkv: {path_str}")

    # Sem trabalho, sai fora
    if not mkv_files:
        print("[ERRO] Nenhum arquivo MKV válido encontrado para processar.")
        sys.exit(1)
        
    # Informa qtd 
    print(f"Total de arquivos MKV para processar: {len(mkv_files)}")
    
    # Laço motor mestre de execução paralela iterada das tarefas de encoding
    for mkv in mkv_files:
        process_mkv(mkv)

# Proteção main idiomatica base python script run only
if __name__ == "__main__":
    main()
