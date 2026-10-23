#!/usr/bin/env bash
# Print one cgroup memory line every N seconds (default 30) until killed.
# current includes file cache; anon is process memory; file is page cache.
set -u

interval="${1:-30}"
cgroup=/sys/fs/cgroup

field() {
    awk -v k="$2" '$1 == k { print $2; found = 1 } END { if (!found) print 0 }' "$1" 2>/dev/null || echo 0
}

gib() {
    awk -v b="${1:-0}" 'BEGIN { printf "%.1f", b / 1024 / 1024 / 1024 }'
}

while true; do
    current="$(cat "$cgroup/memory.current" 2>/dev/null || echo 0)"
    anon="$(field "$cgroup/memory.stat" anon)"
    file_b="$(field "$cgroup/memory.stat" file)"
    oom_kill="$(field "$cgroup/memory.events" oom_kill)"
    max_ev="$(field "$cgroup/memory.events" max)"
    avail_kib="$(awk '/MemAvailable/ { print $2 }' /proc/meminfo 2>/dev/null || echo 0)"
    printf 'memstat %s current_gib=%s anon_gib=%s file_gib=%s mem_available_gib=%.1f oom_kill=%s max_events=%s\n' \
        "$(date -u +%H:%M:%S)" \
        "$(gib "$current")" \
        "$(gib "$anon")" \
        "$(gib "$file_b")" \
        "$(awk -v k="${avail_kib:-0}" 'BEGIN { print k / 1024 / 1024 }')" \
        "$oom_kill" \
        "$max_ev"
    sleep "$interval"
done
