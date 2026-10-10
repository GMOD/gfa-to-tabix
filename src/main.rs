mod alleles;
mod anchor;
mod bed;
mod bubbles;
mod fold;
mod gfa;
mod parallel_bgzf;
mod paths;
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

const USAGE: &str = "usage: gfa-to-tabix alleles|bubbles|paths|fold [-h] ...  (subcommands)\n       gfa-to-tabix [-h] [--version] [--reference REFERENCE] [--layout LAYOUT]\n                    [--walks --refs REFS [--chunk BP] [--cap STEPS] [--settle BP]\n                    [--sequences]] [-o PREFIX] gfa";

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
  --walks               instead write PREFIX.SAMPLE.walks.bed.gz,
                        PREFIX.SAMPLE.nodes.bed.gz and
                        PREFIX.SAMPLE.links.bed.gz for each SAMPLE in --refs:
                        every path cut into pieces filed under fixed chunks of
                        that reference, with the nodes and links the pieces
                        touch. Reads the GFA twice
  --refs REFS           comma-separated reference samples, e.g. GRCh38,CHM13
  --chunk BP            chunk size on the reference (default 65536)
  --cap STEPS           most steps in one row (default 8192)
  --settle BP           a run of reference steps in another chunk shorter than
                        this stays in the piece it interrupts (default 0, off)
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

// The graph and each segment's place on a genome: from the rGFA's tags, or from
// its paths for a plain GFA or when a reference is named
fn load_placed(gfa: &str, reference: Option<&str>) -> Result<(Graph, place::Placed), String> {
    let graph = Graph::read(open_input(gfa)?)?;
    if graph.segment_count() == 0 {
        return Err(format!("{gfa}: no S lines"));
    }
    let use_paths = reference.is_some() || (!graph.is_rgfa() && !graph.paths.is_empty());
    let placed = if use_paths || !graph.has_tags() {
        place::from_paths(&graph, reference)?
    } else {
        place::from_tags(&graph)
    };
    for note in &placed.notes {
        eprintln!("{note}");
    }
    Ok((graph, placed))
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
            settle: args.settle.unwrap_or(0),
            sequences: args.sequences,
        };
        return walks::run(&args.gfa, &prefix, &options);
    }
    let layout = args.layout.unwrap_or(Layout::Anchored);
    let (graph, placed) = load_placed(&args.gfa, args.reference.as_deref())?;
    write_index(&graph, &placed, layout, &prefix)
}

