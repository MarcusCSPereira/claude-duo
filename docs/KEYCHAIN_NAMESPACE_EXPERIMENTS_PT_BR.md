# Experimentos para separar o nome do armazenamento seguro

Em 17/10/2026, dois protótipos descartáveis foram preparados e abertos sem login,
com autorização do usuário para cada abertura. **O Duo instalado não foi
substituído.** O bloqueio de liberação do [primeiro ensaio](KEYCHAIN_FIRST_LAUNCH_PT_BR.md)
continua: os experimentos não aprovam duas contas reais nem o Code gráfico.

## Resultado observado

| Experimento | Mudanças | Resultado |
|---|---|---|
| Nome interno e auxiliares | `CFBundleName` próprio, quatro auxiliares renomeados e reassinados | Abriu, mas ainda pediu `Claude Safe Storage`; usuário negou. Hipótese insuficiente. Também houve pedido de Documentos. |
| Nome de produto do pacote | `package.json.productName` próprio no ASAR; auxiliares originais preservados | Abriu sem pedidos de permissão, conforme interface e confirmação do usuário. Consulta apenas de atributos encontrou uma entrada com o nome próprio esperado. A tela exibida foi o login deslogado do Desktop (claude.ai/login na janela do app), o mesmo estado do Duo antigo; ver reabertura abaixo. |

Os dois protótipos foram fechados com ⌘Q. O observador nativo confirmou os apps
Desktop parados após cada ensaio. Nenhum login foi feito, nenhum valor secreto
foi coletado, e nenhuma autorização de acesso ao Chaveiro foi concedida pela
automação. Não foram apagadas entradas do Chaveiro ou pastas de perfil.
O segundo app pode ter criado sua própria chave como parte da inicialização;
essa entrada foi preservada. A ausência de aviso não comprova ausência de
outras consultas silenciosas nem separação de toda a autenticação.

## Correção da hipótese anterior

