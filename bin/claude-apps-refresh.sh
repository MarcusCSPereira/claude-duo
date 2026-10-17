#!/bin/bash
# Build verified, separate GUI profiles. The source app is never modified.
set -uo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/claude-instances-common.sh"
ci_load_config || exit 1

status() {
    local i app version source_version
    source_version="$(ci_version "$CI_SRC")" || source_version=unavailable
    printf '  %-24s %s\n' 'Claude.app (source)' "$source_version"
    for i in "${!names[@]}"; do
        app="$(ci_app_path "${names[$i]}")"
        version="$(ci_version "$app")" || version='NOT BUILT'
        printf '  %-24s %-14s' "Claude ${names[$i]}" "$version"
        if [ "$version" = "$source_version" ]; then printf 'same version\n'; else printf 'rebuild required\n'; fi
    done
}
list() {
    local i keys pair
    for i in "${!names[@]}"; do
        keys=""; local pairs=()
        IFS=';' read -ra pairs <<<"${envs[$i]}"
        for pair in "${pairs[@]-}"; do [ -z "$pair" ] || keys="${keys}${keys:+, }${pair%%=*}"; done
        printf '%s | %s | %s | hue=%s | env keys: %s\n' "${names[$i]}" "${ids[$i]}" "${dirs[$i]}" "${hues[$i]}" "${keys:--}"
    done
}
verify() {
    local i rc=0
    for i in "${!names[@]}"; do
        if ci_verify_one "$(ci_app_path "${names[$i]}")" "$i"; then
            printf 'Claude %s: verified (local signature; not an Anthropic-signed copy)\n' "${names[$i]}"
        else
            printf 'Claude %s: FAILED -- rebuild required\n' "${names[$i]}" >&2; rc=1
        fi
    done
    return "$rc"
}
build_one() (
    local idx="$1" name="${names[$1]}" dest stage bundle icon old_id
    local old_moved=no published=no
    dest="$(ci_app_path "$name")"
    [ ! -L "$dest" ] || { ci_error 'refusing symlinked destination'; return 1; }
    if [ -e "$dest" ]; then
        [ -d "$dest" ] || { ci_error 'destination is not an application directory'; return 1; }
        old_id="$("$CI_PB" -c 'Print :CFBundleIdentifier' "$dest/Contents/Info.plist")" || return 1
        case "$old_id" in "${ids[$idx]}"|com.anthropic.claudefordesktop) ;; *) ci_error 'refusing to overwrite an unrelated app'; return 1 ;; esac
    fi
    ci_require_stopped "$dest" || return 1
    stage="$(mktemp -d "$CI_APPS/.claude-build.XXXXXXXX")" || return 1
    cleanup() {
        if [ "$old_moved" = yes ] && [ "$published" = no ]; then
            if [ -e "$dest" ] || [ -L "$dest" ]; then
                ci_error "destination reappeared; previous app preserved at $stage/previous.app"
                return
            fi
            if ! mv "$stage/previous.app" "$dest"; then
                ci_error "restore failed; previous app preserved at $stage/previous.app"
                return
            fi
        fi
        rm -rf "$stage"
    }
    trap cleanup EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM
    bundle="$stage/instance.app"
    cp -Rc "$CI_SRC" "$bundle" || return 1
    codesign --verify --strict -R "$CI_REQUIREMENT" "$bundle" || return 1
    "$CI_PB" -c "Set :CFBundleIdentifier ${ids[$idx]}" "$bundle/Contents/Info.plist" || return 1
    "$CI_PB" -c "Set :CFBundleDisplayName Claude $name" "$bundle/Contents/Info.plist" || return 1
    "$CI_PB" -c 'Set :CFBundleExecutable launcher' "$bundle/Contents/Info.plist" || return 1
    local key
    for key in CFBundleURLTypes NSUserActivityTypes; do
        if "$CI_PB" -c "Print :$key" "$bundle/Contents/Info.plist" >/dev/null 2>&1; then
            "$CI_PB" -c "Delete :$key" "$bundle/Contents/Info.plist" || return 1
        fi
    done
    icon="$CI_ICONS/$(ci_lower "$name").icns"
    if [ ! -f "$icon" ]; then
        if ! "$(dirname "${BASH_SOURCE[0]}")/claude-recolor-icon.sh" "${hues[$idx]}" "$icon"; then
            printf 'warning: icon generation failed; using stock icon\n' >&2
        fi
    fi
    if [ -f "$icon" ]; then
        cp "$icon" "$bundle/Contents/Resources/appicon.icns" || return 1
        "$CI_PB" -c 'Set :CFBundleIconFile appicon' "$bundle/Contents/Info.plist" || return 1
        if "$CI_PB" -c 'Print :CFBundleIconName' "$bundle/Contents/Info.plist" >/dev/null 2>&1; then
            "$CI_PB" -c 'Delete :CFBundleIconName' "$bundle/Contents/Info.plist" || return 1
        fi
    fi
    ci_render_launcher "$idx" > "$bundle/Contents/MacOS/launcher" || return 1
    chmod 755 "$bundle/Contents/MacOS/launcher" || return 1
    plutil -lint "$bundle/Contents/Info.plist" >/dev/null || return 1
    # Sign only the executable and outer bundle; never --deep.
    codesign --force -s - "$bundle/Contents/MacOS/Claude" || return 1
    codesign --force -s - "$bundle" || return 1
    ci_verify_one "$bundle" "$idx" || return 1
    mkdir -p "${dirs[$idx]}" "${code_dirs[$idx]}" || return 1
    chmod 700 "${dirs[$idx]}" "${code_dirs[$idx]}" || return 1
    ci_require_stopped "$dest" || return 1
    if [ -e "$dest" ]; then
        mv "$dest" "$stage/previous.app" || return 1
        old_moved=yes
    fi
    [ ! -e "$dest" ] && [ ! -L "$dest" ] || { ci_error 'destination changed during publication'; return 1; }
    mv "$bundle" "$dest" || return 1
    published=yes
    /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$dest" >/dev/null 2>&1 || printf 'warning: LaunchServices registration failed\n' >&2
    printf 'Built Claude %s; local signature, independent GUI profile.\n' "$name"
)

