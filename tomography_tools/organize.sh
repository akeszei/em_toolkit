#!/usr/bin/env bash
# organize_tomos.sh — build per-tomogram folders of symlinks from a flat EER session dir
#
# Usage: organize_tomos.sh <raw_session_dir> [output_dir]
# e.g. $  organize.sh ./ warp_processed
#
# Result:
#   <output_dir>/<tomo>/frames/<tomo>_NNN_<angle>_<date>_<time>_EER.eer -> raw
#   <output_dir>/<tomo>/mdoc/<tomo>.mdoc                                  -> raw
#
# Each tomogram is defined by its .mdoc. EER files are matched with an anchored
# regex (<tomo>_NNN_angle_date_time_EER.eer), so "tomo1" does NOT pick up
# "tomo1_2" frames.

set -euo pipefail
shopt -s nullglob extglob

raw=$(realpath "${1:?usage: $0 <raw_session_dir> [output_dir]}")
out=$(realpath -m "${2:-$(dirname "$raw")/$(basename "$raw")_organized}")
mkdir -p "$out"

mdocs=("$raw"/!(*_override).mdoc)
((${#mdocs[@]})) || {
	echo "No non-override .mdoc files in $raw" >&2
	exit 1
}

for mdoc in "${mdocs[@]}"; do
	#	if [["$mdoc" == *"_override"*]]; then
	#		continue
	#	fi
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
