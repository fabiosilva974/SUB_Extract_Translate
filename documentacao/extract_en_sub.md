# extract_en_sub.py

## Objetivo
Extrair automaticamente a faixa de legenda correspondente ao idioma Inglês (`en`) em arquivos MKV, salvando-a no formato SRT. Este script não confia apenas nas tags (metadados) do arquivo, pois elas frequentemente vêm incorretas ou omitidas.

## Como Funciona a Lógica (Heurística)
Como as faixas de legenda não têm um idioma confiável marcado:
1. O script utiliza o `mkvmerge` para localizar todas as faixas do tipo "subtitles".
2. Ele exporta temporariamente todas essas faixas usando o `ffmpeg`.
3. O script lê as legendas exportadas e procura pelas palavras mais comuns da língua inglesa ("the", "be", "to", "of", "and", "a", "in").
4. A faixa que pontuar mais alto nesta heurística ganha.
5. O arquivo final é salvo com a extensão `.en.srt`.

## Como Usar

Para um único arquivo:
```bash
python scripts/extract_en_sub.py "arquivo_de_video.mkv"
```

Para processar todos os vídeos em uma pasta:
```bash
python scripts/extract_en_sub.py *.mkv
```

## Dependências
- `FFmpeg`: Utilizado para extrair as trilhas em formato `.srt`.
- `MKVToolNix`: Utilizado para identificar a estrutura do arquivo.
