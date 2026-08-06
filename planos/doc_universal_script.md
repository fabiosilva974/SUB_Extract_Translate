# Manual do Script Universal de Conversão (`batch_process_universal.py`)

Este documento descreve as funcionalidades do script universal e como utilizá-lo para processamento em paralelo ("Fazenda de Renderização") entre múltiplas máquinas (Windows e Linux).

## Como Funciona o Paralelismo? (Arquivos `.lock`)

O script foi projetado para ler a exata mesma lista `.csv` em vários computadores simultaneamente.
Para que duas máquinas não processem o mesmo arquivo ao mesmo tempo, ele usa o sistema de **Mutex Locks**:

1. A Máquina A olha a primeira linha da planilha: `Filme 1`.
2. Antes de encodar, a Máquina A cria um arquivo vazio chamado `Filme 1.mkv.lock` no NAS.
3. Segundos depois, a Máquina B também chega na primeira linha da planilha. Ela vê que existe um `.lock`, entende que está em andamento, e pula para a linha debaixo (`Filme 2`).
4. Quando a Máquina A terminar com sucesso (ou der erro), ela mesma limpa e deleta o `.lock`.

Isso garante **0% de chance** de corrupção ou colisão, permitindo que você coloque 2, 3, ou 5 computadores diferentes rodando o mesmo script na mesma lista ao mesmo tempo. Aquele que for mais rápido pegará mais arquivos.

## Vantagens Agnosticas

O script possui "cérebros" embutidos para rodar em qualquer lugar sem precisar ser modificado:
- **Universal Path Translator**: Você pode gerar a lista `.csv` no Windows e usá-la no Linux (ou vice-versa). O script traduz os caminhos na hora (`/mnt/Media` para `\\192.168.0.99\Media`).
- **Autodetect HW**: Ele roda comandos internos (`ffmpeg -hwaccels`) para descobrir se o PC possui NVIDIA (NVENC) ou AMD (AMF/DXVA2) e ajusta a conversão para a velocidade máxima possível de hardware.
- **Anti-Inchaço (Anti-Bloat)**: Se ele descobrir que a conversão em HEVC gerou um arquivo maior que o antigo (raro, mas ocorre com releases RARBG), ele automaticamente descarta o novo arquivo para não gastar o seu espaço à toa, removendo a trava `.lock` e ignorando a tag `--delete`.
- **Subtítulos de Animes**: Preserva os nomes longos dos filmes orientais e os nomes dos episódios, impedindo que colidam com outros da mesma franquia.

## Como Executar

Seja no PowerShell (Windows) ou no Terminal SSH (Linux), a sintaxe é idêntica:

**Fase de Qualidade (Apenas os Lotes Pilotos, sem deletar originais)**
```bash
python batch_process_universal.py --csv "mapa_filmes.csv"
```

**Fase Produção (Limpeza Geral da Biblioteca)**
```bash
python batch_process_universal.py --csv "mapa_filmes.csv" --all --delete
```
