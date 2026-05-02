# MKV Subtitle Translator (Google Translate) / Tradutor de Legendas MKV

[Português](#português) | [English](#english)

---

<a name="português"></a>
## 🇧🇷 Português

### Descrição
Este script automatiza a extração e tradução de legendas de arquivos `.mkv`. Ele identifica as faixas de legenda, extrai a escolhida, converte para o formato SRT (se necessário) e traduz o conteúdo para português brasileiro usando o motor do Google Translate.

### ✨ Funcionalidades
- **Extração Automática:** Busca faixas de legenda dentro do container MKV.
- **Conversão de Codec:** Transforma legendas ASS/SSA/PGS em SRT via FFmpeg.
- **Tradução Inteligente:** Traduz diálogos mantendo tags de formatação (HTML) e timecodes.
- **Tradução em Lote:** Otimizado para evitar bloqueios de API.

### 🚀 Início Rápido
1. **Instale as dependências do sistema:** MKVToolNix e FFmpeg.
2. **Instale a biblioteca Python:**
   ```bash
   pip install -r requirements.txt
   ```
### 🚀 Início Rápido
1. **Instale as dependências do sistema:** MKVToolNix e FFmpeg.
2. **Configure os caminhos (Opcional):** Se as ferramentas não estiverem no seu PATH global, edite as variáveis no topo do script para apontar para as pastas corretas (veja a seção [Configuração de Caminhos](#configuração-de-caminhos)).
3. **Instale a biblioteca Python:**
...
---

<a name="english"></a>
## 🇺🇸 English

### Description
This script automates the extraction and translation of subtitles from `.mkv` files. It identifies subtitle tracks, extracts the chosen one, converts it to SRT format (if necessary), and translates the content to Brazilian Portuguese using the Google Translate engine.

### ✨ Features
- **Automatic Extraction:** Scans for subtitle tracks within the MKV container.
- **Codec Conversion:** Converts ASS/SSA/PGS subtitles to SRT using FFmpeg.
- **Smart Translation:** Translates dialogues while preserving formatting tags (HTML) and timecodes.
- **Customizable Tool Paths:** Easy configuration for environments where tools are not in the system PATH.
- **Batch Translation:** Optimized to prevent API rate limiting.

### 🚀 Quick Start
1. **Install system dependencies:** MKVToolNix and FFmpeg.
2. **Configure paths (Optional):** If tools are not in your global PATH, edit the path variables at the top of the script (see [Path Configuration](#path-configuration) section).
3. **Install the Python library:**
...
<a name="configuração-de-caminhos"></a>
### ⚙️ Configuração de Caminhos / Path Configuration

Se você receber um erro de "Ferramenta não encontrada", edite o script:
If you get a "Tool not found" error, edit the script:

```python
# Windows Example
MKVTOOLNIX_DIR = r"C:\Program Files\MKVToolNix"
FFMPEG_BIN     = r"C:\ffmpeg\bin\ffmpeg.exe"
```
   ```bash
   pip install -r requirements.txt
   ```
3. **Run:**
   ```bash
   python translate_subtitles_google.py your_video.mkv
   ```
