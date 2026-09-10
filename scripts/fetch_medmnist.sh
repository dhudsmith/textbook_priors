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
if [ ! -e "$raw" ]; then
    mkdir -p "$scratch" "$root/data"
    ln -s "$scratch" "$raw"
    echo "linked data/raw -> $scratch"
fi
mkdir -p "$(dirname "$dest")"

part="$dest.part"
echo "fetching $url"
# --retry-all-errors covers Zenodo's 5xx gateway errors; -C - resumes a partial download.
curl -sS -L --fail --retry 10 --retry-delay 30 --retry-all-errors --max-time 14400 \
     -C - -o "$part" "$url" || { rm -f "$part"; echo "download failed" >&2; exit 1; }
got="$(md5sum "$part" | cut -d' ' -f1)"
if [ "$got" != "$md5" ]; then
    echo "MD5 mismatch for $dest: expected $md5, got $got" >&2
    rm -f "$part"
    exit 1
fi
mv "$part" "$dest"
echo "ok $dest $got $(stat -c %s "$dest") bytes"
