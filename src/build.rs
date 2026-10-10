// Everything a JBrowse graph track reads, from one read of the graph. Ports
// jbrowse-components' build_pangenome_graph.sh, which read the graph four times.

use std::fs;
use std::io::{self, BufReader, Read, Write};
use std::process::{ChildStdin, Command, Output, Stdio};
use std::thread::{self, JoinHandle};

use crate::bed::{Layout, Row, Writer};
use crate::gfa::Graph;
use crate::json::{Json, object, text};
use crate::{alleles, bubbles};

const PLUGIN_URL: &str = "https://jbrowse.org/plugins/jbrowse-plugin-graphgenomeviewer/latest/dist/jbrowse-plugin-graphgenomeviewer.esm.js";

pub struct Options {
    pub graph: String,
    pub prefix: String,
    pub reference: Option<String>,
    pub assembly: Option<String>,
    pub snarls: Option<String>,
    pub tier: Option<i64>,
}

#[derive(Clone, Copy, PartialEq)]
enum Route {
    Rgfa,
    Paths,
}

const SAMPLED_SEGMENTS: usize = 100_000;
const SN_TAG: &[u8] = b"\tSN:Z:";

// Passes the GFA through while it decides the route: an rGFA tags every
// segment, and a Minigraph-Cactus base-level GFA tags only its reference
// walk's, so one untagged S line among the first 100,000 means the path route.
// Until it decides on the path route it copies the text to `tee`.
struct Sniffer<R> {
    inner: R,
    tee: Option<ChildStdin>,
    route: Option<Route>,
    segments: usize,
    line_start: bool,
    in_segment: bool,
    tagged: bool,
    // the end of the S line so far, where a tag split across reads begins
    tail: Vec<u8>,
}

impl<R: Read> Sniffer<R> {
    fn new(inner: R, tee: Option<ChildStdin>) -> Self {
        Sniffer {
            inner,
            tee,
            route: None,
            segments: 0,
            line_start: true,
            in_segment: false,
            tagged: false,
            tail: Vec::new(),
        }
    }

    fn end_segment(&mut self) {
        self.segments += 1;
        if !self.tagged {
            self.route = Some(Route::Paths);
            self.tee = None;
        } else if self.segments >= SAMPLED_SEGMENTS {
            self.route = Some(Route::Rgfa);
        }
    }

    fn scan(&mut self, mut bytes: &[u8]) {
        while self.route.is_none() && !bytes.is_empty() {
            if self.line_start {
                self.line_start = false;
                self.in_segment = bytes[0] == b'S';
                self.tagged = false;
                self.tail.clear();
            }
            let newline = memchr::memchr(b'\n', bytes);
            let line = &bytes[..newline.unwrap_or(bytes.len())];
            if self.in_segment && !self.tagged {
                let keep = SN_TAG.len() - 1;
                let mut seam = std::mem::take(&mut self.tail);
                seam.extend_from_slice(&line[..line.len().min(keep)]);
                self.tagged = memchr::memmem::find(&seam, SN_TAG).is_some()
                    || memchr::memmem::find(line, SN_TAG).is_some();
                self.tail = if line.len() >= keep {
                    line[line.len() - keep..].to_vec()
                } else {
                    seam[seam.len().saturating_sub(keep)..].to_vec()
                };
            }
            let Some(newline) = newline else { return };
            if self.in_segment {
                self.end_segment();
            }
            self.line_start = true;
            bytes = &bytes[newline + 1..];
        }
    }

    // Closes the tee, so its reader sees the end of the text.
    fn finish(mut self) -> Option<Route> {
        if self.route.is_none() && self.in_segment && !self.line_start {
            self.end_segment();
        }
        self.tee = None;
        self.route.or((self.segments > 0).then_some(Route::Rgfa))
    }
}

