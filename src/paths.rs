// One tabix-indexed BED of every sample's path through every bubble, in long
// format: a row per bubble and sample, so a multi-row feature display
// partitioned on `strain` draws one lane per haplotype. Reads the files
// `minigraph -cxasm --call graph.rgfa sample.fa` writes, one per sample, the
// reference's first. Ports jbrowse-components' build_minigraph_paths.sh.
//
// minigraph writes one line per `gfatools bubble` line, in the same order for
// every sample, so line N of each file is the same bubble. The last field of a
// line is `path:pathLen:strand:contig:contigStart:contigEnd`, or a bare `.`
// when the sample has no alignment over the bubble. A bare `.` is missing data,
// where read as a colon-separated field it would score as a deletion of the
// whole reference span.
//
// `*` is an empty path. At a bubble with a reference span it is a deletion; at
// a pure-insertion site, which has none, it is the reference allele. Classifying
// on `delta` covers both.

use std::collections::HashSet;
use std::fs;
use std::path::Path;

use crate::alleles::commify;
use crate::bed::Writer;

const HEADER: &str = "#chrom\tstart\tend\tname\tscore\tstrand\tthickStart\tthickEnd\titemRgb\tstrain\tclass\tdelta\tpathLen\trefLen\talleles\tnonRef\tpath\n";

struct Call {
    chrom: String,
    start: String,
    end: String,
    field: String,
}

struct Row {
    chrom: String,
    start: u64,
    end: u64,
    line: String,
}

pub fn sample_name(path: &str) -> String {
    let base = Path::new(path)
        .file_name()
        .map_or(path.to_string(), |n| n.to_string_lossy().into_owned());
    let stem = base
        .strip_suffix(".call.bed")
        .or_else(|| base.strip_suffix(".bed"))
        .unwrap_or(&base);
    stem.to_string()
}

fn read_calls(path: &str) -> Result<Vec<Call>, String> {
    let text = fs::read_to_string(path).map_err(|e| format!("{path}: {e}"))?;
    text.lines()
        .filter(|l| !l.is_empty())
        .map(|line| {
            let f: Vec<&str> = line.split('\t').collect();
            if f.len() < 6 {
                return Err(format!(
                    "{path}: a call line has {} columns, not 6",
                    f.len()
                ));
            }
            Ok(Call {
                chrom: f[0].to_string(),
                start: f[1].to_string(),
                end: f[2].to_string(),
                field: f[f.len() - 1].to_string(),
            })
        })
        .collect()
}

fn number(path: &str, field: &str) -> Result<u64, String> {
    field
        .parse()
        .map_err(|_| format!("{path}: coordinate {field:?} is not a number"))
}

// the path of a `path:pathLen:strand:...` field, or `.` for no call
fn path_of(field: &str) -> &str {
    field.split(':').next().unwrap_or(".")
}

pub fn run(prefix: &str, files: &[String]) -> Result<(), String> {
    let samples: Vec<(String, Vec<Call>)> = files
        .iter()
        .map(|f| Ok((sample_name(f), read_calls(f)?)))
        .collect::<Result<_, String>>()?;
    let (reference, reference_calls) = &samples[0];
    let bubbles = reference_calls.len();
    for (file, (_, calls)) in files.iter().zip(&samples) {
        if calls.len() != bubbles {
            return Err(format!(
                "{file} has {} lines and {} has {bubbles}: minigraph writes one line per bubble, in the same order for every sample",
                calls.len(),
                files[0]
            ));
        }
    }

    let reference_paths: Vec<&str> = reference_calls
        .iter()
        .map(|c| {
            if c.field == "." {
                "."
            } else {
                path_of(&c.field)
            }
        })
        .collect();
    let mut alleles = vec![0usize; bubbles];
    let mut non_reference = vec![0usize; bubbles];
    let mut seen: HashSet<(usize, &str)> = HashSet::new();
    for (_, calls) in &samples {
        for (i, call) in calls.iter().enumerate() {
            let path = path_of(&call.field);
            if path != "." {
                if seen.insert((i, path)) {
                    alleles[i] += 1;
                }
                if path != reference_paths[i] {
                    non_reference[i] += 1;
                }
            }
        }
    }

    let strip = format!("{reference}#");
    let mut rows: Vec<Row> = Vec::new();
    for (strain, calls) in &samples {
        for (i, call) in calls.iter().enumerate() {
            let (start, end) = (number(strain, &call.start)?, number(strain, &call.end)?);
            let ref_span = end as i64 - start as i64;
            let parts: Vec<&str> = call.field.split(':').collect();
            let strand = if call.field == "." || parts.get(2).is_none_or(|s| s.is_empty()) {
                "."
            } else {
                parts[2]
            };
            let (class, rgb, label, path, path_len, delta);
            if call.field == "." {
                (class, rgb, label, path, path_len, delta) = (
                    "nocall",
                    "191,170,64",
                    "no call".to_string(),
                    ".",
                    -1i64,
                    0i64,
                );
            } else {
                path = parts[0];
                path_len = parts
                    .get(1)
                    .and_then(|s| s.parse::<f64>().ok())
                    .unwrap_or(0.0) as i64;
                delta = path_len - ref_span;
                (class, rgb, label) = if path == reference_paths[i] {
                    ("ref", "204,204,204", "ref".to_string())
                } else if delta > 0 {
                    ("ins", "192,0,192", format!("+{}", commify(delta)))
                } else if delta < 0 {
                    ("del", "128,128,128", commify(delta))
                } else {
                    ("sub", "0,154,138", format!("{} sub", commify(path_len)))
                };
            }
            // `ref#hap#contig` -> `contig`, so the rows sit on the reference's own refNames
            let chrom = match call
                .chrom
                .strip_prefix(strip.as_str())
                .and_then(|r| r.split_once('#'))
            {
                Some((_, rest)) => rest.to_string(),
                None => call.chrom.clone(),
            };
            // a pure-insertion bubble has start == end; one base makes it drawable
            let end = end.max(start + 1);
            let line = format!(
                "{chrom}\t{start}\t{end}\t{label}\t0\t{strand}\t{start}\t{end}\t{rgb}\t{strain}\t{class}\t{delta}\t{path_len}\t{ref_span}\t{}\t{}\t{path}\n",
                alleles[i], non_reference[i]
            );
            rows.push(Row {
                chrom,
                start,
                end,
                line,
            });
        }
    }
    rows.sort_unstable_by(|a, b| {
        (a.chrom.as_bytes(), a.start, a.line.as_bytes()).cmp(&(
            b.chrom.as_bytes(),
            b.start,
            b.line.as_bytes(),
        ))
    });

    let out = format!("{prefix}.bed.gz");
    let mut writer = Writer::create(&out)?;
    writer.header(HEADER.as_bytes())?;
    for r in &rows {
        writer.push(r.chrom.as_bytes(), r.start, r.end, r.line.as_bytes())?;
    }
    writer.finish()?;
    eprintln!(
        "{} rows ({} bubbles x {} samples) -> {out} (+ .tbi)",
        rows.len(),
        bubbles,
        samples.len()
    );
    Ok(())
}
