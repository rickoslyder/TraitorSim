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

**Document Created**: December 22, 2024
**Tested Configuration**: 22-player game with 3 Traitors, 11+ days runtime
