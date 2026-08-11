# ==============================================================================
# Script: find_duplicates.py
#
# Objetivo:
#   Localiza arquivos duplicados em um diretório especificado, comparando 
#   primeiramente os tamanhos dos arquivos e, em seguida, calculando o 
#   hash MD5 dos arquivos com mesmo tamanho para confirmar a duplicata.
#   O resultado é exportado para um arquivo Markdown (.md).
#
# Lógica Principal:
#   Faz uma varredura (walk) ignorando Symlinks, agrupando arquivos pelo
#   mesmo tamanho em Bytes. Em seguida, gera hashes MD5 parciais para
#   arquivos de mesmo tamanho para atestar duplicidade idêntica em bits.
#
# Dependências Externas:
#   Nenhuma
# ==============================================================================
# Importação de funções de sistema operacional
import os
# Importação da biblioteca matemática de Hashes (MD5, SHA1)
import hashlib
# Importação para formatar ou ler dicionários
import json
# Importação para ler flags injetadas no prompt de comando
import argparse

# Função base criadora de Hashes por fragmentação
def get_hash(filepath, blocksize=65536):
    # Docstring utilitário nativo
    """
    Calcula o hash MD5 de um arquivo lendo-o em blocos para economizar memória.
    """
    # Inicializa o objeto de cálculo MD5
    hasher = hashlib.md5()
    # Bloco tentar IO
    try:
        # Abre o arquivo alvo em modo 'rb' (read-binary) puramente digital (sem encoding string)
        with open(filepath, 'rb') as afile:
            # Lê o primeiro lote no tamanho do bloco (64KB por padrão)
            buf = afile.read(blocksize)
            # Enquanto o buffer não retornar vazio (fim do arquivo)
            while len(buf) > 0:
                # Alimenta o motor de Hash com esse lote de bytes
                hasher.update(buf)
                # Lê o próximo lote da fila do disco
                buf = afile.read(blocksize)
        # Ao final do loop, consolida as contas matemáticas e retorna o Hash gerado em string hexadecimal 
        return hasher.hexdigest()
    # Em caso de arquivo bloqueado, pastas ocultas do sistema, falta de permissão de admin
    except Exception as e:
        # Ignora silenciosamente e devolve Nulo para não quebrar a macro varredura 
        return None

# Função central orquestradora
def find_duplicates(folder):
    # Dicionário temporário na RAM que atrela tamanho (chave) a lista de arquivos (valor)
    size_dict = {}
    
    # Imprime aviso visual pro terminal
    print(f"[{folder}] Passo 1: Varrendo diretório e agrupando por tamanho...")
    # 1. Agrupar por tamanho (filtro rápido incrivelmente eficiente)
    for dirpath, _, filenames in os.walk(folder):
        # Itera lista de arquivos
        for filename in filenames:
            # Junta partes usando o separador correto do Windows (\) ou Linux (/)
            filepath = os.path.join(dirpath, filename)
            # Bloco tentar
            try:
                # Ignorar links simbólicos e atalhos para evitar loops eternos de OS
                if not os.path.islink(filepath):
                    # Pede pro sistema operacional puxar os metadados de FileSize em bytes precisos
                    size = os.path.getsize(filepath)
                    # Se aquele tamanho numérico exato ainda não existir no dict
                    if size not in size_dict:
                        # Cria uma array vazia pra ele
                        size_dict[size] = []
                    # Apenda o arquivo achado que possui esse mesmo tamanho exato
                    size_dict[size].append(filepath)
            # Tratamento de erro 
            except Exception:
                # Pula arquivo não acessível 
                pass
                
    # Array de resposta final (Os verdadeiros duplicados)
    duplicates = []
    
    # 2. Calcular o Hash apenas para arquivos que magicamente compartilham o exato mesmo tamanho (candidatos)
    print(f"[{folder}] Passo 2: Calculando MD5 para potenciais duplicatas...")
    # Desempacota o dicionário 
    for size, files in size_dict.items():
        # Se existem 2 ou mais arquivos com exatamente mesmo peso E não tem tamanho nulo (zero bytes)
        if len(files) > 1 and size > 0:
            # Cria sub dicionário
            hash_dict = {}
            # Avalia arquivo por arquivo desse grupo candidato
            for filepath in files:
                # Dispara a leitura frenética do disco gerando Hash dele 
                file_hash = get_hash(filepath)
                # Se não falhou IO
                if file_hash:
                    # Registra hash novo 
                    if file_hash not in hash_dict:
                        # Abre array
                        hash_dict[file_hash] = []
                    # Apenda o arquivo nele
                    hash_dict[file_hash].append(filepath)
            
            # 3. Adicionar à lista final se o mesmo hash genético aparecer em múltiplos arquivos confirmando clone
            for file_hash, file_list in hash_dict.items():
                # Se após rodar hashes, de fato 2 arquivos tiveram mesmo hash (e não era só coincidência de bytes)
                if len(file_list) > 1:
                    # Apenda ao relatorio mestre 
                    duplicates.append({
                        'size': size,       # Tamanho da anomalia
                        'hash': file_hash,  # Identidade RG da anomalia 
                        'files': file_list  # Quais arquivos são eles
                    })
                    
    # Ordenar a array de duplicatas pelos maiores arquivos, assim focamos em apagar coisas pesadas (ISOs, MKVs)
    duplicates.sort(key=lambda x: x['size'], reverse=True)
    # Devolve o pacote ao pai
    return duplicates

