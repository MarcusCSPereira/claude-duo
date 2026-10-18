#!/bin/bash -p
# Rebuilds Claude Duo from the current official Claude: asks first, quits both
# apps, rebuilds and verifies with the installed toolset, relinks shared Code
# files, then reopens whatever was open. --yes skips the question.
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)/duo-common.sh" || exit 1
set -u

ask=yes
case "${1:-}" in --yes) ask=no ;; '') ;; *) duo_error 'usage: atualizar-duo.sh [--yes]'; exit 2 ;; esac
/bin/mkdir -p "$DUO_LOG_DIR" || exit 1
LOG="$DUO_LOG_DIR/atualizar-$(/bin/date +%Y%m%d-%H%M%S).log"
log() { printf '%s\n' "$*" >> "$LOG"; }

if ! duo_config >/dev/null 2>>"$LOG"; then
    duo_notify "Claude Duo" "O Claude Duo não está instalado. Rode o instalar-duo.sh."
    exit 1
fi
if [ "$ask" = yes ]; then
    answer="$(duo_ask "Para atualizar o Claude Duo, o Claude e o Claude Duo serão fechados e reabertos no fim. Salve o que estiver fazendo." "Atualizar agora" "Cancelar")"
    [ "$answer" = "Atualizar agora" ] || { log "cancelled"; exit 0; }
fi

claude_open=no; duo_open=no
duo_app_running "$DUO_SOURCE_APP" && claude_open=yes
duo_app_running "$DUO_APP" && duo_open=yes
reopen() {
    [ "$claude_open" = no ] || "$OPEN" -a "$DUO_SOURCE_APP" >/dev/null 2>&1 || true
    [ "$duo_open" = no ] || [ ! -d "$DUO_APP" ] || "$OPEN" -a "$DUO_APP" >/dev/null 2>&1 || true
}

if ! duo_quit_both; then
    log "apps did not quit within ${DUO_QUIT_TIMEOUT}s"
    duo_notify "Claude Duo" "Não consegui fechar o Claude e o Claude Duo. Feche os dois e tente de novo."
    exit 1
fi
duo_notify "Claude Duo" "Atualizando o Claude Duo… leva cerca de um minuto."
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
    duo_notify "Claude Duo" "Claude Duo atualizado para $(duo_version "$DUO_APP") e verificado."
else
    log "FAILED ($status)"
    duo_notify "Claude Duo" "A atualização falhou; o Claude Duo anterior foi mantido. Log: $LOG"
fi
exit "$status"
