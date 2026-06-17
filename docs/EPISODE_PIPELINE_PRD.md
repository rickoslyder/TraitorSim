# TraitorSim → Episode Pipeline: Technical Spec & PRD

> **Status:** Draft v0.1 (for review)
> **Owner:** rickoslyder
> **Last updated:** 2026-06-17
> **Related docs:** `VOICE_INTEGRATION_DESIGN.md`, `VOICE_MODULE.md`, `architectural_spec.md`, `WORLD_BIBLE.md`

---

## 0. TL;DR

Turn a finished TraitorSim game (`reports/game_*.json`) into watchable **episodes** of *The Traitors*.

The pipeline is a **post-processing system**, fully decoupled from the simulation engine: it only ever *reads* game report JSON. It is built in **tiers** so we can validate the story cheaply before spending money on AI video:

| Tier | Name | Visual surface | Primary cost | Use |
|------|------|----------------|--------------|-----|
| **0** | **Audio-first animatic** ✅ *primary target* | Stills + Ken-Burns + Artlist B-roll, full voiced audio | ElevenLabs + Artlist | Validate story/pacing before paying for video |
| **1** | Confessional video | Tier 0 + Higgsfield lip-synced talking heads | + Higgsfield | On-genre, moderate cost |
| **2** | Hybrid tiered | Tier 1 + premium AI video on "money moments" only | + premium Higgsfield models | Balanced spectacle |
| **3** | Cinematic re-enactment | Most shots are AI video | Highest Higgsfield spend | Hero episodes / showcase |

**Decisions locked for v0.1** (from stakeholder Q&A):
- **Format:** Tier 0 (audio-first/animatic) is the build target; Tiers 1–3 are designed-for but deferred.
- **Scale:** spec the full system; budget **both** a *Pilot* (6 players / 3 days / 1 episode) and a *Full Season* (~22 players / ~12 episodes) as cost tiers.
- **Automation:** **gated, human-in-the-loop** with **budget circuit-breakers** at every paid stage.
- **Interface:** **CLI first** (`src/traitorsim/episodes/`), API-shaped so the UI can wrap it later.

---

## 1. Background & problem statement

TraitorSim already simulates a full season and emits a rich `reports/game_*.json` containing the event log, per-player personas (OCEAN + demographics + backstory), trust-matrix snapshots, votes, murders, and Game-Master narration prose. There is also a partially-built `src/traitorsim/voice/` layer (`EpisodeScript`, `DialogueScript`, `DialogueSegment`, ElevenLabs export) designed for an "Episode Mode" that was never completed end-to-end.

**What's missing to produce actual episodes:**

1. **In-character dialogue.** Agents emit structured decisions + private *reasoning*, not spoken lines. We need a synthesis layer turning "voted player_03, reasoning: …" into a dramatic, persona-consistent confessional/accusation.
2. **A visual layer.** No character reference images, no shot list, no media generation/assembly.
3. **An orchestrator.** No stage runner, no budgeting, no review gates, no resumable job queue.

This PRD specifies all three, with explicit external-service limitations and budget caps.

### 1.1 Goals

- G1. Deterministically convert any `reports/game_*.json` into a per-episode **Episode Manifest** and a rendered **`episode_NN.mp4`** (Tier 0).
- G2. Preserve *The Traitors* dramatic grammar (cold open → breakfast reveal → mission → social → Round Table → Turret → next-time teaser).
- G3. Never leak privileged information: a Traitor's public dialogue must respect the **Faithful mask** (per `CLAUDE.md`).
- G4. Make every paid action **gated, capped, cached and resumable** — no surprise bills.
- G5. Pluggable provider backends (ElevenLabs / Higgsfield / Artlist / LLM) behind clean interfaces so tiers and vendors can be swapped.

### 1.2 Non-goals (v0.1)

- N1. Real-time / live episode generation during a running game.
- N2. Modifying the simulation engine or game logic in any way.
- N3. A finished, polished UI (CLI is the v0.1 deliverable; UI is Phase 4).
- N4. Distribution/publishing (YouTube upload, etc.).
- N5. Full lip-synced cinematic video as a *guaranteed* output — Tiers 1–3 are designed but gated behind Tier 0 sign-off.

### 1.3 Success metrics

