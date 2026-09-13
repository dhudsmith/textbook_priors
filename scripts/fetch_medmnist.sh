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
    local i="$1" start end have want part tmp code
    start=$(( i * seg_bytes )); end=$(( start + seg_bytes - 1 ))
    [ "$end" -ge "$bytes" ] && end=$(( bytes - 1 ))
    want=$(( end - start + 1 ))
    part="$dest.seg$i"; tmp="$part.tmp"
    for attempt in $(seq 1 15); do
        have=0; [ -f "$part" ] && have=$(stat -c %s "$part")
        if [ "$have" -ge "$want" ]; then return 0; fi
        # Each attempt lands in its own file and is appended only when the server answered the range
        # with 206 and curl finished cleanly; curl's own --retry is off, because a retry mid-body would
        # re-request the same range and duplicate bytes. A 200 means the range was ignored: discard it.
        rm -f "$tmp"
        code=$(curl -sS -L --fail --max-time 7200 --speed-limit 1000 --speed-time 120 \
                    -r "$(( start + have ))-$end" -o "$tmp" -w '%{http_code}' "$url" 2>>"$part.err") || code="curl-$?"
        if [ "$code" = "206" ] && [ -s "$tmp" ]; then
            cat "$tmp" >> "$part"
            rm -f "$tmp"
            have=$(stat -c %s "$part")
            [ "$have" -ge "$want" ] && return 0
            echo "segment $i: short body, $have of $want bytes; continuing" >&2
        else
            echo "segment $i attempt $attempt: status $code with $have of $want bytes; retrying in 60 s" >&2
            rm -f "$tmp"
            sleep 60
        fi
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
rm -f "$dest".seg* "$dest".seg*.err
echo "ok $dest $got $(stat -c %s "$dest") bytes"
