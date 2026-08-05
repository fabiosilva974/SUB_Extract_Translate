# Documentação: `extract_audio.py`

## Objetivo
O script serve para extrair uma faixa de áudio específica (por padrão a faixa em inglês) de um arquivo de vídeo `.mkv` e salvá-la como um arquivo `.mp3` utilizando as ferramentas MKVToolNix e FFmpeg.

## Fluxo de Funcionamento
1. **Configurações Iniciais**: São definidos os caminhos (hardcoded) para os executáveis `mkvmerge.exe` e `ffmpeg.exe` instalados no Windows.
2. **Recebimento de Parâmetros**: Lê os argumentos da linha de comando, permitindo definir qual arquivo `.mkv` analisar, qual idioma priorizar (opção `--lang`) ou se o usuário deseja apenas ver uma lista das faixas de áudio disponíveis (`--list`).
3. **Mapeamento do Arquivo (mkvmerge)**: O script chama o `mkvmerge` com a flag `-J` (JSON output) e decodifica a resposta para extrair as propriedades das faixas do arquivo, procurando especificamente por aquelas que são do tipo `audio`.
4. **Modo Listagem**: Se a opção `--list` foi informada, o script exibe a tabela de áudios disponíveis com o ID e o idioma e em seguida encerra o script.
5. **Busca e Seleção**: Se a intenção for de fato extrair o áudio, o script varre as faixas identificadas em busca daquela que combine com o idioma alvo.
6. **Extração e Conversão (ffmpeg)**: O arquivo é passado para o `ffmpeg`, que utiliza a flag `-map 0:ID` para capturar apenas a trilha desejada e a converte simultaneamente para `.mp3` usando o codec `libmp3lame`. O arquivo final terá o mesmo nome do vídeo, mas extensão `.mp3`.

## Dependências
- **Python 3.x**
- **MKVToolNix** (`mkvmerge.exe`): Usado para inspeção estrutural e metadados do MKV.
- **FFmpeg**: Usado para extração e transcodificação de áudio de qualquer formato para MP3.
- **Nativas do Python**: `os`, `sys`, `json`, `argparse`, `subprocess`, `pathlib`.

## Lógica Utilizada
Foi separada a fase de "informação" da fase de "extração". Devido ao arquivo MKV conter várias faixas multiplexadas, utilizar o `mkvmerge` para analisar o arquivo no formato JSON é o meio mais robusto para programaticamente encontrar qual ID corresponde a qual idioma. De posse desse ID numérico da faixa, usa-se a capacidade do FFmpeg de pular transcodificações de vídeo desnecessárias mapeando a faixa exata em background para criar um áudio `.mp3` limpo.
