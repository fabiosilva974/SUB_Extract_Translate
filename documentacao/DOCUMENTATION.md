# Technical Documentation / Documentação Técnica

## 🇧🇷 Português

### Requisitos do Sistema
O sistema deve ter os seguintes binários acessíveis:
1.  **MKVToolNix (`mkvmerge`, `mkvextract`):** Extração e análise do container MKV.
2.  **FFmpeg:** Conversão de legendas PGS/ASS para SRT.
3.  **Python 3.10+**

### Funcionalidades Avançadas

#### 1. Suporte a Wildcards e Múltiplos Arquivos
O script aceita uma lista de arquivos ou padrões glob (ex: `*.mkv`). 
- No Windows, o script utiliza a biblioteca `glob` para expandir padrões que o CMD normalmente não processaria.
- O processamento é sequencial: o script extrai e traduz um arquivo completamente antes de passar para o próximo.

#### 2. Parâmetro `--extract-only`
Esta flag altera o fluxo de execução para realizar apenas a extração e normalização:
- Identifica a trilha de legenda (preferencialmente inglês ou o idioma solicitado em `--lang`).
- Extrai a trilha para um diretório temporário.
- Converte para `.srt` se o formato original for baseado em imagem ou estilos (PGS/ASS).
- Move o arquivo final para a pasta de origem e encerra o processo para aquele arquivo, ignorando as chamadas de API de tradução.

### Lógica de Operação
1. **Análise:** `mkvmerge -J` identifica as faixas.
2. **Loop de Arquivos:** Itera sobre a lista expandida de arquivos MKV.
3. **Tradução em Lotes:** Agrupa textos em lotes (padrão 30 linhas) para otimizar o uso da rede e evitar "timeouts".

---

## 🇺🇸 English

### System Requirements
The system must have the following binaries accessible:
1.  **MKVToolNix (`mkvmerge`, `mkvextract`):** MKV container extraction and analysis.
2.  **FFmpeg:** Conversion of PGS/ASS subtitles to SRT.
3.  **Python 3.10+**

### Advanced Features

#### 1. Wildcard and Multiple File Support
The script accepts a list of files or glob patterns (e.g., `*.mkv`).
- On Windows, the script uses the `glob` library to expand patterns that CMD would not normally process.
- Processing is sequential: the script extracts and translates one file completely before moving to the next.

#### 2. `--extract-only` Parameter
This flag changes the execution flow to perform only extraction and normalization:
- Identifies the subtitle track (preferably English or the language requested in `--lang`).
- Extracts the track to a temporary directory.
- Converts to `.srt` if the original format is image-based or stylized (PGS/ASS).
- Moves the final file to the source folder and terminates the process for that file, skipping translation API calls.

### Operational Logic
1. **Analysis:** `mkvmerge -J` identifies tracks.
2. **File Loop:** Iterates over the expanded list of MKV files.
3. **Batch Translation:** Groups texts in batches (default 30 lines) to optimize network usage and avoid timeouts.

### ⚙️ Portable Installations & Path Overrides
If tools are not in your system `PATH`, use the `TOOLS` dictionary at the top of the script:
1. Set `MKVTOOLNIX_DIR` (Folder path).
2. Set `FFMPEG_BIN` (Full path to ffmpeg.exe).
