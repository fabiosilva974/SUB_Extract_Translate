# ==============================================================================
# Script: mux_pt_subs.py
#
# Objetivo:
#   Embutir (mux) as legendas traduzidas em português num arquivo MKV,
#   configurando corretamente qual será o áudio e a legenda "default".
#
# Lógica Principal:
#   O script procura legendas externas '.pt.srt', varre as propriedades do arquivo de
#   vídeo usando o 'mkvmerge -J' para localizar o áudio em Japonês e legendas.
#   Depois, desabilita a propriedade 'default_track' de todas as outras faixas
#   e adiciona a nova legenda externa e o áudio em JP como default no arquivo '_PT.mkv'.
#
# Dependências Externas:
#   MKVToolNix (mkvmerge)
# ==============================================================================
# Import OS IO 
import os
# Import Varredura arquivos 
import glob
# Import Disparo cmd 
import subprocess
# Import Parser log JSON mkvmerge 
import json
# Import args bash 
import argparse
# Paths padrao 
from pathlib import Path

# Caminho absoluto para o executável do mkvmerge sem precisar de PATH Win 
MKVMERGE_PATH = r"C:\Program Files\MKVToolNix\mkvmerge.exe"

# Motor de mesclagem 
def process_mkv(mkv_path):
    # Trunca nome curio 
    base_name = os.path.basename(mkv_path)
    # Diretorio raiz 
    dir_name = os.path.dirname(mkv_path)
    # Tira .mkv do nome 
    prefix = base_name.replace(".mkv", "")
    
    # Procura regex por arquivos soltos de legenda na mesma exata pasta seguindo a tag 'pt'
    srt_pattern = os.path.join(dir_name, f"{prefix}*.pt.srt")
    ass_pattern = os.path.join(dir_name, f"{prefix}*.pt.ass")
    # Une os dois arrays achados pelo OS
    subs = glob.glob(srt_pattern) + glob.glob(ass_pattern)
    
    # Valida vazio 
    if not subs:
        print(f"[AVISO] Nenhuma legenda PT (.pt.srt ou .pt.ass) encontrada para: {base_name}")
        return
    
    # Pega apenas a 1 ocorrencia encontrada (A principal)
    sub_path = subs[0]
    
    # Executa mkvmerge -J para obter informações precisas sobre os pacotes sem corromper a midia 
    cmd_j = [MKVMERGE_PATH, "-J", mkv_path]
    # Bloco try
    try:
        # Puxa 
        res = subprocess.run(cmd_j, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        # Parse 
        info = json.loads(res.stdout)
    # Falhas 
    except Exception as e:
        print(f"[ERRO] Falha ao ler informações de {base_name}: {e}")
        return
    
    # Track ID de JP 
    jap_audio_id = None
    # Arrays salvadoras 
    default_audios = []
    default_subs = []
    
    # Analisa as faixas que ja existem dentro do mkv antigo cru 
    for track in info.get("tracks", []):
        # Tipo legenda/video 
        track_type = track.get("type")
        # Numero ID (1,2)
        track_id = track.get("id")
        # Sub JSON 
        props = track.get("properties", {})
        
        # O objetivo é matar a dublagem PT-BR default se houver e priorizar Audio-JP
        if track_type == "audio":
            # Achei japones 
            if props.get("language") == "jpn":
                # Salva a flag dele 
                jap_audio_id = track_id
            # Se a trilha x estiver marcada como default (toca sozinha)
            if props.get("default_track"):
                # Guarda ID da vitima a ser capada
                default_audios.append(track_id)
        # Se for legenda 
        elif track_type == "subtitles":
            # Se for legenda default antiga (Inglês)
            if props.get("default_track"):
                # Guarda ID da vitima 
                default_subs.append(track_id)
                
    # Falhas ao localizar audio 
    if jap_audio_id is None:
        # Aviso 
        print(f"[AVISO] Áudio em Japonês não encontrado em: {base_name}")
        # Ainda vamos continuar e apenas adicionar a legenda PT se não tiver JP?
        # Sim, continuamos, apenas não alteramos o áudio. (Comentario logico preservado)
    
    # Configura Output path com sufixo pra evitar corrupcao 
    out_mkv = os.path.join(dir_name, f"{prefix}_PT.mkv")
    
    # Se ja rodei 
    if os.path.exists(out_mkv):
        print(f"[AVISO] O arquivo {os.path.basename(out_mkv)} já existe. Pulando...")
        return
    
    # Constrói o comando master do mkvmerge sem flags destrutivas 
    cmd = [MKVMERGE_PATH, "-o", out_mkv]
    
    # Remove a flag de default dos áudios indesejados e põe no jap 
    if jap_audio_id is not None:
        # Itera velhos 
        for aid in default_audios:
            # Se nao for jap 
            if aid != jap_audio_id:
                # Mata bool 
                cmd.extend(["--default-track-flag", f"{aid}:no"])
        # Define o áudio em Japonês intocável como reprodução padrão (Yes)
        cmd.extend(["--default-track-flag", f"{jap_audio_id}:yes"])
            
    # Remove a flag de default de TODAS as legendas velhas cegas do tracker 
    for sid in default_subs:
        # Mata (O MXPlayer não tocará elas de imediato)
        cmd.extend(["--default-track-flag", f"{sid}:no"])
        
    # Adiciona o arquivo MKV original em si pro mux ser engolido
    cmd.append(mkv_path)
    
    # Injeta arquivo local de texto (SRT) forçando que os players assumam ele 
    cmd.extend([
        # ID 0 do SRT será idioma PT
        "--language", "0:por",
        # Nome da Track
        "--track-name", "0:Português (BR)",
        # Força ela como principal
        "--default-track-flag", "0:yes",
        # Caminho do HD pro txt
        sub_path
    ])
    
    # Print status 
    print(f"\n============================================================")
    print(f" Muxing: {out_mkv}")
    print(f"============================================================")
    
    # Tentativa IO 
    try:
        # Executa a junção sem capturar a saída, permitindo que o usuário veja o progresso no terminal em Real-Time da MKVTool
        subprocess.run(cmd, check=True)
        print(f"Arquivo gerado com sucesso!")
    # Crash 
    except subprocess.CalledProcessError as e:
        print(f"[ERRO CRÍTICO] Falha ao processar o arquivo: {e}")

# Executor shell cli 
def main():
    # Helper 
    parser = argparse.ArgumentParser(description="Adiciona legenda PT-BR e altera áudio default para JP em arquivos MKV.")
    # Exige arg
    parser.add_argument("diretorio", help="Caminho para o diretório contendo os arquivos .mkv e .pt.srt")
    args = parser.parse_args()
    
    # Mapeia path 
    target_dir = args.diretorio
    # Varredura fake
    if not os.path.isdir(target_dir):
        # Crashes 
        print(f"[ERRO] O caminho especificado não é um diretório válido: {target_dir}")
        return
        
    # Lista todo *.mkv na raiz absoluta dele 
    mkv_files = glob.glob(os.path.join(target_dir, "*.mkv"))
    # For laço iterativo 
    for mkv in mkv_files:
        # Pula arquivos que já foram processados por este script (evita loops infinitos ou arquivos corrompidos "_PT_PT_PT.mkv")
        if mkv.endswith("_PT.mkv"):
            continue
        # Dispara orquestrador filho 
        process_mkv(mkv)

# Runtime 
if __name__ == "__main__":
    main()
