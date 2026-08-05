# Documentação: `audio_to_srt_whisper.py`

## Objetivo
O script tem a finalidade de extrair o áudio de um arquivo de vídeo (especificamente `.mkv`) e utilizar a inteligência artificial Whisper, da OpenAI, para gerar automaticamente um arquivo de legenda (`.srt`) contendo a transcrição.

## Fluxo de Funcionamento
1. **Configuração de Ambiente**: O script começa adicionando o diretório binário do FFmpeg à variável de ambiente `PATH`. Isso é estritamente necessário porque o Whisper, nos bastidores, chama o comando `ffmpeg` para extrair o áudio de um vídeo passado diretamente para ele.
2. **Validação de Dependências**: Verifica se a biblioteca `openai-whisper` está instalada, orientando o usuário caso não esteja.
3. **Parseamento de Argumentos**: Coleta as informações passadas pelo usuário via terminal (linha de comando). As opções são o arquivo de vídeo `.mkv`, o tamanho do modelo (`tiny`, `base`, `small`, `medium`, `large`), o idioma e um caminho opcional de saída.
4. **Carregamento do Modelo IA**: Instancia na memória o modelo escolhido do Whisper. Se for a primeira execução desse modelo específico, ele fará o download da internet.
5. **Transcrição**: O método `model.transcribe()` é acionado passando o arquivo do vídeo. O próprio Whisper lida com extrair o áudio usando FFmpeg em background e converte o som para texto particionado por tempo.
6. **Exportação da Legenda**: Um utilitário de escrita nativo do Whisper (`get_writer`) pega os resultados da IA e escreve um arquivo estruturado de legenda (SRT) no diretório original ou em outro especificado pelo usuário. O script encerra movendo/renomeando o arquivo gerado para garantir que os nomes fiquem de acordo com as preferências do usuário.

## Dependências
- **Python 3.x**
- **FFmpeg**: Necessário no sistema e configurado no PATH para extração do áudio (o caminho está hardcoded no início do script para facilitar no Windows).
- **openai-whisper**: Biblioteca da OpenAI para transcrição via IA (`pip install openai-whisper`).
- **Nativas do Python**: `os`, `sys`, `argparse`, `pathlib`, `shutil`.

## Lógica e Estratégia Utilizada
A grande vantagem deste script é delegar todo o trabalho pesado de áudio ao Whisper. Em vez de usar scripts separados para extrair o `.mp3` primeiro e passar para transcrição, ele apenas injeta o FFmpeg na rota de execução (`os.environ["PATH"]`) e passa o vídeo original direto pro modelo IA, que faz a pipeline inteligente de separar os canais de áudio, convertê-los a 16kHz e rodar inferência de linguagem para retornar blocos de texto.
