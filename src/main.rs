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

use bed::Layout;
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
    write_index(&graph, &placed, layout, cli.max_component.0, &prefix).map(drop)
}

// Returns the rows written: the nodes', then the links'.
fn write_index(
    graph: &Graph,
    placed: &place::Placed,
    layout: Layout,
    max_component: Option<u64>,
    prefix: &str,
) -> Result<(Vec<bed::Row>, Vec<bed::Row>), String> {
    let spans = match layout {
        Layout::Anchored => anchor::anchored(graph, placed, max_component),
        Layout::Contig => anchor::by_contig(placed),
    };
    let mut nodes = bed::node_rows(graph, &placed.nodes, &spans, layout);
    let (mut links, skipped) = bed::link_rows(graph, &placed.nodes, &spans, layout);
    bed::sort(&mut nodes, &spans);
    bed::sort(&mut links, &spans);
    let nodes_path = format!("{prefix}.segs.bed.gz");
    let links_path = format!("{prefix}.links.bed.gz");
    let index = bed::write(&nodes_path, &nodes, &spans)?;
    bed::write(&links_path, &links, &spans)?;

    let placed_nodes = placed.nodes.iter().flatten().count();
    eprintln!("{}", placed.summary);
    eprintln!(
        "{placed_nodes} nodes, {} links -> {nodes_path}, {links_path} (+ .{index})",
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
    Ok((nodes, links))
}

fn write_tier(
    graph: &Graph,
    placed: &place::Placed,
    below: i64,
    layout: Layout,
    max_component: Option<u64>,
    prefix: &str,
) -> Result<(), String> {
    let folded = Graph::read(io::Cursor::new(fold::fold(graph, placed, below)))?;
    eprintln!(
        "{} segments, {} links -> fold under {below} bp",
        graph.segment_count(),
        graph.links.len()
    );
    write_index(
        &folded,
        &place::from_tags(&folded),
        layout,
        max_component,
        prefix,
    )
    .map(drop)
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
        } => build::run(&build::Options {
            graph: gfa,
            prefix: out,
            reference,
            assembly,
            snarls,
            tier,
            max_component: max_component.0,
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
            out,
        } => {
            let (graph, placed) = load_placed(&gfa, reference.as_deref())?;
            write_tier(&graph, &placed, below, layout, max_component.0, &out)
        }
    }
}

fn main() {
    if let Err(message) = run(Cli::parse()) {
        eprintln!("gfa-to-tabix: error: {message}");
        process::exit(1);
    }
}
