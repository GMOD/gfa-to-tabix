// The bubble BED `gfatools bubble` writes, read out of a `vg deconstruct`
// snarl VCF instead, so a pggb or Minigraph-Cactus graph gets the bubble track
// that an rGFA gets from gfatools, which finds no bubbles on a plain GFA.
// Ports jbrowse-components' snarls_to_bubble_bed.py.
//
// Each VCF record carries what a bubble needs: ID `>source>sink` names the
// snarl's boundary segments, POS and REF its span on the reference, LV its
// level in the snarl tree and AT one traversal per allele. Top level (LV=0) is
// the cut gfatools makes by reporting top-level bubbles only.
//
// Columns are gfatools' own, and only the ones MinigraphBubbleAdapter reads are
// meaningful: chrom, start, end, segments, walks, inversion, shortest, longest,
// three `.`, then the comma-separated segment ids.

use std::collections::HashSet;
use std::io::BufRead;

use crate::bed::Writer;

struct Bubble {
    chrom: String,
    start: u64,
    end: u64,
    segments: usize,
    walks: usize,
    inversion: bool,
    shortest: usize,
    longest: usize,
    ids: Vec<String>,
}

// The steps of a signed node path, `>2<4>5`: orientation and numeric id.
fn steps(path: &str) -> Vec<(char, &str)> {
    let bytes = path.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] == b'<' || bytes[i] == b'>' {
            let digits = bytes[i + 1..]
                .iter()
                .take_while(|b| b.is_ascii_digit())
                .count();
            if digits > 0 {
                out.push((bytes[i] as char, &path[i + 1..i + 1 + digits]));
                i += 1 + digits;
                continue;
            }
        }
        i += 1;
    }
    out
}

fn info<'a>(field: &'a str, key: &str) -> Option<&'a str> {
    field.split(';').find_map(|part| {
        part.split_once('=')
            .filter(|(k, _)| *k == key)
            .map(|(_, v)| v)
    })
}

pub fn run(vcf: &str, prefix: &str, min_alleles: usize) -> Result<(), String> {
    let (mut total, mut top) = (0, 0);
    let mut bubbles: Vec<Bubble> = Vec::new();
    for line in crate::open_input(vcf)?.lines() {
        let line = line.map_err(|e| format!("{vcf}: {e}"))?;
        if line.starts_with('#') {
            continue;
        }
        total += 1;
        let f: Vec<&str> = line.split('\t').collect();
        if f.len() < 8 {
            return Err(format!("{vcf}: a record has {} columns, not 8", f.len()));
        }
        // a nested snarl's span sits inside its parent's, so drawing both would
        // double the node count and overlap the backbone walk
        if info(f[7], "LV") != Some("0") {
            continue;
        }
        top += 1;
        let traversals: Vec<&str> = info(f[7], "AT")
            .unwrap_or("")
            .split(',')
            .filter(|t| !t.is_empty())
            .collect();
        if traversals.len() < min_alleles {
            continue;
        }
        let pos: u64 = f[1]
            .parse()
            .map_err(|_| format!("{vcf}: POS {:?} is not a number", f[1]))?;
        let boundary: Vec<&str> = steps(f[2]).into_iter().map(|(_, id)| id).collect();
        let mut segments: HashSet<&str> = HashSet::new();
        let mut inversion = false;
        for traversal in &traversals {
            for (orientation, id) in steps(traversal) {
                segments.insert(id);
                // a reverse step on an interior segment reads that piece
                // backwards; a snarl written `<5<2` is the same snarl approached
                // from the other end, so the boundaries are excluded
                if orientation == '<' && !boundary.contains(&id) {
                    inversion = true;
                }
            }
        }
        let lengths: Vec<usize> = std::iter::once(f[3].len())
            .chain(f[4].split(',').filter(|a| *a != ".").map(str::len))
            .collect();
        let start = pos - 1;
        // The source segment is qualified by the reference start: pggb folds
        // repeats, so the reference path can walk one snarl more than once and
        // `vg deconstruct` reports it once per visit.
        let mut ids: Vec<String> = boundary.iter().map(|s| s.to_string()).collect();
        if let Some(first) = ids.first_mut() {
            *first = format!("{first}@{start}");
        }
        bubbles.push(Bubble {
            chrom: f[0].to_string(),
            start,
            end: start + f[3].len() as u64,
            segments: segments.len(),
            walks: traversals.len(),
            inversion,
            shortest: lengths.iter().copied().min().unwrap_or(0),
            longest: lengths.iter().copied().max().unwrap_or(0),
            ids,
        });
    }

    if total > 0 && top == 0 {
        eprintln!(
            "note: no record has LV=0, so no bubble was written; `vg deconstruct -a` writes the LV tag"
        );
    }

    // top-level bubbles do not overlap; a snarl VCF does not guarantee it
    bubbles.sort_by(|a, b| {
        (a.chrom.as_bytes(), a.start, a.end).cmp(&(b.chrom.as_bytes(), b.start, b.end))
    });
    let mut kept: Vec<Bubble> = Vec::new();
    let mut dropped = 0;
    for bubble in bubbles {
        match kept.last() {
            Some(prev) if prev.chrom == bubble.chrom && bubble.start < prev.end => dropped += 1,
            _ => kept.push(bubble),
        }
    }

    let out = format!("{prefix}.bubbles.bed.gz");
    let mut writer = Writer::create(&out)?;
    for b in &kept {
        let line = format!(
            "{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t.\t.\t.\t{}\n",
            b.chrom,
            b.start,
            b.end,
            b.segments,
            b.walks,
            u8::from(b.inversion),
            b.shortest,
            b.longest,
            b.ids.join(",")
        );
        writer.push(b.chrom.as_bytes(), b.start, b.end, line.as_bytes())?;
    }
    writer.finish()?;
    eprintln!(
        "{total} records, {top} top level, {} bubbles -> {out} (+ .tbi){}",
        kept.len(),
        if dropped > 0 {
            format!(", {dropped} dropped as overlapping")
        } else {
            String::new()
        }
    );
    Ok(())
}
