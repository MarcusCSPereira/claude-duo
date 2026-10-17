#!/bin/bash
# Only known regenerable caches, only after profile users have stopped.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/claude-instances-common.sh"
ci_load_config || exit 1
rc=0
for i in "${!names[@]}"; do
    if [ "$#" -gt 0 ]; then
        selected=no
        for arg in "$@"; do [ "$(ci_lower "$arg")" != "$(ci_lower "${names[$i]}")" ] || selected=yes; done
        [ "$selected" = yes ] || continue
    fi
    app="$(ci_app_path "${names[$i]}")"; profile="${dirs[$i]}"; was_running=no
    [ -d "$profile" ] || continue
    ci_app_running "$app"; observed=$?
    case "$observed" in
        0) was_running=yes
           /usr/bin/osascript -e "tell application id \"${ids[$i]}\" to quit" >/dev/null 2>&1 || { ci_error 'quit request failed'; rc=1; continue; }
           for ((attempt=0; attempt<25; attempt++)); do
               ci_app_running "$app"; observed=$?
               [ "$observed" -eq 0 ] || break
               sleep 1
           done ;;
        1) ;;
        *) ci_error 'cannot inspect processes; caches unchanged'; rc=1; continue ;;
    esac
    ci_require_stopped "$app" || { rc=1; continue; }
    # Also catch stock Claude sharing Personal's profile, not just the named app.
    ci_profile_in_use "$profile"; observed=$?
    [ "$observed" -eq 1 ] || { ci_error 'profile is in use or its state is unknown; caches unchanged'; rc=1; continue; }
    current="$(ci_canonical_dir "$profile")" || { rc=1; continue; }
    [ "$current" = "$profile" ] && ci_safe_data_dir "$profile" desktop || { ci_error 'profile path changed or is unsafe'; rc=1; continue; }
    for cache in 'Cache' 'Code Cache' GPUCache DawnWebGPUCache DawnGraphiteCache 'Shared Dictionary'; do
        if [ -e "$profile/$cache" ] || [ -L "$profile/$cache" ]; then
            rm -rf "$profile/$cache" || { ci_error 'cache removal failed'; rc=1; }
        fi
    done
    if [ "$was_running" = yes ]; then open -a "$app" || rc=1; fi
    printf 'Claude %s: cache cleanup finished.\n' "${names[$i]}"
done
exit "$rc"
