// Departure records (ADR 0009): each place a path's consecutive steps on one
// reference sequence S are not adjacent there and the walk rows can't show
// it, filed in every block of the departure pyramid that covers its end
// nodes (ADR 0010).

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
    // the stretch of S the step's node covers at its pass
    pub node: (u64, u64),
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

// `own` starts at `hap_start` on the contig, right after the leave.
// `own_tiles` are the starts of S's tiles that hold the steps between the
// leave and the rejoin, in path order
pub struct Departure<'a> {
    pub path: &'a [u8],
    pub hap_start: u64,
    pub own: Own,
    pub leave: End,
    pub rejoin: End,
    pub own_tiles: &'a [u64],
}

// The pyramid's block sizes, in tiles, largest first
const BLOCK_TILES: [u64; 4] = [512, 64, 8, 1];

// Cuts [lo, hi), widened to whole tiles, into the largest aligned blocks of
// the pyramid that fit, as (start, size)
pub fn cover(lo: u64, hi: u64, tile: u64, mut each: impl FnMut(u64, u64)) {
    let mut at = lo / tile * tile;
    let end = hi.div_ceil(tile) * tile;
    while at < end {
        let size = BLOCK_TILES
            .into_iter()
            .map(|n| n * tile)
            .find(|&s| at.is_multiple_of(s) && at + s <= end)
            .unwrap_or(tile);
        each(at, size);
        at += size;
    }
}

fn push_u64(out: &mut Vec<u8>, n: u64) {
    out.extend_from_slice(n.to_string().as_bytes());
}

impl Departure<'_> {
    // From the first base of one end's node to the last of the other's, or
    // the bases beside the breakpoints where wider
    fn extent(&self) -> (u64, u64) {
        let (a, b) = (self.leave.base, self.rejoin.base);
        (
            a.min(b).min(self.leave.node.0).min(self.rejoin.node.0),
            (a.max(b) + 1)
                .max(self.leave.node.1)
                .max(self.rejoin.node.1),
        )
    }

    // `departure path hapStart ownBp missingBp leavePos leaveStrand
    // leavePasses rejoinPos rejoinStrand rejoinPasses ownTiles`
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
        out.push(b'\t');
        if self.own_tiles.is_empty() {
            out.push(b'.');
        }
        for (k, &tile) in self.own_tiles.iter().enumerate() {
            if k > 0 {
                out.push(b',');
            }
            push_u64(out, tile);
        }
    }

    // Sorts the record's line once per block of its cover under `key`, S's
    // place among the file's sequences, as the block's start and size, the
    // record's extent, each big-endian so that bytes sort as numbers, then
    // the line's text from its kind on. Returns how many.
    pub fn file(&self, key: u32, tile: u64, sorter: &mut Sorter) -> Result<u64, String> {
        let (lo, hi) = self.extent();
        let mut body = Vec::new();
        self.body(&mut body);
        let mut blocks = Vec::new();
        cover(lo, hi, tile, |at, size| blocks.push((at, size)));
        for &(at, size) in &blocks {
            sorter.push(key, |out| {
                for n in [at, size, lo, hi] {
                    out.extend_from_slice(&n.to_be_bytes());
                }
                out.extend_from_slice(&body);
            })?;
        }
        Ok(blocks.len() as u64)
    }
}

// A sorted line back as its block's start and size, its extent, and its text
// from its kind on
pub struct Filed<'a> {
    pub block: (u64, u64),
    pub extent: (u64, u64),
    pub body: &'a [u8],
}

pub fn unfile(row: &[u8]) -> Filed<'_> {
    let word = |k: usize| u64::from_be_bytes(row[8 * k..8 * k + 8].try_into().expect("8 bytes"));
    Filed {
        block: (word(0), word(1)),
        extent: (word(2), word(3)),
        body: &row[32..],
    }
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
