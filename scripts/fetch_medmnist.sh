#!/usr/bin/env bash
# Fetch one MedMNIST file from the pinned Zenodo record and verify its MD5.
#
#   scripts/fetch_medmnist.sh <url> <md5> <dest>
#
# The files are large (up to ~10 GB at 224) and not this repository's to own, so they are pulled
# from the record pinned in config/medmnist.yaml rather than vendored. data/raw is a symlink into
# /scratch/$USER (large, purged periodically); a purge simply makes rule fetch run again. The
# download resumes on retry and lands atomically: a partial file never carries the final name.
set -euo pipefail

url="$1"; md5="$2"; dest="$3"

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
raw="$root/data/raw"
scratch="/scratch/$USER/textbook_priors_data"
# Snakemake creates an output's parent directory before the job runs, so data/raw may already exist
# as an empty plain directory; replace it with the symlink. A non-empty directory is left alone.
if [ -d "$raw" ] && [ ! -L "$raw" ] && [ -z "$(ls -A "$raw")" ]; then
    rmdir "$raw"
fi
if [ ! -e "$raw" ]; then
    mkdir -p "$scratch" "$root/data"
    ln -s "$scratch" "$raw"
    echo "linked data/raw -> $scratch"
fi
mkdir -p "$(dirname "$dest")"

part="$dest.part"
echo "fetching $url"
# curl's --retry covers timeouts and HTTP 408/429/5xx (Zenodo's gateway errors); the compute nodes'
# curl (7.61) predates --retry-all-errors. -C - resumes a partial download, and the outer loop
# retries the whole transfer a few more times with a pause, so one bad hour does not fail the job.
ok=0
for attempt in 1 2 3 4; do
    if curl -sS -L --fail --retry 10 --retry-delay 30 --max-time 14400 -C - -o "$part" "$url"; then
        ok=1; break
    fi
    echo "attempt $attempt failed; retrying in 120 s" >&2
    sleep 120
done
[ "$ok" = 1 ] || { rm -f "$part"; echo "download failed" >&2; exit 1; }
got="$(md5sum "$part" | cut -d' ' -f1)"
if [ "$got" != "$md5" ]; then
    echo "MD5 mismatch for $dest: expected $md5, got $got" >&2
    rm -f "$part"
    exit 1
fi
mv "$part" "$dest"
echo "ok $dest $got $(stat -c %s "$dest") bytes"
