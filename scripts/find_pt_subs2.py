# ==============================================================================
# Script: find_pt_subs2.py
#
# Objetivo:
#   Identificar o idioma das faixas de legenda em arquivos MKV lendo as
#   primeiras falas da legenda e escrevendo-as em um arquivo de texto para
#   inspeção visual manual humana, não automatizada.
#
# Lógica Principal:
#   Utiliza o ffprobe para listar todas as faixas e o ffmpeg para extrair e ler 
#   os primeiros segundos de cada uma. O texto extraído de cada ID é salvo
#   num log 'subtitles_peek.txt' para que o usuário identifique o ID de PT.
#
# Dependências Externas:
#   FFmpeg, FFprobe (devem estar instalados e no PATH)
# ==============================================================================
# Importação da biblioteca padrão de invocar outros softwares no prompt
import subprocess
# Importação para consumir dumps JSON de respostas de softwares
import json

# Função identificadora de canais textuais do filme
def get_subtitle_streams(mkv_path):
    # Docstring
    """
    Obtém uma lista de índices numéricos atrelados as streams de legendas no Matroska.
    """
    # Executa binário ffprobe com flags de formatação de log em JSON focado em CodecType
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=index,codec_type', '-of', 'json', mkv_path]
    # Inicia captura de stdout (Log do cmd) decodificando de bytes ansi pra string utf8 universal
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    # Transforma string em classe objeto iterável nativo (Dicionário ou Lista)
    data = json.loads(result.stdout)
    
    # Filtra os streams recursivamente apendizando apenas onde a flag é == subtitle
    subs = [s['index'] for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
    # Restitui valor ao pai
    return subs

# Injeta a agulha na trilha e chupa as palavras iniciais
def peek_subtitle(mkv_path, stream_idx):
    # Docstring explicativo do comportamento exato do ffmpeg
    """
    Extrai as primeiras linhas de uma faixa de legenda específica usando o ffmpeg.
    O "-" final força saída ao console ao inves de arquivo em HD.
    """
    # Array formatadora do FFmpeg 
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    
    # Executa o processo de forma assíncrona travando e puxando o tubo do stdout 
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    # Output placeholder
    out = []
    # Contador placeholder
    lines_read = 0
    # Dispara e descarrega o buffer gerado pelo ffmpeg (ele gera srt dinamicamente durante o processo)
    for line in process.stdout:
        # Coloca linha a linha
        out.append(line.strip())
        # Avança 1 na cota
        lines_read += 1
        # Lemos apenas as primeiras 20 linhas do SRT para abortar extrações gigantescas (Filtro de Performance)
        if lines_read > 20:
            # Sai do laço de leitura local
            break
            
    # Encerra o ffmpeg prematuramente cortando o cordão, matando seu PID, para liberar o processador
    process.terminate() 
    # Une com pular linha 
    return '\n'.join(out)

# Lista de arquivos para inspecionar, hardcoded manual pro dev
files = [
    # Rota 1
    r"Z:\Traducao\Lucky.2026.S01E01.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv",
    # Rota 2
    r"Z:\Traducao\Lucky.2026.S01E02.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv"
]

# Escrevemos os resultados consolidados diretamente em um arquivo de texto limpo para o usuário deitar o olho
with open('subtitles_peek.txt', 'w', encoding='utf-8') as f_out:
    # Laco dos caminhos 
    for f in files:
        # Escreve titulo 
        f_out.write(f"File: {f}\n")
        # Roda listagem
        subs = get_subtitle_streams(f)
        # Roda peek para cada legenda que foi listada
        for s in subs:
            # O processador devolve as strings 
            content = peek_subtitle(f, s)
            # Limpa o formato SRT via regex primitivo (remove linhas de números puras e remove os divisores temporais '00:00:00 -->') 
            lines = [l for l in content.split('\n') if l and not l.isdigit() and '-->' not in l]
            # Pega apenas as 3 primeiras frases isoladas e unidas por espaço
            text = " ".join(lines[:3])
            # Despeja as 3 linhas formatadas num único log 
            f_out.write(f"Stream {s}: {text}\n")
