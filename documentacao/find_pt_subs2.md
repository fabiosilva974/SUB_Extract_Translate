# find_pt_subs2.py

## Objetivo
Este script funciona como uma evolução da versão 1 (`find_pt_subs.py`), cujo o foco foi permitir a inspeção manual (e massiva) de legendas de um grupo de arquivos MKV com mais dezenas de faixas misturadas (sem idioma especificado).

## Como Funciona a Lógica
O script segue o mesmo princípio de isolar e visualizar:
1. Recebe uma lista de arquivos MKV "problemáticos" estipulada no corpo do código.
2. Utiliza o `ffprobe` para levantar o número e o ID das trilhas onde o `codec_type` é "subtitle".
3. Utiliza o `ffmpeg` para abrir um túnel (pipe) e ler somente os 20 primeiros blocos da legenda em SRT.
4. Salva todo o extrato em um arquivo de texto unificado chamado `subtitles_peek.txt`.

Com o arquivo gerado, o usuário pode abri-lo no bloco de notas e rapidamente encontrar algo como:
`File: video.mkv`
`Stream 29: Eles chegaram! Fuja.` -> (Logo, sabemos que a legenda PT é a faixa 29).

## Como Usar
Por ser um script de laboratório, os arquivos de destino estão fixados na variável `files`. 

1. Abra o arquivo em um editor de texto.
2. Altere os caminhos na lista `files`.
3. Salve e execute:
```bash
python scripts/find_pt_subs2.py
```
O arquivo de inspeção `subtitles_peek.txt` será gerado na pasta raiz.

## Dependências
- `FFmpeg`
- `FFprobe`
