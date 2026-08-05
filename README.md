# MKV Subtitle Translator / Tradutor de Legendas MKV

[Português](#português) | [English](#english)

---

<a name="português"></a>
## 🇧🇷 Português

### Descrição
Este projeto automatiza a extração e tradução de legendas de arquivos `.mkv`, além de oferecer diversas ferramentas independentes para traduzir, analisar, extrair e embutir legendas e áudios em múltiplos formatos. 

### 🧰 Guia de Scripts Disponíveis
Todos os scripts estão localizados na pasta `scripts/` e suas documentações detalhadas encontram-se na pasta `documentacao/`.

#### Tradução
- `scripts/translate_subtitles_google_win.py`: Extrai, traduz (via Google Translate) e remonta legendas de MKVs (versão robusta com caminhos fixos para Windows).
- `scripts/translate_subtitles_google.py`: Versão multiplataforma para extrair e traduzir legendas de MKVs via Google.
- `scripts/translate_subtitles.py`: Traduz legendas embutidas no MKV utilizando a API da Anthropic (Claude).
- `scripts/translate_srt_google.py`: Traduz arquivos `.srt` isolados (externos).
- `scripts/translate_ass_google.py`: Traduz arquivos `.ass` mantendo intactos todos os estilos, cores e tags originais.

#### Extração e Transcrição (Áudio)
- `scripts/extract_audio.py`: Extrai a faixa de áudio de um MKV filtrando pelo idioma desejado (salva em `.mp3`).
- `scripts/transcribe_audio.py`: Usa a IA do OpenAI Whisper para ouvir arquivos de áudio e transcrevê-los em legendas `.srt`.

#### Gerenciamento de Legendas e MKV
- `scripts/identify_subs.py`: Analisa faixas de legenda não identificadas usando IA (`langdetect`) e cria um novo MKV com as tags de idioma corretas.
- `scripts/extract_pt_sub.py`: Procura inteligentemente pela faixa de legenda em Português avaliando o texto (heurística) e extrai o `.srt`.
- `scripts/extract_en_sub.py`: Procura inteligentemente pela faixa de legenda em Inglês avaliando o texto e extrai o `.srt`.
- `scripts/mux_pt_subs.py`: Embuti (mux) a legenda traduzida de volta no arquivo de vídeo original, configurando o Áudio e a Legenda correta como "Padrão" (default) automaticamente.
- `scripts/find_pt_subs.py` e `find_pt_subs2.py`: Scripts rápidos de laboratório usando `ffprobe` para extrair amostras de texto e auxiliar na inspeção manual de faixas.

### 🚀 Início Rápido
1. **Instale as dependências:** MKVToolNix, FFmpeg e o comando `pip install -r requirements.txt`.
2. **Exemplos de uso:**
   ```bash
   # Traduzir legendas ASS externas mantendo estilos
   python scripts/translate_ass_google.py *.ass

   # Traduzir legendas SRT externas
   python scripts/translate_srt_google.py *.srt

   # Identificar idiomas desconhecidos dentro de um MKV
   python scripts/identify_subs.py arquivo.mkv

   # Embutir a legenda traduzida configurando como padrao
   python scripts/mux_pt_subs.py *.mkv

   # Extrair áudio em japonês e traduzir direto para INGLÊS com Whisper
   python scripts/extract_audio.py video.mkv --lang jpn
   python scripts/transcribe_audio.py video.mp3 --lang ja --task translate
   ```

---

<a name="english"></a>
## 🇺🇸 English

### Description
This project automates the extraction and translation of subtitles from `.mkv` files, and provides a full suite of standalone tools for translating, analyzing, extracting, and muxing subtitles and audio tracks.

### 🧰 Scripts Guide
All executable scripts are located in the `scripts/` folder, and their detailed documentations can be found in `documentacao/`.

#### Translation
- `scripts/translate_subtitles_google_win.py`: Extracts, translates (via Google Translate), and remuxes subtitles from MKVs (robust version with fixed paths for Windows).
- `scripts/translate_subtitles_google.py`: Cross-platform version for extracting and translating MKV subtitles via Google.
- `scripts/translate_subtitles.py`: Translates embedded MKV subtitles using the Anthropic API (Claude).
- `scripts/translate_srt_google.py`: Translates standalone external `.srt` files.
- `scripts/translate_ass_google.py`: Translates external `.ass` files preserving all original styles, colors, and layout tags.

#### Audio Extraction and Transcription
- `scripts/extract_audio.py`: Extracts the audio track from an MKV based on a specified language (saves as `.mp3`).
- `scripts/transcribe_audio.py`: Uses OpenAI Whisper AI to transcribe audio files directly into `.srt` subtitles.

#### MKV & Subtitles Management
- `scripts/identify_subs.py`: Analyzes unidentified subtitle tracks using AI (`langdetect`) and generates a new MKV with fixed language tags.
- `scripts/extract_pt_sub.py`: Intelligently searches for the Portuguese subtitle track by analyzing text content (heuristics) and extracts the `.srt`.
- `scripts/extract_en_sub.py`: Intelligently searches for the English subtitle track by analyzing text content and extracts the `.srt`.
- `scripts/mux_pt_subs.py`: Muxes translated subtitles back into the video file, automatically setting the correct Audio and Subtitle tracks as "Default".
- `scripts/find_pt_subs.py` & `find_pt_subs2.py`: Fast lab scripts using `ffprobe` to sample text lines for manual inspection of unknown tracks.

### 🚀 Quick Start
1. **Install dependencies:** MKVToolNix, FFmpeg, and `pip install -r requirements.txt`.
2. **Usage examples:**
   ```bash
   # Translate external ASS subtitles preserving styles
   python scripts/translate_ass_google.py *.ass

   # Translate external SRT subtitles
   python scripts/translate_srt_google.py *.srt

   # Identify unknown subtitle languages in an MKV
   python scripts/identify_subs.py file.mkv

   # Mux translated subtitle and set as default
   python scripts/mux_pt_subs.py *.mkv

   # Extract Japanese audio and transcribe/translate directly to ENGLISH with Whisper
   python scripts/extract_audio.py video.mkv --lang jpn
   python scripts/transcribe_audio.py video.mp3 --lang ja --task translate
   ```
