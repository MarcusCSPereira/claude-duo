#!/bin/bash -p
# Rebuilds Claude Duo from the current official Claude: asks first, quits both
# apps, rebuilds and verifies with the installed toolset, relinks shared Code
# files, then reopens whatever was open. --yes skips the question.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/duo-common.sh" || exit 1
set -u

ask=yes
case "${1:-}" in --yes) ask=no ;; '') ;; *) duo_error 'usage: update-duo.sh [--yes]'; exit 2 ;; esac
/bin/mkdir -p "$DUO_LOG_DIR" || exit 1
LOG="$DUO_LOG_DIR/update-$(/bin/date +%Y%m%d-%H%M%S).log"
log() { printf '%s\n' "$*" >> "$LOG"; }

if ! duo_config >/dev/null 2>>"$LOG"; then
    duo_notify "Claude Duo" "$(duo_t "Claude Duo is not installed. Run duo/install-duo.sh." "O Claude Duo não está instalado. Rode o duo/install-duo.sh.")"
    exit 1
fi
if [ "$ask" = yes ]; then
    update_now="$(duo_t "Update now" "Atualizar agora")"
    answer="$(duo_ask "$(duo_t "To update Claude Duo, Claude and Claude Duo will quit and reopen at the end. Save your work first." "Para atualizar o Claude Duo, o Claude e o Claude Duo serão fechados e reabertos no fim. Salve o que estiver fazendo.")" "$update_now" "$(duo_t "Cancel" "Cancelar")")"
    [ "$answer" = "$update_now" ] || { log "cancelled"; exit 0; }
fi

claude_open=no; duo_open=no
duo_app_running "$DUO_SOURCE_APP" && claude_open=yes
duo_app_running "$DUO_APP" && duo_open=yes
reopen() {
    [ "$claude_open" = no ] || "$OPEN" -a "$DUO_SOURCE_APP" >/dev/null 2>&1 || true
    [ "$duo_open" = no ] || [ ! -d "$DUO_APP" ] || "$OPEN" -a "$DUO_APP" >/dev/null 2>&1 || true
}

if ! duo_quit_both; then
    log "apps did not quit within ${DUO_QUIT_TIMEOUT}s; still running (PID executable):"
    { duo_app_processes "$DUO_SOURCE_APP"; duo_app_processes "$DUO_APP" any; } | while IFS= read -r line; do log "  $line"; done
    duo_notify "Claude Duo" "$(duo_t "Could not quit Claude and Claude Duo. Quit both and try again. Log: $LOG" "Não consegui fechar o Claude e o Claude Duo. Feche os dois e tente de novo. Log: $LOG")"
    exit 1
fi
duo_notify "Claude Duo" "$(duo_t "Updating Claude Duo… this takes about a minute." "Atualizando o Claude Duo… leva cerca de um minuto.")"
log "== $(/bin/date) source $(duo_version "$DUO_SOURCE_APP") duo $(duo_version "$DUO_APP" || echo none)"

status=0
{ duo_refresh Duo && duo_refresh --verify; } >> "$LOG" 2>&1 || status=$?
if [ "$status" -eq 0 ] && [ -f "$HOME/.claude-duo/.shared-from-original.json" ] && [ -f "$DUO_HOME/share-code-profile.py" ]; then
    # Links memories of projects created since the last run; never touches login data.
    /usr/bin/python3 -I "$DUO_HOME/share-code-profile.py" --apply >> "$LOG" 2>&1 || log "warning: shared Code files were not refreshed"
fi

reopen
if [ "$status" -eq 0 ]; then
    log "OK"
    version="$(duo_version "$DUO_APP")"
    duo_notify "Claude Duo" "$(duo_t "Claude Duo updated to $version and verified." "Claude Duo atualizado para $version e verificado.")"
else
    log "FAILED ($status)"
    # The native idle check names processes that run a deleted executable,
    # typically a helper of the previous Claude kept alive by Chrome.
    stale=""
    while IFS= read -r line; do
        case "$line" in "process "*") runs a deleted executable"*) stale="${line#process }"; break ;; esac
    done < "$LOG"
    if [ -n "$stale" ]; then
        name="${stale#* (}"; name="${name%%) runs*}"; pid="${stale%% *}"
        duo_notify "Claude Duo" "$(duo_t "Update stopped: $name (PID $pid) still runs a file from the previous Claude. Quit that process and try again. Log: $LOG" "A atualização parou: $name (PID $pid) ainda roda um arquivo da versão anterior do Claude. Encerre esse processo e tente de novo. Log: $LOG")"
    else
        duo_notify "Claude Duo" "$(duo_t "The update failed; the previous Claude Duo was kept. Log: $LOG" "A atualização falhou; o Claude Duo anterior foi mantido. Log: $LOG")"
    fi
fi
exit "$status"
