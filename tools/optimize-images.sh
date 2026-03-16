#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$ROOT_DIR/img/optimized"
mkdir -p "$OUT_DIR"

# source_image|basename|widths(comma-separated)
IMAGES=(
  "img/eclipse_header.png|eclipse_header|540,810,1080"
  "img/vol1.png|vol1|600,900,1200"
  "img/zr_te_structure.png|zr_te_structure|300,450,600"
  "img/grey_waves1.jpg|grey_waves1|300,450,595"
)

for entry in "${IMAGES[@]}"; do
  IFS='|' read -r src base widths <<< "$entry"
  src_path="$ROOT_DIR/$src"

  if [[ ! -f "$src_path" ]]; then
    echo "Skipping missing file: $src"
    continue
  fi

  IFS=',' read -ra width_list <<< "$widths"
  for width in "${width_list[@]}"; do
    ffmpeg -loglevel error -y -i "$src_path" -vf "scale=${width}:-2:flags=lanczos" \
      -frames:v 1 -c:v libwebp -quality 80 "$OUT_DIR/${base}-${width}.webp"

    if [[ "$base" != "eclipse_header" ]]; then
      ffmpeg -loglevel error -y -i "$src_path" -vf "scale=${width}:-2:flags=lanczos" \
        -frames:v 1 -c:v libaom-av1 -still-picture 1 -crf 40 -b:v 0 "$OUT_DIR/${base}-${width}.avif"
    fi
  done

done

echo "Optimized assets written to $OUT_DIR"