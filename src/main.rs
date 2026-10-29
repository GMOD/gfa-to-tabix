mod alleles;
mod anchor;
mod bed;
mod bubbles;
mod build;
mod cli;
mod fold;
mod gfa;
mod intern;
mod json;
mod parallel_bgzf;
mod paths;
mod place;
mod routes;
mod sorter;
mod walks;

use std::collections::HashSet;
use std::fs::File;
use std::io::{self, BufRead, BufReader, Read};
use std::process;

use clap::Parser;
use flate2::read::MultiGzDecoder;

use bed::{Format, Layout};
use cli::{Cli, Command};
use gfa::Graph;

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
    place_graph(gfa, Graph::read(open_input(gfa)?)?, reference)
}

fn place_graph(
    gfa: &str,
    mut graph: Graph,
    reference: Option<&str>,
) -> Result<(Graph, place::Placed), String> {
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
    place::flip(&mut graph, &placed.flipped);
    Ok((graph, placed))
}

fn index(cli: Cli) -> Result<(), String> {
    let gfa = cli.gfa.expect("clap requires a graph");
    let prefix = match cli.out {
        Some(prefix) => prefix,
        None => default_prefix(&gfa)?,
    };
    if cli.walks {
        let mut refs: Vec<String> = Vec::new();
        for name in cli.refs.as_deref().unwrap_or("").split(',') {
            if !name.is_empty() && !refs.iter().any(|r| r == name) {
                refs.push(name.to_string());
            }
        }
        if refs.is_empty() {
            return Err("--refs names no sample".into());
        }
        let options = walks::Options {
            refs,
            chunk: cli.chunk.unwrap_or(65536),
            sequences: cli.sequences,
            stay: cli.stay.unwrap_or(311),
            budget: routes::Budget {
                cost: cli.abridge_steps.unwrap_or(1_000_000),
                bytes: cli.abridge_bytes.unwrap_or(3_000_000),
            },
        };
        return walks::run(&gfa, &prefix, &options);
    }
    let layout = cli.layout.unwrap_or(Layout::Anchored);
    let (mut graph, placed) = load_placed(&gfa, cli.reference.as_deref())?;
    // The rows need no paths, which hold most of a pggb graph's memory.
    graph.paths = Vec::new();
    match cli.format {
        Format::One => write_index(&graph, &placed, layout, cli.max_component.0, &prefix).map(drop),
        Format::Two => write_graph(&graph, &placed, layout, cli.max_component.0, &prefix),
    }
}

fn index_rows(
    graph: &Graph,
    placed: &place::Placed,
    layout: Layout,
    max_component: Option<u64>,
    format: Format,
) -> (anchor::Spans, Vec<bed::Row>, Vec<bed::Row>, usize) {
    let spans = match layout {
        Layout::Anchored => anchor::anchored(graph, placed, max_component),
        Layout::Contig => anchor::by_contig(placed),
    };
    let nodes = bed::node_rows(graph, placed, &spans, layout, format);
    let (links, skipped) = bed::link_rows(graph, placed, &spans, layout, format);
    (spans, nodes, links, skipped)
}

// Returns the rows written: the nodes', then the links'.
fn write_index(
    graph: &Graph,
    placed: &place::Placed,
    layout: Layout,
    max_component: Option<u64>,
    prefix: &str,
) -> Result<(Vec<bed::Row>, Vec<bed::Row>), String> {
    let (spans, mut nodes, mut links, skipped) =
        index_rows(graph, placed, layout, max_component, Format::One);
    bed::sort(&mut nodes, &spans);
    bed::sort(&mut links, &spans);
    let nodes_path = format!("{prefix}.segs.bed.gz");
    let links_path = format!("{prefix}.links.bed.gz");
    let index = bed::write(&nodes_path, b"", &nodes, &spans)?;
    bed::write(&links_path, b"", &links, &spans)?;
    report(
        graph,
        placed,
        &spans,
        max_component,
        skipped,
        &format!("{nodes_path}, {links_path} (+ .{index})"),
    );
    Ok((nodes, links))
}

