import sys, re
p = sys.argv[1] + '/src/walks.rs'
s = open(p).read()
def sub(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)
sub("    unplaced: u64,\n    departures: u64,", "    unplaced: u64,\n    stats: [u64; 6],\n    departures: u64,")
sub("            unplaced: 0,\n            departures: 0,", "            unplaced: 0,\n            stats: [0; 6],\n            departures: 0,")
sub("""            if !self.assign_chunks(r, handles, own) {
                self.references[r].unplaced += 1;
                continue;
            }""", """            if !self.assign_chunks(r, handles, own) {
                self.references[r].unplaced += 1;
                if own.is_none() {
                    self.references[r].stats[5] += self.before[handles.len()];
                }
                continue;
            }
            if own.is_none() {
                let reference = &mut self.references[r];
                reference.stats[4] += self.before[handles.len()];
                for (i, &h) in handles.iter().enumerate() {
                    let bp = self.before[i + 1] - self.before[i];
                    if reference.on_reference((h >> 1) as usize) {
                        reference.stats[2] += 1;
                        reference.stats[3] += bp;
                    }
                    if self.pass[i].name != NONE {
                        reference.stats[0] += 1;
                        reference.stats[1] += bp;
                    }
                }
            }""")
sub("""            reference.unplaced,
            text(&reference.sample)
        );""", """            reference.unplaced,
            text(&reference.sample)
        );
        eprintln!(
            "stats {}: placed_steps {} placed_bp {} refnode_steps {} refnode_bp {} hap_bp_placed_lines {} hap_bp_unplaced_lines {}",
            text(&reference.sample),
            reference.stats[0], reference.stats[1], reference.stats[2], reference.stats[3], reference.stats[4], reference.stats[5]
        );""")
open(p, 'w').write(s)
