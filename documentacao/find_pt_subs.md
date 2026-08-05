# find_pt_subs.py

## Objetivo
Este é um script de rascunho/experimento criado para localizar legendas em português (`pt`) dentro de arquivos de vídeo MKV através de heurística básica.

## Como Funciona
Diferente dos outros scripts robustos que utilizam o `mkvmerge`, este experimento faz uso do `ffprobe` (ferramenta complementar do FFmpeg) para investigar as faixas embutidas:
1. Ele lista os índices dos streams onde o `codec_type` é igual a `subtitle`.
2. Extrai de cada um as primeiras 20 linhas de diálogo.
3. Se identificar a presença de palavras muito exclusivas (como "não", "você"), assume que se trata do idioma português.
4. Imprime no console as 3 primeiras linhas encontradas para inspeção visual do usuário.

## Como Usar
Por ser um script de laboratório, os arquivos de destino (`Z:\Traducao\Lucky...`) estão fixados diretamente no código-fonte em formato de lista (array) na variável `files`. 

Para testar seus próprios arquivos:
1. Abra o arquivo em um editor de texto.
2. Altere os caminhos na lista `files`.
3. Salve e execute:
```bash
python scripts/find_pt_subs.py
```

## Dependências
- `FFmpeg`
- `FFprobe`
