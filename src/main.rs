mod bed;
mod gfa;
mod place;

use std::env;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Read};
use std::process;

use flate2::read::MultiGzDecoder;

use gfa::Graph;

const USAGE: &str = "usage: gfa-to-tabix [-h] [--version] [--reference REFERENCE] [-o PREFIX] gfa";

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
  -o, --out PREFIX      write PREFIX.segs.bed.gz and PREFIX.links.bed.gz, each
                        with a .tbi; default the input name without .gfa[.gz]";

struct Args {
    gfa: String,
    reference: Option<String>,
    prefix: Option<String>,
}

fn fail(message: &str) -> ! {
    eprintln!("{USAGE}\ngfa-to-tabix: error: {message}");
    process::exit(2);
}

fn parse_args() -> Args {
    let mut gfa = None;
    let mut reference = None;
    let mut prefix = None;
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
            "-h" | "--help" => {
                println!("{USAGE}\n{HELP}");
                process::exit(0);
            }
            "--version" => {
                println!("gfa-to-tabix {}", env!("CARGO_PKG_VERSION"));
                process::exit(0);
            }
            "--reference" => reference = Some(value("--reference")),
            "-o" | "--out" => prefix = Some(value("-o/--out")),
            "-" => gfa = Some(arg),
            _ if flag.starts_with('-') => fail(&format!("unrecognized argument: {arg}")),
            _ if gfa.is_some() => fail(&format!("unrecognized argument: {arg}")),
            _ => gfa = Some(arg),
        }
    }
    let Some(gfa) = gfa else {
        fail("the following arguments are required: gfa")
    };
    Args {
        gfa,
        reference,
        prefix,
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

    let mut nodes = bed::node_rows(&graph, &placed.nodes);
    let (mut links, skipped) = bed::link_rows(&graph, &placed.nodes);
    bed::sort(&mut nodes);
    bed::sort(&mut links);
    let nodes_path = format!("{prefix}.segs.bed.gz");
    let links_path = format!("{prefix}.links.bed.gz");
    bed::write(&nodes_path, &nodes)?;
    bed::write(&links_path, &links)?;

    eprintln!("{}", placed.summary);
    eprintln!(
        "{} nodes, {} links -> {nodes_path}, {links_path} (+ .tbi)",
        nodes.len(),
        graph.links.len() - skipped
    );
    if skipped > 0 {
        eprintln!("{skipped} links left out: a node with no coordinate");
    }
    let unplaced = graph.segment_count() - nodes.len();
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
