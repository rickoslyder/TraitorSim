#!/usr/bin/env bash
# Run on rkb-mac — inventory Fab / MetaHuman downloads for TraitorSim3D
set -euo pipefail
PROJECT="${1:-$HOME/Documents/Unreal Projects/TraitorSim3D}"
echo "# Fab / MetaHuman inventory — $(date -Iseconds)"
echo "Project: $PROJECT"
echo

roots=(
  "$HOME/Library/Application Support/Epic/UnrealEngine/Common/Fab"
  "$HOME/Library/Application Support/Epic/FabCache"
  "$HOME/Library/Application Support/Epic/EpicGamesLauncher/Data/Downloads"
  "$PROJECT/Content"
  "$PROJECT/Plugins"
)

for r in "${roots[@]}"; do
  [[ -d "$r" ]] || continue
  echo "## $r"
  find "$r" -maxdepth 8 \( \
    -iname '*metahuman*' -o -iname '*MetaHuman*' -o -iname '*outfit*' -o -iname '*Outfit*' \
    -o -iname '*groom*' -o -iname '*Groom*' -o -iname '*wardrobe*' -o -iname '*Fab*' \
    \) 2>/dev/null | head -400
  echo
done

echo "## .uasset under Content/TraitorSim (top 80)"
find "$PROJECT/Content/TraitorSim" -name '*.uasset' 2>/dev/null | head -80