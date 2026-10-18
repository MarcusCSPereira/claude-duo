#!/bin/bash -p
# One-command Claude Duo setup from a reviewed checkout of this repository:
# checks prerequisites, installs the pinned toolset, writes the Duo config,
# installs the "Atualizar Claude Duo" app and the update check, then builds
# the Duo (asking before closing Claude). Safe to run again.
#   --no-auto-check   do not install the launch agent that asks after updates
#   --no-build        prepare everything but do not build the Duo now
DUO_TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
source "$DUO_TOOLS/duo-common.sh" || exit 1
set -u
REPO="$(cd "$DUO_TOOLS/.." && pwd -P)"
LAUNCHCTL=/bin/launchctl
OSACOMPILE=/usr/bin/osacompile
XCODE_SELECT=/usr/bin/xcode-select
AGENT_LABEL=io.github.guibrbs.claude-duo.update-check
AGENT="$HOME/Library/LaunchAgents/$AGENT_LABEL.plist"
UPDATER_APP="$HOME/Applications/Atualizar Claude Duo.app"

auto_check=yes; build=yes
for arg in "$@"; do
    case "$arg" in
        --no-auto-check) auto_check=no ;;
        --no-build) build=no ;;
        *) duo_error "unknown option: $arg"; exit 2 ;;
    esac
done
step() { printf '\n==> %s\n' "$*"; }
fail() { duo_error "$*"; exit 1; }

step "Conferindo pré-requisitos"
[ "$(/usr/bin/uname -s)" = Darwin ] || fail 'Claude Duo só funciona no macOS'
[ "$(/usr/bin/id -u)" != 0 ] || fail 'rode como o seu usuário, não como root'
"$XCODE_SELECT" -p >/dev/null 2>&1 || fail 'faltam as Xcode Command Line Tools: rode  xcode-select --install  e tente de novo'
[ -d "$DUO_SOURCE_APP" ] || fail "instale o Claude oficial em $DUO_SOURCE_APP primeiro"
/usr/bin/python3 -I -c 'pass' 2>/dev/null || fail 'python3 indisponível (vem com as Command Line Tools)'
if [ ! -e "$HOME/Applications" ]; then
    /bin/mkdir -m 700 "$HOME/Applications" || exit 1
fi
[ -d "$HOME/Applications" ] && [ ! -L "$HOME/Applications" ] && [ -O "$HOME/Applications" ] || fail '~/Applications precisa ser uma pasta sua'
[ "$(/usr/bin/stat -f '%Lp' "$HOME/Applications")" = 700 ] || fail '~/Applications precisa ter permissão 700: rode  chmod 700 ~/Applications  e tente de novo'

step "Configuração do Duo"
/bin/mkdir -p "$DUO_HOME" "$HOME/.config/claude-instances" || exit 1
/bin/chmod 700 "$DUO_HOME" "$HOME/.config/claude-instances" || exit 1
config=""
if [ -f "$DUO_CONFIG_POINTER" ]; then
    config="$(duo_config)" || exit 1
elif [ -f "$HOME/.config/claude-instances/claude-duo.conf" ]; then
    config="$HOME/.config/claude-instances/claude-duo.conf"
elif [ -f "$HOME/.config/claude-instances/duo-validation.conf" ] && /usr/bin/grep -qx '@mode original-copy' "$HOME/.config/claude-instances/duo-validation.conf"; then
    config="$HOME/.config/claude-instances/duo-validation.conf"  # Earlier manual setup.
else
    config="$HOME/.config/claude-instances/claude-duo.conf"
    owner="$(printf '%s' "$USER" | /usr/bin/tr -c 'A-Za-z0-9-' '-' | /usr/bin/tr 'A-Z' 'a-z')"
    ( set -o noclobber
      printf '@mode original-copy\n@apps user\nDuo | io.github.%s.claude-duo | ~/Library/Application Support/Claude-Duo | 212 | CLAUDE_CONFIG_DIR=~/.claude-duo\n' "${owner:-user}" > "$config" ) || fail "não consegui criar $config"
    /bin/chmod 600 "$config" || exit 1
