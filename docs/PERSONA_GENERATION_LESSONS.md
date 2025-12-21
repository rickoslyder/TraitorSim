# Persona Generation Pipeline - Lessons Learned

## Overview
Documentation of best practices from successfully generating 6 high-quality personas using the Deep Research + Claude synthesis pipeline.

## What Worked ✅

### 1. Deep Research API Configuration
**Correct parameters:**
```python
interaction = client.interactions.create(
    agent="deep-research-pro-preview-12-2025",  # NOT "deep-research"
    input=prompt,  # Include instructions IN the prompt, not system_instruction
    background=True,  # Required for Deep Research (10-20 min jobs)
    store=True,  # Required for background jobs
    # NO model parameter - agents don't use it
    # NO system_instruction - not supported by Deep Research
)
```

**Key lessons:**
- Agent ID must be exact: `deep-research-pro-preview-12-2025`
- Cannot use `model` parameter with agents
- Cannot use `system_instruction` - put all instructions in the `input` prompt
- Must use `background=True` and `store=True` for jobs exceeding timeout limits
- File search with Deep Research isn't documented/supported - apply World Bible constraints in Claude synthesis instead

### 2. Claude Agent SDK for Synthesis
**Batch synthesis approach (CRITICAL):**
- Use a **single query** to generate all personas at once, not sequential queries
- Sequential queries caused asyncio lifecycle issues with SDK subprocess management
- Batch approach: one long-running agent context instead of repeated create/destroy cycles

**Working pattern:**
```python
async def synthesize_batch_single_query(reports: list, model: str):
    # Build ONE prompt with ALL persona contexts
    prompt = build_batch_prompt_with_all_skeletons(reports)

    # Single query produces all personas
    async for message in query(prompt=prompt, options=options):
        # Collect full response
        ...

    # Parse JSON array of all personas
    personas = json.loads(response_text)
    return personas
```

**Why this works:**
- SDK maintains one continuous context
- No asyncio cancel scope issues
- Cleaner subprocess lifecycle
- Faster overall (one API call vs many)

### 3. Authentication
**Use Claude Agent SDK with CLAUDE_CODE_OAUTH_TOKEN:**
- The Anthropic SDK doesn't support OAuth tokens (only API keys)
- Claude Agent SDK automatically detects `CLAUDE_CODE_OAUTH_TOKEN` from environment
- Consistent with the main simulator's authentication approach

### 4. World Bible Brand Validation
**Word boundary detection:**
```python
import re

def detect_forbidden_brands(text: str) -> List[str]:
    detected = []
    for brand in FORBIDDEN_BRANDS:
        pattern = r'\b' + re.escape(brand) + r'\b'
        if re.search(pattern, text.lower()):
            detected.append(brand)
    return detected
```

**Why this matters:**
- Prevents false positives like "pret" matching "pretend"
- Only detects actual brand mentions, not substrings

### 5. Backstory Length Validation
**Adjusted limits:**
- Original: 1000 chars max (too restrictive)
- Updated: 1600 chars max
- Reasoning: 200-300 words ≈ 1200-1800 chars; allowing 1600 accommodates natural variation

### 6. Prompt Design for Synthesis
**Effective constraints:**
```
**Critical Constraints:**
1. **In-Universe Brands ONLY**: Highland Spring Co., Cairngorm Coffee, ScotNet, etc.
2. **FORBIDDEN**: Facebook, Twitter, Starbucks, Costa, Tesco, Google, Amazon, etc.
3. Reflect Deep Research findings
4. Cultural authenticity to UK context
5. Specific details - "plays 5-a-side at Victoria Park" not "enjoys sports"
6. Backstory in FIRST PERSON
7. Reference real UK places/neighborhoods
```

**Key insight:** Explicit brand lists (both allowed and forbidden) in the prompt worked better than relying on file_search grounding.

### 7. Deep Research Quality
**What we got:**
- 20-28KB reports per persona
- Rich demographic context with citations
- Authentic UK cultural details (accents, locations, financial situations)
- Grounded in real data (housing costs, salaries, political shifts)

