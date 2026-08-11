# ==============================================================================
# Script: batch_process_windows.py
#
# Objetivo:
#   Processar em lote vídeos a partir de uma lista CSV ou arquivo único,
#   convertendo-os nativamente para H.265 usando hardware AMD (AMF) no Windows.
#
# Lógica Principal:
#   Extrai metadados, formata e higieniza nomes de arquivos. Tenta conversão
#   por hardware AMD; descarta os arquivos se ficarem maiores que o original.
#
# Dependências Externas:
#   guessit (requer instalação via pip)
#   FFmpeg e FFprobe (devem estar instalados e no PATH do sistema)
# ==============================================================================
# Importação do módulo de interações com o sistema operacional
import os
# Importação do módulo para funções e variáveis do sistema
import sys
# Importação do módulo para trabalhar com tempo e delays
import time
# Importação do módulo para parsear dados no formato JSON
import json
# Importação do módulo para execução de comandos externos no terminal (FFmpeg)
import subprocess
# Importação do módulo para parsear argumentos de linha de comando
import argparse
# Importação da classe Path para lidar com caminhos de forma segura cross-plataforma
from pathlib import Path

# Bloco try-except para tentar importar a biblioteca 'guessit'
try:
    # Importa guessit, que extrai tags lógicas de nomes confusos de filmes
    from guessit import guessit
# Captura erro
except ImportError:
    # Mostra mensagem
    print("ERRO: Biblioteca 'guessit' não encontrada. Rode: pip install guessit")
    # Fecha execução em erro
    exit(1)

# Função encarregada de puxar informações brutas do arquivo via FFprobe
def get_video_metadata(file_path):
    # String array contendo os argumentos do FFprobe solicitando JSON
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)]
    # Bloco tentar
    try:
        # No Windows, shell=True pode ajudar a encontrar o binário se houver problemas de PATH, mas geralmente não é necessário
        # Roda trancando a main thread e capta output
        result = subprocess.run(cmd, capture_output=True, check=True)
        # Decodifica pra UTF-8 evitando falhas em cmd antigo CP1252 do Windows
        stdout_str = result.stdout.decode('utf-8', errors='replace')
        # Parseia em ditado Python
        data = json.loads(stdout_str)
    # Exceção
    except Exception:
        # Entrega vazios
        return None, False
    # Var pra guardar Resolução
    width = None
    # Booleano hevc start False
    is_hevc = False
    # Itera por faixas de vídeo e áudio
    for stream in data.get("streams", []):
        # Captura nome do codec forçando minusculas
        codec = stream.get("codec_name", "").lower()
        # Confirma tipo vídeo
        if stream.get("codec_type") == "video":
            # Guarda a largura (resolução horizontal)
            if not width: width = stream.get("width")
            # Valida se e h265 ou nova geração
            if codec in ("hevc", "h265", "x265", "av1", "vp9"): is_hevc = True
    # Devolve a tupla
    return width, is_hevc

# Função para sanitização de strings
def sanitize_title(title):
    # Tira aspas diversas
    title = title.replace("'", "_").replace("’", "_").replace(" ", ".")
    # Achata formatações falhas duplas para manter estetica limpa
    while ".." in title: title = title.replace("..", ".")
    # Fim
    return title

# Função que gera nomenclatura amigavel com guessit
def generate_new_name(original_path, width):
    # Analisa texto original abstrato
    guess = guessit(original_path.name)
    # Puxa main title
    title = guess.get('title', original_path.stem)
    
    # Alternativo título caso filme japonês/europeu
    alt_title = guess.get('alternative_title')
    if alt_title:
        title = f"{title}.{alt_title}"
        
    # Vars extras
    year = guess.get('year', '')
    season = guess.get('season')
    episode = guess.get('episode')
    episode_title = guess.get('episode_title')
    
    import re
    # Override de segurança para Animes (Ex: [Erai-raws] Tokyo 24-ku - 11 ...)
    # Impede que números no nome (24-ku) sejam confundidos com o episódio
    anime_match = re.match(r'^(?:\[.*?\]\s*)?(.+?)\s+-\s+(\d+(?:\.\d+)?(?:v\d+)?)', original_path.name)
    if anime_match:
        title = anime_match.group(1)
        episode = anime_match.group(2)
        season = None
        episode_title = None
    
    # Corrige fallbacks se o título da obra estiver embutido no episode title
    if not season and not episode and episode_title:
        title = f"{title}.{episode_title}"
        episode_title = None
        
    # Limpa
    title = sanitize_title(title)
    
    # Busca flag hardcoded de tela (ex: 1080p, Bluray)
    resolution = guess.get('screen_size')
    # Senão tiver no título, tenta derivar do FFprobe
    if not resolution:
        w = int(width) if width else 0
        if w >= 3800: resolution = "2160p"
        elif w >= 1900: resolution = "1080p"
        elif w >= 1200: resolution = "720p"
        else: resolution = "480p"

    # Junta 
    parts = [title]
    if year:
        # Coloca ano
        parts.append(str(year))
        
    # Formata Season/Ep
    if season is not None:
        if isinstance(season, list): season = season[0]
        s_str = f"S{int(season):02d}"
        if episode is not None:
            if isinstance(episode, list): episode = episode[0]
            s_str += f"E{int(episode):02d}"
        parts.append(s_str)
    # Ep isolado
    elif episode is not None:
        if isinstance(episode, list): episode = episode[0]
        parts.append(f"E{int(episode):02d}")
        
    # Título do capitulo especifico
    if episode_title:
        if isinstance(episode_title, list): episode_title = episode_title[0]
        parts.append(sanitize_title(episode_title))
        
    # Res
    if resolution and resolution != "Unknown":
        parts.append(str(resolution))
        
    # Tag final mandatória
    parts.append("H265")
    
    # Re-une tudo em formato ponto e acopla a extensão MP4/MKV pre-existente
    return ".".join(parts) + original_path.suffix

