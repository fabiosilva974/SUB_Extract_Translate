# Documentação: `translate_srt_google.py`

## Objetivo
Traduzir em lote arquivos de legenda do formato `.srt` (SubRip Subtitle) para o português utilizando o Google Translate de forma gratuita, mantendo a numeração e a temporização do arquivo intactas.

## Fluxo de Funcionamento
1. **Busca e Match de Arquivos**: O usuário submete arquivos ou usa coringas (`*.srt`). O script expande isso (usando `glob`) para suportar a limitação de command lines no Windows e itera sobre a lista de arquivos de legendas um por um.
2. **Separação Regex (`parse_srt`)**: Um arquivo SRT é puramente um arquivo de texto onde cada legenda é composta por três partes (número do bloco, tempo e texto) separadas por uma linha em branco. A lógica usa Expressões Regulares (`ENTRY_RE`) em modo *Multilinha* para fatiar o texto gigante do arquivo e construir uma lista de dicionários Python: `[{index, timecode, text}]`.
3. **Agrupamento**: Para respeitar limites da API gratuita do Google, ele extrai somente o `text` desses dicionários e os manda para a nuvem de 30 em 30 (`BATCH_SIZE`).
4. **Tradução Lote a Lote**: O `deep-translator` processa e devolve a array de strings convertida.
5. **Reestruturação e Gravação**: O código roda um laço reconstruindo o arquivo: repete a numeração indexada, repete o formato de tempo (`00:00:10,500 --> 00:00:13,000`) e imprime o novo texto em português, salvando finalmente num arquivo com extensão `.pt.srt`.

## Dependências
- **Python 3.x**
- **deep-translator**: Instanciado como `GoogleTranslator`.
- **Nativas**: `re` (para processamento de regex crítico do SRT), `os`, `sys`, `argparse`, `glob`, `pathlib`.

## Lógica Utilizada
Legendas SRT não são padronizadas e muitas vezes apresentam quebras de linha (`\r\n` vs `\n`) mal-formadas. Para evitar falhas em leitura por `readlines()`, a lógica principal usa a Expressão Regular `r"(\d+)\r?\n([\d:,]+ --> [\d:,]+)\r?\n([\s\S]*?)(?=\n\n|\Z)"`. Esse super-match captura limpidamente blocos problemáticos sem importar o sistema operacional em que foi gerado, e isola com precisão o que deve ser salvo local e o que deve ir à internet. O agrupamento por *lotes (batching)* garante que traduções de filmes com milhares de linhas não travem na metade do percurso.
