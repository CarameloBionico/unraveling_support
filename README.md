# Suporte desfiável — protótipo 02

Revisão para **PETG, bico de 0,4 mm, um único material e camada de 0,2 mm**. A primeira versão está preservada em `generate.py`, `output/`, `v1.html` e `README_v1.md`.

## O que mudou

Na primeira versão, cada sanfona era uma fileira independente, unida às demais pela base. Mesmo dentro de uma fileira, os cordões dos diferentes níveis dependiam de ligações fracas. Sem base e ligações, sobravam **16 cordões separados**.

Agora o cordão percorre uma fileira, faz um retorno horizontal de 180 graus, volta pela próxima e atravessa a largura do suporte. Ao completar o andar, uma curva vertical leva ao próximo, onde o percurso continua em sentido inverso. São **12 retornos horizontais e 3 curvas verticais**, mantendo a seção nominal do cordão de **0,9 × 0,8 mm**. O caminho total tem aproximadamente **598 mm**.

O cordão principal continua sendo **um único sólido mesmo sem base, ancoragens e ligações fracas**. A auditoria geométrica também verifica que os 31 trechos construtivos formam uma cadeia aberta, com duas extremidades, sem bifurcações, contatos extras ou lacunas. Não depende de uma lingueta nem exige uma única puxada: pode-se agarrar qualquer região acessível e recomeçar caso o cordão rompa.

Essas passagens criam ligações laterais permanentes na geometria, que devem compartilhar os esforços entre fileiras. Isso não mede rigidez nem garante estabilidade durante todas as etapas da impressão. As curvas também precisam resistir à puxada; continuidade geométrica não garante resistência mecânica entre camadas.

## Visualizar e imprimir

Abra `index.html` no navegador. Funciona localmente sem internet, carregando `output_v2/preview-data.js`. Use:

- **Mostrar só o cordão**: remove visualmente a base e as ligações fracas, evidenciando a continuidade.
- **Traçar o percurso**: acompanha a linha central, em sobreposição ao modelo. O controle de progresso não simula a retirada nem a trajetória do bico.
- **Níveis visíveis** e as vistas superior/lateral: permitem inspecionar retornos e subidas.
- **Comparar com a versão 01**: abre a geometria anterior preservada.

| Variante | Ligações fracas | Suporte para imprimir | Com peça de teste |
|---|---|---|---|
| A — fina | 0,45 × 0,45 mm | [A_fina_suporte.stl](output_v2/A_fina_suporte.stl) | [A_fina_conjunto.stl](output_v2/A_fina_conjunto.stl) |
| B — média | 0,60 × 0,60 mm | [B_media_suporte.stl](output_v2/B_media_suporte.stl) | [B_media_conjunto.stl](output_v2/B_media_conjunto.stl) |
| C — forte | 0,80 × 0,80 mm | [C_forte_suporte.stl](output_v2/C_forte_suporte.stl) | [C_forte_conjunto.stl](output_v2/C_forte_conjunto.stl) |

Comece pelo suporte isolado da variante B. As três variantes têm os mesmos retornos de espessura integral; somente os pontos fracos entre níveis variam. Os arquivos `*_cordao_sem_ligacoes.stl` servem para inspecionar a continuidade. **Não são o corpo de prova a imprimir**: não incluem a base e os apoios previstos para a fabricação.

Dimensões externas do suporte: **28,7 × 12,8 × 17,6 mm**. Com a peça de teste: **31,9 × 12,8 × 19 mm**. As curvas laterais exigiram ampliar a base e afastar as paredes da peça. A folga nominal sob o teto continua sendo 0,2 mm.

## Configuração de fatiamento

1. Importe o STL em milímetros, escala 100%, na orientação fornecida. Preserve a base apoiada na mesa.
2. Use seu perfil calibrado de PETG, com bico de 0,4 mm, camada inicial e demais camadas de 0,2 mm. Não altere temperatura, ventilação ou velocidade entre variantes durante a comparação.
3. **Desative os suportes automáticos**: a estrutura já está modelada. Suportes extras preencheriam os vazios necessários para removê-la.
4. Ponto inicial: linhas de 0,4 mm, 2 paredes, preenchimento de 100%, 4 camadas de topo e fundo. Preserve paredes finas/lacunas conforme o seu fatiador.
5. Confira as ligações em Z = 4,6/4,8; 9,0/9,2; 13,4/13,6 mm e a presença de todas as curvas nas pontas. Larguras pequenas podem ser aproximadas à mesma largura de extrusão pelo fatiador.
6. Ao imprimir `*_conjunto.stl`, mantenha as duas cascas como um modelo, sem reorganizar suas partes. Há dois sólidos intencionalmente separados: suporte e peça. Preserve a folga sob o teto.

As curvas horizontais de níveis superiores incluem pequenas pontes entre fileiras. O teste de início de camadas não valida a qualidade dessas pontes nem a ordem exata em que o seu fatiador vai imprimi-las.

## Teste físico

Após esfriar e retirar o modelo da mesa, segure a base e agarre uma curva acessível com o alicate. Puxe para fora da estrutura, observe se os pontos fracos cedem em sequência e acompanhe se o cordão consegue passar pelo retorno horizontal e pela curva vertical. Caso rompa, agarre outro trecho.

Compare A, B e C: sucesso da impressão, tempo e número de puxadas, comprimento dos segmentos retirados, localização das rupturas e eventual saída de blocos inteiros. Se quebrar sempre nos retornos, a próxima revisão deve ajustar seção ou raio dessas curvas. Se quebrar no cordão antes de soltar os pontos de união, compare a variante A.

A base permanece inteira. O teto é uma peça plana para ensaio; esta versão não implementa uma interface densa desfiável nem gera suportes para modelos arbitrários.

## Reproduzir e validar

Ambiente usado: Python 3.12, dependências fixadas em `requirements.txt`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate_v2.py
.\.venv\Scripts\python.exe validate_slicing.py --out output_v2
.\.venv\Scripts\python.exe validate_v2.py
```

`generate_v2.py --config minha_config.json --out outra_pasta` aceita os campos de `output_v2/config.json`. Esta versão exige um número par de fileiras e raio vertical suficiente para a seção do cordão. O visualizador e `validate_v2.py` usam `output_v2` como pasta padrão. Não redimensione o STL para calibrar uma única dimensão; regenere os parâmetros.

Evidências disponíveis:

- `output_v2/validation.json`: malhas fechadas e orientadas, volume positivo, sem faces degeneradas, um componente no cordão principal e no suporte; dois componentes no conjunto, sem interferência com a peça. Verificação da cadeia por interseções volumétricas reais entre os trechos.
- `output_v2/audit/slicing_validation.json`: 88 camadas examinadas por variante, sem ilhas nascendo sem sobreposição alguma com a camada anterior. CuraEngine 4.13.1 preservou as 80 amostras de ligações por variante, sem avisos de faces sobrepostas ou camadas vazias no suporte e no conjunto.
- `output_v2/audit/return_validation.json`: **687 amostras das curvas por variante** encontram extrusão próxima na camada correspondente. Distância máxima observada ao centro de uma linha: 0,247 mm; limite de verificação: 0,30 mm. Esse teste confirma a presença de material nas curvas, sem simular sua resistência.

Os G-codes em `audit/` foram produzidos com uma máquina genérica para inspeção. Para imprimir, gere o G-code dos STLs usando o perfil da sua impressora.

**Ainda não houve teste físico de estabilidade, força ou desfiamento.** Todas as verificações acima são geométricas ou de fatiamento.
