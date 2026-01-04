# DevOps & Infrastructure Lessons Learned

## Overview
Documentation of debugging insights and infrastructure configurations for running TraitorSim's Docker-in-Docker multi-agent architecture.

---

## Lesson 1: kernel.threads-max is the REAL Limit for Docker-in-Docker

### Problem
When running 22+ player simulations with Docker-in-Docker (DinD), the system hit "resource temporarily unavailable" errors during container startup:

```
runtime/cgo: pthread_create failed: resource temporarily unavailable
```

### Initial Diagnosis (Wrong)
- Assumed the issue was `ulimit -u` (per-user process limit)
- Found typo in `/etc/security/limits.conf`: `noproc` instead of `nproc`
- Fixed typo, but errors persisted

### Deeper Investigation (Correct)
The actual bottleneck was **kernel.threads-max**, not user-level nproc:

```bash
# Check current thread usage
cat /proc/sys/kernel/threads-max  # Was: 6337
ps -eo nlwp | tail -n +2 | awk '{sum += $1} END {print sum}'  # Was: 5279 (83% used!)
```

DinD architecture creates exponential thread usage:
- Host → Orchestrator container → Inner Docker daemon → 24 agent containers
- Each layer adds threads for: Docker daemon, health checks, Flask workers, Python GC

### Solution
1. **Immediate fix** (runtime):
   ```bash
   sudo sysctl -w kernel.threads-max=65536
   sudo sysctl -w kernel.pid_max=65536
   ```

2. **Permanent fix** (`/etc/sysctl.conf`):
   ```bash
   # TraitorSim - increased for Docker-in-Docker
   kernel.threads-max = 65536
   kernel.pid_max = 65536
   ```

3. **Container ulimits** (`docker-compose.yml`):
   ```yaml
   orchestrator:
     pids_limit: 32768
     ulimits:
       nproc:
         soft: 65535
         hard: 65535
       nofile:
         soft: 65535
         hard: 65535
   ```

### Key Insight
**`ulimit -u` (nproc) is per-user, but `kernel.threads-max` is system-wide.**

In Docker-in-Docker:
- The inner Docker daemon runs as root inside the container
- All spawned containers share the host's kernel thread pool
- User-level limits don't constrain thread creation as expected

### Verification
After fix, game ran successfully for 11+ days with 22 players:
```
Day 11 Breakfast: "Darren Whitmore was found murdered this morning."
Remaining: 3 Traitors, 9 Faithful
Shield protected multiple players throughout game
```

---

## Lesson 2: Diagnosing Resource Issues Systematically

### Wrong Approach
Immediately assuming the first bottleneck found is the culprit.

### Right Approach
**Check multiple resource dimensions:**

```bash
# 1. Thread usage (most common DinD bottleneck)
echo "Threads: $(ps -eo nlwp | tail -n +2 | awk '{sum += $1} END {print sum}') / $(cat /proc/sys/kernel/threads-max)"

# 2. Process count
echo "Processes: $(ps aux | wc -l) / ulimit -u"

# 3. File descriptors
echo "FD usage: $(cat /proc/sys/fs/file-nr | awk '{print $1}') / $(cat /proc/sys/fs/file-max)"

# 4. inotify watches (for file-heavy workloads)
echo "inotify: $(cat /proc/sys/fs/inotify/max_user_watches)"

# 5. Memory (per-process limits)
cat /proc/$(pgrep docker)/limits | grep "Max processes"
```

---

## Lesson 3: Limits Configuration Hierarchy

### Order of Precedence (most specific wins)
1. **Container runtime limits** (docker-compose.yml ulimits)
2. **Docker daemon defaults** (`/etc/docker/daemon.json`)
3. **User limits** (`/etc/security/limits.conf`)
4. **Kernel limits** (`/etc/sysctl.conf`)

### Key Files
| File | Scope | Applies To |
|------|-------|------------|
| `/etc/sysctl.conf` | Kernel | All processes |
| `/etc/security/limits.conf` | Per-user | Login sessions |
| `/etc/docker/daemon.json` | Docker | All containers |
| `docker-compose.yml` ulimits | Per-container | Specific containers |

### Common Typos to Watch For
- `noproc` instead of `nproc` (no spell check in limits.conf!)
- `nofiles` instead of `nofile`
- Missing `*` for wildcard user

---

## Recommended Configuration for TraitorSim

### /etc/sysctl.conf
```bash
# Kernel limits for Docker-in-Docker multi-agent
kernel.threads-max = 65536
kernel.pid_max = 65536
vm.overcommit_memory = 1
```

### /etc/security/limits.conf
```bash
* soft nproc 50000
* hard nproc 100000
* soft nofile 65535
* hard nofile 65535
```

### docker-compose.yml (orchestrator)
```yaml
orchestrator:
  privileged: true
  pids_limit: 32768
  ulimits:
    nproc:
      soft: 65535
      hard: 65535
    nofile:
      soft: 65535
      hard: 65535
```

---

## Quick Diagnostic Commands

