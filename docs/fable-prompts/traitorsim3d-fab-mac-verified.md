# Fab / MetaHuman on rkb-mac — verified 2026-07-07

Sources: Epic [Exporting Assets from Fab in Launcher](https://dev.epicgames.com/documentation/fab/exporting-assets-from-fab-in-launcher) (extracted); SSH inventory on `rkb@100.95.39.101`.

## Paths that do **not** exist on this Mac (do not scan these)

| Path | Status |
|------|--------|
| `~/Library/Application Support/Epic/UnrealEngine/Common/Fab` | **Missing** |
| `~/Library/Application Support/Epic/FabCache` | **Missing** |
| `$TMPDIR/FabLibrary` | **Not present** (cache empty or never used for in-editor add) |

## Paths that **do** exist

| Path | Purpose |
|------|---------|
| `~/Library/Application Support/Epic/FabPlugins/` | Fab export plugin payloads (`settings_v1.json`; Mac per Epic docs) |
| `~/Library/Application Support/Epic/EpicGamesLauncher/Saved/Config/MacEditor/GameUserSettings.ini` | Fab download history (`*_DownloadHistory`) |
| `~/Library/Application Support/Epic/EpicGamesLauncher/Data/Manifests/*.item` | Installed UE/Fab catalog entries (UE 5.8, FabPlugin, Quixel Bridge, MetaHuman plugins, etc.) |
| **User-chosen** download folder | Set in Launcher → Fab **gear** → **Download** tab (not stored in a single fixed path in repo scans) |

## Epic workflow (UE / MetaHuman)

1. **Acquire** in Fab in Launcher (or fab.com library).
2. **UE `.uasset` / MetaHuman listings**: not “download to disk” like FBX — use **Add to project** / **Export to Unreal** (Fab integration in UE 5.3+).
3. **Permanent project copy**: lands under **that UE project’s `Content/`** after add-to-project.
4. **In-editor Fab plugin** staging cache (when used): `${TMPDIR}/FabLibrary` (see engine `FabAssetsCache.cpp`); configurable via `Fab.ShowSettings` in editor.

## Verified on Richard’s machine

| Metric | Value |
|--------|--------|
| MetaHuman Fab listings **downloaded** (library) | **37** unique UUIDs, all `InstallType=Download`, bulk **2026-07-06 22:42–22:47** |
| Other Fab downloads in same history | **3×** `listing/fbx` |
| **Imported into TraitorSim3D** (disk) | **`Content/Grooms/`** (~733 MB), **`MH_Host`** (presenter asset), **`MH_Faithful1`** (seat 1 contestant) under `Content/TraitorSim/MetaHumans/` — **not** 37 outfit folders yet |
| Fab UE plugin | `FabPlugin_5.8` installed (DownloadHistory) |

**Conclusion:** The “30+” MetaHuman Fab items are **in your Fab library (launcher history)**, not fully **added to TraitorSim3D**. Wardrobe pass = **Fab → Add to project** (TraitorSim3D), then assign to seats via MetaHuman pipeline.

## TraitorSim relevance

| Asset class | Use |
|-------------|-----|
| **MetaHuman outfits / characters** (37 library) | Cast wardrobe after add-to-project |
| **`Content/Grooms`** | Hair/facial hair variety on MH seats |
| **FBX listings (3)** | Only if retarget/prop — not primary for MH bodies |
| **QOOBIT MetaHuman Extras** (manifest) | Check in editor if groom/accessory helpers |

## Commands (Hermes → Mac)

```bash
ssh rkb-mac 'grep -c listing/metahuman ~/Library/Application\ Support/Epic/EpicGamesLauncher/Saved/Config/MacEditor/GameUserSettings.ini'
```