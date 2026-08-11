# ==============================================================================
# Script: identify_subs.py
#
# Objetivo:
#   Identifica o idioma de trilhas de legenda sem nome dentro de um arquivo MKV
#   utilizando inteligência heurística (langdetect) para adivinhar a língua.
#
# Lógica Principal:
#   O script percorre as trilhas de legenda, lê as primeiras dezenas de linhas 
#   com ffmpeg e passa o resultado para a biblioteca 'langdetect'. O resultado 
#   é convertido para o padrão MKV (ISO 639-2) e gravado em um novo arquivo usando
#   o mkvmerge.
#
# Dependências Externas:
#   MKVToolNix (mkvmerge), FFmpeg, langdetect
# ==============================================================================
# Biblioteca manipuladora do SO
import os
# Biblioteca de chamadas via terminal cmd
import subprocess
# Biblioteca de JSON
import json
# Biblioteca de argumentos via prompt
import argparse
# Biblioteca de varredura Wildcard no OS (*.mkv)
import glob
# Biblioteca pesada NLP heurística de detecção de línguas estrangeiras (langdetect)
from langdetect import detect, DetectorFactory
# Paths modernos python 
from pathlib import Path

# Fixa o seed do gerador lógico para garantir resultados determinísticos (iguais em rodadas iguais) do langdetect
DetectorFactory.seed = 0

# Caminho absoluto estático para o executável do mkvmerge (Edita cabeçalhos sem recomprimir vídeo)
MKVMERGE_PATH = r"C:\Program Files\MKVToolNix\mkvmerge.exe"

# Dicionário hardcoded converte as duas letrinhas da WEB para o padrão internacional Matroska ISO de 3 letras
LANG_MAP = {
    'en': 'eng', 'pt': 'por', 'es': 'spa', 'fr': 'fre', 'de': 'ger',
    'it': 'ita', 'ja': 'jpn', 'zh-cn': 'chi', 'zh-tw': 'chi', 'ko': 'kor',
    'ru': 'rus', 'ar': 'ara', 'nl': 'dut', 'pl': 'pol', 'sv': 'swe',
    'da': 'dan', 'no': 'nor', 'fi': 'fin', 'tr': 'tur', 'el': 'gre',
    'he': 'heb', 'hi': 'hin', 'cs': 'cze', 'hu': 'hun', 'ro': 'rum',
    'th': 'tha', 'vi': 'vie', 'id': 'ind', 'bg': 'bul', 'hr': 'hrv',
    'uk': 'ukr', 'sk': 'slo', 'sl': 'slv',
}

# Despeja inicio do texto 
def peek_subtitle(mkv_path, stream_idx):
    # Docstring explicativo
    """
    Usa ffmpeg para extrair as primeiras falas de uma trilha de legenda
    para fins de detecção de idioma.
    """
    # Mapeia especificamente o stream :s: (legendas) para sair puro 
    cmd = ['ffmpeg', '-i', mkv_path, '-map', f'0:s:{stream_idx}', '-f', 'srt', '-v', 'quiet', '-']
    # Param 'errors=ignore' é vital para evitar crash violento se a legenda contiver fontes hebraicas mal codificadas ou símbolos obscuros
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore')
    # Resposta final 
    out = []
    # Count linhas lidas
    lines_read = 0
    
    # Lê as primeiras linhas suficientes para a rede neural NLP ter base teórica (cerca de 50 linhas)
    for line in process.stdout:
        # Poda invisíveis
        line = line.strip()
        # Se a linha existir e não for só número inteiro (ID legenda SRT) e não contiver setinha (Timestamps)
        if line and not line.isdigit() and '-->' not in line:
            # Strip tags HTML nativas de legendas estéticas ASS/SRT avançadas 
            clean_line = line.replace('<i>', '').replace('</i>', '').replace('<b>', '').replace('</b>', '')
            # Apenda buffer limpo
            out.append(clean_line)
            # Avança motor limite
            lines_read += 1
            # Se cruzou cota NLP
            if lines_read >= 50:
                # Mata loop 
                break
    # Mata binário FFMpeg forçadamente p/ não pesar 
    process.terminate()
    # Concatena numa string grandona única pro ML processar
    return ' '.join(out)