- A pilot game renders to a coherent 3–6 min Tier-0 episode in **one CLI command** (plus review gates).
- Zero ground-truth/role leaks in Faithful-visible dialogue (validated by an automated check + spot review).
- Reproducible: same input + same seed/config + cached assets ⇒ identical manifest.
- Pilot total external spend **< $25**; full-season Tier-0 spend within the caps in §10.

---

## 2. Glossary

| Term | Meaning |
|------|---------|
| **Report** | `reports/game_*.json` produced by the engine (schema in `game_state.py::to_export_dict`). |
| **Beat** | A single dramatic unit derived from one or more game events (e.g. "murder reveal"). |
| **Scene** | A group of beats mapped to a phase (breakfast/mission/social/roundtable/turret). |
| **Episode Manifest** | The canonical intermediate artifact: ordered scenes → beats → segments → shots, plus asset refs and cost ledger. |
| **Segment** | One unit of *audio* (narration / dialogue / confessional). Maps to existing `DialogueSegment`. |
| **Shot** | One unit of *video* (a few seconds): setting, on-screen character(s), camera move, bound audio segment. |
| **Asset** | A concrete media file (voice clip, still, video clip, music cue, SFX) produced by a provider. |
| **Soul ID** | Higgsfield's trained per-character identity layer for face consistency (Tiers ≥1). |
| **Circuit-breaker** | A hard cap that halts a stage when projected/actual spend exceeds budget. |

---

## 3. System context

```
┌──────────────────┐     reads      ┌─────────────────────────────────────────────┐
│  Game Engine     │  (never writes)│         Episode Pipeline (NEW)               │
│  reports/*.json  │ ─────────────► │  src/traitorsim/episodes/                    │
└──────────────────┘                │                                              │
                                    │  S1 Script  → S2 Audio → S3 ShotPlan         │
        ┌───────────────┐           │     ↓ (gate)     ↓ (gate)     ↓ (gate)       │
        │  Persona libs │ ─────────►│  S0 Cast bible / voices / Soul IDs (cached)  │
        │ data/personas │           │     ↓                                        │
        └───────────────┘           │  S4 AssetResolver → S5 Render/Assemble       │
                                    │     ↓                                        │
                                    │  reports/episodes/<game_id>/episode_NN.mp4   │
                                    └───────────────┬──────────────────────────────┘
                                                    │ (Phase 4)
                                              ┌─────▼──────┐
                                              │ TraitorSim │  "Episode Studio" tab
                                              │     UI     │  wraps the same APIs
                                              └────────────┘

External providers (via adapters): Anthropic Claude (dialogue/shot LLM),
ElevenLabs (voice/SFX/music-scratch), Artlist (licensed music/SFX/B-roll/LUTs),
Higgsfield (Soul ID + image→video + lip-sync, Tiers ≥1).
```

**Hard rule:** the pipeline imports nothing from the live engine execution path and never mutates `reports/`. It reads JSON and writes only under `reports/episodes/<game_id>/`.

---

## 4. Stakeholders & primary use cases

- **Producer (you):** runs the CLI, reviews each gate, approves spend, gets `episode_NN.mp4`.
- **Reviewer:** reads the script/shot-list at a gate, edits text, re-runs downstream.
- **(Phase 4) UI user:** triggers/monitors renders from the dashboard.

**UC-1 Pilot dry-run:** produce a Tier-0 episode from a 6-player test game for <$25 to validate story quality.
**UC-2 Full-season Tier-0:** batch all ~12 episodes of a real season into animatics within budget caps.
**UC-3 Selective upgrade:** re-render only the Round Table of episode 7 at Tier 2 without redoing the season.
**UC-4 Script edit loop:** hand-edit a confessional line, re-run audio for that segment only (cache everything else).

---

## 5. End-to-end flow (staged pipeline)

Each stage reads the previous stage's artifact, writes its own, and (if it spends money) stops at a **review gate**. All stages are independently re-runnable and content-hash cached.

### Stage 0 — Cast Bible & identities *(once per season; cached)*
- **In:** `players{}` from the report (OCEAN, demographics, backstory, archetype, strategic_profile).
- **Do:**
  - Assign each persona a stable **ElevenLabs voice** (library pick or `text-to-voice` design) → persist `voice_id`.
  - Generate a canonical **character still** (Tier 0 uses it for the animatic; Tiers ≥1 feed it to Higgsfield).
  - (Tiers ≥1) Train a **Higgsfield Soul ID** → persist `soul_id`.
