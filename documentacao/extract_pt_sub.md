# Documentação: `extract_pt_sub.py`

## Objetivo
Este script tem a finalidade de encontrar, entre todas as faixas de legendas disponíveis em um arquivo MKV, aquela que de fato contém diálogos em português, extraí-la e salvá-la em um arquivo separado com sufixo `.pt.srt`.

## Fluxo de Funcionamento
1. **Inspeção de Faixas**: O script aciona o `mkvmerge` (da suíte MKVToolNix) passando o arquivo de vídeo para listar todas as propriedades de trilhas contidas nele, mas filtra e armazena apenas aquelas do tipo `subtitles`.
2. **Extração em Massa**: Para evitar analisar apenas as tags de idioma (que frequentemente são incorretas, ex: marcadas como "und" - undefined, ou "eng" mesmo sendo português), o script extrai *todas* as faixas de legenda encontradas para uma pasta temporária usando o FFmpeg.
3. **Análise Heurística**: Após extraídas temporariamente como `.srt`, o script varre arquivo por arquivo, lendo seu conteúdo e rodando uma função de detecção heurística (`is_portuguese()`). Essa função conta a ocorrência de palavras e pronomes comuns da língua portuguesa ("não", "você", "com", "uma", "está", "também", etc).
4. **Eleição e Salvamento**: O script elege a faixa que obteve a maior "pontuação" (maior quantidade dessas palavras chave). Se a pontuação passar de um limite mínimo aceitável (10 ocorrências), a legenda eleita é copiada da pasta temporária para o diretório de destino e salva como `nome_do_video.pt.srt`. A pasta temporária é destruída automaticamente pelo sistema.

## Dependências
- **Python 3.x**
- **MKVToolNix** (`mkvmerge.exe`): Para descoberta estrutural dos IDs de legenda.
- **FFmpeg**: Para realizar a demultiplexação de todas as faixas de forma rápida num único comando.
- **Nativas do Python**: `re` (Expressões Regulares), `tempfile`, `subprocess`, `json`, `argparse`.

## Lógica Utilizada
A genialidade deste script está em não confiar nos metadados do container `.mkv`. Muitos "releases" piratas ou mal encodados possuem a faixa de legenda em português marcada sem identificação de língua (`und`) ou rotulada incorretamente. Extrair todas e testar por força-bruta através de contagem de _stopwords_ de dicionário português ("não", "você", etc) é um método _bullet-proof_ para garantir que a legenda que vai ser usada realmente é em português, sem necessidade de enviar à APIs externas para detecção de linguagem.
