#!/bin/bash -p
# Removes Claude Duo: both apps, the update check, the Duo tools, config and
# logs, plus the shared toolset and retained build transactions when no other
# config in ~/.config/claude-instances uses them. Everything is moved to one
# folder in the Trash, never deleted, and the list is shown before asking.
# The Duo account data (Desktop and Code profiles) and the Keychain item stay.
#   --include-account-data   also move the Duo's Desktop and Code profiles, as
#                            the config's Duo line names them (by default
#                            ~/Library/Application Support/Claude-Duo and
#                            ~/.claude-duo), to the Trash
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

trim() { local value="${1#"${1%%[![:space:]]*}"}"; printf '%s' "${value%"${value##*[![:space:]]}"}"; }
expand_home() { case "$1" in '~/'*) printf '%s/%s' "$HOME" "${1#\~/}" ;; *) printf '%s' "$1" ;; esac; }
# True for the Duo profile locations the toolset accepts for a managed copy
# (bin/claude-instances-common.sh): a flat Claude-* or .claude-* folder, or a
# managed UUID profile. The original's own folders never match.
is_duo_profile() {
    local kind="$1" path="$2" leaf
    case "$path/" in *'/../'*|*'/./'*|*'//'*) return 1 ;; esac
    [[ "$path" != *[[:cntrl:]]* ]] || return 1
    case "$kind:$path" in
        "$kind:$PROFILES/"*) [[ "${path#"$PROFILES/"}" =~ ^$UUID/$kind$ ]]; return ;;
        "desktop:$HOME/Library/Application Support/Claude-"*) leaf="${path#"$HOME/Library/Application Support/Claude-"}" ;;
        "code:$HOME/.claude-"*) leaf="${path#"$HOME/.claude-"}" ;;
        *) return 1 ;;
    esac
    [ -n "$leaf" ] && [[ "$leaf" != */* ]]
}
PROFILES="$HOME/Library/Application Support/Multi Claude Desktop/Profiles"
UUID='[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}'
# The account data is where the Duo line says: its Desktop profile (third
# column) and its CLAUDE_CONFIG_DIR. The defaults apply only without a config.
account_dirs=("$HOME/Library/Application Support/Claude-Duo" "$HOME/.claude-duo")
refused=()
if [ -f "$config" ] && [ ! -L "$config" ]; then
    account_dirs=()
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%%#*}"
        IFS='|' read -r name _bundle desktop _hue env _extra <<<"$line"
        [ "$(trim "$name")" = Duo ] || continue
        desktop="$(expand_home "$(trim "$desktop")")"
        if is_duo_profile desktop "$desktop"; then account_dirs+=("$desktop"); else refused+=("$desktop"); fi
        IFS=';' read -ra pairs <<<"${env:-}"
        for pair in "${pairs[@]-}"; do
            pair="$(trim "$pair")"
            case "$pair" in CLAUDE_CONFIG_DIR=*)
                code="$(expand_home "$(trim "${pair#CLAUDE_CONFIG_DIR=}")")"
                if is_duo_profile code "$code"; then account_dirs+=("$code"); else refused+=("$code"); fi ;;
            esac
        done
    done < "$config"
fi

items=("$DUO_APP" "$UPDATER_APP" "$LEGACY_UPDATER_APP" "$AGENT" "$DUO_HOME" "$config" "$DUO_LOG_DIR")
if [ "$others" = no ]; then
    items+=("$TOOLSET")
    for txn in "$HOME/Applications"/.claude-txn.*; do items+=("$txn"); done
fi
[ "$account" = no ] || [ "${#account_dirs[@]}" -eq 0 ] || items+=("${account_dirs[@]}")
present=()
for item in "${items[@]}"; do
    [ -e "$item" ] || [ -L "$item" ] && present+=("$item")
done
[ "${#present[@]}" -gt 0 ] || { echo 'Nothing from Claude Duo was found.'; exit 0; }

echo 'Moving to the Trash:'
printf '  %s\n' "${present[@]}"
[ "$others" = no ] || printf 'Keeping %s and %s/.claude-txn.*: another config in %s still uses them.\n' "$TOOLSET" "$HOME/Applications" "$CONFIGS"
if [ "$account" = no ]; then
    [ "${#account_dirs[@]}" -eq 0 ] || { echo 'Keeping the Duo account data (add --include-account-data to move it too):'; printf '  %s\n' "${account_dirs[@]}"; }
elif [ "${#refused[@]}" -gt 0 ]; then
    echo 'Keeping these folders from the Duo line: they are not Duo profile locations:'
    printf '  %s\n' "${refused[@]}"
fi
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
