import sys
import subprocess
import json

def get_streams(file_path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(file_path)]
    try:
        result = subprocess.run(cmd, capture_output=True, check=True)
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
        return data.get('streams', [])
    except Exception as e:
        print(f"Erro lendo {file_path}: {e}")
        return None

def count_tracks(streams):
    counts = {'video': 0, 'audio': 0, 'subtitle': 0}
    for stream in streams:
        codec_type = stream.get('codec_type')
        if codec_type in counts:
            counts[codec_type] += 1
    return counts

def main():
    if len(sys.argv) < 3:
        print("Uso: python compare_media_tracks.py <arquivo_original> <arquivo_convertido>")
        sys.exit(1)
        
    orig = sys.argv[1]
    conv = sys.argv[2]
    
    orig_streams = get_streams(orig)
    conv_streams = get_streams(conv)
    
    if orig_streams is None or conv_streams is None:
        print("FALHA: Não foi possível extrair metadados dos arquivos.")
        sys.exit(1)
        
    orig_counts = count_tracks(orig_streams)
    conv_counts = count_tracks(conv_streams)
    
    print(f"--- Original: {orig} ---")
    print(f"Video: {orig_counts['video']} | Audio: {orig_counts['audio']} | Legenda: {orig_counts['subtitle']}")
    
    print(f"\n--- Convertido: {conv} ---")
    print(f"Video: {conv_counts['video']} | Audio: {conv_counts['audio']} | Legenda: {conv_counts['subtitle']}")
    
    print("\n------------------------------")
    success = True
    if orig_counts['audio'] != conv_counts['audio']:
        print("[ERRO] Quantidade de trilhas de áudio diferente!")
        success = False
    if orig_counts['subtitle'] != conv_counts['subtitle']:
        print("[ERRO] Quantidade de trilhas de legenda diferente!")
        success = False
        
    if success:
        print("[SUCESSO] Trilhas de áudio e legenda foram mantidas de forma idêntica.")
        sys.exit(0)
    else:
        print("[FALHA] Trilhas não correspondem. Recomendado NÃO usar --delete.")
        sys.exit(1)

if __name__ == '__main__':
    main()
