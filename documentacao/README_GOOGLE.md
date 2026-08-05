# Tradutor de Legendas MKV (Google Translate)

Este script automatiza o processo de extração de legendas de arquivos `.mkv` e as traduz para o português brasileiro utilizando o motor do **Google Translate**.

## 🚀 Funcionalidades

- **Listagem de Faixas:** Identifica todas as faixas de legenda (SRT, ASS, PGS) dentro de um arquivo MKV.
- **Extração Automática:** Extrai a faixa desejada sem necessidade de ferramentas manuais.
- **Conversão de Codec:** Converte legendas complexas (como ASS ou PGS) para o formato padrão SRT via `ffmpeg`.
- **Tradução via Google:** Utiliza a biblioteca `deep-translator` para traduzir os diálogos mantendo o formato do arquivo SRT.
- **Processamento em Lote:** Traduz a legenda em blocos para garantir eficiência e evitar bloqueios.

## 📦 Dependências

### Ferramentas do Sistema
O script depende de ferramentas externas para manipular arquivos de vídeo e legendas. Certifique-se de tê-las instaladas:

1.  **MKVToolNix:** Fornece `mkvmerge` e `mkvextract`.
    - **Windows:** Baixe em [mkvtoolnix.download](https://mkvtoolnix.download/downloads.html).
    - **Linux (Ubuntu/Debian):** `sudo apt install mkvtoolnix`
    - **macOS:** `brew install mkvtoolnix`
2.  **FFmpeg:** Necessário para converter legendas PGS/ASS para SRT.
    - **Windows:** Baixe em [ffmpeg.org](https://ffmpeg.org/download.html).
    - **Linux:** `sudo apt install ffmpeg`

### Bibliotecas Python
Instale a biblioteca necessária via `pip`:

```bash
pip install deep-translator
```

## 🛠️ Como Usar

### Uso Básico
Traduz a legenda em inglês (padrão) do arquivo para português:
```bash
python translate_subtitles_google.py filme.mkv
```

### Listar Faixas de Legenda
Para ver quais faixas estão disponíveis no arquivo antes de extrair:
```bash
python translate_subtitles_google.py filme.mkv --list-tracks
```

### Especificar Idioma de Extração
Se a legenda original estiver em outro idioma (ex: japonês):
```bash
python translate_subtitles_google.py anime.mkv --lang jpn --source-lang ja
```

### Opções Disponíveis
- `mkv`: Caminho para o arquivo de vídeo.
- `--lang`: Código de 3 letras do idioma no MKV (padrão: `eng`).
- `--source-lang`: Código de 2 letras para o Google Translate (padrão: `auto`).
- `--output`: Nome personalizado para o arquivo `.srt` de saída.
- `--list-tracks`: Apenas lista as faixas e encerra.

## 📝 Lógica do Script
O script segue este fluxo:
1. **Análise:** Lê os metadados do MKV usando `mkvmerge`.
2. **Seleção:** Escolhe a faixa com base no idioma solicitado.
3. **Extração:** Extrai o arquivo bruto usando `mkvextract`.
4. **Normalização:** Se a legenda não for SRT, o `ffmpeg` a converte.
5. **Parse:** O texto é dividido em blocos de tempo e diálogo.
6. **Tradução:** Os textos são enviados ao Google Translate em lotes.
7. **Montagem:** O script reconstrói o arquivo SRT com os textos traduzidos.
