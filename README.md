# Suporte desfiável — protótipo 01

Experimento para PETG, um bico de **0,4 mm**, um material e camadas de **0,2 mm**. O diâmetro de 0,4 mm foi assumido a partir da conversa; se o bico for realmente de 4 mm, estes modelos não se aplicam.

O cordão tem seção nominal de **0,9 mm na direção Y × 0,8 mm na direção Z** e é construído por várias camadas convencionais. Não depende de extrusão não planar. Sua trajetória ondula em X/Y e em altura. Os níveis alternam picos e vales e são unidos por pequenos pescoços que devem romper antes dos cordões durante a remoção. Essa sequência de ruptura ainda é uma hipótese, não um resultado medido.

## Arquivos para experimentar

Abra `index.html` no navegador; funciona também sem servidor e sem internet. O visualizador permite girar, selecionar a variante, isolar uma fileira, esconder níveis e mostrar a peça de teste. A visualização mostra os componentes de construção coloridos; os STLs de suporte têm as uniões booleanas concluídas.

| Variante | Seção nominal da ligação | Arquivo de suporte | Arquivo com peça de teste |
|---|---|---|---|
| A — fina | 0,45 × 0,45 mm | [A_fina_suporte.stl](output/A_fina_suporte.stl) | [A_fina_conjunto.stl](output/A_fina_conjunto.stl) |
| B — média | 0,60 × 0,60 mm | [B_media_suporte.stl](output/B_media_suporte.stl) | [B_media_conjunto.stl](output/B_media_conjunto.stl) |
| C — forte | 0,80 × 0,80 mm | [C_forte_suporte.stl](output/C_forte_suporte.stl) | [C_forte_conjunto.stl](output/C_forte_conjunto.stl) |

Comece pelo **B_media_suporte.stl**, sem a peça por cima, para testar a fabricação dos cordões e a possibilidade de desfiá-los. Depois compare A e C nas mesmas condições. Use o conjunto com a peça para avaliar acesso, retirada e acabamento inferior numa segunda rodada.

Os STLs usam milímetros. O suporte mede **25,6 × 12,8 × 17,6 mm**, com 4 fileiras, 4 níveis e 40 ligações. A base de 0,4 mm une as fileiras para impressão; ela não foi projetada para desfiar. A peça de teste é um pequeno pórtico com duas paredes apoiadas na mesa e teto de 1,2 mm. O conjunto mede **28,8 × 12,8 × 19 mm**. Há folga vertical nominal de **0,2 mm** entre os picos do suporte e o teto.

## Fatiamento

1. Importe o STL em escala de 100%, na orientação fornecida, com a base na mesa. Não use orientação automática.
2. Use seu perfil já calibrado para PETG e sua impressora, com bico de 0,4 mm, camada inicial de 0,2 mm e demais camadas de 0,2 mm. Mantenha temperatura, ventilação e velocidade iguais entre A, B e C.
3. **Desative suportes automáticos.** A geometria experimental já está modelada como um objeto; suportes extras preencheriam os vazios que permitem desfazê-la.
4. Como ponto inicial, use largura de linha de 0,4 mm, 2 paredes, 100% de preenchimento e 4 camadas de topo/fundo. Habilite a preservação de paredes finas/preenchimento de lacunas conforme seu fatiador. Esses nomes e seus efeitos variam entre programas.
5. Na prévia, confira as ligações nas alturas de impressão **4,6/4,8 mm**, **9,0/9,2 mm** e **13,4/13,6 mm**. Elas precisam conter extrusão. A largura nominal das três versões pode ser parcialmente igualada pela largura mínima de linha do fatiador.
6. Para o teste com teto, importe o arquivo `conjunto` como um só modelo. Ele contém dois sólidos intencionalmente separados: suporte e peça. Não separe e reorganize suas partes, nem abaixe o teto. Confira a camada de folga e as pontes sob o teto.

Não redimensione simplesmente o STL para calibrar a remoção: isso mudaria simultaneamente cordão, pescoço, folgas e alturas. Modifique os parâmetros e gere novamente.

## Teste com alicate

Deixe o corpo de prova esfriar e retire-o da mesa. Segure a base ou a peça de teste; agarre uma curva externa de um cordão e puxe para fora da estrutura. Não há uma ponta obrigatória. Comece nas regiões externas acessíveis e experimente outras direções. Se romper, pegue outro trecho.

Observe se os pescoços cedem sucessivamente ou se o próprio cordão rompe imediatamente. Compare:

| Medição | A | B | C |
|---|---|---|---|
| Terminou a impressão sem colapso? | | | |
| Tempo de remoção | | | |
| Número de puxadas | | | |
| Maior trecho retirado, em mm | | | |
| Rompeu mais no cordão ou na ligação? | | | |
| Com teto: resíduos/danos na peça | | | |

Se os cordões quebrarem antes das ligações, priorize A ou aumente a seção dos cordões numa próxima versão. Se a estrutura falhar durante a impressão, experimente C e confira primeiro a presença das ligações na prévia. Se ela sair em blocos rígidos, o mecanismo de desfiamento ainda não foi alcançado.

## Gerador e reprodução

Python 3.12 foi usado nesta implementação. As dependências estão fixadas em `requirements.txt`; a pasta `.venv` contém o ambiente local instalado.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe generate.py
.\.venv\Scripts\python.exe validate_slicing.py
```

Para experimentar outra geometria, copie `output/config.json`, edite os campos e execute:

```powershell
.\.venv\Scripts\python.exe generate.py --config minha_config.json --out experimento_02
.\.venv\Scripts\python.exe validate_slicing.py --out experimento_02
```

O visualizador padrão usa os arquivos de `output`; gerar outra pasta não muda a visualização padrão. As três larguras de ligação são fixas no gerador desta versão. A configuração permite mudar seção dos cordões, amplitude lateral, elevação, passo, número de fileiras/níveis/períodos e folgas. Alterar o bico para algo incompatível com as ligações gera erro em vez de produzir uma peça silenciosamente inválida.

## Validação e limites

`output/validation.json` registra a auditoria das malhas, incluindo releitura dos STLs: superfície fechada, orientação consistente, volume positivo, ausência de faces degeneradas, um componente por suporte e dois no conjunto. Não há interseção volumétrica entre suporte e peça. A simplificação superficial tem tolerância de 0,02 mm, seguida de limpeza numérica.

`output/audit/slicing_validation.json` registra a checagem das 88 camadas do suporte e a presença de extrusão em 80 amostras de ligação por variante usando **CuraEngine 4.13.1**. A checagem geométrica exige que cada ilha tenha alguma sobreposição com a camada anterior; isso não demonstra apoio integral de cada trajetória, resistência lateral ou qualidade de pontes.

Os arquivos `output/audit/*_NAO_IMPRIMIR.gcode` são evidência técnica de fatiamento com máquina genérica, sem inicialização/finalização específica. **Para imprimir, fatie os STLs com o perfil da sua própria impressora.**

Não houve ensaio físico, medição de força, simulação mecânica ou validação de tempo de remoção. A boa continuidade geométrica de um cordão não garante resistência igual em todas as direções, pois a peça continua sendo impressa em camadas. O teto é uma peça plana para ensaio; esta versão ainda não tem uma interface densa desfiável dedicada nem gera suporte automaticamente a partir de uma peça arbitrária. A base permanece inteira. O experimento avalia primeiro o mecanismo de remoção do corpo do suporte.