# Funcao Orquestradora do subprocess FFmpeg
def encode_video(input_path, output_path, quality=26):
    # Array FFmpeg focado na placa AMD em ambiente Windows
    cmd = [
        "ffmpeg", "-y",               # Supersede/overwrite without ask
        "-hwaccel", "dxva2",          # DXVA2 (Hardware Decoding robusto pro Windows)
        "-i", str(input_path),        # Entrada no OS Windows
        "-map", "0",                  # Mapeia todas trilhas
        "-c:v", "hevc_amf",           # Advanced Media Framework da AMD (Codec)
        "-quality", "quality",        # Preset visual de qualidade interna AMF
        "-rc", "cqp",                 # Rate Control do AMF = Constant Quantization Parameter
        "-qp_p", str(quality),        # P-Frames weight
        "-qp_i", str(quality),        # I-Frames weight
        "-c:a", "copy",               # Audio copy original
        "-c:s", "copy",               # Sub copy original
        "-f", "matroska",             # Força mkv
        str(output_path)              # Saida Windows Path
    ]
    
    # Processo rodado
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
    # Log temporario
    log_output = []
    # Loop leitor
    for line in process.stdout:
        log_output.append(line)
        # Encontra andamentos de tempo/fps
        if "frame=" in line or "time=" in line:
            # Re-escreve por cima da mesma linha no console windows CMD \r
            print(f"\r{line.strip()}", end="")
    # Fica em estado de Halt até o FFmpeg desatracar da RAM
    process.wait()
    # Pula linha esteticamente pra não colar na proxima frase do print
    print()
    # Identifica falha
    if process.returncode != 0:
        # UI de Erro
        print("\n=== LOG DE ERRO DO FFMPEG ===")
        # Imprime 15 últimas de buffer 
        print("".join(log_output[-15:]))
        print("=============================\n")
    # Retorna bool do sucesso da thread
    return process.returncode == 0

