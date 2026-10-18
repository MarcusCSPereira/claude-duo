# Claude Duo

Duas contas do Claude Desktop no mesmo Mac: o **Claude** oficial e uma cópia
gerenciada, o **Claude Duo**, cada um com a própria conta, o próprio Code e a
própria chave no Chaveiro.

*Two Claude Desktop accounts on one Mac: the official app plus a managed copy
with its own account, Code profile and Keychain item. macOS only.*

> ⚠️ **Experimental e não oficial.** Projeto independente, sem vínculo com a
> Anthropic. O Duo é uma cópia do app oficial **assinada localmente**, sem a
> assinatura da Anthropic. Alguns cenários ainda estão em validação (veja
> [Limitações](#limitações)). Use por sua conta e respeite os termos de uso de
> cada conta e as regras da sua organização.

## Instalar

Pré-requisitos: macOS 12 ou mais novo, o Claude oficial em `/Applications`
e as Xcode Command Line Tools (`xcode-select --install`).

```bash
git clone https://github.com/guibrbs/claude-duo.git ~/claude-duo
```

```bash
~/claude-duo/duo/instalar-duo.sh
```

O instalador:

1. confere os pré-requisitos;
2. instala o conjunto versionado de ferramentas (com verificação de conteúdo);
3. cria a configuração em `~/.config/claude-instances/claude-duo.conf`;
4. instala o app **Atualizar Claude Duo** em `~/Applications`;
5. instala um aviso que confere a cada hora se o Claude oficial foi atualizado
   (`--no-auto-check` para não instalar);
6. constrói o Duo. Ele **pergunta antes de fechar o Claude**, porque a
   construção exige os dois apps fechados, e reabre o Claude no fim.

Depois, abra **~/Applications/Claude Duo** e entre com a sua segunda conta.

## Usar no dia a dia

- **Abrir:** `Claude Duo` no Dock, no Launchpad ou no Spotlight. O original
  continua sendo o `Claude` de sempre.
- **Atualizar:** quando o Claude oficial atualizar, aparece o aviso *"Atualizar
  o Duo agora?"*. Você também pode abrir **Atualizar Claude Duo** a qualquer
  momento. Os dois fecham o Claude e o Duo, reconstroem, verificam e reabrem o
  que estava aberto.
- **Conectores (Google Drive, Slack…):** conecte pelo navegador, numa janela
  anônima logada com a conta do Duo (claude.ai → Configurações → Conectores),
  e aperte ⌘R no Duo. De dentro do Duo, o login dos conectores não volta para
  ele, porque os links `claude://` pertencem ao app oficial.
- **Mesmas instruções, memórias e skills no Code (opcional):** com o Duo fechado,
  rode o script abaixo. Ele liga ao original o `CLAUDE.md`, as skills, os
  output styles, as ferramentas, os plugins e as memórias por projeto, e copia
  o `settings.json` uma vez. Login, sessões e histórico continuam separados.
  Instale plugins pelo original. Detalhes em
  [docs/PROFILE_REUSE_PT_BR.md](docs/PROFILE_REUSE_PT_BR.md).

```bash
/usr/bin/python3 -I ~/claude-duo/scripts/share-code-profile.py --apply --backup-existing
```

## Como funciona

- O Duo é uma cópia do `Claude.app` oficial em `~/Applications`, com outro
  identificador, perfil próprio (`~/Library/Application Support/Claude-Duo`) e
  Code próprio (`CLAUDE_CONFIG_DIR=~/.claude-duo`).
- **Chave própria no Chaveiro:** o Electron nomeia a chave como
  `<productName> Safe Storage`. O construtor troca só o `productName` dentro do
  `app.asar` para `Duo Claude`, sem mudar o tamanho do arquivo, e sela de novo
  os hashes do ASAR. Assim o Duo não pede a chave `Claude Safe Storage` do
  original. O nome fica `Duo Claude`, e não `Claude Duo`, porque o User-Agent
  remove espaços (`DuoClaude/…`) e o claude.ai só ativa a interface Desktop
  com um token `claude/`.
- **Verificações:** a origem precisa ter a assinatura da Anthropic e passar no
  Gatekeeper. O registro de integridade **regenera o resultado esperado a partir
  da origem** e exige igualdade byte a byte; qualquer outra diferença é
  recusada. A publicação é atômica e mantém a versão anterior para inspeção.
- Detalhes: [HARDENING.md](HARDENING.md),
  [docs/APP_INTEGRITY.md](docs/APP_INTEGRITY.md),
  [docs/KEYCHAIN_NAMESPACE_EXPERIMENTS_PT_BR.md](docs/KEYCHAIN_NAMESPACE_EXPERIMENTS_PT_BR.md)
  e [docs/TOOLSET_INSTALLATION.md](docs/TOOLSET_INSTALLATION.md).

## Limitações

- Assinatura local: o Duo perde a identidade da Anthropic. Permissões do macOS
  (pastas, microfone, automação) são pedidas de novo para ele.
- Precisa ser reconstruído a cada atualização do Claude oficial; o atualizador
  interno do Duo não deve ser usado.
- Ainda em validação: a conta efetiva do Code em cada app, sair de uma conta
  sem afetar a outra e os dois apps abertos por longos períodos
  ([roteiro](docs/GUI_VALIDATION_PT_BR.md), [roadmap](docs/ROADMAP_PT_BR.md)).
- Não protege contra um processo malicioso do mesmo usuário; os registros
  locais detectam alterações, mas não são uma barreira de segurança.

## Desinstalar

1. Feche o Claude Duo.
2. Rode:

```bash
launchctl bootout gui/$(id -u)/io.github.guibrbs.claude-duo.update-check; rm -f ~/Library/LaunchAgents/io.github.guibrbs.claude-duo.update-check.plist
```

3. Mova para a Lixeira: `~/Applications/Claude Duo.app`,
   `~/Applications/Atualizar Claude Duo.app` e `~/.local/share/claude-duo`.
4. Os dados da conta do Duo ficam em `~/Library/Application Support/Claude-Duo`
   e `~/.claude-duo`. Se você usou o compartilhamento do Code, os itens
   compartilhados dentro de `~/.claude-duo` são links: apagá-los não apaga os
   originais em `~/.claude`.

## Desenvolvimento

```bash
python3 scripts/run-security-tests.py all
```

Os testes rodam apenas em pastas temporárias, com apps e contas sintéticos.
O CI roda a mesma suíte em arm64 e x86_64, mais o analisador estático do Clang.

## Créditos e licença

Baseado no [multi-claude-desktop](https://github.com/cgclark/multi-claude-desktop),
de Christopher Clark, cuja documentação técnica original está em
[docs/MULTI_INSTANCE_REFERENCE.md](docs/MULTI_INSTANCE_REFERENCE.md).
Licença MIT ([LICENSE](LICENSE)). "Claude" é marca da Anthropic; este projeto
não é afiliado nem endossado por ela.
