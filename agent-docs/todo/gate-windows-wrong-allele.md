---
name: gate-windows-wrong-allele
description: Five drawing-gate windows (sv-9, 14, 19, 23, 48) draw a different allele from the VCF record they are named for, so they check a picture of something else.
metadata:
  repo: walks8-evidence (fab8f323)
---

# Gate windows that draw another allele

sv-9, sv-14, sv-19, sv-23 and sv-48 are each named for a record of the raw
vg-deconstruct VCF, but draw a different allele of it (found 2026-11-17;
not rechecked since). sv-19 is a
plant window and stays. Re-pick the other four from the VCF so each draws the
record it names, and record the pick in the gate's window list.
