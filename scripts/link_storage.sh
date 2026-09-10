#!/usr/bin/env bash
# Point data/raw and data/cache at the large-storage root (config: storage_root), idempotently.
#
#   scripts/link_storage.sh <storage_root>
#
# The raw MedMNIST files (~40 GB) and the uint8 caches (~50 GB) live under <storage_root>/{raw,cache}
# on the project filesystem, which is not purged; the repository holds only the symlinks. Snakemake
# creates an output's parent directory before a job runs, so an empty plain data/raw or data/cache
# is replaced by the link; a non-empty plain directory is left alone and reported.
set -euo pipefail

storage="$1"
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p "$root/data"
for name in raw cache; do
    link="$root/data/$name"
    target="$storage/$name"
    mkdir -p "$target"
    if [ -L "$link" ]; then
        continue
    fi
    if [ -d "$link" ]; then
        if [ -z "$(ls -A "$link")" ]; then
            rmdir "$link"
        else
            echo "data/$name is a non-empty directory, not a link into $storage; leaving it alone" >&2
            continue
        fi
    fi
    ln -s "$target" "$link"
    echo "linked data/$name -> $target"
done