# Função de formatação UI UI
def format_size(size):
    """Converte o tamanho em bytes para um formato legível por humanos (KB, MB, GB)."""
    # Laço com categorias estáticas de gigabytes e teras
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        # Se cair pra menos que 1024, ele achou a categoria ideal 
        if size < 1024.0:
            # Retorna arredondado
            return f"{size:.2f} {unit}"
        # Se for maior que 1024, divide e tenta o loop novamente pra ver se é MB ou GB, etc 
        size /= 1024.0

# Func principal autoexec
def main():
    # Cria o interpretador de argumentos da shell
    parser = argparse.ArgumentParser(description="Encontra arquivos duplicados em um diretório.")
    # Target alvo do scanner
    parser.add_argument("target_dir", nargs="?", default=r"e:\Traducao", help="Diretório a ser analisado")
    # Output pra onde salvar o .md
    parser.add_argument("output_file", nargs="?", default=None, help="Caminho do arquivo de saída .md")
    # Lê tudo
    args = parser.parse_args()
    
    # Transfere variavel 
    target_dir = args.target_dir
    # Verifica
    if args.output_file:
        # Puxa 
        output_file = args.output_file
    # Senao defaultiza
    else:
        # Se não fornecer o output_file, gera na raiz do diretório alvo um arquivo txt/md
        output_file = os.path.join(target_dir, "arquivos_duplicados.md")
    
    # Puxa gatilho disparador das funcoes 
    duplicates = find_duplicates(target_dir)

    # UI 
    print(f"[{target_dir}] Passo 3: Gerando relatório em {output_file}...")
    # Monta a String base textual que formará o Markdown document 
    md_content = "# Relatório de Arquivos Duplicados\n\n"
    # Anexa contexto dinâmico
    md_content += f"Lista dos maiores arquivos repetidos encontrados no diretório `{target_dir}`.\n\n"

    # Confere vazia 
    if not duplicates:
        # Felicidade
        md_content += "Nenhum arquivo duplicado encontrado.\n"
    # Confere preenchida
    else:
        # Limita visualmente aos 100 maiores ofensores de limite de disco rígido pra não travar o Notepad/Markdown Viewer
        for i, dup in enumerate(duplicates[:100]): 
            # Injeta Header do infrator 
            md_content += f"## {i+1}. Tamanho: {format_size(dup['size'])} (Hash MD5: `{dup['hash'][:8]}...`)\n"
            # Lista as pastas filhas onde os clones moram
            for f in dup['files']:
                # Formata como lista markdown 
                md_content += f"- `{f}`\n"
            # Linebreak pro proximo infrator
            md_content += "\n"

    # IO Mestre abrindo o documento para escrita física 
    with open(output_file, 'w', encoding='utf-8') as f:
        # Escreve o blocão todo
        f.write(md_content)
    
    # Sucesso 
    print("Concluído!")

# Main protection block default python 
if __name__ == '__main__':
    main()