**Example citations from reports:**
- Regional salary data for IT support in Midlands
- Black Country dialect phrases ("yam", "bostin'")
- Specific locations (Stourbridge Junction, Portobello beach)
- Cost of living data (council tax, rent, pint prices)

## What Didn't Work ❌

### 1. Sequential SDK Queries
**Anti-pattern:**
```python
for skeleton in skeletons:
    persona = await synthesize_persona(skeleton)  # BAD
```

**Problem:** Each query creates/destroys SDK subprocess → asyncio scope errors

### 2. Anthropic SDK with OAuth
**Attempted:**
```python
client = Anthropic(auth_token=oauth_token)  # FAILS
```

**Error:** "OAuth authentication is currently not supported"

**Solution:** Use Claude Agent SDK instead

### 3. Tight Validation Limits
**Original:** 1000 char backstory limit → all personas failed validation
**Fixed:** 1600 char limit aligns with 200-300 word spec

### 4. Substring Brand Detection
**Original:** `if "pret" in text.lower()` → matched "pretend"
**Fixed:** Word boundary regex `\bpret\b`

## Pipeline Architecture

### Proven 5-Stage Process
1. **Skeleton Generation** (`generate_skeleton_personas.py`)
   - Sample OCEAN traits from archetype ranges
   - Generate demographic templates
   - Output: `skeletons/test_batch_001.json`

2. **Deep Research Submission** (`batch_deep_research.py`)
   - Submit background jobs to Gemini Deep Research agent
   - 10-20 min per job
   - Rate limit: 10 jobs/min (we hit quota after ~6 jobs)
   - Output: `jobs/test_batch_001_jobs.json`

3. **Job Polling** (`poll_research_jobs.py`)
   - Poll every 30s until completion
   - Retrieve completed reports
   - Output: `reports/test_batch_001_reports.json`

4. **Claude Synthesis** (`synthesize_backstories.py`)
   - **Batch mode**: Single query for all personas
   - Use Claude Opus 4.5 for narrative quality
   - Apply World Bible constraints
   - Output: `library/test_batch_001_personas.json`

5. **Validation** (`validate_personas.py`)
   - Check brand leakage (word boundaries)
   - Verify backstory length (200-1600 chars)
   - Ensure required fields present
   - Check archetype distribution

## Cost Analysis (Test Batch)

**15 Personas Generated (FINAL):**
- Deep Research: ~$0.35 × 15 = **$5.25**
- Claude Opus 4.5 synthesis (5 batches): **~$1.50** (batch API calls)
- **Total: ~$6.75**

**Per-persona cost:** ~$0.45

**Projected for 100 personas:**
- Deep Research: $35
- Claude synthesis: $10-15 (depending on batch sizes)
- **Total: ~$45-50**

**Cost breakdown:**
- Deep Research dominates cost (~75% of total)
- Claude Opus 4.5 synthesis is ~25% of cost
- Using Sonnet 4.5 instead would reduce synthesis cost by ~66% but may reduce quality

## Quality Metrics

**Test Batch Results (15 personas - FINAL):**
- ✅ 100% validation pass rate
- ✅ 0 brand leaks detected
- ✅ All backstories 200-1600 chars (within spec)
- ✅ Authentic UK regional details across 10+ locations (London, Edinburgh, Glasgow, Bristol, Manchester, Northern England, Midlands, etc.)
- ✅ Specific hobbies and cultural markers (wild swimming, Reformer Pilates, Blood on the Clocktower, pub quiz teams, etc.)
- ✅ First-person narrative voice throughout
- ✅ Consistent in-universe brand usage (Cairngorm Coffee, ScotNet, Highland Spring, CastleVision)
- ✅ Deep Research reports 20-28KB each with extensive citations

