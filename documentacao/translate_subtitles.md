# Documentação: `translate_subtitles.py`

## Objetivo
O script tem o propósito de unificar todo o fluxo de legendagem: extrai a legenda desejada diretamente de um arquivo `.mkv` e realiza uma tradução contextual de alta qualidade para o português (Brasil) utilizando a API do **Claude** (Anthropic), preservando perfeitamente os arquivos originais.

## Fluxo de Funcionamento
1. **Identificação**: Lê parâmetros do usuário (vídeo, idioma a extrair, formato de saída, etc). Verifica a presença das ferramentas `mkvmerge` e `mkvextract`.
2. **Descoberta e Extração**: Enumera as faixas do MKV. Se encontra o idioma selecionado (ou o padrão 'eng'), aciona o `mkvextract` para exportar o arquivo cru para uma pasta temporária (criada por `tempfile`).
3. **Pré-Processamento**: Se a legenda original estiver em um formato complexo como `.ass`, ela é temporariamente convertida para `.srt` pelo FFmpeg (em `convert_subtitle`). Isso é necessário para padronizar o envio à IA.
4. **Comunicação com IA (Claude)**: O script junta os diálogos extraídos em uma única requisição enumerada (ex: `1. Hello`, `2. How are you?`) na função `translate_batch`. Ele empacota as linhas, define o limite de tokens, insere um prompt comportamental rigoroso no formato JSON e envia via POST HTTP (`urllib.request`) para a API oficial do Anthropic (`claude-sonnet-4`).
5. **Reconstrução**: Após a IA devolver a resposta estruturada na mesma numeração (ex: `1. Olá`, `2. Como você está?`), o script aplica regex para quebrar as linhas pelas chaves numéricas, e as une de volta às instâncias de tempo (timecodes) originais da legenda.
6. **Exportação Final**: Grava a legenda final. Se o usuário tiver selecionado `--format ass`, usa o FFmpeg para converter o `.srt` traduzido de volta para `.ass`. Em seguida copia o arquivo para a mesma pasta do vídeo com o sufixo `.pt.srt` ou `.pt.ass`.

## Dependências
- **Python 3.x**
- **Anthropic API Key**: Exige a chave de ambiente configurada no sistema operacional (`ANTHROPIC_API_KEY`).
- **MKVToolNix** e **FFmpeg**: Necessários para manipulação do áudio/vídeo e conversão entre os formatos internos `.ass`/`.srt`.
- **Nativas**: `os`, `re`, `sys`, `json`, `argparse`, `subprocess`, `tempfile`, `glob`, `shutil`, `urllib.request`.

## Lógica Utilizada
A lógica difere dos tradutores burros do Google por inserir um *Prompt* embutido (`Você é um tradutor profissional...`). Quando enviamos um *batch* numérico para um LLM (Large Language Model), o modelo consegue ter o contexto geral do bloco (por exemplo, se é uma conversa formal ou gírias) e traduz de forma natural. A parte crítica da lógica está no parseamento de resposta: usar a numeração injetada nas strings para assegurar que cada frase devolvida corresponda com exatidão à marcação de tempo original, impedindo a dessincronização da legenda.
