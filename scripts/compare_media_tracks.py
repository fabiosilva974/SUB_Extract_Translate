# ==============================================================================
# Script: compare_media_tracks.py
#
# Objetivo:
#   Comparar lado-a-lado as faixas de mídia (Áudio, Vídeo, Legenda) de dois
#   arquivos de vídeo (Original vs Convertido) para garantir que não houve perdas de fluxo.
#
# Lógica Principal:
#   Extrai metadados JSON do FFprobe de ambos os arquivos, conta os tipos de
#   streams presentes e levanta um alerta caso alguma trilha de áudio ou
#   legenda tenha se perdido na conversão (Útil para validação de integridade QA).
#
# Dependências Externas:
#   FFprobe (deve estar instalado e no PATH do sistema)
# ==============================================================================
# Importação de funções de sistema (receber parâmetros de terminal argv e sair)
import sys
# Importação para chamadas shell do ffprobe
import subprocess
# Importação para destrinchar os dados brutos JSON da saída
import json

# Função para extrair todas as streams de dentro do arquivo mkv
def get_streams(file_path):
    # Cria os argumentos invocando ffprobe puro, silencioso e respondendo em modo JSON estruturado
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", str(file_path)]
    # Inicio Try
    try:
        # Atraca na main-thread para rodar capturando stdout sem exibir sujeira
        result = subprocess.run(cmd, capture_output=True, check=True)
        # Decodifica bytes em String UTF8 ignorando falhas
        data = json.loads(result.stdout.decode('utf-8', errors='replace'))
        # Retorna apenas o array 'streams' do documento inteiro extraído
        return data.get('streams', [])
    # Erro de IO ou binário não achado
    except Exception as e:
        # Notifica falha
        print(f"Erro lendo {file_path}: {e}")
        # Retorna nada
        return None

# Função puramente contábil. Enumera as categorias num dict.
def count_tracks(streams):
    # Inicializa variáveis
    counts = {'video': 0, 'audio': 0, 'subtitle': 0}
    # Laço iterando cada stream extraída
    for stream in streams:
        # Pega propriedade definidora do Codec Type
        codec_type = stream.get('codec_type')
        # Verifica se pertence ao nosso grupo catalogado (video, audio, etc)
        if codec_type in counts:
            # Incrementa placar em +1
            counts[codec_type] += 1
    # Retorna o dicionario populado
    return counts

# Função principal ativadora
def main():
    # Garante que o usuario enviou os dois parametros necessarios (nome script + original + novo)
    if len(sys.argv) < 3:
        # Auxilia no display
        print("Uso: python compare_media_tracks.py <arquivo_original> <arquivo_convertido>")
        # Mata run com código erro 1
        sys.exit(1)
        
    # Puxa 1 argumento
    orig = sys.argv[1]
    # Puxa 2 argumento
    conv = sys.argv[2]
    
    # Roda extração
    orig_streams = get_streams(orig)
    conv_streams = get_streams(conv)
    
    # Se alguma falhou catastroficamente
    if orig_streams is None or conv_streams is None:
        # Aviso
        print("FALHA: Não foi possível extrair metadados dos arquivos.")
        sys.exit(1)
        
    # Roda contabilidade
    orig_counts = count_tracks(orig_streams)
    conv_counts = count_tracks(conv_streams)
    
    # Painel comparativo Visual Orig
    print(f"--- Original: {orig} ---")
    print(f"Video: {orig_counts['video']} | Audio: {orig_counts['audio']} | Legenda: {orig_counts['subtitle']}")
    
    # Painel comparativo Visual Novo
    print(f"\n--- Convertido: {conv} ---")
    print(f"Video: {conv_counts['video']} | Audio: {conv_counts['audio']} | Legenda: {conv_counts['subtitle']}")
    
    # Divisória
    print("\n------------------------------")
    # Status Boolean de Integridade Final do Teste
    success = True
    # Valida perdas de faixa de áudio 
    if orig_counts['audio'] != conv_counts['audio']:
        # Ocorreu drop de áudio
        print("[ERRO] Quantidade de trilhas de áudio diferente!")
        success = False
    # Valida perdas de legenda softsub embutida
    if orig_counts['subtitle'] != conv_counts['subtitle']:
        # Ocorreu drop de sub
        print("[ERRO] Quantidade de trilhas de legenda diferente!")
        success = False
        
    # Desfecho
    if success:
        # Sucesso absoluto na clonagem de propriedades metadata
        print("[SUCESSO] Trilhas de áudio e legenda foram mantidas de forma idêntica.")
        # Retorna Zero pro sistema
        sys.exit(0)
    else:
        # Deu diferença! O conversor estragou a fita engolindo faixas.
        print("[FALHA] Trilhas não correspondem. Recomendado NÃO usar --delete.")
        # Retorna errorcode pro sistema operacional
        sys.exit(1)

# Sentinela anti-importacao
if __name__ == '__main__':
    main()
