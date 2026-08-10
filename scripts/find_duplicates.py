"""
Script: find_duplicates.py
Descrição: Localiza arquivos duplicados em um diretório especificado, comparando 
           primeiramente os tamanhos dos arquivos e, em seguida, calculando o 
           hash MD5 dos arquivos com mesmo tamanho para confirmar a duplicata.
           O resultado é exportado para um arquivo Markdown (.md).
"""

import os
import hashlib
import json
import argparse

def get_hash(filepath, blocksize=65536):
    """
    Calcula o hash MD5 de um arquivo lendo-o em blocos para economizar memória.
    
    Args:
        filepath (str): O caminho absoluto ou relativo para o arquivo.
        blocksize (int): O tamanho do bloco a ser lido em cada iteração (padrão: 64KB).
        
    Returns:
        str: O hash MD5 em formato hexadecimal. Retorna None em caso de erro de leitura.
    """
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as afile:
            buf = afile.read(blocksize)
            while len(buf) > 0:
                hasher.update(buf)
                buf = afile.read(blocksize)
        return hasher.hexdigest()
    except Exception as e:
        # Ignora arquivos que não podem ser lidos (ex: permissão negada)
        return None

def find_duplicates(folder):
    """
    Busca por arquivos duplicados no diretório especificado.
    
    Args:
        folder (str): Caminho do diretório raiz para a busca.
        
    Returns:
        list: Lista de dicionários contendo informações dos arquivos duplicados.
              Formato: [{'size': int, 'hash': str, 'files': [str, str, ...]}]
    """
    size_dict = {}
    
    print(f"[{folder}] Passo 1: Varrendo diretório e agrupando por tamanho...")
    # 1. Agrupar por tamanho (filtro rápido)
    for dirpath, _, filenames in os.walk(folder):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                # Ignorar links simbólicos para evitar loops e arquivos repetidos por referência
                if not os.path.islink(filepath):
                    size = os.path.getsize(filepath)
                    if size not in size_dict:
                        size_dict[size] = []
                    size_dict[size].append(filepath)
            except Exception:
                pass
                
    duplicates = []
    
    # 2. Calcular o Hash apenas para arquivos que compartilham o mesmo tamanho
    print(f"[{folder}] Passo 2: Calculando MD5 para potenciais duplicatas...")
    for size, files in size_dict.items():
        if len(files) > 1 and size > 0: # Ignora arquivos vazios e únicos
            hash_dict = {}
            for filepath in files:
                file_hash = get_hash(filepath)
                if file_hash:
                    if file_hash not in hash_dict:
                        hash_dict[file_hash] = []
                    hash_dict[file_hash].append(filepath)
            
            # Adicionar à lista final se o mesmo hash aparecer em múltiplos arquivos
            for file_hash, file_list in hash_dict.items():
                if len(file_list) > 1:
                    duplicates.append({
                        'size': size,
                        'hash': file_hash,
                        'files': file_list
                    })
                    
    # Ordenar pelos maiores arquivos para priorizar a liberação de espaço
    duplicates.sort(key=lambda x: x['size'], reverse=True)
    return duplicates

def format_size(size):
    """Converte o tamanho em bytes para um formato legível por humanos (KB, MB, GB)."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0

def main():
    parser = argparse.ArgumentParser(description="Encontra arquivos duplicados em um diretório.")
    parser.add_argument("target_dir", nargs="?", default=r"e:\Traducao", help="Diretório a ser analisado")
    parser.add_argument("output_file", nargs="?", default=None, help="Caminho do arquivo de saída .md")
    args = parser.parse_args()
    
    target_dir = args.target_dir
    if args.output_file:
        output_file = args.output_file
    else:
        # Se não fornecer o output_file, gera na raiz do diretório alvo
        output_file = os.path.join(target_dir, "arquivos_duplicados.md")
    
    duplicates = find_duplicates(target_dir)

    print(f"[{target_dir}] Passo 3: Gerando relatório em {output_file}...")
    md_content = "# Relatório de Arquivos Duplicados\n\n"
    md_content += f"Lista dos maiores arquivos repetidos encontrados no diretório `{target_dir}`.\n\n"

    if not duplicates:
        md_content += "Nenhum arquivo duplicado encontrado.\n"
    else:
        # Limita aos 100 maiores arquivos duplicados
        for i, dup in enumerate(duplicates[:100]): 
            md_content += f"## {i+1}. Tamanho: {format_size(dup['size'])} (Hash MD5: `{dup['hash'][:8]}...`)\n"
            for f in dup['files']:
                md_content += f"- `{f}`\n"
            md_content += "\n"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    print("Concluído!")

if __name__ == '__main__':
    main()