impl<R: Read> Read for Sniffer<R> {
    fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
        let n = self.inner.read(buf)?;
        self.scan(&buf[..n]);
        if let Some(tee) = &mut self.tee
            && tee.write_all(&buf[..n]).is_err()
        {
            self.tee = None;
        }
        Ok(n)
    }
}

// `gfatools bubble -` reading the text the sniffer passes it. Its stderr is
// shown only when it fails.
struct Bubbler(JoinHandle<io::Result<Output>>);

impl Bubbler {
    fn spawn() -> io::Result<(Bubbler, ChildStdin)> {
        let mut child = Command::new("gfatools")
            .args(["bubble", "-"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()?;
        let stdin = child.stdin.take().expect("stdin is piped");
        Ok((Bubbler(thread::spawn(|| child.wait_with_output())), stdin))
    }

    fn finish(self) -> Result<Vec<u8>, String> {
        let output = self
            .0
            .join()
            .unwrap_or_else(|panic| std::panic::resume_unwind(panic))
            .map_err(|e| format!("gfatools bubble: {e}"))?;
        if !output.status.success() {
            return Err(format!(
                "gfatools bubble failed ({}): {}",
                output.status,
                String::from_utf8_lossy(&output.stderr).trim()
            ));
        }
        Ok(output.stdout)
    }
}

// The order `LC_ALL=C sort -k1,1 -k2,2n` gives.
fn write_bubbles(text: &[u8], out: &str) -> Result<usize, String> {
    let mut rows: Vec<(&[u8], u64, u64, Vec<u8>)> = Vec::new();
    for line in text.split(|&b| b == b'\n').filter(|l| !l.is_empty()) {
        let fields: Vec<&[u8]> = line.splitn(4, |&b| b == b'\t').collect();
        let number = |i: usize| {
            fields
                .get(i)
                .and_then(|f| std::str::from_utf8(f).ok())
                .and_then(|f| f.parse::<u64>().ok())
                .ok_or_else(|| {
                    format!(
                        "gfatools bubble wrote a row with no coordinates: {}",
                        String::from_utf8_lossy(line)
                    )
                })
        };
        rows.push((fields[0], number(1)?, number(2)?, [line, b"\n"].concat()));
    }
    rows.sort_unstable_by(|a, b| (a.0, a.1, &a.3).cmp(&(b.0, b.1, &b.3)));
    let mut writer = Writer::create(out)?;
    for (chrom, start, end, line) in &rows {
        writer.push(chrom, *start, *end, line)?;
    }
    writer.finish()?;
    Ok(rows.len())
}

fn bubble_file(
    route: Route,
    bubbler: Option<Bubbler>,
    missing: Option<io::Error>,
    snarls: Option<&str>,
    prefix: &str,
) -> Result<bool, String> {
    let path = format!("{prefix}.bubbles.bed.gz");
    match (route, bubbler, snarls) {
        (Route::Rgfa, Some(bubbler), _) => {
            let count = write_bubbles(&bubbler.finish()?, &path)?;
            eprintln!("{count} bubbles from gfatools -> {path} (+ .tbi)");
            Ok(true)
        }
        (Route::Rgfa, None, _) => {
            let why = match missing {
                Some(e) if e.kind() != io::ErrorKind::NotFound => format!("gfatools: {e}"),
                _ => "gfatools is not on PATH".into(),
            };
            eprintln!(
                "note: {why}, so no bubble file or bubble tracks for this graph. \
                 Install it from https://github.com/lh3/gfatools"
            );
            Ok(false)
        }
        (Route::Paths, _, Some(snarls)) => bubbles::run(snarls, prefix, 2).map(|()| true),
        (Route::Paths, _, None) => {
            eprintln!("note: no --snarls given, so no bubble file or bubble tracks for this graph");
            Ok(false)
        }
    }
}

// The PanSN sample of the first reference segment in the fine index, as
// `GRCh38` from `GRCh38#0#chr1`; None for a bare name.
fn reference_sample(nodes: &[Row]) -> Option<String> {
    let text = nodes
        .iter()
        .map(Row::text)
        .find(|line| line.split('\t').nth(4) == Some("0"))?;
    let name = text.split('\t').next()?;
    let parts: Vec<&str> = name.split('#').collect();
    (parts.len() >= 3 && !parts[0].is_empty()).then(|| parts[0].to_string())
}

fn basename(prefix: &str) -> &str {
    prefix.rsplit('/').next().unwrap_or(prefix)
}

struct Built<'a> {
    base: &'a str,
    sample: Option<String>,
    assembly: String,
    tier: i64,
    bubbles: bool,
}

impl Built<'_> {
    fn manifest(&self) -> Json {
        let base = self.base;
        let tier = self.tier;
        let file = |present: bool, name: String| if present { text(name) } else { Json::Null };
        object([
            ("schema", Json::Number(1)),
            ("reference", self.sample.clone().map_or(Json::Null, text)),
            ("index", text(base)),
            ("contig", text(format!("{base}.contig"))),
            (
                "tier",
                object([
                    ("prefix", text(format!("{base}.fold{tier}"))),
                    ("foldBelowBp", Json::Number(tier)),
                ]),
            ),
            (
                "bubbles",
                file(self.bubbles, format!("{base}.bubbles.bed.gz")),
            ),
            ("alleles", text(format!("{base}.alleles.bed.gz"))),
        ])
    }