**Final archetype distribution (perfectly balanced):**
- The Bitter Traitor: 2
- The Incompetent Authority Figure: 2
- The Charming Sociopath: 2
- The Comedic Psychic: 2
- The Mischievous Operator: 2
- The Prodigy: 1
- The Misguided Survivor: 1
- The Quirky Outsider: 1
- The Romantic: 1
- The Charismatic Leader: 1

**Notable personas:**
- Darren Whitmore (Bitter Traitor) - IT support, Midlands with Black Country dialect
- Rowan Achebe-Campbell (Prodigy) - Mixed-race psychologist, Edinburgh
- Gemma Ashworth-Clarke (Charismatic Leader) - Motivational speaker, Parsons Green London
- Siobhan Mallory (Mischievous Operator) - Professional poker player, Bristol
- Robin Hartley (Bitter Traitor) - Non-binary accountant, Northern England

## Recommendations for Scale-Up

### To Generate 100+ Personas:

1. **Batch size:** Process in batches of 15-20 to manage quota limits
2. **Synthesis:** Use batch mode (single query) for each batch of completed reports
3. **Model choice:** Opus 4.5 for quality vs Sonnet 4.5 for cost (~3x cheaper)
4. **Timing:** Deep Research jobs can run overnight; synthesis is ~2-3 min per batch
5. **Validation:** Run after each batch to catch issues early

### Quality Assurance:
- Manually review 10% of personas for authenticity
- Check for repeated phrases across personas (ensure uniqueness)
- Verify archetype diversity (no more than 2 per archetype in 10-player games)

## Session 2 Updates: Incremental Generation (Dec 21, 2024)

### New Lessons Learned

**7. Incremental Synthesis is Critical**
- **Anti-pattern:** Re-synthesizing already-completed personas
- **Correct approach:**
  ```python
  # Load existing personas
  existing_personas = json.load(open('library/personas.json'))
  existing_ids = {p['skeleton_id'] for p in existing_personas}

  # Filter to only NEW reports
  new_reports = [r for r in all_reports if r['skeleton_id'] not in existing_ids]

  # Synthesize ONLY new ones
  synthesize_batch(new_reports)

  # Merge with existing library
  all_personas = existing_personas + new_personas
  ```

**Why this matters:** Avoided wasting ~$0.90 in tokens by not re-synthesizing 6 already-complete personas.

**8. Quota Management Strategy**
- Gemini Deep Research quota resets allow ~2-6 jobs per submission attempt
- Strategy: Submit in waves, wait for completions, then retry quota-limited jobs
- Pattern observed:
  - Wave 1: 6 jobs succeeded before quota
  - Wave 2: 4 jobs succeeded
  - Wave 3: 2 jobs succeeded
  - Remaining: 3 jobs awaiting quota reset

**9. Polling Script Behavior**
- Jobs showing as "processing" even when completed is expected
- The poller correctly retrieves reports and updates the jobs file
- "Job failed" poll_error for old jobs is harmless - reports were already manually retrieved
- Key: Check jobs file for `report` field, not just poller output

**10. Deep Research Completion Time**
- **Observed:** Most jobs completed in 10-15 minutes
- **Range:** 10-30 minutes depending on complexity
- **Planning:** Budget 20 minutes per batch for safety

**11. Deep Research Quota Limits (December 2025)**

**Current Status:**
- Deep Research agent is in **preview** - specific quota limits are not publicly documented
- Agent ID: `deep-research-pro-preview-12-2025` (powered by Gemini 3 Pro)
- **Maximum research time:** 60 minutes per task
- **Google Search tool:** Free until January 5th, 2026

**General Gemini API Rate Limits (as of December 7, 2025):**
- Rate limits apply **per project**, not per API key
- Measured across: RPM (requests/min), TPM (tokens/min), RPD (requests/day)
- RPD quotas reset at midnight Pacific time

**Free Tier Limits:**
- Gemini 2.5 Flash: 15 RPM, 250K TPM, 250 RPD
- Gemini 2.5 Pro: 5 RPM, 250K TPM, 100 RPD

