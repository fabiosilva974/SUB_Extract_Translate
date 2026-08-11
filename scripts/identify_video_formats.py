# ==============================================================================
# Script: identify_video_formats.py
#
# Objetivo:
#   Analisar um arquivo de vídeo (como MKV, MP4) e exibir de forma legível
#   os formatos (codecs) de vídeo, áudio e legendas contidos nele, bem como
#   informações gerais sobre as faixas.
#
# Lógica Principal:
#   O script utiliza o utilitário 'ffprobe' (parte do pacote FFmpeg) para 
#   extrair os metadados do arquivo em formato JSON. Em seguida, ele analisa
#   os dados e imprime um relatório consolidado no console CLI.
#
# Dependências Externas:
#   FFmpeg / FFprobe (devem estar instalados e no PATH do sistema)
# ==============================================================================
# Interação OS
import os
# Interação system functions (exit, argv)
import sys
# Manipulação de dicionarios json format
import json
# Executar apps de cmd
import subprocess
# Parser das chamadas de console 
import argparse

# Formatador de strings matemáticas de bytes em Megas/Gigas limpos
def format_size(size_bytes):
    # Docstring
    """Formata o tamanho do arquivo em bytes para uma unidade legível (KB, MB, GB)."""
    # Exceção div zero 
    if size_bytes == 0:
        return "0B"
    # Unidades de medida estáticas
    size_name = ("B", "KB", "MB", "GB", "TB")
    # Cursor do loop
    i = 0
    # Equação base 1024 
    while size_bytes >= 1024 and i < len(size_name) - 1:
        # Subtrai casa
        size_bytes /= 1024.0
        # Pula categoria
        i += 1
    # Devolve formatado em 2 casas decimais Float
    return f"{size_bytes:.2f} {size_name[i]}"

# Inicia o scanner probe 
def analyze_video(file_path):
    # Docstring
    """Analisa o arquivo de vídeo usando ffprobe e exibe um relatório."""
    # Valida IO físico 
    if not os.path.exists(file_path):
        # Aborta printando defeito
        print(f"[ERRO] Arquivo não encontrado: {file_path}")
        return

    # Banner visual 
    print(f"\nAnalisando arquivo: {os.path.basename(file_path)}")
    print("=" * 60)

    # Comando complexo que extrai 100% dos metadados absolutos em formato JSON parseável
    cmd = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]

    # Bloco tentar capturar dados
    try:
        # Executa o comando travando e captura a saída textual (check=True engatilha excessao p/ return != 0)
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        # Transforma o mega texto JSON numa classe nativa do python 
        data = json.loads(result.stdout)
    # Erro nativo do processo ffmpeg
    except subprocess.CalledProcessError as e:
        print(f"[ERRO] Falha ao executar o ffprobe. Verifique se o vídeo é válido. {e}")
        return
    # Erro de variável PATH Windows não possuir o ffmpeg listado
    except FileNotFoundError:
        print("[ERRO] FFprobe não encontrado! Certifique-se de que o FFmpeg está instalado e no PATH.")
        return
    # Erro no parser (Arquivo sem header/sujo gerou JSON inválido)
    except json.JSONDecodeError:
        print("[ERRO] Falha ao ler os dados JSON retornados pelo ffprobe.")
        return

    # Extrai o sub-dicionário "format" do cabeçalho json
    fmt = data.get("format", {})
    # Salva tamanho total do container lendo string
    size_bytes = int(fmt.get("size", 0))
    # Salva duração macro lendo dict format
    duration = float(fmt.get("duration", 0))
    # Divide pra tirar minutos e segs 
    mins, secs = divmod(duration, 60)
    
    # Monta painel Console Log 
    print("INFORMAÇÕES GERAIS")
    print(f"  Container : {fmt.get('format_long_name', 'Desconhecido')}")
    print(f"  Tamanho   : {format_size(size_bytes)}")
    print(f"  Duração   : {int(mins)}m {int(secs)}s")
    print("-" * 60)

    # Extrai o array "streams" contendo a tupla completa das N fitas/faixas dentro do MKV
    streams = data.get("streams", [])
    
    # Preparando listas vazias agregadoras
    videos = []
    audios = []
    subs = []

    # Categoriza e lê cada fita contida no arquivo isoladamente
    for stream in streams:
        # Define se ela é vídeo ou som 
        codec_type = stream.get("codec_type")
        # Nome curto caixa alta (Ex: H264)
        codec_name = stream.get("codec_name", "Desconhecido").upper()
        # Algumas faixas têm nome longo completo técnico oficial e descritivo
        codec_long = stream.get("codec_long_name", "")
        
        # O sub-dicionario interno "tags" carrega os nomes de idiomas escritos pelos Fansubbers
        tags = stream.get("tags", {})
        # Undefined default caso fãs não rotularem a língua original 
        language = tags.get("language", "und")
        
        # Filtro de grupo Visual 
        if codec_type == "video":
            # Pega a resolução bidimensional pixels
            width = stream.get("width", "?")
            height = stream.get("height", "?")
            # Adiciona tag inteira no array videos[]
            videos.append(f"{codec_name} ({codec_long}) - Resolução: {width}x{height}")
            
        # Filtro de grupo Auditivo 
        elif codec_type == "audio":
            # Adiciona string contendo Idioma na lista audios[]
            audios.append(f"{codec_name} ({codec_long}) - Idioma: {language}")
            
        # Filtro de grupo Subtitles Textuais 
        elif codec_type == "subtitle":
            # Adiciona SRT strings no array subs[]
            subs.append(f"{codec_name} ({codec_long}) - Idioma: {language}")

    # UI Exibe as informações agrupadas de Vídeo listando por Numeração ordinal 
    print("VÍDEO")
    # Valida falhas
    if not videos:
        print("  Nenhuma faixa de vídeo encontrada.")
    # Enumerador enumera array incrementando 1 a partir do índice 1 (Humano)
    for idx, v in enumerate(videos, 1):
        print(f"  Faixa {idx}: {v}")
    
    # UI Exibe as informações de Áudio
    print("\nÁUDIO")
    # Validações 
    if not audios:
        print("  Nenhuma faixa de áudio encontrada.")
    # Itera
    for idx, a in enumerate(audios, 1):
        print(f"  Faixa {idx}: {a}")
        
    # UI Exibe as informações de Legendas
    print("\nLEGENDAS")
    # Valida
    if not subs:
        print("  Nenhuma faixa de legenda encontrada.")
    # Itera 
    for idx, s in enumerate(subs, 1):
        print(f"  Faixa {idx}: {s}")
        
    # Fechamento visual separador 
    print("=" * 60)

# Entrypoint default terminal Python run script.py 
def main():
    # Helper parser obj 
    parser = argparse.ArgumentParser(description="Analisa e exibe os formatos/codecs de um arquivo de vídeo.")
    # Param 1 required path 
    parser.add_argument("arquivo", help="Caminho para o arquivo de vídeo a ser analisado (ex: video.mkv)")
    # Parsed
    args = parser.parse_args()

    # Passa var cmd direto p/ engine principal 
    analyze_video(args.arquivo)

# Escudo anti importação indevida de bibliotecas cruzadas 
if __name__ == "__main__":
    main()
