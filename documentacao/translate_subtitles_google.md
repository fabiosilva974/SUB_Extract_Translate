# Documentação: `translate_subtitles_google.py`

## Objetivo
Funciona como uma alternativa gratuita e autônoma ao script que usa o modelo do Claude. Este script extrai a legenda interna do arquivo `.mkv` selecionado e, mantendo toda a sincronia, traduz os textos para português usando o Google Translate via web scraping/API.

## Fluxo de Funcionamento
1. **Inspeção de Requisitos**: Valida se o MKVToolNix (`mkvmerge`, `mkvextract`) e o `ffmpeg` estão presentes no sistema, quebrando a execução caso faltem.
2. **Descoberta do MKV**: Passa o arquivo pelo `mkvmerge -J` para elencar as faixas presentes, selecionando a faixa cujo idioma bate com o solicitado pelo usuário (ou inglês/padrão caso não especificado).
3. **Extração e Normalização**: Extrai a legenda bruta (`mkvextract`). Como as legendas extraídas podem vir em formatos avançados (como ASS), o script se aproveita da capacidade do FFmpeg para converter a legenda em `.srt` (formato de texto simples) em uma pasta temporária, garantindo um padrão de processamento.
4. **Desmembramento (Regex)**: Uma vez que a legenda é um texto `.srt`, aplica regex para quebrar as linhas pelas chaves de tempo e isolar a porção de "fala" dos diálogos.
5. **Tradução em Batch**: Grupos de 30 falas são injetados no objeto `GoogleTranslator` que se comunica de forma assíncrona com os servidores de tradução do Google para converter o idioma base em português.
6. **Agrupamento e Salvamento**: Tendo os textos convertidos em mãos, une de volta às flags de marcação de tempo. Por fim, se o usuário tiver requisitado a saída em formato `.ass` (via `--format ass`), utiliza novamente o `ffmpeg` para recompor a estrutura ASS a partir do SRT traduzido, e salva o resultado final como `.pt.srt` ou `.pt.ass`.

## Dependências
- **Python 3.x**
- **deep-translator**: Encapsula as requisições ao Google Translate.
- **Ferramentas de CLI (Vídeo)**: `mkvmerge`, `mkvextract` e `ffmpeg`.
- **Nativas**: `os`, `re`, `sys`, `json`, `argparse`, `subprocess`, `tempfile`, `glob`, `shutil`, `pathlib`.

## Lógica Utilizada
Ao contrário das abordagens linha-a-linha que falhariam por estourar o limite de requisições web do Google (Timeouts de segurança), a separação baseada em blocos e a agregação num array submetido via `translate_batch()` diluem o tempo de espera de rede. A normalização forçada via FFmpeg de qualquer codec exótico para SRT resolve os gargalos onde as bibliotecas de tradução costumam quebrar a semântica visual dos arquivos.
