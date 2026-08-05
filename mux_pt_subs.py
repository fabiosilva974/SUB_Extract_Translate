# ==============================================================================
# Script: mux_pt_subs.py
#
# Objetivo:
#   Embutir (mux) as legendas traduzidas em português num arquivo MKV,
#   configurando corretamente qual será o áudio e a legenda "default".
#
# Lógica Principal:
#   O script procura legendas '.pt.srt', varre as propriedades do arquivo de
#   vídeo usando o 'mkvmerge -J' para localizar o áudio em Japonês e legendas.
#   Depois, desabilita a propriedade 'default_track' de todas as outras faixas
#   e adiciona a nova legenda e o áudio em JP como default no arquivo '_PT.mkv'.
#
# Dependências Externas:
#   MKVToolNix (mkvmerge)
# ==============================================================================
import os
import glob
import subprocess
import json
import argparse
from pathlib import Path

# Caminho para o executável do MKVToolNix no Windows
MKVMERGE_PATH = r"C:\Program Files\MKVToolNix\mkvmerge.exe"

def process_mkv(mkv_path):
    base_name = os.path.basename(mkv_path)
    dir_name = os.path.dirname(mkv_path)
    prefix = base_name.replace(".mkv", "")
    
    # Procura pelo arquivo de legenda .pt.srt correspondente
    srt_pattern = os.path.join(dir_name, f"{prefix}*.pt.srt")
    srts = glob.glob(srt_pattern)
    
    if not srts:
        print(f"[AVISO] Nenhuma legenda .pt.srt encontrada para: {base_name}")
        return
    
    srt_path = srts[0]
    
    # Executa mkvmerge -J para obter informações sobre as faixas no formato JSON
    cmd_j = [MKVMERGE_PATH, "-J", mkv_path]
    try:
        res = subprocess.run(cmd_j, capture_output=True, text=True, encoding="utf-8", errors="replace", check=True)
        info = json.loads(res.stdout)
    except Exception as e:
        print(f"[ERRO] Falha ao ler informações de {base_name}: {e}")
        return
    
    jap_audio_id = None
    default_audios = []
    default_subs = []
    
    # Analisa as faixas existentes
    for track in info.get("tracks", []):
        track_type = track.get("type")
        track_id = track.get("id")
        props = track.get("properties", {})
        
        if track_type == "audio":
            if props.get("language") == "jpn":
                jap_audio_id = track_id
            if props.get("default_track"):
                default_audios.append(track_id)
        elif track_type == "subtitles":
            if props.get("default_track"):
                default_subs.append(track_id)
                
    if jap_audio_id is None:
        print(f"[AVISO] Áudio em Japonês não encontrado em: {base_name}")
        # Ainda vamos continuar e apenas adicionar a legenda PT se não tiver JP?
        # Sim, continuamos, apenas não alteramos o áudio.
    
    out_mkv = os.path.join(dir_name, f"{prefix}_PT.mkv")
    
    # Constrói o comando do mkvmerge
    cmd = [MKVMERGE_PATH, "-o", out_mkv]
    
    # Remove a flag de default dos áudios que estão como default (se encontrarmos o áudio JP)
    if jap_audio_id is not None:
        for aid in default_audios:
            if aid != jap_audio_id:
                cmd.extend(["--default-track-flag", f"{aid}:no"])
        # Define o áudio em Japonês como default
        cmd.extend(["--default-track-flag", f"{jap_audio_id}:yes"])
            
    # Remove a flag de default de todas as legendas existentes
    for sid in default_subs:
        cmd.extend(["--default-track-flag", f"{sid}:no"])
        
    # Adiciona o arquivo MKV original como entrada principal
    cmd.append(mkv_path)
    
    # Configurações para a nova legenda em português
    cmd.extend([
        "--language", "0:por",
        "--track-name", "0:Português (BR)",
        "--default-track-flag", "0:yes",
        srt_path
    ])
    
    print(f"\n============================================================")
    print(f" Muxing: {out_mkv}")
    print(f"============================================================")
    
    try:
        # Executa a junção sem capturar a saída, permitindo que o usuário veja o progresso no terminal
        subprocess.run(cmd, check=True)
        print(f"Arquivo gerado com sucesso!")
    except subprocess.CalledProcessError as e:
        print(f"[ERRO CRÍTICO] Falha ao processar o arquivo: {e}")

def main():
    parser = argparse.ArgumentParser(description="Adiciona legenda PT-BR e altera áudio default para JP em arquivos MKV.")
    parser.add_argument("diretorio", help="Caminho para o diretório contendo os arquivos .mkv e .pt.srt")
    args = parser.parse_args()
    
    target_dir = args.diretorio
    if not os.path.isdir(target_dir):
        print(f"[ERRO] O caminho especificado não é um diretório válido: {target_dir}")
        return
        
    mkv_files = glob.glob(os.path.join(target_dir, "*.mkv"))
    for mkv in mkv_files:
        # Pula arquivos que já foram processados por este script (evita loops se rodar duas vezes)
        if mkv.endswith("_PT.mkv"):
            continue
        process_mkv(mkv)

if __name__ == "__main__":
    main()