# Orquestrador individual
def process_mkv(mkv_path):
    # Nome 
    base_name = os.path.basename(mkv_path)
    # Pasta raiz 
    dir_name = os.path.dirname(mkv_path)
    # Retira ext 
    prefix = base_name.replace(".mkv", "")
    # Batiza o destino novo (Clone identificado e re-marcado)
    out_mkv = os.path.join(dir_name, f"{prefix}_Identified.mkv")
    
    # Ui 
    print(f"\n============================================================")
    print(f" Analisando legendas em: {base_name}")
    print(f"============================================================")
    
    # Obtém informações brutas e absolutas do MKV sem alterá-lo usando JSON mode (-J) do MKVToolNix
    cmd_j = [MKVMERGE_PATH, "-J", mkv_path]
    # Bloco Seguro
    try:
        # Captura log do mkvmerge
        res = subprocess.run(cmd_j, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        # Cria variável Python de dicionário 
        info = json.loads(res.stdout)
    # Fatal Fail 
    except Exception as e:
        # Aviso na tela
        print(f"[ERRO] Falha ao ler {base_name} com mkvmerge: {e}")
        # Aborta
        return
        
    # Faixas de leg separadas 
    subtitle_tracks = []
    # Índice que o ffmpeg usa (O FFmpeg numera apenas a própria categoria 0, 1, 2 e ignora videos entre elas)
    ffmpeg_sub_idx = 0
    
    # Percorre cada elemento de media do container mkv
    for track in info.get("tracks", []):
        # Valida que é do tipo sub 
        if track.get("type") == "subtitles":
            # Guarda a ID original real gravada no Container MKV mestre 
            track_id = track.get("id")
            # A função de extração ffmpeg exige o formato :s:index.
            # Roda na CPU chamando o bloco 
            sample_text = peek_subtitle(mkv_path, ffmpeg_sub_idx)
            # Default "und" (Undefined) se tudo der errado 
            lang_code_3 = "und"
            
            # NLP só roda e evita divZero se pelo menos teve 10 caracteres válidos pro motor
            if len(sample_text.strip()) > 10:
                # Bloco NLP Inteligente
                try:
                    # Envia textão, e LangDetect cospe um ISO code (ex: 'pt')
                    lang_2 = detect(sample_text)
                    # Transforma ISO WEB no ISO Matroska ('pt' -> 'por')
                    lang_code_3 = LANG_MAP.get(lang_2, lang_2)
                    # Log 
                    print(f"  - Trilha ID {track_id} (ffmpeg s:{ffmpeg_sub_idx}): Identificado como '{lang_code_3}' ({lang_2})")
                # Se falhar probabilidade 
                except:
                    # Log 
                    print(f"  - Trilha ID {track_id} (ffmpeg s:{ffmpeg_sub_idx}): Não foi possível identificar o idioma.")
            # Strings curtas demias 
            else:
                print(f"  - Trilha ID {track_id} (ffmpeg s:{ffmpeg_sub_idx}): Texto insuficiente para detecção.")
                
            # Apenda tupla final para gravarmos o mkv novo
            subtitle_tracks.append((track_id, lang_code_3))
            # Avança cursor exclusivo do FFmpeg 
            ffmpeg_sub_idx += 1
            
    # MKV sem legendas no container
    if not subtitle_tracks:
        print("  - Nenhuma trilha de legenda encontrada.")
        return
        
    # Comando de Escrita Rápida MKVMerge (Remuxing s/ re-encode, duração: ~1 segundo)
    cmd = [MKVMERGE_PATH, "-o", out_mkv]
    
    # Configura a flag de sobrescrita visual na etiqueta MKV para cada ID que detectamos e descobrimos a língua correta!
    for track_id, lang_code in subtitle_tracks:
        # Se NLP conseguiu definir 
        if lang_code != "und":
            # Injeta comando MKV Merge (Força lingua X no track Y)
            cmd.extend(["--language", f"{track_id}:{lang_code}"])
            
    # Adiciona a fonte final à cauda da string CMD 
    cmd.append(mkv_path)
    
    # Anuncia muxing (cópia binária direta no disco)
    print(f"\nGerando arquivo com metadados corrigidos: {out_mkv} ...")
    # Try mux 
    try:
        # Vai! 
        subprocess.run(cmd, check=True)
        print("Arquivo gerado com sucesso!")
    # Queda de disco rígido ou erro fatal de bytes
    except subprocess.CalledProcessError as e:
        print(f"[ERRO CRÍTICO] Falha na junção do mkv: {e}")

# Entrypoint default Terminal Python
def main():
    # Cria o interpretador de flags 
    parser = argparse.ArgumentParser(description="Identifica o idioma das trilhas de legendas e gera um novo MKV.")
    # Exige path
    parser.add_argument("alvo", help="Caminho para um arquivo MKV ou diretório.")
    # Leitor 
    args = parser.parse_args()
    
    # Transfere variavel 
    target = args.alvo
    
    # Fluxograma p/ Arquivo Isolado (Is File)
    if os.path.isfile(target):
        # Vai 
        process_mkv(target)
    # Fluxograma p/ Batch em Pasta 
    elif os.path.isdir(target):
        # Wildcard global
        for f in glob.glob(os.path.join(target, "*.mkv")):
            # Evita loop infinito processando arquivos que este próprio script acabou de criar 
            if f.endswith("_Identified.mkv") or f.endswith("_PT.mkv"):
                # Pula arquivo renderizado 
                continue
            # Vai
            process_mkv(f)
    # Falhas
    else:
        print(f"[ERRO] Caminho inválido: {target}")

# Clausula idiomatica proteçao root 
if __name__ == "__main__":
    main()
