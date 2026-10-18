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

answer="$(duo_ask "O Claude foi atualizado para $source_version e o Claude Duo está na $duo_version_now. Para atualizar o Duo, os dois apps serão fechados e reabertos." "Atualizar agora" "Depois")"
[ "$answer" = "Atualizar agora" ] || exit 0
exec /bin/bash -p "$DUO_HOME/atualizar-duo.sh" --yes
