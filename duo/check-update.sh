#!/bin/bash -p
# Run by the launch agent: when the official Claude has a different version
# from Claude Duo, asks (at most once a day per version) whether to update now.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/duo-common.sh" || exit 1
set -u

duo_config >/dev/null 2>&1 || exit 0
source_version="$(duo_version "$DUO_SOURCE_APP")" || exit 0
duo_version_now="$(duo_version "$DUO_APP")" || exit 0
[ -n "$source_version" ] && [ "$source_version" != "$duo_version_now" ] || exit 0

state="$DUO_HOME/asked-version"
today="$(/bin/date +%Y-%m-%d)"
previous=""
[ ! -f "$state" ] || [ -L "$state" ] || IFS= read -r previous < "$state" || true
[ "$previous" != "$source_version $today" ] || exit 0
printf '%s %s\n' "$source_version" "$today" > "$state"

update_now="$(duo_t "Update now" "Atualizar agora")"
answer="$(duo_ask "$(duo_t "Claude was updated to $source_version and Claude Duo is on $duo_version_now. Updating the Duo quits and reopens both apps." "O Claude foi atualizado para $source_version e o Claude Duo está na $duo_version_now. Para atualizar o Duo, os dois apps serão fechados e reabertos.")" "$update_now" "$(duo_t "Later" "Depois")")"
[ "$answer" = "$update_now" ] || exit 0
exec /bin/bash -p "$DUO_HOME/update-duo.sh" --yes