fi
printf '%s\n' "$config" > "$DUO_CONFIG_POINTER" && /bin/chmod 600 "$DUO_CONFIG_POINTER" || exit 1
echo "Configuração: $config"

step "Instalando as ferramentas versionadas"
work="$(/usr/bin/mktemp -d "$DUO_HOME/.install.XXXXXXXX")" || exit 1
trap '/bin/rm -rf "$work"' EXIT
digest="$(/usr/bin/python3 -I "$REPO/scripts/prepare-toolset.py" "$work/package")" || fail 'não consegui preparar o pacote de ferramentas (há mudanças locais em bin/?)'
/bin/mkdir -m 700 "$work/tmp" || exit 1
/usr/bin/env -i HOME="$HOME" USER="$USER" LOGNAME="$USER" PATH="$PATH" LANG=en_US.UTF-8 TMPDIR="$work/tmp" \
    /bin/bash -p "$REPO/bin/claude-toolset.sh" install "$work/package" "$digest" || fail 'a instalação das ferramentas falhou'
"$DUO_DISPATCHER" verify >/dev/null || fail 'as ferramentas instaladas não passaram na verificação'

step "Instalando o atualizador"
for file in duo-common.sh atualizar-duo.sh verificar-atualizacao.sh; do
    /usr/bin/install -m 700 "$DUO_TOOLS/$file" "$DUO_HOME/$file" || exit 1
done
/usr/bin/install -m 700 "$REPO/scripts/share-code-profile.py" "$DUO_HOME/share-code-profile.py" || exit 1
script="do shell script \"/bin/bash -p \" & quoted form of \"$(duo_as_text "$DUO_HOME/atualizar-duo.sh")\" & \" >/dev/null 2>&1 &\""
/bin/rm -rf "$UPDATER_APP"
"$OSACOMPILE" -o "$UPDATER_APP" -e "$script" || fail 'não consegui criar o app Atualizar Claude Duo'
echo "App: $UPDATER_APP"

if [ "$auto_check" = yes ]; then
    step "Aviso automático quando o Claude atualizar"
    /bin/mkdir -p "$HOME/Library/LaunchAgents" || exit 1
    new="$work/agent.plist"
    "$PLISTBUDDY" -c "Add :Label string $AGENT_LABEL" \
        -c 'Add :ProgramArguments array' -c 'Add :ProgramArguments:0 string /bin/bash' \
        -c 'Add :ProgramArguments:1 string -p' -c "Add :ProgramArguments:2 string $DUO_HOME/verificar-atualizacao.sh" \
        -c 'Add :StartInterval integer 3600' -c 'Add :RunAtLoad bool true' \
        -c 'Add :ProcessType string Background' "$new" >/dev/null || exit 1
    /usr/bin/plutil -lint "$new" >/dev/null || exit 1
    "$LAUNCHCTL" bootout "gui/$(/usr/bin/id -u)/$AGENT_LABEL" >/dev/null 2>&1 || true
    /bin/mv "$new" "$AGENT" && /bin/chmod 644 "$AGENT" || exit 1
    "$LAUNCHCTL" bootstrap "gui/$(/usr/bin/id -u)" "$AGENT" || fail 'não consegui ativar o aviso automático'
    echo "Agente: $AGENT (confere a cada hora)"
fi

if [ "$build" = yes ]; then
    step "Construindo o Claude Duo"
    if [ -d "$DUO_APP" ] && [ "$(duo_version "$DUO_APP")" = "$(duo_version "$DUO_SOURCE_APP")" ] && duo_refresh --verify >/dev/null 2>&1; then
        echo "O Claude Duo já está atualizado e verificado."
    else
        /bin/bash -p "$DUO_HOME/atualizar-duo.sh" || fail "a construção falhou; veja o log em $DUO_LOG_DIR"
    fi
fi
printf '\nPronto. Abra ~/Applications/Claude Duo e entre com a sua segunda conta.\nPara atualizar depois: abra "Atualizar Claude Duo" (ou aceite o aviso quando o Claude atualizar).\n'