- **Out:** `cast_bible.json` (per-player: voice_id, portrait path, soul_id, visual prompt seed).
- **Gate:** review voices + portraits before they propagate. **Most expensive one-time step at Tiers ≥1 — cache hard.**

### Stage 1 — Script synthesis *(LLM; cheap)*
- **In:** event log + `agent_reasoning_by_day` + cast bible + trust snapshots.
- **Do:** Walk events → **beats** → **scenes**. For each beat, generate persona-consistent text (Claude) conditioned on OCEAN traits + archetype + that player's captured reasoning. Produces narration, confessionals, Round-Table accusations/defenses, Turret scheming.
- **Faithful-mask filter (G3):** the prompt for a Traitor's *public* lines is fed only what that character may publicly know; private knowledge is allowed only in Turret/confessional segments explicitly flagged traitor-visible.
- **Out:** `EpisodeScript` per episode (reuses `voice/models.py`): scenes → `DialogueSegment[]` with `speaker_id`, `emotion_tags`, `segment_type`, `music_cue`, `sfx`.
- **Gate:** human reads/edits the script. **No paid media yet.** This is where most creative iteration happens.

### Stage 2 — Audio render *(ElevenLabs; metered)*
- **In:** approved `EpisodeScript`.
- **Do:** synthesize each segment via ElevenLabs (TTS / Text-to-Dialogue), apply emotion tags & pauses; generate **scratch** SFX/music where flagged.
- **Out:** per-segment audio files + `audio_manifest.json` (durations, credit ledger).
- **Gate + circuit-breaker:** projected character count × rate is computed *before* calling; if over the episode cap, halt.

### Stage 3 — Shot plan *(LLM; cheap, no media)*
- **In:** approved `EpisodeScript` + `audio_manifest` (for real durations).
- **Do:** convert each scene to an ordered **shot list** using the fixed "Traitors visual grammar" template. Each shot: `{shot_type, on_screen[], setting, camera_preset, audio_segment_ref, duration, render_tier}`.
- **Out:** `shot_plan.json`.
- **Gate:** review shot list & per-shot tier assignment (this determines video spend).

### Stage 4 — Asset resolution *(routing; the cost-control brain)*
- **In:** `shot_plan.json` + tier policy + budget.
- **Do:** for each shot decide the cheapest acceptable source:
  - Character/talking shot → **Higgsfield** (Tiers ≥1) **or** still+Ken-Burns (Tier 0).
  - Establishing/B-roll → **Artlist catalog** lookup (preferred) → else AI.
  - Music/SFX → **Artlist** (publishable) → else ElevenLabs scratch.
- **Out:** `asset_plan.json` with a per-shot provider + projected cost, and a **total projected cost**.
- **Gate + circuit-breaker:** present projected total; require explicit approval; refuse if over cap.

### Stage 5 — Render & assemble *(metered + ffmpeg)*
- **In:** approved `asset_plan.json`.
- **Do:** resumable job queue. For Higgsfield: submit async job, store `request_id`, await webhook or poll `GET /v2/requests/status/{request_id}`. Download Artlist assets. Then **ffmpeg**: stitch clips/stills + master audio + music + SFX + LUT → `episode_NN.mp4`.
- **Out:** `reports/episodes/<game_id>/episode_NN.mp4` + `render_ledger.json` (actual spend).
- **Gate:** final QA review.

---

## 6. Data model & artifacts

All artifacts live under `reports/episodes/<game_id>/`:

```
reports/episodes/<game_id>/
  cast_bible.json
  ep_01/
    episode_script.json      # Stage 1 (EpisodeScript)
    audio/segment_*.wav
    audio_manifest.json      # Stage 2
    shot_plan.json           # Stage 3
    asset_plan.json          # Stage 4
    media/shot_*.mp4|png
    render_ledger.json       # Stage 5
    episode_01.mp4
  cost_ledger.json           # rolling, whole-season spend across providers
  pipeline_state.json        # which stages complete/approved per episode
```

**Caching key:** every segment/shot/asset is keyed by a content hash of its inputs (text + voice_id + emotion + provider + params). Re-runs regenerate only changed items. This is what makes the edit loop (UC-4) and selective upgrade (UC-3) cheap.

