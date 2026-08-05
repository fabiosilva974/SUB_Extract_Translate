# identify_subs.py

## Objetivo
Processar em lote a identificação automática de IDIOMA para todas as faixas de legendas ocultas (não identificadas) dentro de um arquivo MKV. No final, um novo arquivo de vídeo é criado onde cada faixa tem sua propriedade (tag) de idioma perfeitamente configurada no padrão internacional.

## Como Funciona a Lógica
Para não confiar nos cabeçalhos mentirosos ou vazios ("und") presentes nos arquivos:
1. O script varre o MKV original via `mkvmerge` para encontrar todas as faixas de legenda.
2. Faz extração temporária (stream pipe) das primeiras falas via `ffmpeg` para cada faixa identificada.
3. Alimenta a amostra textual na inteligência computacional da biblioteca `langdetect`.
4. O `langdetect` devolve um código de duas letras (ex: 'pt', 'en', 'fr'). O script traduz isso para o padrão aceito pelo MKV (ISO 639-2 de 3 letras: 'por', 'eng', 'fre').
5. Por fim, executa o `mkvmerge` montando o comando final que pega o arquivo original e injeta todas as flags `--edit track:ID --set language=X`, exportando como `[NomeOriginal]_Identified.mkv`.

## Como Usar
Para um único arquivo:
```bash
python scripts/identify_subs.py "caminho/do/video.mkv"
```

Para processar uma pasta cheia (ex: temporada inteira de série), usando curingas (wildcards):
```bash
python scripts/identify_subs.py "Z:\Pasta\De\Series\*.mkv"
```
*(Lembre-se de colocar as aspas no Windows ao usar curingas na pasta).*

## Dependências
- `FFmpeg`
- `MKVToolNix`
- Python: `langdetect` (instalar via `pip install langdetect`)
