# Documentação: `translate_subtitles_google_win.py`

## Objetivo
Trata-se de uma versão aprimorada/otimizada do script `translate_subtitles_google.py`, projetada com *hardcodes* de caminhos específicos e tratamento especial para funcionar de forma mais confiável e tolerante a erros no ambiente Microsoft Windows.

## Fluxo de Funcionamento
1. **Configuração de Caminhos Globais**: Diferente das versões Linux/Mac, o script define explicitamente as pastas de instalação (`C:\Program Files\MKVToolNix` e a pasta do executável do FFmpeg em `C:\ffmpeg-...`).
2. **Override de Executáveis**: A função utilitária `run` verifica um dicionário `TOOLS` para mapear comandos curtos (`mkvmerge`, `ffmpeg`) diretamente para o caminho exato do `.exe`, evitando dores de cabeça se o usuário não configurou as variáveis de ambiente PATH do Windows.
3. **Parseamento de Trilhas**: O `mkvmerge -J` devolve a estrutura das faixas, sendo listadas em tela caso o usuário invoque com `--list-tracks`.
4. **Extração Baseada no Codec Original**: O arquivo cru é removido para dentro de uma pasta `tempfile` respeitando a extensão do codec nativo do vídeo (ex: salva como `.ass` temporário se a trilha for detectada como advanced substation).
5. **Normalização FFmpeg**: Força a conversão do arquivo nativo para o formato "Seguro" `.srt` internamente.
6. **Desmembramento e Tradução**: Como nas outras versões, aplica Regex *multiline*, quebra em lotes de 30 para fugir do rate-limiting do Google, envia via API *deep-translator* e remonta o quebra-cabeça.
7. **Reconstrução Otimizada**: Constrói o texto na pasta temporária. Se o usuário pediu saída em `.ass`, o FFmpeg roda por último e injeta as regras CSS/estilos padrão na legenda; caso contrário, é apenas uma operação de cópia (`shutil.copy`).

## Dependências
- **Python 3.x**
- **Ferramentas de Terceiros Locais**: MKVToolNix instalado (`mkvmerge.exe`, `mkvextract.exe`) e FFmpeg *build* para Windows (`ffmpeg.exe`).
- **Bibliotecas Python**: `deep-translator` (Google Translate API hook).
- **Módulos**: `subprocess` (parametrizado para evitar bugs de enconding do `cmd.exe` usando `errors="replace"`), `argparse`, `json`, `re`.

## Lógica Utilizada
A lógica primária dessa versão é blindar o script contra o caos de paths e encodings de terminal do Windows. A função `subprocess.run()` recebe `encoding="utf-8"` com flag de fallback de erro. Ao injetar um dicionário global de caminhos absolutos, ele evita que dependências externas interfiram. Outro refinamento lógico importante é que na fase temporária, a legenda sempre começa na sua extensão de nascença e é transcodificada pelo FFmpeg local internamente, garantindo que o interpretador regex não engasgue em binários bizarros que poderiam corromper a tradução.