**Reuse existing types:** Stage 1/2 output conforms to `src/traitorsim/voice/models.py` (`EpisodeScript`, `DialogueScript`, `DialogueSegment`, `SegmentType`, `EmotionIntensity`). New schemas (`ShotPlan`, `AssetPlan`, `CastBible`, `CostLedger`) are additive Pydantic/dataclass models in `episodes/models.py`.

---

## 7. Architecture & module layout

```
src/traitorsim/episodes/
  __init__.py
  cli.py                 # `python -m traitorsim.episodes ...`
  orchestrator.py        # stage runner, gating, state machine, resume
  budget.py              # CostLedger, circuit-breakers, projections
  models.py              # CastBible, ShotPlan, AssetPlan, CostLedger (+ reuse voice/models.py)
  loader.py              # read+validate reports/*.json (versioned)
  stage0_cast.py
  stage1_script.py       # LLM dialogue synth + Faithful-mask filter
  stage2_audio.py
  stage3_shotplan.py     # "Traitors visual grammar" templates
  stage4_assets.py       # AssetResolver routing
  stage5_render.py       # job queue + ffmpeg assembly
  providers/
    base.py              # VoiceProvider, VideoProvider, CatalogProvider, LLMProvider, ImageProvider (ABCs)
    elevenlabs.py
    higgsfield.py        # async/webhook client (Tiers ≥1)
    artlist.py
    anthropic_llm.py
    null.py              # offline/dry-run stub (returns silent audio / placeholder frames, zero cost)
  templates/
    visual_grammar.yaml  # shot patterns per phase
    dialogue_prompts/    # per segment_type prompt templates
```

**Provider abstraction (key to swappability & testability):** every paid provider implements an ABC and reports `estimate_cost(request)` *before* `execute(request)`. A `null` provider lets the entire pipeline run offline at zero cost for development and CI.

**CLI surface (Phase 1):**
```bash
python -m traitorsim.episodes plan   --report reports/game_X.json --tier 0      # stages 0,1,3 (no spend)
python -m traitorsim.episodes audio  --game X --ep 1 --max-credits 30000        # stage 2 (gated)
python -m traitorsim.episodes assets --game X --ep 1                            # stage 4 (projection)
python -m traitorsim.episodes render --game X --ep 1 --confirm                  # stage 5 (gated)
python -m traitorsim.episodes status --game X                                   # pipeline_state
python -m traitorsim.episodes cost   --game X                                   # cost_ledger
```
The orchestrator functions are the API the Phase-4 UI will call directly.

---

## 8. Human-in-the-loop gating & budget circuit-breakers

