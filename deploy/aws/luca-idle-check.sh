#!/bin/sh
# Apaga la instancia cuando nadie usó LUCA en LUCA_IDLE_MINUTES (60 por defecto). Lo corre luca-idle.timer.
# Actividad = la última vez que la app tocó /app/data/last_activity (sólo con alumnos logueados) o el
# arranque de la máquina, lo que sea más reciente: recién despierta, tiene una hora de gracia.
# Mantenimiento: `sudo touch /etc/luca-idle-disabled` evita el apagado; borrarlo lo reactiva.
set -eu

IDLE_MINUTES="${LUCA_IDLE_MINUTES:-60}"
VOLUME="${LUCA_DATA_VOLUME:-luca_luca_data}"

if [ -e /etc/luca-idle-disabled ]; then
    exit 0
fi

now=$(date +%s)
last=$(( now - $(cut -d. -f1 /proc/uptime) ))  # boot time
mountpoint=$(docker volume inspect "$VOLUME" --format '{{ .Mountpoint }}' 2>/dev/null || true)
if [ -n "$mountpoint" ] && [ -f "$mountpoint/last_activity" ]; then
    activity=$(stat -c %Y "$mountpoint/last_activity")
    if [ "$activity" -gt "$last" ]; then
        last=$activity
    fi
fi

idle=$(( (now - last) / 60 ))
if [ "$idle" -ge "$IDLE_MINUTES" ]; then
    echo "Sin uso hace $idle minutos: apagando"
    systemctl poweroff
fi
