# Mapeamento e Diagnóstico da Unidade U:\

A varredura da unidade `U:\` revelou ser um verdadeiro gigante em comparação ao disco anterior. Encontramos mais de **6.288 arquivos de vídeo**, e as oportunidades de compressão são colossais. 

## Análise da Varredura Piloto (Top 15 Oportunidades)
Filtrando tudo que ainda não está em HEVC/x265, aqui está o ranking de "esponjas de disco" onde podemos ganhar mais espaço na unidade U:

1. **`U:\Anime-Cartoon\LegendoftheGalacticHeroes...`** - 63.65 GB (48 arquivos)
2. **`U:\Anime-Cartoon\Nana [BD 1080p FLAC]`** - 42.93 GB (47 arquivos)
3. **`U:\Anime-Cartoon\SteinsGate\S01`** - 40.91 GB (25 arquivos)
4. **`U:\Anime-Cartoon\Sousou no Frieren`** - 39.55 GB (28 arquivos)
5. **`U:\Anime-Cartoon\SpyxFamily\...`** - 37.45 GB (25 arquivos)
6. **`U:\Anime-Cartoon\Souten Kouro [BD][1080P]`** - 35.76 GB (26 arquivos)
9. **`U:\Anime-Cartoon\Kimetsu.no.Yaiba\S03 Yuukaku Hen`** - 33.21 GB (22 arquivos)
10. **`U:\series\Dark.Matter.2024`** - 31.86 GB (8 arquivos)
11. **`U:\Anime-Cartoon\Shangri-La Frontier`** - 31.33 GB (22 arquivos)
12. **`U:\Anime-Cartoon\Konpeki no Kantai [BDRip 1080p]`** - 30.77 GB (15 arquivos)
13. **`U:\Anime-Cartoon\Dr. Stone\[Erai-raws] Dr. Stone - 01 ~ 24...`** - 30.18 GB (24 arquivos)
14. **`U:\Anime-Cartoon\Dr. Stone\Dr. Stone - New World`** - 30.10 GB (22 arquivos)
15. **`U:\series\Yumis.Cells\...`** - 29.12 GB (14 arquivos)

*Somente nesse Top 15, temos mais de **580 GB** de espaço que pode ser convertido e reduzido em 60 a 70%!*

## Proposed Changes

Para que você tenha controle absoluto sobre esses dados de forma contínua, vou criar um script permanente na sua pasta de ferramentas.

### [NEW] [map_drive_opportunities.py](file:///E:/Traducao/scripts/map_drive_opportunities.py)
Um script desenhado especificamente para criar relatórios de bibliotecas de mídia:
- **Varredura Completa**: Lê qualquer unidade ou pasta (ex: `U:\`).
- **Detecção Inteligente**: Identifica pelo nome ou por Metadados (se você quiser) se o arquivo é HEVC.
- **Relatório CSV/TXT**: Gera um arquivo exportável (`mapeamento_U.csv`) ordenado por tamanho desperdiçado, dizendo exatamente o caminho da Série/Temporada, quantos arquivos são HEVC e o tamanho em GB da oportunidade de compressão.

## Open Questions

> [!IMPORTANT]
> **Você prefere que o relatório gerado pelo novo script seja um CSV (para abrir no Excel e fazer gráficos/tabelas dinâmicas) ou apenas um `.txt` simples com a lista?**

## Verification Plan
1. Após a sua aprovação, criarei o script `map_drive_opportunities.py`.
2. Executaremos o script apontando para `U:\`.
3. Verificaremos o relatório final gerado para garantir que você tenha um mapa detalhado da sua biblioteca antes de decidirmos mandar nosso batch de compressão atacar essas pastas.

## Execução Atual
- O script `map_drive_opportunities.py` já foi modificado para gerar o arquivo `.md` dividido por subpastas.
- A execução atual está ocorrendo em segundo plano e salvando o relatório em: `E:\Traducao\melhorias\relatorio_U.md`
