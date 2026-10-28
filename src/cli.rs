use clap::{Parser, Subcommand, value_parser};

use crate::bed::Layout;

const WALKS: &str = "Walks (a base-level GFA with integer node ids and W or P lines)";

// The most nodes an off-reference component may hold and still file under the
// reference interval it hangs from; None files every component there.
#[derive(Clone, Copy)]
pub struct ComponentLimit(pub Option<u64>);

fn component_limit(value: &str) -> Result<ComponentLimit, String> {
    if value == "none" {
        return Ok(ComponentLimit(None));
    }
    value
        .parse()
        .map(|n| ComponentLimit(Some(n)))
        .map_err(|_| format!("expected a node count or `none`, got `{value}`"))
}

/// Index a pangenome graph's GFA by genome coordinate: write its nodes and
/// links as two bgzip-compressed, Tabix-indexed BED files, which a JBrowse
/// graph track reads by region. https://github.com/GMOD/gfa-to-tabix
///
/// An rGFA (minigraph, or the minigraph stage of Minigraph-Cactus) gives every
/// node a coordinate in its SN/SO/SR tags. A plain GFA (pggb, odgi, vg,
/// base-level Minigraph-Cactus) gets coordinates from its P or W lines
/// instead: each node takes its position on the first path to reach it,
/// reference paths first, and reads forward there.
#[derive(Parser)]
#[command(
    name = "gfa-to-tabix",
    version,
    args_conflicts_with_subcommands = true,
    args_override_self = true,
    subcommand_negates_reqs = true
)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Option<Command>,

    /// GFA file, gz accepted; - reads stdin
    #[arg(required = true)]
    pub gfa: Option<String>,

    /// For a plain GFA, the reference: a PanSN sample (GRCh38), an assembly
    /// (HG002#1) or a path name. Default: the first path in the file. Given
    /// with an rGFA, coordinates come from the paths, not the tags
    #[arg(long, conflicts_with = "walks")]
    pub reference: Option<String>,

    /// anchored (default) files every node under the reference interval its
    /// bubble hangs from, so one query per file returns the whole graph under
    /// a region. contig files every node under its coordinate, as 0.1.0 did
    #[arg(long, value_enum, conflicts_with = "walks")]
    pub layout: Option<Layout>,

    /// anchored: nodes off the reference that link to each other form a
    /// component. One of more than N nodes keeps its own coordinates, so a
    /// window under it reads only the links into it, which a graph track draws
    /// as stubs. `none` files every component under the reference; the README
    /// says when to change it
    #[arg(long, value_name = "N", default_value = "10000", value_parser = component_limit, conflicts_with = "walks")]
    pub max_component: ComponentLimit,

    /// Write PREFIX.segs.bed.gz and PREFIX.links.bed.gz, each with a .tbi;
    /// default the input name without .gfa[.gz]
    #[arg(short, long = "out", value_name = "PREFIX")]
    pub out: Option<String>,

    /// Instead write PREFIX.SAMPLE.walks.bed.gz and a .tbi for each SAMPLE in
    /// --refs. Each file lists every haplotype's path in SAMPLE's coordinates.
    /// Reads the GFA twice
    #[arg(long, requires = "refs", help_heading = WALKS)]
    pub walks: bool,

    /// Comma-separated reference samples, e.g. GRCh38,CHM13
    #[arg(long, requires = "walks", help_heading = WALKS)]
    pub refs: Option<String>,

    /// Chunk size on the reference (default 65536)
    #[arg(long, value_name = "BP", value_parser = value_parser!(u64).range(1..), requires = "walks", help_heading = WALKS)]
    pub chunk: Option<u64>,

    /// Add the bases of each reference and route row's nodes as SQ:Z:
    #[arg(long, requires = "walks", help_heading = WALKS)]
    pub sequences: bool,

    /// Keep a path's piece in its chunk across a stretch elsewhere that
    /// returns to it with at most BP of reference nodes (default 311; 0 off)
    #[arg(long, value_name = "BP", requires = "walks", help_heading = WALKS)]
    pub stay: Option<u64>,

    /// Move a chunk's costliest paths to its detail rows until the rest cost
    /// at most N interior steps, a step along the reference counting as a
    /// quarter of one (default 1000000; 0 off)
    #[arg(long, value_name = "N", requires = "walks", help_heading = WALKS)]
    pub abridge_steps: Option<u64>,

    /// ...and at most BYTES compressed (default 3000000; 0 off)
    #[arg(long, value_name = "BYTES", requires = "walks", help_heading = WALKS)]
    pub abridge_bytes: Option<u64>,
}

const BUILD_ABOUT: &str =
    "Write everything a JBrowse graph track reads, from one read of the graph (gz
accepted; - reads stdin):
  PREFIX.segs/links.bed.gz           the fine index, anchored layout
  PREFIX.contig.segs/links.bed.gz    the contig layout
  PREFIX.foldBP.segs/links.bed.gz    the coarse tier, as `fold` writes it
  PREFIX.alleles.bed.gz              the allele inventory, as `alleles` writes it
  PREFIX.bubbles.bed.gz              `gfatools bubble` for an rGFA, --snarls for a plain GFA
  PREFIX.graph.json                  a manifest naming the files above
  PREFIX.config.json                 the JBrowse tracks, ready to merge into a config
