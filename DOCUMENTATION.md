# Technical Documentation / Documentação Técnica

## 🇧🇷 Português

### Requisitos do Sistema
Para o funcionamento pleno do script, o sistema deve ter os seguintes binários no PATH:
1.  **MKVToolNix (`mkvmerge`, `mkvextract`):** Responsável pela manipulação do container MKV.
2.  **FFmpeg:** Utilizado para a conversão de formatos de legenda de imagem (PGS) ou estilosos (ASS) para texto simples (SRT).
3.  **Python 3.10+:** Linguagem base do script.

### Lógica de Operação
1.  **Análise EBML:** O script invoca `mkvmerge -J` para ler a estrutura do arquivo em JSON, identificando faixas do tipo `subtitles`.
2.  **Extração de Stream:** O `mkvextract` isola a trilha de dados brutos da legenda em um arquivo temporário.
3.  **Conversão via FFmpeg:** Caso a legenda não seja SRT original, o script usa `ffmpeg -i input output.srt` para normalizar o formato.
4.  **Processamento SRT:** O texto é limpo e dividido em objetos contendo `index`, `timecode` e `content`.
5.  **Tradução em Lotes (Batches):** Para respeitar limites de requisição e otimizar a velocidade, o script agrupa 30 linhas de diálogo por vez antes de enviar ao Google Translate.
6.  **Reconstrução:** O script gera um novo arquivo `.srt` seguindo rigorosamente a ordem original dos timecodes, garantindo a sincronia.

---

## 🇺🇸 English

### System Requirements
For the script to function fully, the system must have the following binaries in its PATH:
1.  **MKVToolNix (`mkvmerge`, `mkvextract`):** Responsible for manipulating the MKV container.
2.  **FFmpeg:** Used for converting image-based (PGS) or stylized (ASS) subtitle formats to plain text (SRT).
3.  **Python 3.10+:** The script's base language.

### Operational Logic
1.  **EBML Analysis:** The script invokes `mkvmerge -J` to read the file structure in JSON, identifying tracks of type `subtitles`.
2.  **Stream Extraction:** `mkvextract` isolates the raw subtitle data track into a temporary file.
3.  **FFmpeg Conversion:** If the subtitle is not original SRT, the script uses `ffmpeg -i input output.srt` to normalize the format.
4.  **SRT Processing:** The text is cleaned and split into objects containing `index`, `timecode`, and `content`.
5.  **Batch Translation:** To respect request limits and optimize speed, the script groups 30 lines of dialogue at a time before sending them to Google Translate.
6.  **Reconstruction:** The script generates a new `.srt` file strictly following the original order of timecodes, ensuring sync.

### ⚙️ Portable Installations & Path Overrides (Importante)
Em ambientes Windows, é comum que ferramentas como o `ffmpeg` ou `MKVToolNix` não sejam adicionadas automaticamente ao `PATH` do sistema. 

O script foi desenhado com um dicionário `TOOLS` no topo. Para configurar sua máquina ou instruir novos usuários:
1. Localize as variáveis `MKVTOOLNIX_DIR` e `FFMPEG_BIN`.
2. Insira os caminhos absolutos (usando `r""` para evitar erros com barras invertidas).
3. O script priorizará estes caminhos antes de tentar chamadas globais.

---

## 🇺🇸 English
...
### ⚙️ Portable Installations & Path Overrides (Important)
On Windows environments, it is common for tools like `ffmpeg` or `MKVToolNix` not to be automatically added to the system `PATH`.

The script is designed with a `TOOLS` dictionary at the top. To configure your machine or instruct new users:
1. Locate the `MKVTOOLNIX_DIR` and `FFMPEG_BIN` variables.
2. Insert the absolute paths (using `r""` to avoid backslash errors).
3. The script will prioritize these paths before attempting global calls.
