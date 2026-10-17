#!/bin/bash
# Project 5: test the internet once and add one line to the log.
# Run every minute from cron:  * * * * * /home/YOU/uptime_check.sh
LOG="$HOME/uptime.csv"
TARGETS=(1.1.1.1 8.8.8.8 9.9.9.9)    # three different companies

now=$(date '+%Y-%m-%d %H:%M:%S')
if [ ! -f "$LOG" ]; then
    echo "time,status,ms" > "$LOG"
fi

for target in "${TARGETS[@]}"; do
    if reply=$(ping -c 1 -W 2 "$target" 2>/dev/null); then
        ms=$(echo "$reply" | sed -n 's/.*time=\([0-9.]*\) ms.*/\1/p')
        echo "$now,up,$ms" >> "$LOG"
        exit 0
    fi
done

echo "$now,down," >> "$LOG"    # all three failed
