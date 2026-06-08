# Documentação: `translate_ass_google.py`

## Objetivo
O script processa arquivos de legenda no formato `.ass` (Advanced SubStation Alpha) para traduzir o texto dos diálogos sem quebrar a intrincada formatação (cores, posições e tags complexas) usando a API pública e gratuita do Google Translate através da biblioteca `deep-translator`.

## Fluxo de Funcionamento
1. **Ingestão de Arquivos**: O script recebe via terminal múltiplos arquivos ou *wildcards* (como `*.ass`) e itera sobre cada um deles, abrindo-os e lendo todas as linhas.
2. **Parseamento ASS (`translate_ass_file`)**: Como o `.ass` não é um formato de blocos empilhados (como SRT), mas sim tabelado, o script lê linha a linha procurando por `Dialogue:`. A especificação ASS diz que após `Dialogue:`, os 9 primeiros campos divididos por vírgulas representam metadados (camada, tempo de início, tempo de fim, estilo, ator, margens e efeitos) e tudo após a nona vírgula é o texto do diálogo em si. O script salva essas duas informações separadas.
3. **Tradução em Lotes**: Para não ser bloqueado pela API do Google Translate por fazer requisições demais muito rápido, os textos isolados são agrupados em "blocos" (`BATCH_SIZE = 30`) e submetidos ao `GoogleTranslator`.
4. **Reconstrução Segura**: De posse dos blocos textuais agora em português, o script itera novamente sobre os índices salvos e concatena os mesmos metadados de 9 campos (tempos e estilos inalterados) com o novo texto traduzido.
5. **Gravação**: Gera um novo arquivo sobrescrevendo a versão local adicionando `.pt.ass`.

## Dependências
- **Python 3.x**
- **deep-translator**: Utilitário robusto que mapeia acessos web gratuitos (não-oficiais sem chave API) a diversos tradutores (neste caso, `GoogleTranslator`).
- **Nativas**: `os`, `sys`, `argparse`, `glob`, `pathlib`.

## Lógica Utilizada
A lógica primária contorna o problema de formatadores de legendas animes (ASS) onde tradutores online normais destroem o layout ao traduzir nomes de classes ou tempos de formatação (`{\fad(500,500)\pos(50,50)}`). Separando explicitamente o array do CSV interno através de `split(',', 9)`, asseguramos que o script só envie letras e caracteres legíveis aos servidores do Google e re-encaixe o output sem perturbar a infraestrutura subjacente.
