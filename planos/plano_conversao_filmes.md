# Plano Faseado: Conversão Segura de Filmes e Padronização

Para garantir que a qualidade final dos vídeos fique perfeita (sem perdas visíveis ou dessincronização) e os nomes padronizados no formato correto, implementaremos a solução em três fases controladas.

## Fase 1: Mapeamento e Conversão Piloto (Segura)
1. **Script de Mapeamento (`planner_filmes.py`)**: 
   - Varrerá a pasta `/mnt/Media/filmes` inteira.
   - Usará a biblioteca `guessit` e o FFprobe para extrair Título, Ano e Resolução (1080p, 4K, etc).
   - Gerará os novos nomes padronizados (ex: `Nome.Ano.Resolucao.H265.mkv`).
   - Avaliará a oportunidade de ganho em Gigabytes.
2. **Seleção Cirúrgica do Lote de Teste**:
   - Ordenaremos a lista gerada para extrair **apenas os 20 arquivos individuais** soltos que darão a maior economia de disco.
   - Incluiremos **1 filme específico da subpasta "HarryPotter"** (onde há um alto ganho documentado).
3. **Conversão Conservadora (`batch_process_linux.py`)**:
   - O script rodará apenas nesses 21 arquivos.
   - Ele **NÃO excluirá** o arquivo H.264 original. O original e o arquivo novo (H265) ficarão lado a lado para comparação.

## Fase 2: Homologação Manual (QA)
Você assistirá a trechos críticos (explosões, cenas escuras, etc.) desses 21 filmes piloto diretamente da sua TV ou computador.
- Se o áudio, a qualidade de imagem e as legendas estiverem perfeitos, daremos o sinal verde.

## Fase 3: Automação Definitiva e Limpeza
Após a sua aprovação da Fase 2:
- Alterarei o script `batch_process_linux.py` para ativar a rotina de exclusão (`delete`).
- O script rodará sobre o resto da pasta `filmes` (lote completo) e, **assim que gerar o H265 com sucesso, ele deletará o arquivo H264 antigo instantaneamente** para recuperar o espaço no NAS.
