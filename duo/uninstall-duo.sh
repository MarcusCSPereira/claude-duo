#!/bin/bash -p
# Removes Claude Duo: both apps, the update check, the Duo tools, config and
# logs, plus the shared toolset and retained build transactions when no other
# config in ~/.config/claude-instances uses them. Everything is moved to one
# folder in the Trash, never deleted, and the list is shown before asking.
# The Duo account data (Desktop and Code profiles) and the Keychain item stay.
#   --include-account-data   also move ~/Library/Application Support/Claude-Duo
#                            and ~/.claude-duo to the Trash
#   --yes                    do not ask before moving
DUO_TOOLS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)" || exit 1
source "$DUO_TOOLS/duo-common.sh" || exit 1
set -u
LAUNCHCTL=/bin/launchctl
AGENT_LABEL=io.github.guibrbs.claude-duo.update-check
AGENT="$HOME/Library/LaunchAgents/$AGENT_LABEL.plist"
UPDATER_APP="$HOME/Applications/Update Claude Duo.app"
LEGACY_UPDATER_APP="$HOME/Applications/Atualizar Claude Duo.app"
CONFIGS="$HOME/.config/claude-instances"
TOOLSET="$HOME/.local/share/claude-instances"

account=no; ask=yes
for arg in "$@"; do
    case "$arg" in
        --include-account-data) account=yes ;;
        --yes) ask=no ;;
        *) duo_error "unknown option: $arg"; exit 2 ;;
    esac
done
fail() { duo_error "$*"; exit 1; }

[ "$(/usr/bin/id -u)" != 0 ] || fail 'run as your own user, not as root'
! duo_app_running "$DUO_APP" || fail 'quit Claude Duo and try again'

config="$(duo_config 2>/dev/null)" || config="$CONFIGS/claude-duo.conf"
others=no
for file in "$CONFIGS"/*.conf; do
    [ -e "$file" ] && [ "$file" != "$config" ] && others=yes
done

items=("$DUO_APP" "$UPDATER_APP" "$LEGACY_UPDATER_APP" "$AGENT" "$DUO_HOME" "$config" "$DUO_LOG_DIR")
if [ "$others" = no ]; then
    items+=("$TOOLSET")
    for txn in "$HOME/Applications"/.claude-txn.*; do items+=("$txn"); done
fi
[ "$account" = no ] || items+=("$HOME/Library/Application Support/Claude-Duo" "$HOME/.claude-duo")
present=()
for item in "${items[@]}"; do
    [ -e "$item" ] || [ -L "$item" ] && present+=("$item")
done
[ "${#present[@]}" -gt 0 ] || { echo 'Nothing from Claude Duo was found.'; exit 0; }

echo 'Moving to the Trash:'
printf '  %s\n' "${present[@]}"
[ "$others" = no ] || printf 'Keeping %s and %s/.claude-txn.*: another config in %s still uses them.\n' "$TOOLSET" "$HOME/Applications" "$CONFIGS"
[ "$account" = yes ] || echo 'Keeping the Duo account data: ~/Library/Application Support/Claude-Duo and ~/.claude-duo (add --include-account-data to move them too).'
if [ "$ask" = yes ]; then
    [ -t 0 ] || fail 'no terminal to confirm; run again with --yes'
    read -r -p 'Continue? [y/N] ' answer
    case "$answer" in y|Y|yes|Yes) ;; *) echo 'Nothing was changed.'; exit 0 ;; esac
fi

"$LAUNCHCTL" bootout "gui/$(/usr/bin/id -u)/$AGENT_LABEL" >/dev/null 2>&1 || true
# One folder per run, mirroring the paths under the home folder.
destination="$HOME/.Trash/Claude Duo uninstalled $(/bin/date +%Y-%m-%d\ %H.%M.%S)"
[ ! -e "$destination" ] && [ ! -L "$destination" ] || fail "already exists: $destination"
/bin/mkdir -p -m 700 "$destination" || exit 1
status=0
for item in "${present[@]}"; do
    target="$destination/${item#"$HOME"/}"
    /bin/mkdir -p "${target%/*}" && /bin/mv "$item" "$target" || { duo_error "could not move: $item"; status=1; }
done
# Only an empty folder: rmdir refuses anything else.
[ "$others" = yes ] || /bin/rmdir "$CONFIGS" 2>/dev/null || true
printf 'Moved to %s\n' "$destination"
echo 'The "Duo Claude Safe Storage" item stays in the Keychain; delete it in Keychain Access if you want.'
exit "$status"