**Our Observed Pattern:**
- Wave 1: 6 successful Deep Research submissions before quota
- Wave 2: 4 successful submissions
- Wave 3: 2 successful submissions
- Wave 4: 2 successful submissions
- Pattern suggests progressive quota tightening or time-based reset

**12. Programmatic Quota Checking**

**Problem:** Gemini API does not provide direct methods or response headers to check remaining quota.

**Solution 1: Client-Side Tracking (Recommended)**
```python
from datetime import datetime, timedelta
from collections import deque

class QuotaTracker:
    def __init__(self, rpm_limit=10, rpd_limit=100):
        self.rpm_limit = rpm_limit
        self.rpd_limit = rpd_limit
        self.minute_requests = deque()
        self.daily_requests = deque()

    def can_make_request(self) -> bool:
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)

        # Clean old requests
        while self.minute_requests and self.minute_requests[0] < minute_ago:
            self.minute_requests.popleft()

        return (len(self.minute_requests) < self.rpm_limit and
                len(self.daily_requests) < self.rpd_limit)

    def record_request(self):
        now = datetime.now()
        self.minute_requests.append(now)
        self.daily_requests.append(now)
```

**Solution 2: Exponential Backoff (Error Handling)**
```python
import time
import random

def submit_with_backoff(client, prompt, max_retries=5):
    for attempt in range(max_retries):
        try:
            interaction = client.interactions.create(
                agent="deep-research-pro-preview-12-2025",
                input=prompt,
                background=True,
                store=True
            )
            return interaction
        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                if attempt == max_retries - 1:
                    raise

                # Exponential backoff with jitter
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                print(f"Quota exceeded, waiting {wait_time:.2f}s...")
                time.sleep(wait_time)
            else:
                raise
```

**Solution 3: Google Cloud Quotas API (For GCP Projects)**
```bash
pip install google-cloud-quotas
```

```python
from google.cloud import cloudquotas_v1

def check_quotas(project_id: str):
    client = cloudquotas_v1.CloudQuotasClient()
    parent = f"projects/{project_id}/locations/global/services/generativelanguage.googleapis.com"

    request = cloudquotas_v1.ListQuotaInfosRequest(parent=parent)
    for quota_info in client.list_quota_infos(request=request):
        print(f"Quota: {quota_info.name}")
```

