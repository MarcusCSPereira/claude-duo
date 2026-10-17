# Ensaio gráfico do Claude original com o Claude Duo

Este roteiro prepara a etapa de viabilidade do [roadmap](ROADMAP_PT_BR.md).
O código de manutenção foi testado com dados inventados. **Login, contas
simultâneas e Code na cópia continuam sem validação gráfica.** Uma assinatura
local válida ou um ícone diferente não comprova independência das contas.

A seleção de destino privado passou por oito novos testes, dentro da suíte de
145 casos, e por oito checagens de construção/assinatura/conteúdo com a origem
real, em pasta descartável. Nos últimos, processos foram simulados e não houve
abertura do Claude. [Evidências e hashes](evidence/gui-preparation.json).

## Ambiente escolhido

Usar **um usuário local de teste, do tipo Padrão**, no macOS. Dentro dessa mesma
sessão ficam o original e o Duo: isso permite ensaiar as duas contas juntas,
enquanto os diretórios padrão do original pertencem ao usuário de teste.
Não trocar HOME, usar perfis pessoais existentes ou copiar credenciais para
simular esse isolamento.

A Apple descreve contas separadas e os privilégios de um
[usuário Padrão](https://support.apple.com/pt-br/guide/mac-help/mtusr001/mac).
Escolhemos uma conta persistente porque precisamos testar reinício e retomada.
A conta Convidado apaga arquivos ao sair e, com FileVault, limita o acesso ao
Safari, conforme a [documentação da Apple](https://support.apple.com/pt-br/guide/mac-help/mh15600/mac).

Essa conta reduz a exposição dos dados do usuário habitual; não é uma máquina
virtual. O macOS, o aplicativo oficial, rede e serviços do sistema continuam
compartilhados. Dentro do laboratório os dois apps têm o mesmo UID e podem ler
arquivos acessíveis a esse usuário. Não conceder acesso a pastas pessoais do
usuário habitual nem importar seu Chaveiro ou sincronizar seu iCloud no ensaio.

## Preparação e participação do usuário

1. Criar em Ajustes do Sistema → Usuários e Grupos uma conta Padrão, sugerida
   como **Claude Duo Teste**, nome curto `claudeduo-lab`. O usuário define a
   senha diretamente no macOS; nenhuma senha deve ser enviada ao agente.
   Não criar uma conta administrativa ou habilitar login automático para o teste.
2. Entrar nessa sessão gráfica. A preparação que grava arquivos deve ocorrer
   nessa conta real, sem `sudo`, sem trocar HOME e sem macros de teste nativas.
   A criação e a entrada nessa conta ainda dependem dessa ação local do usuário.
3. Transferir somente o pacote de ferramentas revisado e o material de teste.
   Conferir o hash do manifesto com a referência independente do candidato.
   Não tornar a pasta pessoal do usuário habitual compartilhada para isso.
4. Confirmar o usuário efetivo, seu home e que não existem configuração,
   ferramentas, perfis ou app Duo anteriores nessa conta. Se houver dados,
   interromper a preparação e revisar; não sobrescrever ou fazer limpeza automática.
5. Criar uma pasta **nova** `~/Applications`, privada, com modo 0700. O modo
   `@apps user` exige essa pasta já existente; recusa arquivos, links, permissões
   especiais, escrita de outros usuários e ACLs de concessão. As ferramentas
   não alteram permissões de outros apps para permitir a instalação.
6. Instalar o conjunto completo pelo [instalador versionado](TOOLSET_INSTALLATION.md).
   Criar uma configuração nova e privada, conforme o exemplo abaixo. Não usar
   os scripts legados do usuário habitual ou cadastrar um LaunchAgent.
7. Conferir a origem oficial, construir o Duo com os apps dessa sessão fechados
   e verificar conteúdo, configuração e assinatura antes de abrir qualquer app.
   Não substituir erros de observação de processos por resultados simulados.

Essa preparação é feita uma vez pelo responsável técnico. O ensaio e o uso
diário são na interface do Claude; não exigem usar o Claude Code CLI.
A conta extra do macOS serve somente ao laboratório. O objetivo de uso diário
continua sendo original e Duo juntos na sua sessão habitual, após a validação
e uma transição revisada dos aplicativos e dados existentes.

## Topologia do laboratório

| Item | Local na conta de teste |
|---|---|
| Original, executável oficial | `/Applications/Claude.app`, somente origem/leitura pelas nossas ferramentas |
| Duo | `~/Applications/Claude Duo.app` |
| Dados Desktop do original | `~/Library/Application Support/Claude` |
| Configuração Code do original | `~/.claude` e outros locais que a versão efetivamente usar |
| Dados Desktop do Duo | `~/Library/Application Support/Claude-Duo` |
| Configuração Code solicitada ao Duo | `~/.claude-duo` via `CLAUDE_CONFIG_DIR` |
| Projetos inventados e distintos | `~/Claude Duo Lab/original` e `~/Claude Duo Lab/duo` |

Exemplo exclusivo para uma instalação nova no laboratório:

```text
@mode original-copy
@apps user
Duo | com.guibrbs.claude-duo.lab | ~/Library/Application Support/Claude-Duo | 212 | CLAUDE_CONFIG_DIR=~/.claude-duo
```

O identificador `.lab` identifica o candidato de teste; não migra o identificador
de uma cópia instalada. Mudar identidade, localização ou versão depois do teste
exige nova validação do que a mudança afetar. O original permanece fora da lista
de destinos. A seleção de pasta não altera a origem `/Applications/Claude.app`.

O bloqueio de manutenção é comum a rebuild, caches e checkpoints **dentro da
pasta de aplicativos selecionada**. Não coordenamos duas configurações que
escolham pastas distintas e reutilizem os mesmos perfis. Usar somente a
configuração do laboratório, sem cópias antigas sobre esses dados. Trocar
`@apps` não migra nem desativa apps antigos e altera a vinculação de integridade.

## Conferência antes da abertura

Registrar versão e build do macOS, arquitetura, versão do Claude, commit/hash do
pacote, identificador e caminho exato do Duo. Conferir assinatura Anthropic e
Gatekeeper da origem, assinatura/conteúdo da cópia e destinos dos iniciadores.
Registrar hashes dos arquivos críticos da origem antes/depois da construção.
Esses testes não devem ler conteúdo de perfis, variáveis de processos ou Chaveiro.

Abrir o original pelo caminho completo e o Duo pelo seu caminho privado no
Finder. Conferir atalhos/Dock antes de adicioná-los. Não abrir um app retido
em uma transação nem procurar uma cópia só pelo nome. Retornos pelo navegador
devem ser observados; o iniciador atual recusa argumentos e URLs.

O app oficial é compartilhado no disco: uma atualização por outro processo pode
alterá-lo. Se origem, versão ou assinatura mudarem durante o ensaio, pausar e
identificar um novo candidato. Não conceder privilégios de administrador,
desativar Gatekeeper ou contornar políticas de organização para obter um passe.

## Matriz de aceitação

Fluxo declarado pelo usuário: **login por link de e-mail, sem SSO**. G07 é
obrigatório para esse link; SSO fica fora do escopo inicial e não será tratado
como testado.

Todos os itens começam como **NÃO EXECUTADO**. Usar somente os rótulos A e B
no relatório público; confirmar e-mail/organização privadamente na interface.
Declarar o tipo de login e os recursos necessários; SSO não ensaiado continua
pendente. Nova autenticação é feita pelo usuário dentro do Claude/navegador.

| ID | Ensaio | Evidência necessária |
|---|---|---|
| G01 | Entrar em A no original e B no Duo | Identidade esperada na interface de cada app |
| G02 | Repetir na ordem inversa com perfis novos | O segundo login não troca a primeira conta |
| G03 | Abrir Code local nos dois simultaneamente | Conta efetiva do Code confirmada; tarefas nos projetos corretos |
| G04 | Fechar, reabrir, sair da sessão macOS e reiniciar | Retomada e identidades preservadas, sem abrir versões retidas |
| G05 | Sair e entrar novamente em B com A ativo | Sessão/tarefa de A continua correta |
| G06 | Renovação de login e revogação da sessão de teste em B | Impacto observado; não revogar sessões habituais ou todas as sessões da conta |
| G07 | Retorno do link de e-mail/navegador | Retorno para a conta e janela corretas; sem burlar o iniciador |
| G08 | Finder, Dock e atalhos | Caminhos, identidade do app e perfil corretos |
| G09 | Construção e checkpoint com original, Duo ou ambos abertos | Recusa segura, sem encerrar tarefas para forçar manutenção |
| G10 | Preferências e extensões inventadas | Reaproveitamento sem transferir autenticação, conforme proposta abaixo |
| G11 | Permissões e recursos declarados | Funcionamento por identidade; falhas registradas |

Criar marcadores inofensivos distintos nos projetos e nas instruções de teste.
Uma resposta contendo um marcador demonstra configuração carregada, não prova
qual conta pagou/executou o Code. Não usar essa resposta como substituto da
identificação efetiva da conta; se não for possível observá-la, marcar
**INCONCLUSIVO**, mantendo o requisito de viabilidade aberto.

A [proposta de reaproveitamento](PROFILE_REUSE_PT_BR.md) adiciona o requisito do
usuário sem compartilhar o perfil inteiro. Primeiro validar autenticação básica;
depois repetir os casos essenciais com configurações inventadas importadas. O
importador ainda não está implementado, portanto G10 continua pendente.
Se o serviço não permitir limitar uma revogação à sessão do laboratório, usar
uma conta descartável para esse caso ou mantê-lo pendente. Não usar a limpeza
de caches como teste de recusa sem saída: o comando atual pode pedir ao app
selecionado que feche antes da limpeza, comportamento distinto de construção
e checkpoint.

## Registro e encerramento

Para cada caso registrar data, candidato, tipo de conta A/B, resultado
(`APROVADO`, `FALHOU`, `INCONCLUSIVO`, `NÃO EXECUTADO` ou `NÃO APLICÁVEL`) e
observação sanitizada. A exclusão de um recurso do escopo exige decisão explícita;
não transformar um teste pendente em aprovado. Não publicar perfis, logs de
autenticação, conversas, URLs de callback ou capturas contendo dados privados.

Troca inesperada de conta, perda de dados ou origem incerta interrompe a
liberação. No fim, fechar apps e preservar resultados sanitizados. Desconectar
as sessões de teste e remover a conta/dados do laboratório são ações posteriores,
com revisão; não apagar automaticamente perfis ou presumir que excluir arquivos
revoga sessões no serviço. Nenhum resultado autoriza substituir os perfis reais
ou iniciar atualização automática antes dos demais critérios do roadmap.
