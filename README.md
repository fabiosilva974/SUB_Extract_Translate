# MKV Subtitle Translator (Google Translate) / Tradutor de Legendas MKV

[Português](#português) | [English](#english)

---

<a name="português"></a>
## 🇧🇷 Português

### Descrição
Este script automatiza a extração e tradução de legendas de arquivos `.mkv`. Ele identifica as faixas de legenda, extrai a escolhida, converte para o formato desejado (SRT ou ASS) e traduz o conteúdo para português brasileiro.

### ✨ Funcionalidades
- **Suporte a Formatos:** Agora você pode escolher entre os formatos **SRT** ou **ASS** (`--format ass`). O formato ASS é mais completo e preserva melhor as características da legenda original.
- **Múltiplos Arquivos:** Suporta o processamento de vários vídeos ou arquivos SRT em sequência.
- **Extração Automática:** Busca faixas de legenda dentro do container MKV.
- **Tradutor Independente de SRT:** Script `translate_srt_google.py` dedicado a traduzir arquivos `.srt` existentes.
- **Apenas Extração:** Parâmetro `--extract-only` para extrair a legenda original sem realizar a tradução.
- **Conversão de Codec:** Transforma legendas complexas (PGS/ASS) em SRT para tradução via FFmpeg.

### 🚀 Início Rápido
1. **Instale as dependências do sistema:** MKVToolNix e FFmpeg.
2. **Instale a biblioteca Python:** `pip install -r requirements.txt`
3. **Execute:**
   ```bash
   # Extrair legenda em formato ASS (mais completo)
   python translate_subtitles_google_win.py filme.mkv --extract-only --format ass

   # Extrair e traduzir (saída em .pt.srt)
   python translate_subtitles_google_win.py *.mkv
   ```

---

<a name="english"></a>
## 🇺🇸 English

### Description
This script automates the extraction and translation of subtitles from `.mkv` files. It identifies subtitle tracks, extracts the chosen one, converts it to the desired format (SRT or ASS), and translates the content to Brazilian Portuguese.

### ✨ Features
- **Format Support:** You can now choose between **SRT** or **ASS** formats (`--format ass`). The ASS format is more comprehensive and better preserves the characteristics of the original subtitle.
- **Batch Processing:** Supports multiple MKV or SRT files in sequence.
- **Automatic Extraction:** Scans for subtitle tracks within the MKV container.
- **Standalone SRT Translator:** Dedicated `translate_srt_google.py` script for translating existing `.srt` files.
- **Extraction Only:** Use `--extract-only` parameter to extract the original subtitle without translating.
- **Codec Conversion:** Converts complex subtitles (PGS/ASS) to SRT for translation using FFmpeg.

### 🚀 Quick Start
1. **Install system dependencies:** MKVToolNix and FFmpeg.
2. **Install Python library:** `pip install -r requirements.txt`
3. **Run:**
   ```bash
   # Extract subtitle in ASS format (more comprehensive)
   python translate_subtitles_google_win.py movie.mkv --extract-only --format ass

   # Extract and translate (outputs .pt.srt)
   python translate_subtitles_google_win.py *.mkv
   ```