    fn tracks(&self) -> Vec<Json> {
        let base = self.base;
        let stem = base.replace(['.', '-'], "_");
        let assembly = || Json::List(vec![text(&self.assembly)]);
        let pansn = || match &self.sample {
            Some(sample) if *sample != self.assembly => vec![(
                "assemblyNameToPanSN",
                object([(self.assembly.as_str(), text(sample))]),
            )],
            _ => Vec::new(),
        };
        let display = |kind: &str| {
            object([
                ("type", text(kind)),
                ("displayId", text(format!("{stem}_graph-{kind}"))),
            ])
        };
        let mut graph_adapter = vec![("type", text("RgfaTabixAdapter")), ("uri", text(base))];
        graph_adapter.extend(pansn());
        graph_adapter.push((
            "coarse",
            object([
                ("uri", text(format!("{base}.fold{}", self.tier))),
                ("foldBelowBp", Json::Number(self.tier)),
            ]),
        ));
        let mut tracks = vec![
            object([
                ("type", text("GraphTrack")),
                ("trackId", text(format!("{stem}_graph"))),
                ("name", text(format!("{base} graph"))),
                ("assemblyNames", assembly()),
                ("adapter", object(graph_adapter)),
                ("displayDefaults", object([("showLabels", text("none"))])),
                (
                    "displays",
                    Json::List(vec![
                        display("LinearGraphDisplay"),
                        display("LinearBasicDisplay"),
                    ]),
                ),
            ]),
            object([
                ("type", text("AlignmentsTrack")),
                ("trackId", text(format!("{stem}_alleles"))),
                ("name", text(format!("{base} alleles"))),
                ("assemblyNames", assembly()),
                (
                    "adapter",
                    object([
                        ("type", text("BedTabixAdapter")),
                        ("uri", text(format!("{base}.alleles.bed.gz"))),
                    ]),
                ),
            ]),
        ];
        if self.bubbles {
            let adapter = || {
                let mut fields = vec![
                    ("type", text("MinigraphBubbleAdapter")),
                    ("uri", text(format!("{base}.bubbles.bed.gz"))),
                ];
                fields.extend(pansn());
                object(fields)
            };
            for (kind, id, name) in [
                ("FeatureTrack", "bubbles", "bubbles"),
                ("QuantitativeTrack", "bubble_score", "segments per bubble"),
            ] {
                tracks.push(object([
                    ("type", text(kind)),
                    ("trackId", text(format!("{stem}_{id}"))),
                    ("name", text(format!("{base} {name}"))),
                    ("assemblyNames", assembly()),
                    ("adapter", adapter()),
                ]));
            }
        }
        tracks
    }

