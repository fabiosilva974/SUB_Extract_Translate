# MKV Subtitle Translator (Google Translate) / Tradutor de Legendas MKV

[Português](#português) | [English](#english)

---

<a name="português"></a>
## 🇧🇷 Português

### Descrição
Este projeto automatiza a extração e tradução de legendas de arquivos `.mkv`, além de oferecer ferramentas independentes para traduzir arquivos de legenda `.srt` e `.ass`.

### ✨ Funcionalidades
- **Suporte a Formatos:** Escolha entre **SRT** ou **ASS** (`--format ass`) na extração.
- **Tradutores Independentes:** 
  - `translate_srt_google.py`: Traduz arquivos `.srt` externos.
  - `translate_ass_google.py`: Traduz arquivos `.ass` mantendo todos os estilos, cores e fontes originais (tradução cirúrgica).
  - `extract_audio.py`: Extrai a faixa de áudio de um vídeo MKV filtrando pelo idioma.
  - `transcribe_audio.py`: Usa a IA do OpenAI Whisper para transcrever áudio em legendas `.srt`.
- **Múltiplos Arquivos:** Suporta o processamento de vários vídeos ou legendas em sequência usando curingas (ex: `*.mkv`, `*.ass`).
- **Extração Automática:** Busca e isola faixas de legenda dentro do container MKV.
- **Apenas Extração:** Parâmetro `--extract-only` para isolar a legenda original sem traduzir.

### 🚀 Início Rápido
1. **Instale as dependências:** MKVToolNix, FFmpeg e `pip install -r requirements.txt`.
2. **Execute:**
   ```bash
   # Traduzir legendas ASS externas mantendo estilos
   python translate_ass_google.py *.ass

   # Traduzir legendas SRT externas
   python translate_srt_google.py *.srt

   # Extrair e traduzir de MKVs
   python translate_subtitles_google_win.py *.mkv

   # Extrair áudio em inglês de um MKV e gerar legenda SRT com IA
   python extract_audio.py video.mkv --lang eng
   python transcribe_audio.py video.mp3 --lang en
   ```

---

<a name="english"></a>
## 🇺🇸 English

### Description
This project automates the extraction and translation of subtitles from `.mkv` files, and provides standalone tools for translating `.srt` and `.ass` subtitle files.

### ✨ Features
- **Format Support:** Choose between **SRT** or **ASS** formats (`--format ass`) during extraction.
- **Standalone Translators:**
  - `translate_srt_google.py`: Translates external `.srt` files.
  - `translate_ass_google.py`: Translates external `.ass` files while preserving all original styles, colors, and fonts (surgical translation).
  - `extract_audio.py`: Extracts the audio track from an MKV video based on language.
  - `transcribe_audio.py`: Uses OpenAI Whisper AI to transcribe audio into `.srt` subtitles.
- **Batch Processing:** Supports multiple videos or subtitles in sequence using wildcards (e.g., `*.mkv`, `*.ass`).
- **Automatic Extraction:** Scans and isolates subtitle tracks within the MKV container.
- **Extraction Only:** Use `--extract-only` to isolate the original subtitle without translating.

### 🚀 Quick Start
1. **Install dependencies:** MKVToolNix, FFmpeg, and `pip install -r requirements.txt`.
2. **Run:**
   ```bash
   # Translate external ASS subtitles preserving styles
   python translate_ass_google.py *.ass

   # Translate external SRT subtitles
   python translate_srt_google.py *.srt

   # Extract and translate from MKVs
   python translate_subtitles_google_win.py *.mkv

   # Extract english audio from an MKV and generate SRT subtitle using AI
   python extract_audio.py video.mkv --lang eng
   python transcribe_audio.py video.mp3 --lang en
   ```
