#!/usr/bin/env bash

# Author: Landon J. Getz
# Date: 28-09-2026
#
# organize_tomos.sh — build per-tomogram folders of symlinks from a flat EER session dir for WarpTools session
#
# Usage: organize_tomos.sh <raw_session_dir> [output_dir]
#   output_dir defaults to <raw_session_dir>/../<session_name>_organized (i.e. one folder above the raw_session_dir )
#
# Typically my workflow has the following folders in the main workspace for a tomo collection session:
#
#  for_processing --> Output from this script
#  raw_data --> raw_session_dir copied from tomo session
#  organize.sh --> this script
#  warp_etomo_patches.sh --> Processing script
#
# Result:
#   <output_dir>/<tomo>/frames/<tomo>_NNN_<angle>_<date>_<time>_EER.eer -> raw
#   <output_dir>/<tomo>/mdoc/<tomo>.mdoc                                  -> raw
#
# Each tomogram is defined by its .mdoc. EER files are matched with an anchored
# regex (<tomo>_NNN_angle_date_time_EER.eer), so "tomo1" does NOT pick up
# "tomo1_2" frames.
#
# TODO: This script currently processes folders for each .mdoc, including the overrides which typically are not necessary. This needs to be cleaned up so only the main mdoc files are processed.
# TODO: Currently warp_etomo_patches.sh requires the gain file to be present in the input folder ("for_processing" above). This script could copy that from the raw data as well.

set -euo pipefail
shopt -s nullglob

raw=$(realpath "${1:?usage: $0 <raw_session_dir> [output_dir]}")
out=$(realpath -m "${2:-$(dirname "$raw")/$(basename "$raw")_organized}")
mkdir -p "$out"

mdocs=("$raw"/*.mdoc)
((${#mdocs[@]})) || {
  echo "No .mdoc files in $raw" >&2
  exit 1
}

for mdoc in "${mdocs[@]}"; do
  tomo=$(basename "$mdoc" .mdoc)
  mkdir -p "$out/$tomo/frames" "$out/$tomo/mdoc"
  ln -sfn "$mdoc" "$out/$tomo/mdoc/$tomo.mdoc"

  # Escape regex metacharacters in the tomo name (e.g. '.')
  esc=$(printf '%s' "$tomo" | sed 's/[][\.*^$+?(){}|/]/\\&/g')
  pat="^${esc}_[0-9]{3}_-?[0-9]+\.[0-9]+_[0-9]{8}_[0-9]{6}_EER\.eer$"

  n=0
  for eer in "$raw"/*.eer; do
    f=$(basename "$eer")
    if [[ $f =~ $pat ]]; then
      ln -sfn "$eer" "$out/$tomo/frames/$f"
      n=$((n + 1))
    fi
  done

  # Sanity check: tilts recorded in mdoc vs frames found on disk
  nz=$(grep -c '^\[ZValue' "$mdoc" || true)
  flag=""
  ((n != nz)) && flag="   <-- MISMATCH"
  printf '%-50s %3d frames linked, %3d tilts in mdoc%s\n' "$tomo" "$n" "$nz" "$flag"
done

echo "Done: $out"
