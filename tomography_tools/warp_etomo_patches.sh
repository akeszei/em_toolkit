#!/usr/bin/env bash

# Author: Landon J. Getz
# Date: 28-09-2026
#
# warp_etomo_patches.sh — initial tomograms with WarpTools + IMOD patch tracking
#
# Usage: warp_etomo_patches.sh <tomo_dir>
#   <tomo_dir> is one tomogram folder from organize.sh, containing
#   mdoc/ and frames/ directly; the gain reference sits in the folder above it.
#   Warp runs inside <tomo_dir>: settings files, warp_frameseries/,
#   tomostar/ and warp_tiltseries/ are written next to mdoc/ and frames/.
#
# Pipeline: fs_motion_and_ctf -> ts_import -> ts_etomo_patches ->
#           ts_defocus_hand -> ts_ctf -> ts_reconstruct
#
# Parameters are read from the first mdoc where possible; override any of
# these by setting them in the environment, e.g.
#   ANGPIX=2.53 DOSE=2.0 THICK_A=5000 ./warp_etomo_patches.sh tomo/
#
#   ANGPIX       pixel size of the EER frames, Å         (mdoc PixelSpacing)
#   DOSE         exposure per tilt, e-/Å²                (mdoc ExposureDose)
#   AXIS         tilt axis angle, degrees                (mdoc RotationAngle) # Still not sure this is the correct thing to do
#   DIMS_XY      detector size "XxY" in pixels           (mdoc ImageSize)
#   THICK_A      reconstruction thickness, Å             (3000) # My default
#   GAIN         gain reference     (auto: the one gain file in the folder
#                above <tomo_dir>; GAIN='' to run without)  # Needs to be put in above "tomo_dir" manually
#   REC_ANGPIX   alignment + reconstruction pixel, Å     (10)
#   PATCH_A      etomo patch size, Å                     (2000)
#   AXIS_SEARCH  1 = let etomo refine the tilt axis (--do_axis_search) (1)
#   DEFOCUS_MAX  max defocus, µm                         (8)
#   RANGE_HIGH   CTF fit high-res limit, Å               (7)
#   PERDEVICE    Warp workers per GPU                    (2)
#   FLIP_HAND    unset = decide from ts_defocus_hand --check (default);
#                1 = force flip, 0 = force no flip
#   HAND_MIN     |correlation| below this gets a warning; Warp's sign is
#                still followed (0.3)
#   START_AT     resume from step N (1-7, see step headers)  (1)
#   WARP_ENV     conda env with WarpTools                (warp)
#   IMOD_DIR     IMOD install                            (cryoet env's IMOD)
#
#   To run sequentially on an entire folder of organized tomos you can use this for loop:
#   for folder in <organized_dir>/*; do
#     bash warp_etomo_patches.sh $folder
#   done
#

set -euo pipefail
shopt -s nullglob

org=$(realpath "${1:?usage: $0 <tomo_dir>}")

# ---------- environment: WarpTools + IMOD (etomo_patches calls batchruntomo)
for t in WarpTools batchruntomo; do
  command -v "$t" >/dev/null || {
    echo "ERROR: $t not on PATH" >&2
    exit 1
  }
done

