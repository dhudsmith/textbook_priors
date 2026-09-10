#!/usr/bin/env bash
# Fetch one MedMNIST file from the pinned Zenodo record in parallel byte ranges and verify its MD5.
#
#   scripts/fetch_medmnist.sh <url> <md5> <bytes> <segments> <dest> <storage_root>
#
# The files are large (pathmnist_224.npz is 11.8 GB) and not this repository's to own, so they are
# pulled from the record pinned in config/medmnist.yaml rather than vendored. Zenodo serves about
# 105 KB/s per connection (measured 2026-09-09 from every node) but as many connections as you
# open, so a file is fetched as <segments> byte ranges at once, each resumable from wherever it
# stopped, then concatenated and checked against the pinned MD5. A partial file never carries the
# final name. data/raw is a symlink into <storage_root>/raw (scripts/link_storage.sh).
set -euo pipefail

url="$1"; md5="$2"; bytes="$3"; segments="$4"; dest="$5"; storage="$6"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"$root/scripts/link_storage.sh" "$storage"
mkdir -p "$(dirname "$dest")"
rm -f "$dest.part"                       # a single-stream partial from an earlier version of this script

seg_bytes=$(( (bytes + segments - 1) / segments ))
echo "fetching $url: $bytes bytes in $segments segments of $seg_bytes"

fetch_segment() {                        # resumes from the bytes already on disk; retries transient errors
    local i="$1" start end have part
    start=$(( i * seg_bytes )); end=$(( start + seg_bytes - 1 ))
    [ "$end" -ge "$bytes" ] && end=$(( bytes - 1 ))
    part="$dest.seg$i"
    for attempt in $(seq 1 12); do
        have=0; [ -f "$part" ] && have=$(stat -c %s "$part")
        if [ "$have" -ge $(( end - start + 1 )) ]; then return 0; fi
        if curl -sS -L --fail --retry 5 --retry-delay 20 --max-time 7200 --speed-limit 1000 --speed-time 120 \
                -r "$(( start + have ))-$end" -o - "$url" >> "$part"; then
            have=$(stat -c %s "$part")
            [ "$have" -ge $(( end - start + 1 )) ] && return 0
        fi
        echo "segment $i attempt $attempt ended at $have of $(( end - start + 1 )) bytes; retrying in 60 s" >&2
        sleep 60
    done
    echo "segment $i failed" >&2
    return 1
}

pids=()
for i in $(seq 0 $(( segments - 1 ))); do
    fetch_segment "$i" &
    pids+=($!)
done
fail=0
for pid in "${pids[@]}"; do wait "$pid" || fail=1; done
[ "$fail" = 0 ] || { echo "download failed" >&2; exit 1; }

cat $(for i in $(seq 0 $(( segments - 1 ))); do echo "$dest.seg$i"; done) > "$dest.part"
got="$(md5sum "$dest.part" | cut -d' ' -f1)"
if [ "$got" != "$md5" ]; then
    echo "MD5 mismatch for $dest: expected $md5, got $got; removing the segments" >&2
    rm -f "$dest.part" "$dest".seg*
    exit 1
fi
mv "$dest.part" "$dest"
rm -f "$dest".seg*
echo "ok $dest $got $(stat -c %s "$dest") bytes"
