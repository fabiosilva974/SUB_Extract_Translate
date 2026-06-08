# Documentação: `transcribe_audio.py`

## Objetivo
O script serve para converter um arquivo de áudio puro (como `.mp3` ou `.wav`) em um arquivo de legenda formato `.srt`. Ele usa a IA Whisper da OpenAI, e suporta tanto transcrever no idioma original quanto traduzir diretamente para o inglês durante a transcrição.

## Fluxo de Funcionamento
1. **Injeção de Dependências de Sistema**: O diretório binário do FFmpeg é adicionado explicitamente ao `PATH` do sistema para que o Whisper possa utilizá-lo na extração de dados do áudio.
2. **Definição de Argumentos**: O usuário passa o arquivo de áudio e pode parametrizar o modelo de IA, o idioma e a tarefa (`transcribe` ou `translate`).
3. **Instanciação do Modelo Whisper**: A IA carrega o modelo especificado (`tiny`, `base`, `small`, `medium` ou `large`) em memória (baixando, se necessário).
4. **Execução da Tarefa**: 
   - Se for `--task transcribe`, o Whisper apenas escreve o áudio mantendo o idioma.
   - Se for `--task translate`, o Whisper faz o *speech-to-text* traduzindo o conteúdo de áudio estrangeiro diretamente para o inglês.
5. **Geração do Arquivo SRT**: O método `get_writer` é usado para exportar o resultado processado em um arquivo de legenda padrão, movendo em seguida para a pasta final designada com o nome configurado pelo usuário.

## Dependências
- **Python 3.x**
- **openai-whisper**: Módulo de IA.
- **FFmpeg**: Configurado obrigatoriamente no sistema para que o Whisper possa processar a mídia.
- **Nativas**: `os`, `sys`, `argparse`, `pathlib`, `shutil`.

## Lógica Utilizada
Diferente do script `audio_to_srt_whisper.py` que lida com o vídeo inteiro, esse script é focado num pipeline mais modular onde a pessoa já possui o arquivo `.mp3` isolado. A principal sacada lógica é aproveitar a funcionalidade embutida no Whisper de *cross-lingual translation* (tarefa `translate`), que permite receber um áudio em japonês ou português, por exemplo, e gerar automaticamente uma legenda SRT em inglês, sem precisar de um serviço externo de tradução extra de texto.
