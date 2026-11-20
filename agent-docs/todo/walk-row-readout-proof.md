---
name: walk-row-readout-proof
description: The S5 check proves walk-row readouts against the file except for 174 pggb rows where a departure's attached steps draw as own steps inside a gap; proving those needs the readout to dump attached-step ids.
metadata:
  repo: bandage-core
---

# Walk-row readouts not fully proved

- S5 bounds those 174 pggb rows by the gap size and marks them, because the
  attached steps are not visible in the decoded tiles it checks. Make the
  readout code dump attached-step ids and have the checker decode them, with
  a planted wrong id that fails
- Also from that review: on a pass that crosses the window edge, the ", of
  which" list follows the last phrase and can read as that phrase's. Look at
  a crossing-pass readout at today's head before changing the wording