- **Gate model:** each stage writes its artifact and sets `pipeline_state.json[ep][stage] = "awaiting_review"`. Downstream stages refuse to run until the upstream is `approved`. Approval is `--confirm` on the CLI (later: a UI button).
- **Two-phase spend:** every paid stage first computes a **projection** (`estimate_cost`) and prints it; it executes only on explicit confirm AND if under the cap.
- **Circuit-breakers (configurable, hard fails):**
  - `per_segment_max_credits`, `per_episode_max_credits`, `per_season_max_usd`.
  - Provider-level monthly cap mirrors (don't exceed the plan we bought).
  - On breach: stop, write partial ledger, exit non-zero, print exactly what would have been spent.
- **Idempotency:** re-running a confirmed stage is a no-op if cache hits; `--force` to override.
- **Dry-run default:** `--dry-run` (and the `null` provider) prints projected costs for the whole season without spending a cent.

---

## 9. External services — capabilities, **limitations/restrictions**, and pricing

> ⚠️ Pricing and limits below are as researched **June 2026** and **must be re-verified at build time** — these vendors change plans frequently. Treat all figures as planning estimates, not contractual.

### 9.1 Anthropic Claude (dialogue & shot-plan LLM) — Stages 1, 3
- **Role:** generate confessional/accusation/narration text and the shot plan.
- **Limitations:** standard token rate limits; must enforce the **Faithful-mask** in-prompt (model won't know game secrets unless we feed them — feature, not bug); output must pass the `world-bible-validator` (no real-world brand leakage, in-universe lore only).
- **Cost:** token-based, **low** relative to media. A full season's scripts ≈ low tens of dollars at most. Cap via a token budget per episode.

### 9.2 ElevenLabs (voice, SFX, scratch music) — Stage 2, Stage 0 voices
- **Capabilities:** TTS (`eleven_v3`, `eleven_multilingual_v2`, `eleven_flash_v2_5`), Text-to-Dialogue (multi-speaker), voice design from text, voice cloning, AI SFX, music; 10,000+ voice library. Async + streaming API. **Already the target of `voice/` layer.**
- **Limitations / restrictions:**
  - **Credit = ~1 character** of text for standard TTS; `v3` and higher-quality paths can consume more per character — **verify multiplier per model**.
  - **Voice cloning gating:** Professional Voice Cloning requires **Creator tier ($22/mo) or above**.
  - **Commercial rights / attribution** vary by tier — confirm the plan grants commercial use for published episodes.
  - **Voice likeness/consent:** cloned/celebrity-like voices are prohibited without consent; we use **synthetic designed voices** for personas to stay clean.
  - Rate limits + max characters per request → must **chunk** long narration.
  - Generated audio is **non-deterministic**; cache the *output*, not just the request.
- **Pricing (monthly, 2026):** Free 10k cr · Starter $6/30k · **Creator $22/121k** · **Pro $99/500k** · Scale $299/2M · Business $990/11M. Overage on Creator ≈ $0.30 / 1k chars (drops to $0.12 at Business). Annual ≈ −17%.
- **Rule of thumb:** ~1,000 credits ≈ ~1 minute of speech (≈150 words). So **Creator ≈ ~2 hours/mo**, **Pro ≈ ~8 hours/mo** of finished audio.

### 9.3 Higgsfield (Soul ID, image→video, lip-sync) — Stages 0, 5 (**Tiers ≥1 only**)
- **Capabilities:** Image-to-Video, Soul ID character consistency (≈20 photos, 3–5 min train), DoP/cinematic presets (50–70+ camera moves), Talking Avatar + lip-sync / Speech-to-Video, multi-model broker (Veo 3.1, Sora 2, Kling 3.0, Seedance 2.0, WAN 2.6, Hailuo). Official **Node/TS SDK** + REST v2; **async webhook** pattern (`GET /v2/requests/status/{request_id}`).
- **Limitations / restrictions:**
  - **Clips are short** (seconds) — an episode is an *assembly* of many shots, not one render. This is the core architectural constraint.
  - **Credit-metered, non-trivial per clip:** basic 15–25 cr, **premium (Sora 2 / Veo 3.1) 40–70 cr**, images 0.25–5 cr.
  - **Plan credit ceilings are low vs. our needs:** Starter $15/200 · Plus $39/1,000 · Ultra $99/3,000 cr/mo → a cinematic season needs **credit packs or many months** (see §10).
  - **Async latency & failure modes:** jobs can queue/fail; need retry + resume + `request_id` persistence.
  - **Consistency isn't perfect** even with Soul ID — expect retries (budget for ~15–25% reroll waste).
  - **Content/likeness policy:** no real-person likeness without rights; personas must be synthetic. Re-verify ToS on commercial use & AI-content labeling.
  - **No official Python SDK** confirmed (Node/TS) — we wrap the REST API directly in `providers/higgsfield.py`.
- **Pricing (monthly, 2026):** Starter $15/200cr · Plus $39/1,000cr · Ultra $99/3,000cr; annual billing applies.

### 9.4 Artlist (licensed music, SFX, B-roll, LUTs, AI suite) — Stage 4/5 finishing
- **Capabilities:** licensed music/SFX/8K stock footage/templates/LUTs; **Clearlist** Content-ID protection; license certificates & cue sheets; Premiere extension; AI Suite (voiceover/image/video) + **Studio** (character-consistent AI video, spring 2026).
- **Why it's here:** the only source of **copyright-cleared** music/SFX/B-roll → keeps published episodes free of takedowns/strikes. Neither ElevenLabs nor Higgsfield provides licensing cover.
- **Limitations / restrictions:**
  - **License is tied to an active subscription** for newly-published content — content published while subscribed stays licensed "forever," but **lapsing mid-production is risky**; keep the sub active across a release.
  - AI generations consume **credits** that renew monthly; catalog vs. AI are **different plan axes**.
  - **No first-class automation API** for the catalog comparable to Higgsfield's — Studio/extension are GUI-oriented; treat Artlist as **assisted/manual** in v0.1 (resolver emits a "fetch list" for a human, or uses any available download endpoint). **Do not assume headless catalog API.**
  - Studio overlaps Higgsfield but is not the programmatic webhook pipeline we need for automation → use Higgsfield for automated video, Artlist for licensed assets/finishing.
- **Pricing (2026, annual):** AI Starter from ~$13.99/mo (7,500 cr, scaling to 120k) · AI Professional from ~$99.99/mo (180k cr) · **Max from ~$89.99/mo annual (~$149.99 monthly)** = catalog + all AI + Studio. Annual ≈ −40% vs monthly.

---

## 10. Cost model & budget caps

### 10.1 Cost drivers
1. **Audio minutes** (ElevenLabs) — scales with total dialogue length.
2. **Video shots** (Higgsfield, Tiers ≥1) — scales with shot count × model tier × reroll waste.
3. **Soul ID training** (Higgsfield, Tiers ≥1) — one-off per cast member.
4. **Licensed assets** (Artlist) — flat subscription during production.
5. **LLM tokens** (Claude) — small.

### 10.2 Worked estimates

Assumptions: ~1,000 ElevenLabs credits/min of speech; basic Higgsfield clip ~20cr, premium ~55cr; ~20–25% reroll waste; clip ≈ 5s ⇒ ~12 shots/finished-minute.

#### Pilot (6 players, 3 days, ~1 episode, ~4 min)
| Item | Tier 0 | Tier 1 (confessional) |
|------|--------|------------------------|
| Audio (~4 min ≈ 4k cr) | Starter $6 covers it | same |
| LLM scripts/shots | ~$1–3 | ~$1–3 |
| Soul IDs (6 cast) | — | included in Higgsfield plan |
| Video (~50 shots ×20cr ×1.25 ≈ 1,250cr) | — (stills only) | Plus $39 / Ultra $99 |
| Artlist (1 month, optional) | $14 (AI Starter) | $14 |
| **Pilot total** | **≈ $20** ✅ (<$25 target) | **≈ $60–120** |

#### Full season (~22 players, ~12 episodes)
Assume ~25 min finished audio/episode ⇒ ~300 min/season ⇒ ~300k ElevenLabs credits.

| Item | Tier 0 (target) | Tier 1 | Tier 3 (cinematic) |
|------|-----------------|--------|---------------------|
| Audio (~300k cr) | **Pro $99** (1 month) | Pro $99 | Pro $99 |
| LLM | ~$10–30 | ~$10–30 | ~$20–50 |
| Soul IDs (22 cast) | — | within Higgsfield plan | within plan |
| Video shots | — | ~12 ep × ~120 talking shots ≈ 1,440 shots ×20cr ×1.25 ≈ **36,000 cr** | ~12 ep × ~180 shots ≈ 2,160 ×55cr ×1.25 ≈ **148,500 cr** |
| Higgsfield $ (≈ Ultra $99/3,000cr ≈ $0.033/cr) | — | ~36k cr ⇒ **~$1,200** (credit packs / multi-month Ultra) | ~148k cr ⇒ **~$4,900** |
| Artlist (production months) | Max ~$90–150/mo × ~2 mo ≈ $180–300 | same | same |
| **Season total (rough)** | **≈ $300–450** | **≈ $1,500–2,000** | **≈ $5,000–6,500** |

> The video tiers are where cost explodes. This is exactly why Tier 0 is the build target and Tiers ≥1 sit behind a gate. **Verify Higgsfield credit-pack pricing before committing — per-credit cost on packs may differ materially from the subscription ratio used above.**

### 10.3 Recommended budget caps (defaults in `budget.py`)
- `per_episode_max_credits.elevenlabs = 40_000` (~40 min audio safety).
- `per_episode_max_credits.higgsfield = 3_000` (≈ one Ultra month/episode ceiling).
- `per_season_max_usd`: **Pilot $30 · Tier-0 season $500 · Tier-1 $2,000 · Tier-3 $7,000** — pipeline hard-stops at the configured value.
- Default run mode = **dry-run**; spending requires `--confirm` and a configured cap.

---

## 11. Licensing, legal & content safety

- **Synthetic identities only.** Personas, voices, and faces are AI-generated; no real-person likeness or voice cloning without consent (ElevenLabs & Higgsfield ToS).
- **AI-content disclosure.** Plan to label episodes as AI-generated per platform rules (and likely Higgsfield/ElevenLabs ToS).
- **Music/SFX licensing.** Publishable music/SFX come from **Artlist** with retained license certificates; keep the subscription active across release. AI-generated music is **scratch-only** unless its ToS explicitly grants commercial publishing rights — verify per provider.
- **Brand safety.** All generated text passes `world-bible-validator` (no real-world brands; in-universe lore only, e.g. Ardross Castle).
- **Format trademark.** "The Traitors" is a TV format/trademark — for any public release, treat output as parody/fan-work and seek guidance before commercial distribution.
- **Data retention.** Reports may contain rich persona data; episode artifacts inherit it — keep under existing `reports/` handling.

---

## 12. Phasing & milestones

- **Phase 0 — Foundations:** `episodes/` package skeleton, `loader.py` (+ report schema versioning), `models.py`, provider ABCs, `null` provider, `budget.py`, `cost_ledger`. *Exit: full pipeline runs offline at $0 producing placeholder output.*
- **Phase 1 — Tier 0 vertical slice (Pilot):** Stages 0(voices/stills)→1→2→3→5 for the 6-player test game; real ElevenLabs audio; ffmpeg animatic. *Exit: UC-1 pilot episode < $25.*
- **Phase 2 — Tier 0 full season:** batch all episodes; Artlist licensed music/SFX integration; gating/circuit-breakers hardened. *Exit: UC-2 within Tier-0 cap.*
- **Phase 3 — Tiers 1–2 (video):** Higgsfield adapter (Soul ID + image→video + lip-sync), AssetResolver routing, reroll handling. *Exit: UC-3 selective upgrade works.*
- **Phase 4 — UI "Episode Studio":** wrap orchestrator APIs in `traitorsim-ui` (trigger, gate-approve, cost dashboard, preview).
- **Phase 5 (optional) — Tier 3 cinematic & polish.**

---

## 13. Risks & mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Vendor pricing/limits drift | Budget blowout | Re-verify at build; `estimate_cost` before every spend; hard caps |
| Higgsfield clip inconsistency | Reroll cost, jarring cuts | Soul ID; budget reroll waste; Tier-0 fallback to stills |
| Dialogue leaks role/secret | Breaks the game's integrity | Faithful-mask prompt filter + automated leak check at Stage 1 gate |
| Async render failures | Stuck pipeline | Resumable job queue, `request_id` persistence, retries |
| Artlist has no headless API | Manual toil | Treat as assisted; resolver emits fetch-list; revisit if API appears |
| Non-deterministic media | Non-reproducible | Cache *outputs* by input hash; pin seeds where supported |
| Long audio chunking errors | Garbled narration | Sentence-aware chunking + stitch with crossfades |

---

## 14. Open questions

1. **Episode length / count** for a "full season" — confirm target minutes/episode (drives the audio budget directly).
2. **Publishing intent** — internal showcase vs. public release? (Changes the licensing/trademark posture in §11.)
3. **Higgsfield credit-pack** real per-credit price — confirm before approving any video tier.
4. **Artlist plan choice** — Max (catalog+AI) vs. catalog-only (we use ElevenLabs for AI audio anyway).
5. **Music strategy** — Artlist licensed throughout, or AI-scratch for drafts + Artlist only on final cut?
6. **Determinism expectations** — is "same manifest, cached media" sufficient, or do we need frame-level reproducibility (likely impossible with these vendors)?

---

## 15. Appendix — source report fields consumed

From `game_state.py::to_export_dict` / `types/game.ts`:
`players{}` (id, name, role, alive, archetype, backstory, strategic_profile, demographics, personality OCEAN, stats) · `events[]` (day, phase, type, actor, target, narrative, data) · `trust_snapshots[]` · `vote_history[]` · `breakfast_order_history[]` · `murdered_players/banished_players/recruited_players` · `agent_reasoning_by_day` (vote/murder/dilemma reasoning) · `winner`, `prize_pot`, `rule_variant`, `config`.

Reused voice types from `voice/models.py`: `EpisodeScript`, `DialogueScript`, `DialogueSegment`, `SegmentType`, `EmotionIntensity`.
