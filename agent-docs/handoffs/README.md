---
name: handoffs-index
description: What a handoff is and when it is deleted. Read before writing one, and before reopening anything a closed thread settled.
---

# Handoffs

A handoff is the live state of an unfinished thread. It holds pointers, not
content, and is deleted when the thread lands, with its remainder filed in
`../todo/`, `../ideas/` or an ADR. Git history keeps
the deleted ones.
