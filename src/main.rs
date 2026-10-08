mod anchor;
mod bed;
mod gfa;
mod parallel_bgzf;
mod place;
mod sorter;
mod walks;

use std::env;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Read};
use std::process;

use flate2::read::MultiGzDecoder;

use bed::Layout;
use gfa::Graph;

const USAGE: &str = "usage: gfa-to-tabix [-h] [--version] [--reference REFERENCE] [--layout LAYOUT]\n                    [--walks --refs REFS [--chunk BP] [--cap STEPS] [--settle BP]\n                    [--sequences]] [-o PREFIX] gfa";

const HELP: &str = "
Index a pangenome graph's GFA by genome coordinate: write its nodes and links
as two bgzip-compressed, Tabix-indexed BED files, which a JBrowse graph track
reads by region. https://github.com/GMOD/gfa-to-tabix

An rGFA (minigraph, or the minigraph stage of Minigraph-Cactus) gives every
node a coordinate in its SN/SO/SR tags. A plain GFA (pggb, odgi, vg, base-level
Minigraph-Cactus) gets coordinates from its P or W lines instead: each node
takes its position on the first path to reach it, reference paths first.

positional arguments:
  gfa                   GFA file, gz accepted; - reads stdin

options:
  -h, --help            show this help message and exit
  --version             show the version and exit
  --reference REFERENCE
                        for a plain GFA, the reference: a PanSN sample (GRCh38),
                        an assembly (HG002#1) or a path name. Default: the
                        first path in the file. Given with an rGFA, coordinates
                        come from the paths, not the tags
  --layout LAYOUT       anchored (default) files every node under the reference
                        interval its bubble hangs from, so one query per file
                        returns the whole graph under a region. contig files
                        every node under its own coordinate, as 0.1.0 did
  -o, --out PREFIX      write PREFIX.segs.bed.gz and PREFIX.links.bed.gz, each
                        with a .tbi; default the input name without .gfa[.gz]

walks (a base-level GFA with integer node ids and W or P lines):
  --walks               instead write PREFIX.walks.bed.gz, PREFIX.nodes.bed.gz
                        and PREFIX.links.bed.gz: every path cut into pieces
                        filed under fixed chunks of each reference, with the
                        nodes and links the pieces touch. Reads the GFA twice
  --refs REFS           comma-separated reference samples, e.g. GRCh38,CHM13
  --chunk BP            chunk size on the reference (default 65536)
  --cap STEPS           most steps in one row (default 8192)
  --settle BP           a run of reference steps in another chunk shorter than
                        this stays in the piece it interrupts (default chunk/2)
  --sequences           add each node's sequence to its rows as SQ:Z:";

struct Args {
    gfa: String,
    reference: Option<String>,
    prefix: Option<String>,
    layout: Option<Layout>,
    walks: bool,
    refs: Option<String>,
    chunk: Option<u64>,
    cap: Option<usize>,
    settle: Option<u64>,
    sequences: bool,
}

fn positive<T: std::str::FromStr + PartialOrd + Default>(name: &str, value: &str) -> T {
    match value.parse::<T>() {
        Ok(n) if n > T::default() => n,
        _ => fail(&format!(
            "argument {name}: {value} is not a positive integer"
        )),
    }
}

fn fail(message: &str) -> ! {
    eprintln!("{USAGE}\ngfa-to-tabix: error: {message}");
    process::exit(2);
}

fn parse_args() -> Args {
    let mut gfa = None;
    let mut reference = None;
    let mut prefix = None;
    let mut layout = None;
    let (mut walks, mut sequences) = (false, false);
    let (mut refs, mut chunk, mut cap, mut settle) = (None, None, None, None);
    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        let (flag, inline) = match arg.split_once('=') {
            Some((flag, value)) if flag.starts_with("--") => {
                (flag.to_string(), Some(value.to_string()))
            }
            _ => (arg.clone(), None),
        };
        let mut value = |name: &str| {
            inline
                .clone()
                .or_else(|| args.next())
                .unwrap_or_else(|| fail(&format!("argument {name}: expected one argument")))
        };
        match flag.as_str() {
            "-h" | "--help" | "--version" | "--walks" | "--sequences" if inline.is_some() => {
                fail(&format!("argument {flag}: takes no value"))
            }
            "-h" | "--help" => {
                println!("{USAGE}\n{HELP}");
                process::exit(0);
            }
            "--version" => {
                println!("gfa-to-tabix {}", env!("CARGO_PKG_VERSION"));
                process::exit(0);
            }
            "--reference" => reference = Some(value("--reference")),
            "--layout" => {
                layout = match value("--layout").as_str() {
                    "anchored" => Some(Layout::Anchored),
                    "contig" => Some(Layout::Contig),
                    other => fail(&format!(
                        "argument --layout: {other} is not anchored or contig"
                    )),
                }
            }
            "-o" | "--out" => prefix = Some(value("-o/--out")),
            "--walks" => walks = true,
            "--sequences" => sequences = true,
            "--refs" => refs = Some(value("--refs")),
            "--chunk" => chunk = Some(positive("--chunk", &value("--chunk"))),
            "--cap" => cap = Some(positive("--cap", &value("--cap"))),
            "--settle" => {
                let given = value("--settle");
                settle = Some(given.parse().unwrap_or_else(|_| {
                    fail(&format!(
                        "argument --settle: {given} is not a non-negative integer"
                    ))
                }))
            }
            "-" => gfa = Some(arg),
            _ if flag.starts_with('-') => fail(&format!("unrecognized argument: {arg}")),
            _ if gfa.is_some() => fail(&format!("unrecognized argument: {arg}")),
            _ => gfa = Some(arg),
        }
    }
    let Some(gfa) = gfa else {
        fail("the following arguments are required: gfa")
    };
    if walks {
        if refs.is_none() {
            fail("--walks needs --refs");
        }
        if reference.is_some() || layout.is_some() {
            fail("--reference and --layout do not apply with --walks; name references with --refs");
        }
    } else if refs.is_some() || chunk.is_some() || cap.is_some() || settle.is_some() || sequences {
        fail("--refs, --chunk, --cap, --settle and --sequences apply only with --walks");
    }
    Args {
        gfa,
        reference,
        prefix,
        layout,
        walks,
        refs,
        chunk,
        cap,
        settle,
        sequences,
    }
}