    fn config(&self) -> Json {
        object([
            (
                "$schema",
                text("https://jbrowse.org/jb2/schema/v5/config.json"),
            ),
            (
                "plugins",
                Json::List(vec![object([
                    ("name", text("GraphGenomeView")),
                    ("esmUrl", text(PLUGIN_URL)),
                ])]),
            ),
            ("tracks", Json::List(self.tracks())),
        ])
    }
}

fn joined<T>(handle: thread::ScopedJoinHandle<'_, T>) -> T {
    handle
        .join()
        .unwrap_or_else(|panic| std::panic::resume_unwind(panic))
}

fn write_json(path: &str, value: &Json) -> Result<(), String> {
    fs::write(path, value.pretty()).map_err(|e| format!("{path}: {e}"))
}

pub fn run(options: &Options) -> Result<(), String> {
    let prefix = options.prefix.as_str();
    let forced = options.reference.is_some() || options.snarls.is_some();
    let (bubbler, tee, missing) = match (!forced).then(Bubbler::spawn) {
        Some(Ok((bubbler, tee))) => (Some(bubbler), Some(tee), None),
        Some(Err(e)) => (None, None, Some(e)),
        None => (None, None, None),
    };
    let mut sniffer = Sniffer::new(crate::open_input(&options.graph)?, tee);
    let graph = Graph::read(BufReader::with_capacity(1 << 20, &mut sniffer))?;
    let sniffed = sniffer.finish();
    let (graph, placed) = crate::place_graph(&options.graph, graph, options.reference.as_deref())?;
    let route = if forced {
        Route::Paths
    } else {
        sniffed.ok_or_else(|| format!("{}: no S lines", options.graph))?
    };
    let (name, default_tier) = match route {
        Route::Rgfa => ("rgfa", 10000),
        Route::Paths => ("paths", 50),
    };
    eprintln!("{name} graph: {}", options.graph);
    let tier = options.tier.unwrap_or(default_tier);

    let (graph, placed, snarls) = (&graph, &placed, options.snarls.as_deref());
    let (sample, bubbles) = thread::scope(|scope| {
        let bubbles = scope.spawn(move || bubble_file(route, bubbler, missing, snarls, prefix));
        let fine = scope.spawn(|| {
            crate::write_index(graph, placed, Layout::Anchored, prefix)
                .map(|(nodes, _)| reference_sample(&nodes))
        });
        let contig = scope.spawn(|| {
            let contig = format!("{prefix}.contig");
            let (segs, links) = crate::write_index(graph, placed, Layout::Contig, &contig)?;
            alleles::from_rows(
                &contig,
                segs.iter().map(Row::text),
                links.iter().map(Row::text),
                &format!("{prefix}.alleles.bed.gz"),
            )
        });
        let coarse = scope.spawn(|| {
            let tier_prefix = format!("{prefix}.fold{tier}");
            crate::write_tier(graph, placed, tier, Layout::Anchored, &tier_prefix)
        });
        let sample = joined(fine)?;
        joined(contig)?;
        joined(coarse)?;
        Ok::<_, String>((sample, joined(bubbles)?))
    })?;

    let built = Built {
        base: basename(prefix),
        assembly: options
            .assembly
            .clone()
            .or_else(|| sample.clone())
            .unwrap_or_else(|| "reference".into()),
        sample,
        tier,
        bubbles,
    };
    write_json(&format!("{prefix}.graph.json"), &built.manifest())?;
    write_json(&format!("{prefix}.config.json"), &built.config())?;
    eprintln!(
        "{} tracks on assembly '{}'{} -> {prefix}.graph.json, {prefix}.config.json",
        built.tracks().len(),
        built.assembly,
        built
            .sample
            .as_ref()
            .map_or_else(String::new, |s| format!(", graph sample '{s}'"))
    );
    Ok(())
}