// Format 2: nodes and links in one file, each row's kind after its interval,
// under a header naming the format, layout, graph and, for a plain GFA, the
// assemblies that SB:H: numbers.
fn write_graph(
    graph: &Graph,
    placed: &place::Placed,
    layout: Layout,
    max_component: Option<u64>,
    prefix: &str,
) -> Result<(), String> {
    let (spans, mut rows, links, skipped) =
        index_rows(graph, placed, layout, max_component, Format::Two);
    rows.extend(links);
    bed::sort(&mut rows, &spans);
    let layout = match layout {
        Layout::Anchored => "anchored",
        Layout::Contig => "contig",
    };
    let mut header = format!(
        "#gfa-to-tabix\tformat:i:2\tlayout:Z:{layout}\tgraph:Z:{:016x}\n",
        graph.content_hash()
    )
    .into_bytes();
    if !placed.samples.is_empty() {
        header.extend_from_slice(b"#samples\t");
        header.extend_from_slice(&placed.samples.join(&b','));
        header.push(b'\n');
    }
    let path = format!("{prefix}.graph.bed.gz");
    let index = bed::write(&path, &header, &rows, &spans)?;
    report(
        graph,
        placed,
        &spans,
        max_component,
        skipped,
        &format!("{path} (+ .{index})"),
    );
    Ok(())
}

fn report(
    graph: &Graph,
    placed: &place::Placed,
    spans: &anchor::Spans,
    max_component: Option<u64>,
    skipped: usize,
    written: &str,
) {
    let placed_nodes = placed.nodes.iter().flatten().count();
    eprintln!("{}", placed.summary);
    eprintln!(
        "{placed_nodes} nodes, {} links -> {written}",
        graph.links.len() - skipped
    );
    if skipped > 0 {
        eprintln!("{skipped} links left out: a node with no coordinate");
    }
    if let Some(max) = max_component
        && !spans.moved.is_empty()
    {
        let n = spans.moved.len();
        let (are, they) = if n == 1 {
            ("is", "it")
        } else {
            ("are", "them")
        };
        eprintln!(
            "{n} of the graph's components {are} over --max-component {max}, so a graph track \
             draws {they} as stubs; --max-component none files {they} under the reference:"
        );
        for (nodes, (sequence, start, end)) in spans.moved.iter().take(10) {
            let sequence = String::from_utf8_lossy(&spans.sequences[*sequence as usize]);
            eprintln!("  {nodes} nodes under {sequence}:{start}-{end}");
        }
        if n > 10 {
            eprintln!("  and {} more", n - 10);
        }
    }
    let unplaced = graph.segment_count() - placed_nodes;
    if unplaced > 0 {
        eprintln!("{unplaced} nodes left out: no path visits them, or no SN tag");
    }
}

fn write_tier(
    graph: &Graph,
    placed: &place::Placed,
    below: i64,
    layout: Layout,
    max_component: Option<u64>,
    format: Format,
    prefix: &str,
) -> Result<(), String> {
    let folded = Graph::read(io::Cursor::new(fold::fold(graph, placed, below)))?;
    eprintln!(
        "{} segments, {} links -> fold under {below} bp",
        graph.segment_count(),
        graph.links.len()
    );
    let placed = place::from_tags(&folded);
    match format {
        Format::One => write_index(&folded, &placed, layout, max_component, prefix).map(drop),
        Format::Two => write_graph(&folded, &placed, layout, max_component, prefix),
    }
}

fn run(cli: Cli) -> Result<(), String> {
    let Some(command) = cli.command else {
        return index(cli);
    };
    match command {
        Command::Build {
            gfa,
            out,
            reference,
            assembly,
            snarls,
            tier,
            max_component,
            format,
        } => build::run(&build::Options {
            graph: gfa,
            prefix: out,
            reference,
            assembly,
            snarls,
            tier,
            max_component: max_component.0,
            format,
        }),
        Command::Alleles { prefix } => alleles::run(&prefix),
        Command::Bubbles {
            snarls,
            out,
            min_alleles,
        } => bubbles::run(&snarls, &out, min_alleles, &HashSet::new()),
        Command::Paths { out, files } => paths::run(&out, &files),
        Command::Fold {
            gfa,
            below,
            reference,
            layout,
            max_component,
            format,
            out,
        } => {
            let (graph, placed) = load_placed(&gfa, reference.as_deref())?;
            write_tier(
                &graph,
                &placed,
                below,
                layout,
                max_component.0,
                format,
                &out,
            )
        }
    }
}

fn main() {
    if let Err(message) = run(Cli::parse()) {
        eprintln!("gfa-to-tabix: error: {message}");
        process::exit(1);
    }
}