case "${1:-all}" in
    --status|-s) status; exit $? ;;
    --list|-l) list; exit $? ;;
    --verify|-v) verify; exit $? ;;
    all) selected=("${!names[@]}") ;;
    *) selected=(); for i in "${!names[@]}"; do
           if [ "$(ci_lower "$1")" = "$(ci_lower "${names[$i]}")" ]; then selected+=("$i"); fi
       done
       [ "${#selected[@]}" -gt 0 ] || { ci_error 'unknown instance or option'; exit 2; } ;;
esac
umask 077
[ -d "$CI_SRC" ] && [ ! -L "$CI_SRC" ] || { ci_error 'missing or symlinked source Claude.app'; exit 1; }
codesign --verify --strict -R "$CI_REQUIREMENT" "$CI_SRC" || { ci_error 'source is not a valid Anthropic-signed Claude.app'; exit 1; }
spctl --assess --type execute "$CI_SRC" || { ci_error 'Gatekeeper did not accept the source'; exit 1; }
mkdir -p "$CI_ICONS" || exit 1
[ ! -L "$CI_ICONS" ] || { ci_error 'refusing symlinked icon/lock directory'; exit 1; }
lock="$CI_ICONS/.refresh-lock"
mkdir "$lock" || { ci_error 'another rebuild or a stale lock exists; inspect .refresh-lock before retrying'; exit 1; }
trap 'rmdir "$lock" 2>/dev/null || true' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
rc=0
for i in "${selected[@]}"; do build_one "$i" || rc=1; done
status
exit "$rc"
