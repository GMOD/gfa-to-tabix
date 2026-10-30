// Everything a JBrowse graph track reads, from one read of the graph. Ports
// jbrowse-components' build_pangenome_graph.sh, which read the graph four times.

use std::collections::HashSet;
use std::fs;
use std::io::{self, BufReader, Read, Write};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::thread::{self, JoinHandle};

use crate::bed::{self, Format, Layout, Line, Row};
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
    pub max_component: Option<u64>,
    pub format: Format,
}

#[derive(Clone, Copy, Debug, PartialEq)]
enum Route {
    Rgfa,
    Paths,
}

const SN_TAG: &[u8] = b"\tSN:Z:";
const NO_BUBBLES: &str = "so no bubble file or bubble tracks for this graph";

// Copies the GFA to `tee` as it passes through, until an S line with no SN tag
// shows the graph is no rGFA, which `gfatools bubble` needs. A
// Minigraph-Cactus base-level GFA tags only its reference walk's segments.
struct Sniffer<R> {
    inner: R,
    tee: Option<ChildStdin>,
    untagged: bool,
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
            untagged: false,
            line_start: true,
            in_segment: false,
            tagged: false,
            tail: Vec::new(),
        }
    }

    fn end_segment(&mut self) {
        if !self.tagged {
            self.untagged = true;
            self.tee = None;
        }
    }

    fn scan(&mut self, mut bytes: &[u8]) {
        while !self.untagged && !bytes.is_empty() {
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

    // Closes the tee, so its reader sees the end of the text. True when every
    // S line has an SN tag.
    fn finish(mut self) -> bool {
        if !self.untagged && self.in_segment && !self.line_start {
            self.end_segment();
        }
        self.tee = None;
        !self.untagged
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
struct Bubbler {
    child: Child,
    stdout: JoinHandle<io::Result<Vec<u8>>>,
    stderr: JoinHandle<io::Result<Vec<u8>>>,
}

fn read_all(mut pipe: impl Read + Send + 'static) -> JoinHandle<io::Result<Vec<u8>>> {
    thread::spawn(move || {
        let mut out = Vec::new();
        pipe.read_to_end(&mut out).map(|_| out)
    })
}

fn join<T>(handle: JoinHandle<T>) -> T {
    handle
        .join()
        .unwrap_or_else(|panic| std::panic::resume_unwind(panic))
}

impl Bubbler {
    fn spawn() -> io::Result<(Bubbler, ChildStdin)> {
        let mut child = Command::new("gfatools")
            .args(["bubble", "-"])
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped())
            .spawn()?;
        let stdin = child.stdin.take().expect("stdin is piped");
        let stdout = read_all(child.stdout.take().expect("stdout is piped"));
        let stderr = read_all(child.stderr.take().expect("stderr is piped"));
        Ok((
            Bubbler {
                child,
                stdout,
                stderr,
            },
            stdin,
        ))
    }

    // The bubbles, or the note that says why there are none
    fn finish(mut self) -> Result<Vec<u8>, String> {
        let fail = |e: io::Error| format!("gfatools bubble: {e}, {NO_BUBBLES}");
        let status = self.child.wait().map_err(fail)?;
        let stdout = join(self.stdout).map_err(fail)?;
        let stderr = join(self.stderr).map_err(fail)?;
        if !status.success() {
            let stderr = String::from_utf8_lossy(&stderr);
            let lines: Vec<&str> = stderr
                .lines()
                .map(str::trim)
                .filter(|l| !l.is_empty())
                .collect();
            let said = match lines[lines.len().saturating_sub(3)..].join("; ") {
                tail if tail.is_empty() => tail,
                tail => format!(": {tail}"),
            };
            return Err(format!(
                "gfatools bubble failed ({status}){said}, {NO_BUBBLES}"
            ));
        }
        Ok(stdout)
    }

    fn cancel(mut self) {
        let _ = self.child.kill();
        let _ = self.child.wait();
    }
}

fn bubble_rows(text: &[u8]) -> Result<Vec<Line>, String> {
    let mut rows: Vec<Line> = Vec::new();
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
        rows.push(Line {
            chrom: fields[0].to_vec(),
            start: number(1)?,
            end: number(2)?,
            text: [line, b"\n"].concat(),
        });
    }
    Ok(rows)
}

// `gfatools` is the bubbler, or the note that says why there is none.
fn bubble_file(
    route: Route,
    gfatools: Result<Bubbler, String>,
    snarls: Option<&str>,
    flipped: &HashSet<&[u8]>,
    prefix: &str,
) -> Result<bool, String> {
    let path = format!("{prefix}.bubbles.bed.gz");
    match (route, gfatools.and_then(Bubbler::finish), snarls) {
        (Route::Rgfa, Ok(text), _) => match bubble_rows(&text) {
            Ok(mut rows) => {
                let index = bed::write_lines(&path, b"", &mut rows)?;
                eprintln!(
                    "{} bubbles from gfatools -> {path} (+ .{index})",
                    rows.len()
                );
                Ok(true)
            }
            Err(why) => {
                eprintln!("note: {why}, {NO_BUBBLES}");
                Ok(false)
            }
        },
        (Route::Rgfa, Err(note), _) => {
            eprintln!("note: {note}");
            Ok(false)
        }
        (Route::Paths, _, Some(snarls)) => bubbles::run(snarls, prefix, 2, flipped).map(|()| true),
        (Route::Paths, _, None) => {
            eprintln!("note: no --snarls given, {NO_BUBBLES}");
            Ok(false)
        }
    }
}

// The PanSN sample of the first reference segment among format 1's node rows,
// as `GRCh38` from `GRCh38#0#chr1`; None for a bare name.
fn reference_sample(nodes: &[String]) -> Option<String> {
    let text = nodes
        .iter()
        .find(|line| line.split('\t').nth(4) == Some("0"))?;
    let name = text.split('\t').next()?;
    let parts: Vec<&str> = name.split('#').collect();
    (parts.len() >= 3 && !parts[0].is_empty()).then(|| parts[0].to_string())
}

fn basename(prefix: &str) -> &str {
    prefix.rsplit('/').next().unwrap_or(prefix)
}

// Which files the tracks read have a `.csi` index rather than a `.tbi`
struct Csi {
    graph: bool,
    coarse: bool,
    alleles: bool,
    bubbles: bool,
}

fn index_suffix(format: Format) -> &'static str {
    match format {
        Format::One => ".segs.bed.gz",
        Format::Two => ".graph.bed.gz",
    }
}

