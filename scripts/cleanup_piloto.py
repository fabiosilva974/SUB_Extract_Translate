# ==============================================================================
# Script: cleanup_piloto.py
#
# Objetivo:
#   Deletar os arquivos de vídeo originais (não-convertidos) listados no CSV
#   caso a versão convertida em H.265 já exista no mesmo diretório.
#
# Lógica Principal:
#   Lê o arquivo 'test_map.csv', traduz os caminhos de rede (Windows/Linux),
#   calcula o novo nome sanitizado esperado e verifica a existência de ambos.
#   Se o novo existir, o antigo é apagado permanentemente.
#
# Dependências Externas:
#   Nenhuma biblioteca externa além da biblioteca padrão do Python.
# ==============================================================================
# Importação da biblioteca nativa para leitura de arquivos CSV
import csv
# Importação da biblioteca de interface com o SO para manipulação de arquivos
import os
# Importação da classe Path moderna para lidar com caminhos de forma robusta
from pathlib import Path
# Importação da biblioteca de Expressões Regulares (Regex) para limpeza de strings
import re

# Função que traduz os caminhos absolutos baseados na montagem do servidor NAS
def translate_path(path_str):
    # Substitui a notação de rede UNC do Windows para a estrutura de montagem do Linux
    path_str = path_str.replace("\\\\192.168.0.99\\Media\\", "/mnt/Media/")
    # Substitui uma possível montagem por drive mapado local (U:) para a montagem do Linux
    path_str = path_str.replace("U:\\", "/mnt/Media/")
    # Garante que qualquer barra invertida restante (Windows) vire barra normal (UNIX)
    path_str = path_str.replace("\\", "/")
    # Retorna o caminho limpo e unificado
    return path_str

# Função que higieniza o título removendo caracteres não ideais
def sanitize_title(title):
    # Usa Regex para deletar colchetes, parênteses, aspas, apóstrofos, exclamações e dois-pontos
    title = re.sub(r'[\[\]\(\)\'\":!]', '', title)
    # Transforma qualquer ocorrência de espaços ou hífens seguidos em um único ponto
    title = re.sub(r'[\s\-]+', '.', title)
    # Previne a formação de duplo ou triplos pontos seguidos (ex: "..")
    title = re.sub(r'\.+', '.', title)
    # Retorna a string retirando qualquer ponto solto que tenha sobrado no início ou fim
    return title.strip('.')

# Função central e inicial do script
def main():
    # Detecta automaticamente qual é a pasta onde este script python está rodando
    script_dir = Path(__file__).parent
    # Deduz que o arquivo CSV de mapa se encontra na mesma pasta do script
    csv_path = script_dir / "test_map.csv"
    # Se o arquivo CSV por acaso não existir neste caminho
    if not csv_path.exists():
        # Informa na tela para o usuário e interrompe
        print(f"Erro: CSV não encontrado em {csv_path}")
        return

    # Inicia e exibe o cabeçalho estético de largada
    print("Iniciando limpeza dos originais (Lote Piloto)...")
    # Zera o contador aritmético de arquivos deletados fisicamente
    apagados = 0

    # Abre o arquivo CSV garantindo tratamento do cabeçalho invisível UTF-8 BOM
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        # Lê interpretando como dicionário onde a primeira linha vira o título da chave
        reader = csv.DictReader(f, delimiter=';')
        # Laço (loop) lendo linha por linha (vídeo por vídeo) do arquivo
        for row in reader:
            # Armazena o caminho original passando pela nossa função tradutora de plataformas
            orig_path = Path(translate_path(row['Caminho_Completo_Original']))
            
            # Puxa o nome ideal projetado que estava mapeado no CSV
            new_name = row['Novo_Nome_Padronizado']
            # Usa a mesma regra agressiva de limpeza do script de H265, tirando provisoriamente o .mkv para não dar bug nos pontos
            new_name = sanitize_title(new_name.replace(".mkv", "")) + ".mkv"
            # Assegura que não há ".." no nome final da fita
            while ".." in new_name: new_name = new_name.replace("..", ".")
            
            # Recria o caminho absoluto onde o novo arquivo convertido (h265) deveria estar
            conv_path = orig_path.parent / new_name
            
            # Lógica central: Verifica com dupla segurança se o arquivo FINAL existe E se o arquivo ANTIGO original ainda existe
            if conv_path.exists() and orig_path.exists():
                # Avisa visualmente que este irá pra lixeira
                print(f"Apagando: {orig_path.name}")
                # Bloco de tentativa IO
                try:
                    # Executa a deleção física (unlink) permanentemente do HD/Rede
                    orig_path.unlink()
                    # Aumenta nosso placar contador de vitórias
                    apagados += 1
                # Em caso de falha no disco ou permissão negada
                except Exception as e:
                    # Pula emitindo alerta
                    print(f"Erro ao apagar {orig_path.name}: {e}")
            # Se o arquivo original velho não existe, significa que já fizemos nosso trabalho aqui antes
            elif not orig_path.exists():
                # Reporta que essa linha do csv é inútil pois o arquivo evaporou ou já foi deletado
                print(f"Já apagado ou renomeado: {orig_path.name}")
            # Se o original EXISTE mas o FINAL/Convertido NÃO existe, aborta.
            else:
                # Segurança extrema: Se não achamos o renderizado, não podemos apagar o root, senão perdemos o filme todo.
                print(f"Ignorando (Convertido não achado): {orig_path.name}")

    # Ao final da iteração completa do documento, exibe sumário total salvos via contador
    print(f"\nLimpeza concluída! {apagados} arquivos originais apagados.")

# Cláusula idiomática para permitir apenas execução direta do código
if __name__ == '__main__':
    # Roda main
    main()
