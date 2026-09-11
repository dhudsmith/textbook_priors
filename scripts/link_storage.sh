#!/usr/bin/env bash
# One-time setup: point data/raw and data/cache at the project filesystem.
#
# Not a rule, because neither is a computation. The raw releases under <storage_root>/raw were
# downloaded, sized and checksummed before the workflow existed and no rule fetches or re-verifies
# them (WORKFLOW.md section 4); the cache holds the arrays the sample stage writes, which are
# inputs to later stages rather than results. Both are gitignored, so a fresh clone runs this once.
#
#     scripts/link_storage.sh [storage_root]
#
# The default comes from config/config.yaml. Re-running it is safe.
set -euo pipefail
cd "$(dirname "$0")/.."
root="${1:-$(sed -n 's/^storage_root: *//p' config/config.yaml)}"
[ -n "$root" ] || { echo "no storage_root in config/config.yaml, and none given" >&2; exit 1; }
[ -d "$root/raw" ] || { echo "$root/raw does not exist: the releases are prior work, not fetched here" >&2; exit 1; }

mkdir -p "$root/cache"
ln -sfn "$root/raw" data/raw
ln -sfn "$root/cache" data/cache
ls -ld data/raw data/cache
echo "release files visible: $(ls data/raw/*_224.npz 2>/dev/null | wc -l)"
