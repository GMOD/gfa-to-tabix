---
name: ada-and-laptop-gotchas
description: What running jobs on ada and the laptop taught - kill by PID, shared memory on ada, zsh word-splitting, the laptop's full disk; collected from the session handoffs of 2026-10-30 to 2026-11-07, each line saying whether it was rechecked on 2026-11-25.
---

# Running jobs on ada and the laptop

Collected on 2026-11-25 from the session handoffs of 2026-10-30 to
2026-11-07, which git history keeps. ssh habits and waiting on a job are in
`release-tooling.md`, "ada".

## ada

- Kill a job by its PID. `pkill -f PATTERN`, or `pgrep -f PATTERN | xargs
  kill`, sent over ssh also matches the ssh session's own command line,
  which holds the pattern, and kills it
- ada's memory is shared with other heavy jobs on the same account. On
  2026-11-03 they filled its 125 GB, the kernel killed audits well under
  their `systemd-run` caps, and sshd refused connections for a while.
  Check `free -g` before starting anything over 30 GB, and cap every job
  with `systemd-run --user --scope -p MemoryMax=… -p MemorySwapMax=0`. Not
  rechecked since
- ada's login shell was zsh on 2026-11-05 (not rechecked): an unquoted
  `$pids` is one word there, so kill a list of PIDs through `xargs`
- ada's `tabix` could not read https on 2026-10-30 (not rechecked): query
  hosted files from the laptop

## The laptop

- The login shell is zsh (checked 2026-11-25), which does not word-split
  an unquoted variable: run a loop over a string of options or seeds under
  `bash -c`
- In early November `/tmp` was a tmpfs with a per-user quota, and other
  projects' scratch under `/tmp/claude-1001` filled it until tool output
  failed with "Disk quota exceeded". On 2026-11-25 `/tmp` is no separate
  mount: it shares the root disk, which was 93% full with 35 GB free, and
  `/tmp/claude-1001` held 25 GB. Keep large builds and their scratch on
  ada