fn has_csi(path: &str) -> bool {
    std::path::Path::new(&format!("{path}.csi")).exists()
}

struct Built<'a> {
    base: &'a str,
    sample: Option<String>,
    assembly: String,
    format: Format,
    tier: i64,
    bubbles: bool,
    csi: Csi,
}

impl Built<'_> {
    fn manifest(&self) -> Json {
        let base = self.base;
        let tier = self.tier;
        let file = |present: bool, name: String| if present { text(name) } else { Json::Null };
        let format = || Json::Number(self.format_number());
        object([
            ("schema", Json::Number(1)),
            ("reference", self.sample.clone().map_or(Json::Null, text)),
            ("format", format()),
            ("index", text(base)),
            ("contig", text(format!("{base}.contig"))),
            (
                "tier",
                object([
                    ("prefix", text(format!("{base}.fold{tier}"))),
                    ("foldBelowBp", Json::Number(tier)),
                    ("format", format()),
                ]),
            ),
            (
                "bubbles",
                file(self.bubbles, format!("{base}.bubbles.bed.gz")),
            ),
            ("alleles", text(format!("{base}.alleles.bed.gz"))),
        ])
    }

    fn format_number(&self) -> i64 {
        match self.format {
            Format::One => 1,
            Format::Two => 2,
        }
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
        let csi = |on: bool| on.then_some(("csi", Json::Bool(true)));
        let format = || (self.format == Format::Two).then_some(("format", Json::Number(2)));
        let mut graph_adapter = vec![("type", text("RgfaTabixAdapter")), ("uri", text(base))];
        graph_adapter.extend(format());
        graph_adapter.extend(csi(self.csi.graph));
        graph_adapter.extend(pansn());
        let mut coarse = vec![
            ("uri", text(format!("{base}.fold{}", self.tier))),
            ("foldBelowBp", Json::Number(self.tier)),
        ];
        coarse.extend(format());
        if self.csi.coarse != self.csi.graph {
            coarse.push(("csi", Json::Bool(self.csi.coarse)));
        }
        graph_adapter.push(("coarse", object(coarse)));
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
                    object(
                        [
                            ("type", text("BedTabixAdapter")),
                            ("uri", text(format!("{base}.alleles.bed.gz"))),
                        ]
                        .into_iter()
                        .chain(csi(self.csi.alleles)),
                    ),
                ),
            ]),
        ];
        if self.bubbles {
            let adapter = || {
                let mut fields = vec![
                    ("type", text("MinigraphBubbleAdapter")),
                    ("uri", text(format!("{base}.bubbles.bed.gz"))),
                ];
                fields.extend(csi(self.csi.bubbles));
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
                    ("storePlugin", text("GraphGenomeView")),
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
    let (bubbler, tee) = match (!forced).then(Bubbler::spawn) {
        Some(Ok((bubbler, tee))) => (Ok(bubbler), Some(tee)),
        spawned => {
            let why = match spawned {
                Some(Err(e)) if e.kind() != io::ErrorKind::NotFound => format!("gfatools: {e}"),
                _ => "gfatools is not on PATH".into(),
            };
            let install = "Install it from https://github.com/lh3/gfatools";
            (Err(format!("{why}, {NO_BUBBLES}. {install}")), None)
        }
    };
    let mut sniffer = Sniffer::new(crate::open_input(&options.graph)?, tee);
    let graph = Graph::read(BufReader::with_capacity(1 << 20, &mut sniffer))?;
    let tagged = sniffer.finish();
    let (mut graph, placed) =
        crate::place_graph(&options.graph, graph, options.reference.as_deref())?;
    // The rows need no paths, which hold most of a pggb graph's memory.
    graph.paths = Vec::new();
    let route = if placed.from_tags && options.snarls.is_none() {
        Route::Rgfa
    } else {
        Route::Paths
    };
    let gfatools = match bubbler {
        Ok(bubbler) if route == Route::Rgfa && tagged => Ok(bubbler),
        Ok(bubbler) => {
            bubbler.cancel();
            Err(format!(
                "not every S line has an SN tag, which gfatools bubble needs, {NO_BUBBLES}"
            ))
        }
        Err(why) => Err(why),
    };
    let (name, default_tier) = match route {
        Route::Rgfa => ("rgfa", 10000),
        Route::Paths => ("paths", 50),
    };
    eprintln!("{name} graph: {}", options.graph);
    let tier = options.tier.unwrap_or(default_tier);

    let flipped: HashSet<&[u8]> = graph
        .node_ids
        .iter()
        .zip(&placed.flipped)
        .filter(|&(_, &flipped)| flipped)
        .map(|(id, _)| id.as_slice())
        .collect();
    let (graph, placed, snarls) = (&graph, &placed, options.snarls.as_deref());
    let flipped = &flipped;
    let (sample, bubbles) = thread::scope(|scope| {
        let bubbles = scope.spawn(move || bubble_file(route, gfatools, snarls, flipped, prefix));
        let fine = scope.spawn(|| match options.format {
            Format::One => crate::write_index(
                graph,
                placed,
                Layout::Anchored,
                options.max_component,
                prefix,
            )
            .map(drop),
            Format::Two => crate::write_graph(
                graph,
                placed,
                Layout::Anchored,
                options.max_component,
                prefix,
            )
            .map(drop),
        });
        let contig = scope.spawn(|| {
            let contig = format!("{prefix}.contig");
            let (nodes, links) = match options.format {
                Format::One => {
                    let (nodes, links) =
                        crate::write_index(graph, placed, Layout::Contig, None, &contig)?;
                    let text = |rows: Vec<Row>| rows.iter().map(Row::text).collect();
                    (text(nodes), text(links))
                }
                Format::Two => {
                    let rows = crate::write_graph(graph, placed, Layout::Contig, None, &contig)?;
                    alleles::split_graph(&contig, rows.iter().map(|row| Ok(row.text())))?
                }
            };
            let sample = reference_sample(&nodes);
            alleles::from_rows(
                &contig,
                nodes.into_iter(),
                links.into_iter(),
                &format!("{prefix}.alleles.bed.gz"),
            )?;
            Ok::<_, String>(sample)
        });
        let coarse = scope.spawn(|| {
            let tier_prefix = format!("{prefix}.fold{tier}");
            crate::write_tier(
                graph,
                placed,
                tier,
                Layout::Anchored,
                options.max_component,
                options.format,
                &tier_prefix,
            )
        });
        joined(fine)?;
        let sample = joined(contig)?;
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
        format: options.format,
        tier,
        bubbles,
        csi: Csi {
            graph: has_csi(&format!("{prefix}{}", index_suffix(options.format))),
            coarse: has_csi(&format!(
                "{prefix}.fold{tier}{}",
                index_suffix(options.format)
            )),
            alleles: has_csi(&format!("{prefix}.alleles.bed.gz")),
            bubbles: has_csi(&format!("{prefix}.bubbles.bed.gz")),
        },
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

#[cfg(test)]
mod tests {
    use super::*;

    struct ByteAtATime<'a>(&'a [u8]);

    impl Read for ByteAtATime<'_> {
        fn read(&mut self, buf: &mut [u8]) -> io::Result<usize> {
            let Some((&first, rest)) = self.0.split_first() else {
                return Ok(0);
            };
            buf[0] = first;
            self.0 = rest;
            Ok(1)
        }
    }

    fn tagged(text: &str) -> bool {
        let mut sniffer = Sniffer::new(ByteAtATime(text.as_bytes()), None);
        io::copy(&mut sniffer, &mut io::sink()).unwrap();
        sniffer.finish()
    }

    #[test]
    fn a_tag_split_across_reads_is_found() {
        assert!(tagged("S\ts1\tACGT\tSN:Z:chr1\nS\ts2\tAC\tSN:Z:chr1"));
        assert!(!tagged("S\ts1\tACGT\tSN:Z:chr1\nS\ts2\tAC\tLN:i:2\n"));
        assert!(tagged("S\ts1\tSN:Z\tSN:Z:x\n"));
        assert!(!tagged("S\ts1\tSN:Z\n"));
    }
}
