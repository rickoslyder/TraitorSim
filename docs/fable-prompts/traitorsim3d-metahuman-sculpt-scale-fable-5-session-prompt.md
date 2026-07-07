# TraitorSim3D — MetaHuman sculpt + scale (Fable 5)

**CWD:** `~/Documents/Unreal Projects/TraitorSim3D` · `claude-fable-5` · effort `high`  
**Style:** Goal-oriented — you choose the steps.

---

## COPY FROM HERE ↓

# End goal

**Hero faces:** **presenter host** (`MH_Host` / `HostActor`) and **contestant seat 1** (`MH_Faithful1`) read as specific UK adults—not stock archetypes. **Seat 0** stays contestant (Manny unless you deliberately swap). MetaHuman banish believable on MH seats; host is **not** banished.

**Done when:** `BUILD-STATUS.md` / `implementation-notes.md` updated with seat coverage table, sculpt/rig time notes, anim paths for MH banish, viewport evidence for 0–1, and honest recommendation for seats 4–11 (MH vs mannequin + outfit).

**Why:** Manny death anim skips on MH skeleton today; mannequins on 2+ break immersion; cloud rig budget is real.

---

## Ground truth

- `Content/Python/mh_build.py` patterns + Creator plugin Python examples.
- Brief: **host** presenter male ~40s authoritative; **seat 1** female ~30s sharp/analytical **contestant**. `BUILD-STATUS.md` § Host rework — do not conflate host with seat 0.
- Keep existing `SeatActors` / banish Blueprint wiring — swap bodies/faces, don’t redesign ceremony.
- `Content/Grooms/` for hair; extend `mh_build.py` CLI if that’s the cleanest automation.

---

## Boundaries

- No lip sync, voice face, mocap, API/backend.
- Perf: note PIE FPS if you add grooms/MH count.

---

## Close-out

TLDR: seats done vs planned, cloud minutes, anim assets, next slice for Richard.

## COPY TO HERE ↑