# TraitorSim3D — Audio, Animation & Polish Pass (Fable 5, standalone)

**Use with:** Claude Code on **rkb-mac**, CWD `~/Documents/Unreal Projects/TraitorSim3D`, **`claude-fable-5`**, effort **`high`**.

**Prerequisite:** `BP_CeremonyDirector` and dressing from prior sessions must be on disk. Editor open, MCP server running.

---

## Scope — four beats in order

### 1) Audio — real SoundWaves for sting + ambient
- **Sting (`SC_Sting`)**: Replace silent placeholder with a dramatic orchestral hit (2-3s). Create a `SoundCue` → import a royalty-free WAV (search UE Marketplace or generate via `Tools/generate_sting.py` if present). Wire to `BP_CeremonyDirector`'s `StingCue` var.
- **Ambient (`SC_CastleAmbient`)**: 30s loop — low wind, torch crackle, distant hall reverb. Apply to `LS_RoundTable_Wide` as an audio track, or spawn `AmbientSound` actor in `L_CastleCourt`.
- **Verify**: PIE → banish fires sting audibly. Ambient plays on game start.

### 2) Stand-up animation before banish-hide
- In `BP_CeremonyDirector`'s `OnPlayerBanished` logic:
  - Before hiding the mannequin: play a brief stand-up anim (2s) on the banished player's skeletal mesh.
  - Use a simple `Matinee`/`LevelSequence` or `PlayAnimation` node targeting the mannequin's `SKM_Manny` component.
  - If no animation asset exists: create a simple "stand from chair" blend via Control Rig → bake to anim sequence. Keep it under 3 seconds.
  - **Order**: stand-up → sting plays → camera beat → hide after 0.5s delay.

### 3) MetaHuman pass (partial — 2 key seats first)
- **Seat 0 (Host)**: Replace `SKM_Manny` with MetaHuman. Use Bridge plugin: download a "authoritative male, 40s" preset → place at Seat 0 position. Verify it's seated correctly on the existing chair.
- **Seat 1 (Key Faithful)**: Same — MetaHuman, female, 30s, "analytical" look.
- Adjust `LS_RoundTable_Wide` camera framing if needed.
- Leave remaining 10 seats as Manny for now (full MetaHuman pass is expensive).

### 4) Banish camera polish
- `LS_Banish_Close` currently does a simple cut. Enhance:
  - Add a subtle camera shake (0.3 magnitude, 0.5s) on the sting beat.
  - Add a vignette ramp during the sequence (post-process blend from 0→1 over 0.5s).
  - Seat-specific camera positions: compute the angle from `SeatAngles` array in the director; offset 200cm from mannequin's head at that angle, look-at the face.
  - If seat 0 (Host) is banished: use a special "throne empty" wide shot instead of close-up (narrative weight).

### 5) Status report
- Update `BUILD-STATUS.md` with what was done.
- Take a PIE screenshot of the MetaHuman host seated at the Round Table.
- Log any blockers (missing plugins, import failures, perf issues).

---

## Guardrails (from prior sessions' `implementation-notes.md`)

1. **One asset per `run_python_script`** — `EditorToolset` scripts that create multiple assets in one call ghost everything after the first. Create assets individually.
2. **Never `write_graph_dsl` on a freshly-created function graph** — it wipes the entry node name. Inline banish logic in the EventGraph instead of a callable function.
3. **Blueprint `Array Get` node is lazy** — accessing array elements in BP may not evaluate as expected inside a branch. Use `IsValid` guards before reading.

## Verification checklist
- [ ] Sting plays audibly on banish
- [ ] Ambient loops in PIE
- [ ] Stand-up anim plays before mannequin hide
- [ ] MetaHuman host at Seat 0, Faithful at Seat 1
- [ ] Camera shake + vignette on banish
- [ ] Seat-specific camera angles work for seats 0-11
- [ ] BUILD-STATUS.md updated
- [ ] No regressions: phase debounce, seat visibility, turret hook
- [ ] Screenshot: Saved/dressed_metahuman.png