fn open_input(path: &str) -> Result<Box<dyn BufRead>, String> {
    let mut raw: Box<dyn Read> = if path == "-" {
        Box::new(io::stdin())
    } else {
        Box::new(File::open(path).map_err(|e| format!("{path}: {e}"))?)
    };
    let mut magic = Vec::with_capacity(2);
    (&mut raw)
        .take(2)
        .read_to_end(&mut magic)
        .map_err(|e| e.to_string())?;
    let gzipped = magic == [0x1f, 0x8b];
    let stream = io::Cursor::new(magic).chain(raw);
    Ok(if gzipped {
        Box::new(BufReader::with_capacity(
            1 << 20,
            MultiGzDecoder::new(stream),
        ))
    } else {
        Box::new(BufReader::with_capacity(1 << 20, stream))
    })
}

fn default_prefix(gfa: &str) -> Result<String, String> {
    if gfa == "-" {
        return Err("reading stdin needs -o PREFIX".into());
    }
    let stem = gfa.strip_suffix(".gz").unwrap_or(gfa);
    let stem = stem
        .strip_suffix(".rgfa")
        .or_else(|| stem.strip_suffix(".gfa"))
        .unwrap_or(stem);
    Ok(stem.to_string())
}

fn run(args: &Args) -> Result<(), String> {
    let prefix = match &args.prefix {
        Some(prefix) => prefix.clone(),
        None => default_prefix(&args.gfa)?,
    };
    if args.walks {
        let chunk = args.chunk.unwrap_or(65536);
        let mut refs: Vec<String> = Vec::new();
        for name in args.refs.as_deref().unwrap_or("").split(',') {
            if !name.is_empty() && !refs.iter().any(|r| r == name) {
                refs.push(name.to_string());
            }
        }
        if refs.is_empty() {
            return Err("--refs names no sample".into());
        }
        let options = walks::Options {
            refs,
            chunk,
            cap: args.cap.unwrap_or(8192),
            settle: args.settle.unwrap_or(chunk / 2),
            sequences: args.sequences,
        };
        return walks::run(&args.gfa, &prefix, &options);
    }
    let layout = args.layout.unwrap_or(Layout::Anchored);
    let graph = Graph::read(open_input(&args.gfa)?)?;
    if graph.segment_count() == 0 {
        return Err(format!("{}: no S lines", args.gfa));
    }
    let use_paths = args.reference.is_some() || (!graph.is_rgfa() && !graph.paths.is_empty());
    let placed = if use_paths || !graph.has_tags() {
        place::from_paths(&graph, args.reference.as_deref())?
    } else {
        place::from_tags(&graph)
    };
    for note in &placed.notes {
        eprintln!("{note}");
    }

    let spans = match layout {
        Layout::Anchored => anchor::anchored(&graph, &placed.nodes),
        Layout::Contig => anchor::by_contig(&placed.nodes),
    };
    let mut nodes = bed::node_rows(&graph, &placed.nodes, &spans, layout);
    let (mut links, skipped) = bed::link_rows(&graph, &placed.nodes, &spans, layout);
    bed::sort(&mut nodes, &spans);
    bed::sort(&mut links, &spans);
    let nodes_path = format!("{prefix}.segs.bed.gz");
    let links_path = format!("{prefix}.links.bed.gz");
    bed::write(&nodes_path, &nodes, &spans)?;
    bed::write(&links_path, &links, &spans)?;

    let placed_nodes = placed.nodes.iter().flatten().count();
    eprintln!("{}", placed.summary);
    eprintln!(
        "{placed_nodes} nodes, {} links -> {nodes_path}, {links_path} (+ .tbi)",
        graph.links.len() - skipped
    );
    if skipped > 0 {
        eprintln!("{skipped} links left out: a node with no coordinate");
    }
    let unplaced = graph.segment_count() - placed_nodes;
    if unplaced > 0 {
        eprintln!("{unplaced} nodes left out: no path visits them, or no SN tag");
    }
    Ok(())
}

fn main() {
    let args = parse_args();
    if let Err(message) = run(&args) {
        eprintln!("gfa-to-tabix: error: {message}");
        process::exit(1);
    }
}
