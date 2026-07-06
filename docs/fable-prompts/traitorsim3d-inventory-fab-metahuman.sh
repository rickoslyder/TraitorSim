#!/usr/bin/env bash
# Run on rkb-mac — inventory Fab / MetaHuman downloads for TraitorSim3D
set -euo pipefail
PROJECT="${1:-$HOME/Documents/Unreal Projects/TraitorSim3D}"
echo "# Fab / MetaHuman inventory — $(date -Iseconds)"
echo "Project: $PROJECT"
echo

FAB_ROOTS=(
  "$HOME/Library/Application Support/Epic/FabPlugins"
  "$HOME/Library/Application Support/Epic/EpicGamesLauncher/Data/Manifests"
  "$HOME/Library/Application Support/Epic/EpicGamesLauncher/Saved/Config/MacEditor"
  "${TMPDIR:-/tmp}"
  "$PROJECT/Content"
)
# NOTE: Epic does NOT use ~/Library/.../Common/Fab on Mac. UE assets live in project Content/ after Add to Project.
# MetaHuman library download count: grep -c listing/metahuman GameUserSettings.ini (see traitorsim3d-fab-mac-verified.md)

for r in "${FAB_ROOTS[@]}"; do
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