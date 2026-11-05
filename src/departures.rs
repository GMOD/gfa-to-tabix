// Departure records (ADR 0009): each place a path's consecutive steps on one
// reference sequence S are not adjacent there and the walk rows can't show
// it, filed under the sibling sequence `S~departure` as one row per
// bin-sized block of the bases between its ends.

use crate::sorter::Sorter;

// One end of a departure: a step on S
#[derive(Clone, Copy)]
pub struct End {
    // where the path's sequence stops following S: the node's end for a step
    // along S, its start for one against it, and the other way round for the
    // rejoin
    pub bp: u64,
    // whether the step runs against S's orientation at its pass
    pub against: bool,
    // the base of the node beside the breakpoint, clipped to S
    pub base: u64,
    // how many times the reference's paths pass the step's node: above 1,
    // which pass the step takes is the placement's choice
    pub passes: u32,
}

// A stretch of a contig that is the path's own sequence for S: its bp, and
// the bp of it no line of the contig covers
#[derive(Clone, Copy, Default)]
pub struct Own {
    pub bp: u64,
    pub missing: u64,
}

impl std::ops::Add for Own {
    type Output = Own;

    fn add(self, other: Own) -> Own {
        Own {
            bp: self.bp + other.bp,
            missing: self.missing + other.missing,
        }
    }
}

// `own` starts at `hap_start` on the contig, right after the leave
pub struct Departure<'a> {
    pub path: &'a [u8],
    pub hap_start: u64,
    pub own: Own,
    pub leave: End,
    pub rejoin: End,
}

const BIN_SIZES: [u64; 4] = [1 << 26, 1 << 23, 1 << 20, 1 << 17];

// Cuts [lo, hi) at aligned multiples of the index's bin sizes, each block
// clipped to the stretch, so that each lands in a bin no larger than its own
// size
fn blocks(lo: u64, hi: u64, mut each: impl FnMut(u64, u64)) {
    let unit = BIN_SIZES[3];
    let mut at = lo / unit * unit;
    let end = (hi - 1) / unit * unit + unit;
    while at < end {
        let size = BIN_SIZES
            .into_iter()
            .find(|&s| at.is_multiple_of(s) && at + s <= end)
            .unwrap_or(unit);
        each(lo.max(at), hi.min(at + size));
        at += size;
    }
}

fn push_u64(out: &mut Vec<u8>, n: u64) {
    out.extend_from_slice(n.to_string().as_bytes());
}

impl Departure<'_> {
    // The bases the record is filed over: from one base of one end's node
    // beside its breakpoint to one of the other's
    fn extent(&self) -> (u64, u64) {
        let (a, b) = (self.leave.base, self.rejoin.base);
        (a.min(b), a.max(b) + 1)
    }

    // `departure path hapStart ownBp missingBp leavePos leaveStrand
    // leavePasses rejoinPos rejoinStrand rejoinPasses`
    fn body(&self, out: &mut Vec<u8>) {
        out.extend_from_slice(b"departure\t");
        out.extend_from_slice(self.path);
        for n in [self.hap_start, self.own.bp, self.own.missing] {
            out.push(b'\t');
            push_u64(out, n);
        }
        for end in [self.leave, self.rejoin] {
            out.push(b'\t');
            push_u64(out, end.bp);
            out.extend_from_slice(if end.against { b"\t-\t" } else { b"\t+\t" });
            push_u64(out, u64::from(end.passes));
        }
    }

    // Sorts the record's rows under `key`, S's place among the file's
    // sequences, each as its block's start and end, big-endian so that bytes
    // sort as numbers, then the row's text from its kind on. Returns how many.
    pub fn file(&self, key: u32, sorter: &mut Sorter) -> Result<u64, String> {
        let (lo, hi) = self.extent();
        let mut body = Vec::new();
        self.body(&mut body);
        let mut rows = Vec::new();
        blocks(lo, hi, |a, b| rows.push((a, b)));
        for &(a, b) in &rows {
            sorter.push(key, |out| {
                out.extend_from_slice(&a.to_be_bytes());
                out.extend_from_slice(&b.to_be_bytes());
                out.extend_from_slice(&body);
            })?;
        }
        Ok(rows.len() as u64)
    }
}

// A sorted row back as (start, end, text from its kind on)
pub fn unfile(row: &[u8]) -> (u64, u64, &[u8]) {
    let word = |at: usize| u64::from_be_bytes(row[at..at + 8].try_into().expect("8 bytes"));
    (word(0), word(8), &row[16..])
}

// The stretches of a reference sequence no line of the reference covers,
// before its first and between its lines, with the bp of the holes before
// each
pub struct Holes {
    spans: Vec<(u64, u64)>,
    before: Vec<u64>,
}

impl Holes {
    // From the stretches the reference's lines cover; a line with no steps
    // covers nothing
    pub fn between(mut cover: Vec<(u64, u64)>) -> Holes {
        cover.retain(|&(a, b)| b > a);
        cover.sort_unstable();
        let mut holes = Holes {
            spans: Vec::new(),
            before: vec![0],
        };
        let mut at = 0;
        for (a, b) in cover {
            if a > at {
                holes.spans.push((at, a));
                holes
                    .before
                    .push(holes.before[holes.before.len() - 1] + a - at);
            }
            at = at.max(b);
        }
        holes
    }

    pub fn spans(&self) -> &[(u64, u64)] {
        &self.spans
    }

    // A position with the holes before it removed
    fn squeeze(&self, bp: u64) -> u64 {
        bp - self.before[self.spans.partition_point(|&(_, end)| end <= bp)]
    }

    // Whether two consecutive steps on S follow S at their passes: no
    // sequence of the path's own between them, the same strand, and one's
    // breakpoint the other's, holes removed
    pub fn adjacent(&self, own_bp: u64, leave: &End, rejoin: &End) -> bool {
        own_bp == 0
            && leave.against == rejoin.against
            && self.squeeze(leave.bp) == self.squeeze(rejoin.bp)
    }
}
