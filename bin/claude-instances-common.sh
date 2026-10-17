#!/bin/bash
# Shared data-only configuration and verification; macOS Bash 3.2 compatible.
CI_SRC="/Applications/Claude.app"
CI_APPS="/Applications"
CI_CONF="${CLAUDE_INSTANCES_CONF:-$HOME/.config/claude-instances/instances.conf}"
CI_ICONS="$HOME/.local/share/claude-instances"
CI_PB=/usr/libexec/PlistBuddy
CI_REQUIREMENT='=anchor apple generic and certificate leaf[subject.OU] = "Q6L2SF6YDW" and identifier "com.anthropic.claudefordesktop"'
ci_error() { printf 'error: %s\n' "$*" >&2; }
ci_trim() {
    local value="$1"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    printf '%s' "$value"
}
ci_lower() { printf '%s' "$1" | LC_ALL=C tr '[:upper:]' '[:lower:]'; }
ci_expand() {
    case "$1" in '~') printf '%s\n' "$HOME" ;; '~/'*) printf '%s/%s\n' "$HOME" "${1#\~/}" ;; *) printf '%s\n' "$1" ;; esac
}
# Resolve existing ancestors physically; never interpret config as shell code.
ci_canonical_dir() (
    local path suffix="" part physical
    path="$(ci_expand "$1")" || exit 1
    case "$path" in /*) ;; *) ci_error 'directory must be absolute'; exit 1 ;; esac
    case "$path" in *$'\n'*|*$'\r'*|*$'\t'*) ci_error 'control character in directory'; exit 1 ;; esac
    while [ "$path" != / ] && [ "${path%/}" != "$path" ]; do path="${path%/}"; done
    case "$path/" in *'/../'*|*'/./'*|*'//'*) ci_error 'dot components or repeated slashes in directory'; exit 1 ;; esac
    while [ ! -d "$path" ]; do
        if [ -e "$path" ] || [ -L "$path" ]; then ci_error 'directory is a file or dangling link'; exit 1; fi
        part="${path##*/}"; suffix="/$part$suffix"; path="${path%/*}"
        [ -n "$path" ] || path=/
    done
    physical="$(cd -- "$path" && pwd -P)" || exit 1
    printf '%s%s\n' "${physical%/}" "$suffix"
)
ci_safe_data_dir() {
    local path="$1" home
    home="$(ci_canonical_dir "$HOME")" || return 1
    case "$path" in ''|/|"$home"|"$CI_APPS"|"$CI_APPS/"*|*.app|*.app/*)
        ci_error 'refusing root, home or application bundle as a data directory'; return 1 ;;
    esac
}
ci_load_config() {
    [ -f "$CI_CONF" ] && [ ! -L "$CI_CONF" ] || { ci_error 'missing or symlinked instance config'; return 1; }
    names=(); ids=(); dirs=(); hues=(); envs=(); code_dirs=()
    local line n bid dir hue env extra pair key value seen normalized code_dir a b
    while IFS= read -r line || [ -n "$line" ]; do
        line="${line%%#*}"; line="$(ci_trim "$line")"
        [ -n "$line" ] || continue
        IFS='|' read -r n bid dir hue env extra <<<"$line"
        [ -z "${extra:-}" ] && [[ "$line" != *'|'*'|'*'|'*'|'*'|'* ]] || { ci_error 'too many config columns'; return 1; }
        n="$(ci_trim "$n")"; bid="$(ci_trim "$bid")"; dir="$(ci_trim "$dir")"
        hue="$(ci_trim "${hue:-212}")"; env="$(ci_trim "${env:-}")"
        [[ "$n" =~ ^[A-Za-z][A-Za-z0-9_-]{0,63}$ ]] || { ci_error 'invalid instance name'; return 1; }
        [[ "$bid" =~ ^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$ ]] && [ "$(ci_lower "$bid")" != com.anthropic.claudefordesktop ] || { ci_error 'invalid or reserved bundle id'; return 1; }
        [[ "$hue" =~ ^[0-9]{1,3}$ ]] && [ "$((10#$hue))" -le 359 ] || { ci_error 'hue must be an integer from 0 to 359'; return 1; }
        dir="$(ci_canonical_dir "$dir")" && ci_safe_data_dir "$dir" || return 1
        code_dir="$(ci_canonical_dir "$HOME/.claude")" || return 1
        seen='|'; normalized=""
        local pairs=()
        IFS=';' read -ra pairs <<<"$env"
        for pair in "${pairs[@]-}"; do
            pair="$(ci_trim "$pair")"; [ -n "$pair" ] || continue
            [[ "$pair" == *=* ]] || { ci_error 'environment entry must be KEY=VALUE'; return 1; }
            key="${pair%%=*}"; value="${pair#*=}"
            [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] || { ci_error 'invalid environment variable name'; return 1; }
            case "$key" in HOME|PATH|USER|LOGNAME|SHELL|CODEX_HOME|BASH_ENV|ENV|IFS|CDPATH|SHELLOPTS|BASHOPTS|DYLD_*|LD_*|NODE_OPTIONS)
                ci_error 'unsafe environment override'; return 1 ;;
            esac
            [[ "$seen" != *"|$key|"* ]] || { ci_error 'duplicate environment variable'; return 1; }
            seen="$seen$key|"; value="$(ci_expand "$value")" || return 1
            case "$key" in CLAUDE_CONFIG_DIR)
                value="$(ci_canonical_dir "$value")" && ci_safe_data_dir "$value" || return 1
                code_dir="$value" ;;
            esac
            normalized="${normalized}${normalized:+;}$key=$value"
        done
        names+=("$n"); ids+=("$bid"); dirs+=("$dir"); hues+=("$hue"); envs+=("$normalized"); code_dirs+=("$code_dir")
    done < "$CI_CONF"
    [ "${#names[@]}" -gt 0 ] || { ci_error 'no instances configured'; return 1; }
    for a in "${!names[@]}"; do
        for b in "${!names[@]}"; do
            [ "$a" -lt "$b" ] || continue
            [ "$(ci_lower "${names[$a]}")" != "$(ci_lower "${names[$b]}")" ] || { ci_error 'duplicate instance name'; return 1; }
            [ "$(ci_lower "${ids[$a]}")" != "$(ci_lower "${ids[$b]}")" ] || { ci_error 'duplicate bundle id'; return 1; }
            [ "$(ci_lower "${dirs[$a]}")" != "$(ci_lower "${dirs[$b]}")" ] || { ci_error 'instances share a profile (including case aliases)'; return 1; }
            [ "$(ci_lower "${code_dirs[$a]}")" != "$(ci_lower "${code_dirs[$b]}")" ] || { ci_error 'instances share a Claude Code config directory; set CLAUDE_CONFIG_DIR per account'; return 1; }
        done
    done
}
ci_app_path() { printf '%s/Claude %s.app\n' "$CI_APPS" "$1"; }
ci_version() { "$CI_PB" -c 'Print :CFBundleShortVersionString' "$1/Contents/Info.plist" 2>/dev/null; }
# 0=running, 1=not running, 2=unknown. Observation errors must stop mutations.
ci_app_running() {
    local snapshot pid executable line
    snapshot="$(ps -Aww -o pid=,comm=)" || return 2
    while IFS= read -r line; do
        read -r pid executable <<<"$line"
        [ "$executable" != "$1/Contents/MacOS/Claude" ] || return 0
        [ "$executable" != "$1/Contents/MacOS/launcher" ] || return 0
    done <<<"$snapshot"
    return 1
}
ci_require_stopped() {
    local rc
    ci_app_running "$1"; rc=$?
    case "$rc" in 1) return 0 ;; 0) ci_error "quit $1 with Cmd-Q first" ;; *) ci_error 'cannot inspect processes; refusing to continue' ;; esac
    return 1
}
ci_profile_of_pid() {
    local args value
    args="$(ps -ww -o command= -p "$1")" || return 2
    [ -n "$args" ] || return 2
    if [[ "$args" == *--user-data-dir* ]]; then
        value="${args#*--user-data-dir}"; value="${value#=}"; value="${value# }"
        case "$value" in *' --'*) value="${value%% --*}" ;; esac
    else
        value="$HOME/Library/Application Support/Claude"
    fi
    [ -d "$value" ] || return 2
    ci_canonical_dir "$value"
}
ci_profile_in_use() {
    local snapshot pid executable line profile
    snapshot="$(ps -Aww -o pid=,comm=)" || return 2
    while IFS= read -r line; do
        read -r pid executable <<<"$line"
        case "$executable" in */Contents/MacOS/Claude) ;; *) continue ;; esac
        profile="$(ci_profile_of_pid "$pid")" || return 2
        [ "$profile" != "$1" ] || return 0
    done <<<"$snapshot"
    return 1
}
ci_render_launcher() {
    local idx="$1" pair key value
    printf '#!/bin/bash\nset -euo pipefail\numask 077\n'
    printf 'HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"\n'
    printf 'DATA_DIR=%q\n' "${dirs[$idx]}"
    printf 'mkdir -p "$DATA_DIR"\nchmod 700 "$DATA_DIR"\n'
    printf 'unset CLAUDE_CONFIG_DIR\n'
    local pairs=()
    IFS=';' read -ra pairs <<<"${envs[$idx]}"
    for pair in "${pairs[@]-}"; do
        [ -n "$pair" ] || continue
        key="${pair%%=*}"; value="${pair#*=}"
        printf 'export %s=%q\n' "$key" "$value"
    done
    printf 'for ARG in "$@"; do\n  case "$ARG" in --user-data-dir|--user-data-dir=*) echo "profile override refused" >&2; exit 1 ;; esac\ndone\n'
    if [ "$(uname -m)" = arm64 ]; then
        printf 'exec /usr/bin/arch -arm64 "$HERE/Claude" --user-data-dir="$DATA_DIR" "$@"\n'
    else
        printf 'exec "$HERE/Claude" --user-data-dir="$DATA_DIR" "$@"\n'
    fi
}
ci_verify_one() {
    local app="$1" idx="$2" id executable
    [ -d "$app" ] && [ ! -L "$app" ] || { ci_error "missing or symlinked app: $app"; return 1; }
    id="$("$CI_PB" -c 'Print :CFBundleIdentifier' "$app/Contents/Info.plist")" || return 1
    executable="$("$CI_PB" -c 'Print :CFBundleExecutable' "$app/Contents/Info.plist")" || return 1
    [ "$id" = "${ids[$idx]}" ] && [ "$executable" = launcher ] || { ci_error 'bundle identity changed'; return 1; }
    [ -f "$app/Contents/MacOS/launcher" ] && [ ! -L "$app/Contents/MacOS/launcher" ] && [ -x "$app/Contents/MacOS/launcher" ] || return 1
    # Compare bytes, never evaluate or run the inspected launcher.
    cmp -s "$app/Contents/MacOS/launcher" <(ci_render_launcher "$idx") || { ci_error 'launcher differs from expected configuration'; return 1; }
    codesign --verify --strict "$app" || return 1
}