Mudar só `CFBundleName` não resolveu. O pacote distribuído declara
`productName: "Claude"`. O
[bootstrap do Electron 44.7.2](https://github.com/electron/electron/blob/v44.7.2/lib/browser/init.ts)
atribui esse valor a `app.name`. Assim, os metadados do bundle não são a única
fonte de nome relevante. A combinação do teste negativo, da definição no
pacote e do teste positivo aponta para esse mecanismo; não é uma reconstrução
completa de todos os caminhos do binário da Anthropic.

Na segunda amostra, os nomes dos auxiliares e `CFBundleName` ficaram iguais aos
da origem. A alteração semântica no ASAR foi limitada a `productName` em
`package.json`. Foram atualizados tamanho, offsets afetados e os hashes desse
membro, além do hash do cabeçalho em `ElectronAsarIntegrity`. Nenhum payload
JavaScript foi alterado. O executável principal e o bundle externo foram
reassinados localmente, como já ocorre na construção atual; os quatro
auxiliares mantiveram seus arquivos e assinaturas originais.

A consulta de confirmação pediu **somente atributos** da entrada com o nome
exato da segunda amostra. Retorno de dados secretos e de referências foi
explicitamente desativado; interação de autenticação foi configurada para
falhar, sem fallback interativo. A consulta confirmou existência, não leu o
valor, não editou ACLs e não comparou chaves. Isso não prova que todos os
segredos usados pelo aplicativo estejam separados.

## Verificações de construção

- Origem oficial verificada por identidade Anthropic, assinatura aninhada e
  Gatekeeper. Versões do experimento fixadas em Claude 2.42304.0 / Electron 44.7.2;
  versões diferentes são recusadas para nova revisão.
- Comparação de 4.964 entradas da origem com a primeira amostra, incluindo os
  cinco executáveis antes/depois da assinatura. Somente os campos de assinatura
  previstos foram normalizados; formatos e disposições desconhecidos falham.
- Na segunda amostra, comparação de todos os 508 membros do ASAR e dos demais
  arquivos da origem. Apenas a semântica `package.json.productName` mudou no
  pacote; payloads externos a esse membro ficaram byte a byte iguais. Auxiliares
  e seus recursos/assinaturas ficaram iguais aos da origem.
- Assinatura aninhada e comparação de conteúdo da segunda amostra passaram
  também depois do ensaio gráfico. Conteúdo da origem ficou igual durante cada
  preparação; nenhuma ferramenta instalou ou substituiu um app em uso.
- 25 novos testes offline aprovados: 12 sobre comparação de Mach-O/auxiliares e
  13 sobre limites e alterações do ASAR. A distribuição de CI cobre agora 170
  testes sem lacunas ou duplicatas: 86 perfis/experimentos, 59 armazenamento e
  25 instalador. Os 145 testes anteriores permanecem evidência da implementação
  `b938c7d`; não se infere um resultado remoto novo a partir desse histórico.

A primeira tentativa de preparar a segunda amostra recusou arquivos deduplicados
do ASAR antes de criar o app. A inspeção encontrou 25 pares que compartilham
intervalos exatamente iguais. O parser passou a aceitar esses aliases, com
testes adicionais; continua recusando sobreposições parciais e qualquer alias
do intervalo de `package.json`. A tentativa recusada ficou registrada, sem
fallback para uma cópia menos verificada.

O pedido de Documentos do primeiro experimento coincidiu com app e dados de
ensaio dentro dessa pasta. Não foi demonstrado o gatilho exato. A segunda
amostra e seus dados novos ficaram fora de Documentos e não pediram a permissão.

## Reabertura e comparação por logs

Em 17/10/2026, às 22:07, a mesma amostra foi reaberta pelo agente, a pedido do
usuário, com a mesma pasta de dados descartável e sem login. Ela mostrou a tela
deslogada padrão do Desktop: janela própria do app, logo Claude, “Continuar com
o Google” e o aviso de cookies, que ficou sem resposta. Nenhum pedido do
Chaveiro apareceu, e o app fechou limpo com ⌘Q.

Os logs locais (`main.log`) dos três apps de teste mostram o mesmo fluxo
deslogado (`sign_in_cookie_present: false`), com as mesmas rotinas do Desktop
(Code, Cowork, `startup-sign-in`). A única diferença é o Chaveiro:

| App | Travamento até o estado de login | `safeStorage` |
|---|---|---|
| Duo antigo (`b938c7d`) | 88,7 s (`event-loop-stall`) | `isEncryptionAvailable=false` após a negação |
| 1º protótipo (auxiliares) | 41,0 s | `isEncryptionAvailable=false` após a negação |
| Amostra `productName` (2 aberturas) | ~1 s | sem aviso |

O registro do Duo antigo (G11) já descrevia `claude.ai/login` depois da negação.
Portanto, a “introdução anterior do Desktop” não era um estado comparável, e a
troca de `productName` não mudou a tela de entrada. O User-Agent não foi medido.
O login real continua não testado.

## O que falta antes de integrar

1. ~~Preservar a experiência Desktop~~ **descartado em 17/10/2026, 22:07.**
   A suspeita de uma página web diferente não se confirmou (ver
   [reabertura](#reabertura-e-comparação-por-logs)).
2. **Integrar verificações ao construtor de produção.** Ele atualmente recusa
   alterações no ASAR fora do plano existente. Não afrouxar essa política para
   instalar o protótipo. Uma integração precisa validar a mudança por membro,
   os hashes selados, a origem estável e o conjunto completo de ferramentas,
   com testes de adulteração, interrupção e atualização. Os scripts de pesquisa
   usam Python; não adicionam uma dependência ao uso diário ou ao instalador atual.
3. **Repetir abertura, fechamento e reconstrução**, incluindo outra arquitetura
   quando houver a origem correspondente. Os ensaios reais desta rodada são arm64.
   Assinaturas ad-hoc podem provocar novas solicitações após reconstruções.
4. **Retomar G01–G11 com o usuário**, começando por login por e-mail, retorno ao
   app correto e identidade efetiva do Code. Contas simultâneas, saída de uma
   conta sem afetar a outra e continuidade ainda não foram testadas.

Os [resultados sanitizados](evidence/keychain-namespace-experiments.json)
separam os fatos observados das hipóteses. Não há proteção contra um processo
malicioso do mesmo usuário, nem garantia absoluta de segurança.

## Ferramentas experimentais

Os scripts abaixo somente preparam novas cópias; não abrem aplicativos, não
instalam em Applications e não importam perfis ou acessam o Chaveiro:

- [Preparação por nome de produto](../scripts/prepare-product-name-probe.py), com
  [alteração e verificação limitada do ASAR](../scripts/asar_product_name.py).
- [Experimento anterior](../scripts/prepare-namespace-probe.py), cuja reprodução
  exige `--reproduce-helper-only-failure` porque a separação falhou na interface.

Não são comandos do conjunto versionado de produção. Uma nova abertura de
software modificado ou uma nova permissão sensível é revisada na hora da ação.
