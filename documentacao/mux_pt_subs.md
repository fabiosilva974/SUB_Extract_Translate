# mux_pt_subs.py

## Objetivo
Após você traduzir os seus arquivos SRT externamente para o idioma desejado (ex: `.pt.srt`), este script automatiza a etapa exaustiva de embutir (mux) de volta essas novas legendas dentro do MKV.
Além de simplesmente colocar a legenda pra dentro, ele é configurado de forma inteligente para marcar a faixa de Áudio nativa (ex: Japonês) e a sua nova Legenda Traduzida como "Padrão" (`default_track_flag`), garantindo que os reprodutores as abram automaticamente.

## Como Funciona a Lógica
1. O usuário passa o caminho base de uma pasta onde se encontram o vídeo original (`nome.mkv`) e a legenda traduzida na mesma pasta (`nome.pt.srt`).
2. O script emparelha-os e usa o `mkvmerge -J` para escanear todas as faixas do vídeo.
3. Procura ativamente por uma faixa de áudio japonesa (`language: jpn`), armazenando sua ID.
4. Gera um comando dinâmico pro `mkvmerge` desabilitando a tag `default` de **todas** as outras legendas e áudios que o arquivo original possuía (`--default-track ID:0`).
5. Habilita a tag `default` somente para o áudio Japonês e a nova legenda PT (`--default-track ID:1`).
6. Cria um vídeo perfeitamente mastigado finalizado em `_PT.mkv`.

## Como Usar
Execute o script em um diretório com episódios, usando `*` para processar uma temporada inteira (série) automaticamente:

```bash
python scripts/mux_pt_subs.py "E:\Pasta\Downloads\Episodios\*.mkv"
```

## Dependências
- `MKVToolNix`: Responsável por toda a manipulação do contêiner (`mkvmerge.exe`).