fn write_index(
    graph: &Graph,
    placed: &place::Placed,
    layout: Layout,
    prefix: &str,
) -> Result<(), String> {
    let spans = match layout {
        Layout::Anchored => anchor::anchored(graph, &placed.nodes),
        Layout::Contig => anchor::by_contig(&placed.nodes),
    };
    let mut nodes = bed::node_rows(graph, &placed.nodes, &spans, layout);
    let (mut links, skipped) = bed::link_rows(graph, &placed.nodes, &spans, layout);
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

const ALLELES_USAGE: &str = "usage: gfa-to-tabix alleles [-h] PREFIX

Read PREFIX.segs.bed.gz and PREFIX.links.bed.gz, as this tool writes them with
--layout contig, and write PREFIX.alleles.bed.gz (+ .tbi): one row per allele
the graph holds, anchored on the reference, with a CIGAR that states its size.
The two files are all it needs, so a hosted pair works without the graph.";

const BUBBLES_USAGE: &str =
    "usage: gfa-to-tabix bubbles [-h] [--min-alleles N] -o PREFIX --snarls VCF

Write PREFIX.bubbles.bed.gz (+ .tbi) from a `vg deconstruct` snarl VCF (gz
accepted; `pggb -V` writes one too), in the layout `gfatools bubble` writes for
an rGFA. gfatools finds no bubbles on a plain GFA, and a snarl VCF carries each
bubble's reference span and alleles. Keeps the top-level snarls, none of which
overlap.

options:
  --snarls VCF       the snarl VCF
  -o, --out PREFIX   output prefix
  --min-alleles N    skip a snarl with fewer traversals (default 2)";

const PATHS_USAGE: &str =
    "usage: gfa-to-tabix paths [-h] -o PREFIX REFERENCE.call.bed [SAMPLE.call.bed ...]

Write PREFIX.bed.gz (+ .tbi) from the files `minigraph -cxasm --call graph.rgfa
sample.fa` writes, one per sample and the reference's first: a row per bubble
and sample, with the sample's path, its length change against the reference and
how many samples carry each allele. Each file's name, without .call.bed, is its
sample, and the reference's names the PanSN prefix the rows drop from their
contigs. Every file must have the same lines, which minigraph writes.";

fn subcommand_fail(usage: &str, message: &str) -> ! {
    eprintln!("{usage}\ngfa-to-tabix: error: {message}");
    process::exit(2)
}

fn finish(result: Result<(), String>) -> ! {
    if let Err(message) = result {
        eprintln!("gfa-to-tabix: error: {message}");
        process::exit(1);
    }
    process::exit(0)
}

fn alleles_command(args: Vec<String>) -> ! {
    match args.as_slice() {
        [flag] if flag == "-h" || flag == "--help" => {
            println!("{ALLELES_USAGE}");
            process::exit(0)
        }
        [prefix] if !prefix.starts_with('-') => finish(alleles::run(prefix)),
        _ => subcommand_fail(ALLELES_USAGE, "expected one PREFIX"),
    }
}

fn bubbles_command(args: Vec<String>) -> ! {
    let (mut snarls, mut prefix, mut min_alleles) = (None, None, 2usize);
    let mut args = args.into_iter();
    while let Some(arg) = args.next() {
        let mut value = |name: &str| {
            args.next()
                .unwrap_or_else(|| subcommand_fail(BUBBLES_USAGE, &format!("{name} needs a value")))
        };
        match arg.as_str() {
            "-h" | "--help" => {
                println!("{BUBBLES_USAGE}");
                process::exit(0)
            }
            "--snarls" => snarls = Some(value("--snarls")),
            "-o" | "--out" => prefix = Some(value("-o/--out")),
            "--min-alleles" => {
                let given = value("--min-alleles");
                min_alleles = given.parse().unwrap_or_else(|_| {
                    subcommand_fail(
                        BUBBLES_USAGE,
                        &format!("--min-alleles: {given} is not a non-negative integer"),
                    )
                })
            }
            other => subcommand_fail(BUBBLES_USAGE, &format!("unrecognized argument: {other}")),
        }
    }
    let (Some(snarls), Some(prefix)) = (snarls, prefix) else {
        subcommand_fail(BUBBLES_USAGE, "--snarls and -o are required")
    };
    finish(bubbles::run(&snarls, &prefix, min_alleles))
}

const FOLD_USAGE: &str = "usage: gfa-to-tabix fold [-h] --below BP [--reference REFERENCE] [--layout LAYOUT] -o PREFIX gfa

Write PREFIX.segs.bed.gz and PREFIX.links.bed.gz (+ .tbi) for the graph with
every variant under BP folded into the reference: the coarse tier a graph track
draws once zoomed out past the fine index. It keeps the backbone, every allele
whose own length or the reference it replaces reaches BP, and the shortest way
from each one's ends back to the backbone. The graph track folds each cut it
draws the same way, at ten of the linear view's pixels, so a tier folded at BP
and handed over at BP / 10 bp per pixel draws what the fine cut drew just below
the handover. --layout should match the fine index's.

  --below BP         the size to fold under
  --reference NAME   for a plain GFA, the backbone path, as for the index
  --layout LAYOUT    anchored (default) or contig
  -o, --out PREFIX   output prefix";

fn fold_command(args: Vec<String>) -> ! {
    let (mut gfa, mut prefix, mut below, mut reference) = (None, None, None, None);
    let mut layout = Layout::Anchored;
    let mut args = args.into_iter();
    while let Some(arg) = args.next() {
        let mut value = |name: &str| {
            args.next()
                .unwrap_or_else(|| subcommand_fail(FOLD_USAGE, &format!("{name} needs a value")))
        };
        match arg.as_str() {
            "-h" | "--help" => {
                println!("{FOLD_USAGE}");
                process::exit(0)
            }
            "--below" => {
                let given = value("--below");
                below = Some(
                    given
                        .parse::<i64>()
                        .ok()
                        .filter(|n| *n > 0)
                        .unwrap_or_else(|| {
                            subcommand_fail(
                                FOLD_USAGE,
                                &format!("--below: {given} is not a positive integer"),
                            )
                        }),
                )
            }
            "--reference" => reference = Some(value("--reference")),
            "--layout" => {
                layout = match value("--layout").as_str() {
                    "anchored" => Layout::Anchored,
                    "contig" => Layout::Contig,
                    other => subcommand_fail(
                        FOLD_USAGE,
                        &format!("--layout: {other} is not anchored or contig"),
                    ),
                }
            }
            "-o" | "--out" => prefix = Some(value("-o/--out")),
            "-" => gfa = Some(arg),
            other if other.starts_with('-') => {
                subcommand_fail(FOLD_USAGE, &format!("unrecognized argument: {other}"))
            }
            _ => gfa = Some(arg),
        }
    }
    let (Some(gfa), Some(prefix), Some(below)) = (gfa, prefix, below) else {
        subcommand_fail(FOLD_USAGE, "--below, -o and a graph are required")
    };
    finish((|| {
        let (graph, placed) = load_placed(&gfa, reference.as_deref())?;
        let folded = Graph::read(io::Cursor::new(fold::fold(&graph, &placed, below)))?;
        eprintln!(
            "{} segments, {} links -> fold under {below} bp",
            graph.segment_count(),
            graph.links.len()
        );
        write_index(&folded, &place::from_tags(&folded), layout, &prefix)
    })())
}

fn paths_command(args: Vec<String>) -> ! {
    let (mut prefix, mut files) = (None, Vec::new());
    let mut args = args.into_iter();
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-h" | "--help" => {
                println!("{PATHS_USAGE}");
                process::exit(0)
            }
            "-o" | "--out" => {
                prefix = Some(
                    args.next()
                        .unwrap_or_else(|| subcommand_fail(PATHS_USAGE, "-o/--out needs a value")),
                )
            }
            other if other.starts_with('-') => {
                subcommand_fail(PATHS_USAGE, &format!("unrecognized argument: {other}"))
            }
            _ => files.push(arg),
        }
    }
    let Some(prefix) = prefix else {
        subcommand_fail(PATHS_USAGE, "-o is required")
    };
    if files.is_empty() {
        subcommand_fail(PATHS_USAGE, "needs at least the reference's call file")
    }
    finish(paths::run(&prefix, &files))
}

fn main() {
    let mut raw = env::args().skip(1);
    match raw.next().as_deref() {
        Some("alleles") => alleles_command(raw.collect()),
        Some("bubbles") => bubbles_command(raw.collect()),
        Some("paths") => paths_command(raw.collect()),
        Some("fold") => fold_command(raw.collect()),
        _ => {}
    }
    let args = parse_args();
    if let Err(message) = run(&args) {
        eprintln!("gfa-to-tabix: error: {message}");
        process::exit(1);
    }
}
