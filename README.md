# MKV Subtitle Translator (Google Translate) / Tradutor de Legendas MKV

[Português](#português) | [English](#english)

---

<a name="português"></a>
## 🇧🇷 Português

### Descrição
Este script automatiza a extração e tradução de legendas de arquivos `.mkv`. Ele identifica as faixas de legenda, extrai a escolhida, converte para o formato SRT (se necessário) e traduz o conteúdo para português brasileiro usando o motor do Google Translate.

### ✨ Funcionalidades
- **Extração Automática:** Busca faixas de legenda dentro do container MKV.
- **Múltiplos Arquivos:** Suporta o processamento de vários vídeos em sequência ou o uso de wildcards (ex: `*.mkv`).
- **Apenas Extração:** Novo parâmetro para extrair a legenda original sem realizar a tradução.
- **Conversão de Codec:** Transforma legendas ASS/SSA/PGS em SRT via FFmpeg.
- **Tradução Inteligente:** Traduz diálogos mantendo tags de formatação (HTML) e timecodes.
- **Tradução em Lote:** Otimizado para evitar bloqueios de API.

### 🚀 Início Rápido
1. **Instale as dependências do sistema:** MKVToolNix e FFmpeg.
2. **Configure os caminhos (Opcional):** Se as ferramentas não estiverem no seu PATH global, edite as variáveis no topo do script (`MKVTOOLNIX_DIR` e `FFMPEG_BIN`).
3. **Instale a biblioteca Python:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Execute:**
   ```bash
   # Traduzir todos os MKVs da pasta
   python translate_subtitles_google_win.py *.mkv

   # APENAS EXTRAIR a legenda (sem traduzir)
   python translate_subtitles_google_win.py seu_video.mkv --extract-only
   ```

---

<a name="english"></a>
## 🇺🇸 English

### Description
This script automates the extraction and translation of subtitles from `.mkv` files. It identifies subtitle tracks, extracts the chosen one, converts it to SRT format (if necessary), and translates the content to Brazilian Portuguese using the Google Translate engine.

### ✨ Features
- **Automatic Extraction:** Scans for subtitle tracks within the MKV container.
- **Batch Processing:** Supports multiple files or wildcards (e.g., `*.mkv`) to process several videos in sequence.
- **Extraction Only:** New parameter to extract the original subtitle without translating.
- **Codec Conversion:** Converts ASS/SSA/PGS subtitles to SRT using FFmpeg.
- **Smart Translation:** Translates dialogues while preserving formatting tags (HTML) and timecodes.
- **Batch Translation:** Optimized to prevent API rate limiting.

### 🚀 Quick Start
1. **Instale as dependências do sistema:** MKVToolNix e FFmpeg.
2. **Configure paths (Optional):** If tools are not in your global PATH, edit the path variables at the top of the script (`MKVTOOLNIX_DIR` e `FFMPEG_BIN`).
3. **Install the Python library:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Run:**
   ```bash
   # Translate all MKVs in the folder
   python translate_subtitles_google_win.py *.mkv

   # EXTRACT ONLY (no translation)
   python translate_subtitles_google_win.py your_video.mkv --extract-only
   ```

<a name="configuração-de-caminhos"></a>
### ⚙️ Configuração de Caminhos / Path Configuration

Se você receber um erro de "Ferramenta não encontrada", edite o script:
If you get a "Tool not found" error, edit the script:

```python
# Windows Example
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
FFMPEG_BIN     = r"C:\ffmpeg\bin\ffmpeg.exe"
```
