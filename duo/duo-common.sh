#!/bin/bash -p
# Shared helpers for the Claude Duo convenience tools (installer, updater,
# update check). They call the versioned toolset; they never edit apps or
# profiles directly. External commands are absolute paths on purpose.
PATH=/usr/bin:/bin:/usr/sbin:/sbin
export PATH
umask 077

OSASCRIPT=/usr/bin/osascript
OPEN=/usr/bin/open
PS=/bin/ps
PLISTBUDDY=/usr/libexec/PlistBuddy
SLEEP=/bin/sleep

DUO_HOME="$HOME/.local/share/claude-duo"
DUO_CONFIG_POINTER="$DUO_HOME/config-path"
DUO_LOG_DIR="$HOME/Library/Logs/Claude Duo Updater"
DUO_APP="$HOME/Applications/Claude Duo.app"
DUO_SOURCE_APP="/Applications/Claude.app"
DUO_DISPATCHER="$HOME/.local/share/claude-instances/toolsets/dispatcher"
DUO_QUIT_TIMEOUT=60
# Dialogs and notifications follow the macOS language: Portuguese when the
# first preferred language is Portuguese, English otherwise.
DUO_LANGUAGE="$(/usr/bin/defaults read -g AppleLanguages 2>/dev/null | /usr/bin/awk -F'"' 'NF>1{print $2; exit}')"

# duo_t ENGLISH PORTUGUESE
duo_t() { case "$DUO_LANGUAGE" in pt*) printf '%s' "$2" ;; *) printf '%s' "$1" ;; esac; }

duo_error() { printf 'claude-duo: %s\n' "$*" >&2; }

# Text for AppleScript string literals: backslashes and quotes escaped.
duo_as_text() { local text="${1//\\/\\\\}"; printf '%s' "${text//\"/\\\"}"; }

duo_notify() {
    "$OSASCRIPT" -e "display notification \"$(duo_as_text "$2")\" with title \"$(duo_as_text "$1")\"" >/dev/null 2>&1 || true
}

# Prints the chosen button; empty when dismissed or unavailable.
duo_ask() {
    local message="$1" first="$2" second="$3"
    "$OSASCRIPT" -e "button returned of (display alert \"Claude Duo\" message \"$(duo_as_text "$message")\" buttons {\"$(duo_as_text "$second")\", \"$(duo_as_text "$first")\"} default button \"$(duo_as_text "$first")\")" 2>/dev/null || true
}

duo_config() {
    local path
    [ -f "$DUO_CONFIG_POINTER" ] && [ ! -L "$DUO_CONFIG_POINTER" ] || { duo_error 'Claude Duo is not installed (run duo/install-duo.sh)'; return 1; }
    IFS= read -r path < "$DUO_CONFIG_POINTER" || true
    case "$path" in "$HOME"/.config/claude-instances/*.conf) ;; *) duo_error 'unexpected config location'; return 1 ;; esac
    [ -f "$path" ] && [ ! -L "$path" ] || { duo_error "missing config: $path"; return 1; }
    printf '%s\n' "$path"
}

duo_refresh() {
    local config
    config="$(duo_config)" || return 1
    /usr/bin/env -i HOME="$HOME" USER="$USER" LOGNAME="$USER" PATH="$PATH" LANG=en_US.UTF-8 \
        CLAUDE_INSTANCES_CONF="$config" "$DUO_DISPATCHER" run claude-apps-refresh.sh "$@"
}

duo_version() { "$PLISTBUDDY" -c 'Print :CFBundleShortVersionString' "$1/Contents/Info.plist" 2>/dev/null; }

# Prints "PID executable" for the app and its Electron helpers. Helpers in
# Contents/Helpers are started by other programs (chrome-native-host by
# Chrome, disclaimer by the claude CLI) and outlive the app; as in the native
# desktop-idle check (bin/claude-maintenance.h), only executables in a
# Contents/MacOS count.
duo_app_processes() {
    local prefix="$1/Contents/" pid executable
    while read -r pid executable; do
        case "$executable" in "$prefix"MacOS/*|"$prefix"*/Contents/MacOS/*) printf '%s %s\n' "$pid" "$executable" ;; esac
    done < <("$PS" -axo pid=,comm=)
}

duo_app_running() { [ -n "$(duo_app_processes "$1")" ]; }

duo_quit_app() {
    local app="$1" identifier
    duo_app_running "$app" || return 0
    identifier="$("$PLISTBUDDY" -c 'Print :CFBundleIdentifier' "$app/Contents/Info.plist" 2>/dev/null)" || return 1
    "$OSASCRIPT" -e "tell application id \"$(duo_as_text "$identifier")\" to quit" >/dev/null 2>&1 || true
}

# Asks both apps to quit (they may show their own save prompts) and waits.
duo_quit_both() {
    local waited=0
    duo_quit_app "$DUO_SOURCE_APP"
    duo_quit_app "$DUO_APP"
    while duo_app_running "$DUO_SOURCE_APP" || duo_app_running "$DUO_APP"; do
        [ "$waited" -lt "$DUO_QUIT_TIMEOUT" ] || return 1
        "$SLEEP" 1
        waited=$((waited + 1))
    done
}