```bash
# Check current kernel limits
sysctl kernel.threads-max kernel.pid_max

# Check active thread count
ps -eo nlwp | tail -n +2 | awk '{sum += $1} END {print "Active threads:", sum}'

# Check limits for running Docker daemon
cat /proc/$(pgrep -x dockerd)/limits

# Watch thread usage in real-time
watch -n 1 'ps -eo nlwp | tail -n +2 | awk "{sum += \$1} END {print sum}"'
```

---

## Related Issues

- **"too many open files"**: Increase `nofile` in limits.conf or docker ulimits
- **"cannot allocate memory"**: Check vm.overcommit_memory and container memory limits
- **"fork: cannot allocate memory"**: Usually kernel.pid_max or threads-max exhausted

---

## Lesson 4: Game Logic Bug Patterns (January 2026 Audit)

### Overview
After running a full 22-player containerized game, an extensive audit revealed several critical bugs that had been hiding in plain sight. These patterns are common in complex game engines.

### Bug 1: Logic Inversion (Revote Tie-Breaking)

**Location**: `src/traitorsim/core/game_engine_containerized.py:1269-1271`

**Original Code (WRONG)**:
```python
# Ignore votes for tied players (they're immune)
if target_id not in tied_players:
    revotes[voter.id] = target_id
```

**The Problem**: The comment was correct ("tied players are the candidates"), but the logic was inverted. In a revote, voters should ONLY vote for tied players (to break the tie), but the code rejected those votes and accepted votes for non-tied players.

**Impact**: When 8 players tied, the revote could select someone NOT in the original tie.

**Fix**:
```python
# Only accept votes FOR tied players (they're the candidates)
if target_id in tied_players:
    revotes[voter.id] = target_id
```

**Lesson**: Comments and code can contradict each other. Always verify logic matches intent by tracing through with real data.

---

### Bug 2: Dictionary Key Mismatch (Vote Count Display)

**Location**: `src/traitorsim/agents/game_master_interactions.py:400`

**Original Code (WRONG)**:
```python
- Vote count: {votes.get(banished_name, 0)} votes
```

**The Problem**: The `votes` dict was keyed by `player_id` (e.g., "player_01"), but the lookup used `banished_name` (e.g., "Keeley Barton"). They never matched, so vote count always returned 0.

**Impact**: Every banishment announcement said "0 votes" regardless of actual votes.

**Fix**: Added `banished_id` parameter and use it for lookup:
```python
vote_count = votes.get(banished_id, 0) if banished_id else max(votes.values()) if votes else 0
```

**Lesson**: When passing data between functions, verify the key type matches at both ends. IDs and names are NOT interchangeable.

---

### Bug 3: Binary Values Where Spectrum Expected

**Location**: `src/traitorsim/missions/skill_check.py:31`

**Original Code**:
```python
performance_scores[player.id] = 1.0 if success else 0.0
```

**The Problem**: Performance was binary (0 or 1), providing no granularity. Made gameplay feel unrealistic and limited observability for debugging.

**Fix**: Calculate performance as a spectrum:
```python
base_performance = intellect * (1 - difficulty * 0.5)
random_factor = random.uniform(0.7, 1.3)
performance = max(0.0, min(1.0, base_performance * random_factor))
performance_scores[player.id] = round(performance, 2)
```

**Lesson**: Game mechanics feel more realistic with continuous values. Binary outcomes should be reserved for final pass/fail decisions, not intermediate scoring.

---

### Bug 4: Miscalibrated Difficulty

**Location**: `src/traitorsim/core/config.py:90`

**Original**: `mission_difficulty: float = 0.5`

**Formula**: `success_chance = intellect * (1 - difficulty)`

**The Math**:
- With difficulty=0.5 and average intellect=0.5: success = 0.5 × 0.5 = 25%
- Even max intellect (1.0) only had 50% success chance

**Impact**: All missions failed because the math guaranteed <50% average success.

**Fix**: Reduced to `mission_difficulty: float = 0.3`, giving ~50-60% success rates.

**Lesson**: Always verify game balance formulas with actual numbers. What looks reasonable (0.5 difficulty) can be punishing in practice.

---

### Debugging Methodology

1. **Run a complete game** - Unit tests miss integration issues
2. **Grep for key patterns** - `grep -E "(votes|TIE|performance)" game.log`
3. **Trace data flow** - Follow values from source to destination
4. **Check dict key types** - ID vs name mismatches are common
5. **Verify math formulas** - Plug in actual values, not just variables
6. **Compare implementations** - The async engine had correct logic; containerized engine had bugs

### Verification Checklist

After fixing game logic bugs:
- [ ] Vote counts appear in banishment announcements (not 0)
- [ ] Revotes select from tied candidates only
- [ ] Performance scores show variety (0.3, 0.45, 0.67, not just 0/1)
- [ ] Mission success rates are reasonable (40-60%, not 20-30%)
- [ ] Both Faithfuls and Traitors can win games

---

**Document Updated**: January 4, 2026
**Tested Configuration**: 22-player game with 3 Traitors, 10 days runtime, Faithfuls won