# ---------- work inside the tomogram folder (Warp reads mdoc/ and frames/ as-is)
[[ -d $org/mdoc && -d $org/frames ]] || {
  echo "ERROR: $org should contain mdoc/ and frames/" >&2
  exit 1
}
cd "$org"
mkdir -p tomostar
mdocs=(mdoc/*.mdoc)
((${#mdocs[@]})) || {
  echo "ERROR: no .mdoc in $org/mdoc/" >&2
  exit 1
}
echo "Found ${#mdocs[@]} tilt series, $(ls frames/*.eer | wc -l) EER frames in $org"

# ---------- parameters (mdoc first, env overrides)
# parse a CR-stripped copy (Windows-written mdocs have CRLF line endings)
m1=$(mktemp)
trap 'rm -f "$m1"' EXIT
tr -d '\r' <"${mdocs[0]}" >"$m1"
mval() { grep -m1 -iE "^\s*$1\s*=" "$m1" | cut -d= -f2 | awk '{print $1}'; }
ANGPIX=${ANGPIX:-$(mval PixelSpacing)}
DOSE=${DOSE:-$(grep -iE '^\s*ExposureDose\s*=' "$m1" | cut -d= -f2 | awk '$1>0{print $1; exit}')}
AXIS=${AXIS:-$(mval RotationAngle)}
DIMS_XY=${DIMS_XY:-$(grep -m1 -iE '^\s*ImageSize\s*=' "$m1" | cut -d= -f2 | awk '{print $1"x"$2}')}
THICK_A=${THICK_A:-3000}
REC_ANGPIX=${REC_ANGPIX:-10}
PATCH_A=${PATCH_A:-2000}
AXIS_SEARCH=${AXIS_SEARCH:-1}
DEFOCUS_MAX=${DEFOCUS_MAX:-8}
RANGE_HIGH=${RANGE_HIGH:-7}
PERDEVICE=${PERDEVICE:-2}

for v in ANGPIX DOSE AXIS DIMS_XY; do
  [[ -n ${!v} ]] || {
    echo "ERROR: could not read $v from $m1 — set it manually" >&2
    exit 1
  }
done
Z=$(awk -v t="$THICK_A" -v p="$ANGPIX" 'BEGIN{printf "%d", t/p}')
DIMS="${DIMS_XY}x${Z}"
# gain reference: auto-detected in the folder above the tomo_dir.
# GAIN unset -> auto; GAIN=/path -> use it; GAIN='' -> run without a gain.
find_gain() {
  local d
  d=$(dirname "$1")
  local hits=()
  for f in "$d"/*.gain "$d"/*[Gg]ain*.mrc "$d"/*[Gg]ain*.tif "$d"/*[Gg]ain*.tiff; do
    [[ -f $f ]] && hits+=("$(realpath "$f")")
  done
  mapfile -t hits < <(printf '%s\n' "${hits[@]}" | awk 'NF && !seen[$0]++')
  case ${#hits[@]} in
  1) echo "${hits[0]}" ;;
  0) echo "WARNING: no gain reference (*.gain, *gain*.mrc/.tif) found in $d" >&2 ;;
  *)
    echo "WARNING: several gain references in $d — set GAIN explicitly:" >&2
    printf '         %s\n' "${hits[@]}" >&2
    ;;
  esac
}
if [[ -z ${GAIN+set} ]]; then
  GAIN=$(find_gain "$org")
  [[ -n $GAIN ]] || {
    echo "ERROR: no unique gain reference found; set GAIN=/path (or GAIN='' to skip)" >&2
    exit 1
  }
fi
[[ -z $GAIN || -f $GAIN ]] || {
  echo "ERROR: GAIN=$GAIN does not exist" >&2
  exit 1
}
gain_args=()
[[ -n $GAIN ]] && gain_args=(--gain_path "$(realpath "$GAIN")")

cat <<EOF
---------------------------------------------
 pixel size     $ANGPIX Å
 dose / tilt    $DOSE e-/Å²
 tilt axis      $AXIS°
 tomo dims      $DIMS px  (~$THICK_A Å thick)
 recon pixel    $REC_ANGPIX Å   patch $PATCH_A Å   axis search $AXIS_SEARCH
 gain           ${GAIN:-none}
---------------------------------------------
EOF

START_AT=${START_AT:-1}
echo "Starting at step $START_AT"

# ---------- 1. settings
if ((START_AT <= 1)); then
  WarpTools create_settings \
    --folder_data frames --extension "*.eer" \
    --folder_processing warp_frameseries --output warp_frameseries.settings \
    --angpix "$ANGPIX" --exposure "$DOSE" "${gain_args[@]}"

  WarpTools create_settings \
    --folder_data tomostar --extension "*.tomostar" \
    --folder_processing warp_tiltseries --output warp_tiltseries.settings \
    --angpix "$ANGPIX" --exposure "$DOSE" --tomo_dimensions "$DIMS" "${gain_args[@]}"
fi

# ---------- 2. motion correction + per-tilt CTF on the EER frames
if ((START_AT <= 2)); then
  WarpTools fs_motion_and_ctf \
    --settings warp_frameseries.settings \
    --m_grid 1x1x3 --c_grid 2x2x1 \
    --c_range_max "$RANGE_HIGH" --c_defocus_max "$DEFOCUS_MAX" --c_use_sum \
    --out_averages --out_average_halves \
    --perdevice "$PERDEVICE"
fi

# ---------- 3. assemble tilt series from mdocs
if ((START_AT <= 3)); then
  WarpTools ts_import \
    --mdocs mdoc --frameseries warp_frameseries \
    --tilt_exposure "$DOSE" --min_intensity 0.3 --dont_invert \
    --override_axis "$AXIS" \
    --output tomostar
fi

# ---------- 4. alignment: IMOD patch tracking
if ((START_AT <= 4)); then
  axis_search_args=()
  [[ $AXIS_SEARCH == 1 ]] && axis_search_args=(--do_axis_search)
  WarpTools ts_etomo_patches \
    --settings warp_tiltseries.settings \
    --angpix "$REC_ANGPIX" --patch_size "$PATCH_A" --initial_axis "$AXIS" \
    "${axis_search_args[@]}" \
    --perdevice "$PERDEVICE"
fi

# ---------- 5. defocus handedness (auto)
if ((START_AT <= 5)); then
  # --check prints "Average correlation: X". Negative -> data need 'flip';
  # positive -> 'no flip' (Warp's default on import, so nothing to do).
  hand_log=warp_tiltseries/defocus_hand_check.log
  mkdir -p warp_tiltseries
  if [[ -z ${FLIP_HAND:-} ]]; then
    WarpTools ts_defocus_hand --settings warp_tiltseries.settings --check | tee "$hand_log"
    corr=$(grep -oP 'Average correlation:\s*\K-?[0-9.]+' "$hand_log" | tail -1 || true)
    [[ -n $corr ]] || {
      echo "ERROR: couldn't read correlation from $hand_log" >&2
      exit 1
    }
    if awk -v c="$corr" -v m="${HAND_MIN:-0.3}" 'BEGIN{exit !((c<0?-c:c) < m)}'; then
      echo "WARNING: handedness correlation $corr is weak (|c| < ${HAND_MIN:-0.3}); following its sign anyway." >&2
      echo "         Worth confirming on another tomogram. Override with FLIP_HAND=0/1 START_AT=5." >&2
      weak=" (weak)"
    fi
    FLIP_HAND=$(awk -v c="$corr" 'BEGIN{print (c<0)?1:0}')
    echo "Handedness correlation $corr -> FLIP_HAND=$FLIP_HAND"
  else
    echo "Handedness forced by environment: FLIP_HAND=$FLIP_HAND"
  fi
  if [[ $FLIP_HAND == 1 ]]; then
    WarpTools ts_defocus_hand --settings warp_tiltseries.settings --set_flip
  else
    echo "No flip needed; keeping Warp's default handedness."
  fi
  echo "FLIP_HAND=$FLIP_HAND${corr:+  (correlation $corr${weak:-})}" >>warp_tiltseries/pipeline_decisions.txt
fi

# ---------- 6. tilt-series CTF
if ((START_AT <= 6)); then
  WarpTools ts_ctf \
    --settings warp_tiltseries.settings \
    --range_high "$RANGE_HIGH" --defocus_max "$DEFOCUS_MAX" \
    --perdevice "$PERDEVICE"
fi

# ---------- 7. reconstruction
if ((START_AT <= 7)); then
  WarpTools ts_reconstruct \
    --settings warp_tiltseries.settings \
    --angpix "$REC_ANGPIX" --perdevice "$PERDEVICE"
fi

echo "Done. Tomograms: $org/warp_tiltseries/reconstruction/"