# Orquestrador do Processo Unico do Arquivo
def process_file(file_path, delete_original=False):
    # Prevenção inicial
    if not file_path.exists():
        print(f"Erro: Arquivo não existe {file_path}")
        return False
        
    # Get Metadata FFprobe
    width, is_hevc = get_video_metadata(file_path)
    # Bypass 
    if is_hevc:
        print(f"O arquivo {file_path.name} já é HEVC. Pulando.")
        return True
        
    # Gera label do nome com classe Guessit
    new_name = generate_new_name(file_path, width)
    # Constrói string do destino com a variação correta
    final_dest = file_path.parent / new_name
    
    # Bypass 2
    if final_dest.exists():
        print(f"O destino já existe: {final_dest.name}. Pulando.")
        return True
        
    # Imprime visual target
    print(f"\n[{file_path.name}] Iniciando processamento (Windows)...")
    print(f"  -> Nome final será: {new_name}")
    
    # Var pra nome temporário com suffix .part
    encoded_temp = file_path.parent / (new_name + ".part")
    
    # Capta inicio
    start_time = time.time()
    # Inicia motor AMD
    print("  -> Lendo e escrevendo diretamente pela rede...")
    # Engatilha função de encoding
    success = encode_video(file_path, encoded_temp)
    # Contabiliza decorrido
    elapsed = time.time() - start_time
    
    # Trata anomalias
    if not success or not encoded_temp.exists():
        print("  [ERRO] A conversão falhou!")
        # Expulsa resto
        if encoded_temp.exists(): encoded_temp.unlink()
        return False
        
    # Calcula e avalia resultados mb
    orig_size = file_path.stat().st_size / (1024*1024)
    new_size = encoded_temp.stat().st_size / (1024*1024)
    
    # Escudo Anti-Inchaço (Tamanho)
    if new_size >= orig_size:
        print("  -> [ANTI-INCHAÇO] O arquivo H265 ficou MAIOR que o original H264!")
        print("  -> Descartando a conversão para economizar espaço e mantendo o original intacto.")
        # Elimina do disco a burrada da AMD
        encoded_temp.unlink()
        # Matemática
        mins, secs = divmod(elapsed, 60)
        # Loga desperdício pro user
        print(f"  [DESCARTADO] Tempo desperdiçado: {int(mins)}m {int(secs)}s | Tamanho: {orig_size:.1f}MB -> {new_size:.1f}MB")
        return True

    # Consagra sucesso visualmente
    print("  -> Finalizando arquivo convertido...")
    # Retira tag '.part'
    encoded_temp.rename(final_dest)
    
    # Executa checagem parametrica de ordem
    if delete_original:
        print("  -> Excluindo arquivo original na rede...")
        # Apaga raiz H264
        file_path.unlink()
    else:
        # Mantem e avisa
        print("  -> Mantendo arquivo original na rede (Fase 1 - QA).")
        
    # Log de Conclusão temporal
    mins, secs = divmod(elapsed, 60)
    print(f"  [CONCLUÍDO] Tempo: {int(mins)}m {int(secs)}s | Tamanho: {orig_size:.1f}MB -> {new_size:.1f}MB")
    return True

# Main Entrypoint Routine
def main():
    # Inicializa parseador de CLI
    parser = argparse.ArgumentParser(description="Conversor Nativo Windows (In-Place na Rede)")
    # Argumento isolado opcional
    parser.add_argument("--input", help="Arquivo de vídeo único para processar")
    # Planilha Excel (CSV)
    parser.add_argument("--csv", help="Caminho para o CSV de mapeamento")
    # Flag varredura total
    parser.add_argument("--all", action="store_true", help="Processar todos os arquivos do CSV (ignora a flag de Lote Piloto)")
    # Flag apagamento de roots
    parser.add_argument("--delete", action="store_true", help="Deletar o original após sucesso")
    # Interpreta injetados
    args = parser.parse_args()
    
    # Rota Single File
    if args.input:
        # Instancia objeto
        input_path = Path(args.input).resolve()
        # Checa legitimidade de path e arquivo unico
        if input_path.is_file():
            # Encaminha à esteira
            process_file(input_path, args.delete)
        else:
            # Imprime correção de sintaxe pro usuario do powershell
            print("Para --input, passe o caminho exato do arquivo .mkv")
    
    # Rota Mass File Excel
    elif args.csv:
        # Instancia objeto CSV
        csv_path = Path(args.csv).resolve()
        # Valida CSV
        if not csv_path.exists():
            print(f"Erro: CSV não encontrado em {csv_path}")
            return
            
        # Importa CSV handler python (Somente lido se a rota cair aqui)
        import csv as csv_lib
        # Fila de strings array
        to_process = []
        # Tenta abrindo forçando remoção de BOM UTF8 pra evitar bug de nome invisivel
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            # Usa DictReader 
            reader = csv_lib.DictReader(f, delimiter=';')
            # Extrai colunas
            for row in reader:
                # Regras de negocio 
                if args.all or row.get('Lote_Piloto') == 'SIM':
                    # Array apendiza URL
                    to_process.append(row['Caminho_Completo_Original'])
                    
        # Monta label UI
        desc = "toda a biblioteca" if args.all else "o Lote Piloto"
        # Print
        print(f"Encontrados {len(to_process)} vídeos para {desc}.")
        # Laco Final Orquestrador
        for path_str in to_process:
            # Universal Path Translator (Linux -> Windows)
            # Traduz montagens pra formato de Windows UNC Universal Naming Convention SMB
            path_str = path_str.replace("/mnt/Media/", "\\\\192.168.0.99\\Media\\")
            # Substitui barras nativas invertidas
            path_str = path_str.replace("/", "\\")
            
            # Encapsula na classe Object
            file_path = Path(path_str)
            # Envia o processo pra thread
            process_file(file_path, args.delete)
            
        # Avisa 
        print(f"\nProcessamento concluído para {desc}!")
    # Missing args
    else:
        # Help auto gerado CLI 
        parser.print_help()

# Boilerplate padrão Python que protege e inicializa script unicamente
if __name__ == "__main__":
    main()
