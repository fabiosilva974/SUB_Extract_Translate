# Configuração Definitiva do Linux Mint para Conversão de Vídeo (GTX 1080)

> [!NOTE]
> **Status: [CONCLUÍDO]**
> Servidor Linux Mint configurado com sucesso! Usuário `conversor` criado, encoder de hardware NVENC validado e o script principal `batch_process_anime.py` foi atualizado para suporte 100% multiplataforma.

Este plano foi ajustado com as informações coletadas do seu servidor **Linux Mint 22.3**.
Excelente notícia: **Os drivers da NVIDIA (535.288.01) e o CUDA 12.2 já estão instalados perfeitamente!** Os diretórios de rede do seu NAS (`192.168.0.99`) já estão montados na pasta `/mnt/`.

Isso significa que **NÃO precisamos reiniciar o servidor** e a configuração será super rápida.

### Etapa 1: Criação do Usuário Dedicado

Criaremos o usuário `conversor` e daremos a ele permissões administrativas.

```bash
sudo adduser conversor
sudo usermod -aG sudo conversor
```

### Etapa 2: Instalação do Python e FFmpeg

O FFmpeg nativo do Linux Mint já vem com o suporte `nvenc` (NVIDIA) ativado. Instalaremos ele e as bibliotecas do Python.

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg pciutils
```

### Etapa 3: Validação do FFmpeg com a GTX 1080

Testaremos se o FFmpeg reconhece a sua placa de vídeo para conversão acelerada:

```bash
ffmpeg -encoders 2>/dev/null | grep hevc_nvenc
```

### Etapa 4: Setup dos Scripts e Acesso aos Vídeos

Como seus vídeos estão nos compartilhamentos do NAS (provavelmente em `/mnt/Files`), daremos permissão de leitura/escrita para todos nos pontos de montagem, e configuraremos os scripts para rodar de lá.

```bash
# Copiar o diretório de scripts (assumindo que você faça um git clone ou copie a pasta)
# O usuário conversor usará o "batch_process_anime.py" passando --input /mnt/Files/...
```