**Where to Check Quotas:**
- [AI Studio Usage Dashboard](https://aistudio.google.com/usage?timeRange=last-28-days&tab=rate-limit)
- Google Cloud Console → IAM & Admin → Quotas & System Limits

**References:**
- [Gemini API Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Deep Research Documentation](https://ai.google.dev/gemini-api/docs/deep-research)
- [Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
- [Cloud Quotas API](https://cloud.google.com/docs/quota)

### Progress Update

**✅ COMPLETE - All 15 Personas Generated (December 21, 2024)**

**Final Status:**
- ✅ Batch 1: 6 personas (skeleton_000, 001, 007, 008, 013, 014)
- ✅ Batch 2: 4 personas (skeleton_002, 003, 011, 012)
- ✅ Batch 3: 2 personas (skeleton_004, 005)
- ✅ Batch 4: 2 personas (skeleton_006, 009)
- ✅ Batch 5: 1 persona (skeleton_010)

**Final Cost Tracking:**
- Batch 1 (6 personas): ~$2.70
- Batch 2 (4 personas): ~$1.80
- Batch 3 (2 personas): ~$0.90
- Batch 4 (2 personas): ~$0.90
- Batch 5 (1 persona): ~$0.45
- **Grand Total: ~$6.75 for 15 complete personas**
- **Final per-persona cost: $0.45**

### Final Archetype Distribution (15 complete)

- The Bitter Traitor: 2
- The Incompetent Authority Figure: 2
- The Charming Sociopath: 2
- The Comedic Psychic: 2
- The Mischievous Operator: 2
- The Prodigy: 1
- The Misguided Survivor: 1
- The Quirky Outsider: 1
- The Romantic: 1
- The Charismatic Leader: 1

**All 15 personas passed validation:**
- ✅ 0 brand leaks detected
- ✅ All backstories within 200-1600 char range
- ✅ Complete demographics and UK authenticity
- ✅ In-universe brand usage (Highland Spring, Cairngorm Coffee, ScotNet, CastleVision)
- ✅ First-person narrative voice
- ✅ Specific hobbies and cultural details

## Next Steps

1. ✅ Complete all 15 personas in test batch
2. ✅ Validate complete 15-persona library
3. ⏭️ Test integration with game simulator
4. ⏭️ Scale to 100+ personas for production deployment
5. ⏭️ Implement quota tracking in batch_deep_research.py using QuotaTracker class
6. ⏭️ Add exponential backoff retry logic for quota errors

## Files Reference

**Scripts:**
- `scripts/generate_skeleton_personas.py`
- `scripts/batch_deep_research.py`
- `scripts/poll_research_jobs.py`
- `scripts/synthesize_backstories.py`
- `scripts/validate_personas.py`
- `scripts/generate_persona_library.sh` (orchestrator)

**Data:**
- `data/personas/skeletons/test_batch_001.json` (15 skeletons)
- `data/personas/jobs/test_batch_001_jobs.json` (15 job records with reports)
- `data/personas/reports/test_batch_001_reports.json` (15 completed Deep Research reports)
- `data/personas/library/test_batch_001_personas.json` (15 final validated personas)

**Core modules:**
- `src/traitorsim/core/archetypes.py` (archetype definitions)
- `src/traitorsim/utils/world_flavor.py` (brand validation)
- `src/traitorsim/persona/persona_loader.py` (runtime loading)

---

## Summary & Key Takeaways

### What We Accomplished
✅ **Successfully generated 15 high-quality personas** using Gemini Deep Research + Claude Opus 4.5
✅ **100% validation pass rate** with zero brand leaks
✅ **Total cost: ~$6.75** ($0.45 per persona)
✅ **Pipeline validated** and ready for scale-up to 100+ personas

### Critical Success Factors
1. **Batch synthesis approach** - Single query per batch eliminated asyncio issues
2. **Incremental generation** - Only synthesize new personas, merge with existing
3. **Exponential backoff** - Handle quota limits gracefully with retries
4. **Client-side quota tracking** - API doesn't provide quota status, track locally
5. **Word boundary brand detection** - Prevent false positives in validation
6. **Claude Agent SDK with OAuth** - Proper authentication for Claude Code subscriptions

### Quota Management Insights
- Deep Research quota limits are **not publicly documented**
- Observed pattern: 2-6 jobs per submission wave before quota exhaustion
- Quotas reset at **midnight Pacific time** (RPD dimension)
- Rate limits apply **per project**, not per API key
- No programmatic API to check remaining quota - must track client-side

### Cost Optimization Options
- **Deep Research**: 75% of cost (~$0.35/persona) - no alternative
- **Synthesis**: 25% of cost (~$0.10/persona with Opus 4.5)
  - Switch to Sonnet 4.5: ~$0.03/persona (66% savings, possible quality trade-off)
  - Projected 100 personas: $35 (research) + $10-15 (synthesis) = **$45-50 total**

### Production Readiness Checklist
- [x] 15-persona test batch complete and validated
- [x] Documentation of lessons learned
- [x] Quota tracking and backoff strategies documented
- [ ] Implement QuotaTracker class in batch_deep_research.py
- [ ] Add exponential backoff to production scripts
- [ ] Test game integration with 15-persona library
- [ ] Scale to 100 personas for full deployment

### Timeline for 100 Personas
- **Deep Research**: 15-20 batches × 20 min/batch = **5-7 hours** (can run overnight)
- **Synthesis**: 10 batches × 2-3 min/batch = **20-30 minutes**
- **Validation**: 5 minutes
- **Total elapsed time**: ~6-8 hours with quota management

---

**Document Last Updated**: December 21, 2024
**Pipeline Version**: v1.0 (Production Ready)
**Test Batch**: 15/15 personas complete ✅
