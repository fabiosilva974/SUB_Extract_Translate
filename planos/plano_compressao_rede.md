# Escalonamento Global: Processamento de Toda a Unidade V:\

O objetivo desta etapa é evoluir o nosso script atual para que ele consiga varrer e processar discos inteiros (ou bibliotecas completas de séries e filmes), gerando um relatório detalhado de todo o espaço economizado.

## Análise e Ranking de Oportunidades na Unidade V:\
Acabei de rodar um script de diagnóstico avançado na unidade `V:\` inteira. Ele encontrou **42 pastas** contendo cerca de **280 arquivos de vídeo**.

Para maximizar a eficiência, o script filtrou os vídeos que já estão em HEVC/x265 e somou o tamanho dos arquivos restantes. Assim, descobrimos onde estão os maiores ganhos de espaço.

**Top 10 Pastas com Maior Oportunidade de Compressão (GB Livres):**
1. `V:\Banksters.S01` - Oportunidade: **14.14 GB** (6 arquivos não-HEVC)
2. `V:\Series\LietoMe\S01` - Oportunidade: **11.69 GB** (25 arquivos)
3. `V:\anime\Tensei shitara Dragon no Tamago datta` - Oportunidade: **7.87 GB** (11 arquivos)
4. `V:\Series\Pluribus` - Oportunidade: **6.75 GB** (5 arquivos)
5. `V:\Spider-Noir.S01\Spider-Noir - Season 1 [Color]` - Oportunidade: **5.91 GB** (8 arquivos)
6. `V:\anime\Isekai no Seikishi Monogatari...\Season 1` - Oportunidade: **5.36 GB** (13 arquivos)
7. `V:\Hell Mode` - Oportunidade: **5.13 GB** (6 arquivos)
8. `V:\Star City S01` - Oportunidade: **4.72 GB** (1 arquivo)
9. `V:\anime\Seiken Gakuin no Makentsukai` - Oportunidade: **4.26 GB** (12 arquivos)
10. `V:\anime\Mushoku no Eiyuu` - Oportunidade: **4.21 GB** (7 arquivos)

*Total de oportunidade apenas no Top 10: Mais de 70 GB de economia em potencial!*

## Proposed Changes

### [MODIFY] [batch_process_anime.py](file:///E:/Traducao/scripts/batch_process_anime.py)
Eu atualizarei o script atual para adicionar 3 novas funcionalidades robustas:

1. **Suporte a Subpastas (Recursividade):**
   Adicionarei um parâmetro `--recursive` (ou `-r`). Quando ativado, o script vai entrar em cada subpasta, processar os vídeos, e manter a organização.

2. **Geração do Log de Relatório (CSV):**
   Criarei um sistema de Log que vai escrever em um arquivo na raiz (`V:\compress_log.csv`) toda vez que um vídeo for finalizado. O Log conterá as colunas exatas que você pediu:
   * Caminho completo + Nome anterior
   * Tamanho anterior (em MB)
   * Tempo de Conversão (Min:Seg)
   * Novo Nome
   * Novo Tamanho (em MB)

3. **Arquitetura de Saída (Output) com Pastas Limpas:**
   Como vamos processar dezenas de pastas, a abordagem de criar uma pasta "Convertidos" dentro de cada pasta original pode virar uma bagunça. 
   **Minha sugestão de design**: Fazer o script recriar a estrutura de pastas em um diretório espelho `V:\Convertidos\`, **mas também sanitizando os nomes das pastas!**
   Ex: Se o original está em `V:\anime\Sousou no Frieren 2nd Season\ep1.mkv`, o script vai limpar os espaços e símbolos e salvar em `V:\Convertidos\anime\Sousou_no_Frieren_2nd_Season\ep1_HEVC.mkv`. Isso mantém sua biblioteca original intocada e organiza todos os convertidos em um único espelho, já com pastas padronizadas e sem espaços!

## Estratégia de Execução

Ao invés de processar tudo de uma vez, **vamos adotar uma abordagem gradual**:
1. Eu alterarei o script (`batch_process_anime.py`) para suportar a recursividade, o Log CSV e a limpeza de nomes de pastas, conforme planejado.
2. Nós executaremos o script **inicialmente apenas na pasta `V:\Banksters.S01`** (a campeã de gordura, com 14 GB).
3. Isso servirá como nosso "Lote Piloto". Poderemos verificar o tempo de processamento dessa pasta para estimarmos quanto tempo a unidade inteira vai levar.
4. As demais pastas da unidade `V:\` (o resto do Top 10) só serão iniciadas futuramente, através do seu comando explícito.

## Verification Plan

### Teste Simulado (Lote Piloto)
- Assim que você aprovar este plano, eu alterarei o script para implementar todas as novas funcionalidades (Log, Espelho com nomes limpos).
- Em seguida, nós acionaremos o script passando APENAS `--input "V:\Banksters.S01"` para fazer o lote piloto.
- Analisaremos o Log (CSV) gerado para estimar o tempo e a economia de disco exata dessa primeira rodada!
