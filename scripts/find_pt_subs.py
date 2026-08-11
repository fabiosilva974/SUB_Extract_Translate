# ==============================================================================
# Script: find_pt_subs.py
#
# Objetivo:
#   Rascunho simples/experimento para encontrar faixas de legendas em português.
#   Usa FFprobe em vez de mkvmerge para identificar as faixas e testa as primeiras
#   linhas com heurística básica de dicionário PT-BR.
#
# Lógica Principal:
#   Invoca o FFprobe para pegar os índices das trilhas de legenda, depois
#   usa o FFmpeg para ler um número pequeno de linhas via pipe. Imprime 
#   os resultados no console se as palavras-chave PT-BR baterem.
#
# Dependências Externas:
#   FFmpeg, FFprobe (devem estar instalados e no PATH)
# ==============================================================================
# Importação do módulo de comunicação com terminal e captura de stdout
import subprocess
# Importação do parseador de arquivos e relatórios em formato JSON (Padrão WEB)
import json

# Função para listar numericamente as faixas de vídeo/audio/legenda 
def get_subtitle_streams(mkv_path):
    """Obtém os índices das faixas de legenda através do ffprobe."""
    # Comando ffprobe limitando a saída apenas aos índices (ID: 0,1,2,3) e tipos de codec, estruturado em JSON
    cmd = ['ffprobe', '-v', 'error', '-show_entries', 'stream=index,codec_type', '-of', 'json', mkv_path]
    # Dispara comando no ambiente sub shell nativo
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
    # Recepciona todo o print do terminal dentro da variável data como objeto Python 
    data = json.loads(result.stdout)
    # List Comprehension avançada: Puxa o número do índice somente e se o codec for estritamente legendas
    subs = [s['index'] for s in data.get('streams', []) if s.get('codec_type') == 'subtitle']
    # Devolve a mini-lista filtrada (Ex: [2, 4, 5])
    return subs

# Função extratora por Popen 
def peek_subtitle(mkv_path, stream_idx):
    """Usa ffmpeg pipe para ler as primeiras 20 linhas da legenda na memória sem extrair arquivo fisico."""
    # Monta comando que extrai (-map), forçadamente via SRT (-f), emudecido (-v quiet), e envia pro buffer terminal hifen (-)
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    # Roda o ffmpeg em um Popen assíncrono para ler a saída em stream realtime ao invés de esperar o final (O que extrairia o filme todo atoa)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    # Array de buffers
    out = []
    # Contador manual
    lines_read = 0
    # Loop contínuo que esvazia a fila do pipe do terminal conforme as palavras surgem 
    for line in process.stdout:
        # Limpa quebras e joga na nossa variavel String out 
        out.append(line.strip())
        # Avança limite
        lines_read += 1
        # Se bateu cota (Limitador para poupar RAM e tempo de IO de 1 segundo)
        if lines_read > 20:
            # Cancela abruptamente
            break
    # Força o assassinato do processo órfão do FFmpeg que ficou rodando pra sempre travado 
    process.terminate()
    # Retorna o texto concatenado inteiro como 1 único parágrafo quebrado
    return '\n'.join(out)

# Array estática com caminhos absolutos hardcoded (Exclusivamente p/ testes locais do dev)
files = [
    # Elemento 1 (MKV 1)
    r"Z:\Traducao\Lucky.2026.S01E01.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv",
    # Elemento 2 (MKV 2)
    r"Z:\Traducao\Lucky.2026.S01E02.1080p.HEVC.x265-MeGusta[EZTVx.to].mkv"
]

# Roda o simulador de bancada para cada elemento do array
for f in files:
    # Print 
    print(f"File: {f}")
    # Busca 
    subs = get_subtitle_streams(f)
    # Loga
    print(f"Found subtitle streams: {subs}")
    # Interage e disseca os retornos
    for s in subs:
        # Puxa conteudo bufferizado
        content = peek_subtitle(f, s)
        # Bate na heurística porca hardcoded com padronização minúscula (Lower-case)
        if ' não ' in content.lower() or ' você ' in content.lower() or ' que ' in content.lower() or ' para ' in content.lower():
            # A simple heuristic for Portuguese, though 'que', 'para' also in Spanish
            # Retira números puros de timecode e retira a setinha clássica de srt '-->' do meio do texto
            lines = [l for l in content.split('\n') if l and not l.isdigit() and '-->' not in l]
            # Mescla pegando só os 3 primeiros dialogos úteis extraidos
            text = " ".join(lines[:3])
            # Imprime provando quem venceu
            print(f"Stream {s}: {text}")