Each file gets a .tbi. An rGFA's bubbles need gfatools on PATH; without it the
build notes so and writes no bubble file.";

const ALLELES_ABOUT: &str =
    "Read PREFIX.segs.bed.gz and PREFIX.links.bed.gz, as this tool writes them with
--layout contig, and write PREFIX.alleles.bed.gz (+ .tbi): one row per allele
the graph holds, anchored on the reference, with a CIGAR that states its size.
The two files are all it needs, so a hosted pair works without the graph.";

const BUBBLES_ABOUT: &str =
    "Write PREFIX.bubbles.bed.gz (+ .tbi) from a `vg deconstruct` snarl VCF (gz
accepted; `pggb -V` writes one too), in the layout `gfatools bubble` writes for
an rGFA. gfatools finds no bubbles on a plain GFA, and a snarl VCF has each
bubble's reference span and alleles. Keeps the top-level snarls, none of which
overlap.";

const PATHS_ABOUT: &str =
    "Write PREFIX.bed.gz (+ .tbi) from the files `minigraph -cxasm --call graph.rgfa
sample.fa` writes, one per sample and the reference's first: a row per bubble
and sample, with the sample's path, its length change against the reference and
how many samples have each allele. Each file's name, without .call.bed, is its
sample, and the reference's sample name gives the PanSN prefix the rows drop
from their contigs. Every file must have the same lines, which minigraph writes.";

const FOLD_ABOUT: &str =
    "Write PREFIX.segs.bed.gz and PREFIX.links.bed.gz (+ .tbi) for the graph with
every variant under BP folded into the reference: the coarse tier a graph track
draws once zoomed out past the fine index. It keeps the backbone, every allele
whose own length or the reference it replaces reaches BP, and the shortest way
from each one's ends back to the backbone. The graph track folds each cut it
draws the same way, at ten of the linear view's pixels, so a tier folded at BP
and handed over at BP / 10 bp per pixel draws close to what the fine cut drew
just below the handover. Not exactly: the way back from a big allele to the
backbone can run through part of a small allele in one fold and not the other.
--layout should match the fine index's.";

#[derive(Subcommand)]
pub enum Command {
    #[command(about = "Write everything a JBrowse graph track reads", long_about = BUILD_ABOUT, args_override_self = true)]
    Build {
        /// GFA file, gz accepted; - reads stdin
        gfa: String,
        /// Output prefix
        #[arg(short, long = "out", value_name = "PREFIX")]
        out: String,
        /// For a plain GFA, the backbone path, as for the index
        #[arg(long, value_name = "SAMPLE")]
        reference: Option<String>,
        /// The JBrowse assembly the tracks sit on. Default: the graph's
        /// reference sample, else `reference`
        #[arg(long, value_name = "NAME")]
        assembly: Option<String>,
        /// A `vg deconstruct -a` snarl VCF: a plain GFA's bubbles
        #[arg(long, value_name = "VCF")]
        snarls: Option<String>,
        /// Fold variants under BP into the coarse tier. Default 10000 for an
        /// rGFA, 50 for a plain GFA
        #[arg(long, value_name = "BP", value_parser = value_parser!(i64).range(1..))]
        tier: Option<i64>,
        /// A component of more than N nodes keeps its own coordinates, as for
        /// the index
        #[arg(long, value_name = "N", default_value = "10000", value_parser = component_limit)]
        max_component: ComponentLimit,
    },
    #[command(about = "Write the allele inventory from an index's two files", long_about = ALLELES_ABOUT, args_override_self = true)]
    Alleles {
        /// The index's prefix
        prefix: String,
    },
    #[command(about = "Write the bubbles from a snarl VCF", long_about = BUBBLES_ABOUT, args_override_self = true)]
    Bubbles {
        /// The snarl VCF
        #[arg(long, value_name = "VCF")]
        snarls: String,
        /// Output prefix
        #[arg(short, long = "out", value_name = "PREFIX")]
        out: String,
        /// Skip a snarl with fewer traversals
        #[arg(long, value_name = "N", default_value_t = 2)]
        min_alleles: usize,
    },
    #[command(about = "Write every sample's path through every bubble", long_about = PATHS_ABOUT, args_override_self = true)]
    Paths {
        /// Output prefix
        #[arg(short, long = "out", value_name = "PREFIX")]
        out: String,
        /// The reference's call file, then each sample's
        #[arg(required = true, value_name = "CALL_BED")]
        files: Vec<String>,
    },
    #[command(about = "Write the coarse tier: the graph with small variants folded", long_about = FOLD_ABOUT, args_override_self = true)]
    Fold {
        /// GFA file, gz accepted; - reads stdin
        gfa: String,
        /// The size to fold under
        #[arg(long, value_name = "BP", value_parser = value_parser!(i64).range(1..))]
        below: i64,
        /// For a plain GFA, the backbone path, as for the index
        #[arg(long, value_name = "NAME")]
        reference: Option<String>,
        /// The fine index's layout
        #[arg(long, value_enum, default_value = "anchored")]
        layout: Layout,
        /// The fine index's --max-component
        #[arg(long, value_name = "N", default_value = "10000", value_parser = component_limit)]
        max_component: ComponentLimit,
        /// Output prefix
        #[arg(short, long = "out", value_name = "PREFIX")]
        out: String,
    },
}
