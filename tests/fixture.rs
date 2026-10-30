// Every row worked out by hand over graphs small enough to check on paper.
//
// rgfa.gfa: s1 (8 bp) and s2 (5 bp, length from LN) lie on chr1 at rank 0, and
// s3 (3 bp) on b#1#c at 100, rank 1.
// rgfa_reordered.gfa lists the same segments in reverse.
// island.gfa adds s4 and s5 on d#1#x, linked to each other and to nothing else.
// paths.gfa: ref#1#chr walks 1 2 4 and alt#1#ctg walks 1 3 4; node lengths are
// 4, 2, 1, 3. walks.gfa says the same in W lines, alt first, starting at 10.
// order.gfa: ref#1#chr walks 1 2 4, then b#1#ctg walks 4 3 1 reversed from 100
// and a#1#ctg walks 1 3 4 from 10.
// genome.gfa: one genome's chr1 walks 1 2 and chr2 walks 3, with no PanSN
// names; haplotype.gfa names them HG002#1#chr1 and HG002#1#chr2.

use std::fs;
use std::io::Read;
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::read::MultiGzDecoder;

fn run(fixture: &str, args: &[&str]) -> (Output, String, String) {
    let (output, mut files) = run_files(fixture, args, &["segs", "links"]);
    let links = files.pop().unwrap();
    (output, files.pop().unwrap(), links)
}

// Runs the tool and reads back out.KIND.bed.gz for each of `kinds`, empty
// where the tool wrote none.
fn run_files(fixture: &str, args: &[&str], kinds: &[&str]) -> (Output, Vec<String>) {
    static RUNS: AtomicUsize = AtomicUsize::new(0);
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-{}-{}",
        std::process::id(),
        RUNS.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&dir).unwrap();
    let prefix = dir.join("out");
    let output = Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg(format!(
            "{}/tests/data/{fixture}",
            env!("CARGO_MANIFEST_DIR")
        ))
        .arg("-o")
        .arg(&prefix)
        .args(args)
        .args(if args.contains(&"--layout") {
            vec![]
        } else {
            vec!["--layout", "contig"]
        })
        .args(if args.contains(&"--format") {
            vec![]
        } else {
            vec!["--format", "1"]
        })
        .output()
        .unwrap();
    let read = |kind: &str| {
        let path = dir.join(format!("out.{kind}.bed.gz"));
        let mut text = String::new();
        if let Ok(file) = fs::File::open(&path) {
            MultiGzDecoder::new(file).read_to_string(&mut text).unwrap();
            assert!(dir.join(format!("out.{kind}.bed.gz.tbi")).exists());
        }
        text
    };
    let files = kinds.iter().map(|kind| read(kind)).collect();
    fs::remove_dir_all(&dir).unwrap();
    (output, files)
}

fn tsv(rows: &[&str]) -> String {
    rows.iter().map(|r| r.replace(' ', "\t") + "\n").collect()
}

#[test]
fn rgfa_nodes_come_from_the_tags() {
    let (output, nodes, _) = run("rgfa.gfa", &[]);
    assert!(output.status.success());
    assert_eq!(
        nodes,
        tsv(&["b#1#c 100 103 s3 1", "chr1 0 8 s1 0", "chr1 8 13 s2 0"])
    );
}

#[test]
fn each_link_has_a_row_under_both_of_its_nodes() {
    let (_, _, links) = run("rgfa.gfa", &[]);
    let to_s2 = "s1+ s2+ chr1 0 8 0 chr1 8 13 0";
    let to_s3 = "s1+ s3- chr1 0 8 0 b#1#c 100 103 1";
    let s3_to_s2 = "s3- s2+ b#1#c 100 103 1 chr1 8 13 0";
    assert_eq!(
        links,
        tsv(&[
            &format!("b#1#c 100 103 {to_s3}"),
            &format!("b#1#c 100 103 {s3_to_s2}"),
            &format!("chr1 0 8 {to_s2}"),
            &format!("chr1 0 8 {to_s3}"),
            &format!("chr1 8 13 {to_s2}"),
            &format!("chr1 8 13 {s3_to_s2}"),
        ])
    );
}

#[test]
fn paths_place_nodes_with_the_reference_walking_first() {
    let (output, nodes, links) = run("paths.gfa", &["--reference", "ref"]);
    assert!(output.status.success());
    assert_eq!(
        nodes,
        tsv(&[
            "alt#1#ctg 4 5 3 1 SM:Z:alt.1",
            "ref#1#chr 0 4 1 0 SM:Z:ref.1,alt.1",
            "ref#1#chr 4 6 2 0 SM:Z:ref.1",
            "ref#1#chr 6 9 4 0 SM:Z:ref.1,alt.1",
        ])
    );
    assert!(links.contains(&tsv(&[
        "alt#1#ctg 4 5 1+ 3+ ref#1#chr 0 4 0 alt#1#ctg 4 5 1 SM:Z:ref.1,alt.1 SM:Z:alt.1"
    ])));
    assert_eq!(links.lines().count(), 8);
}

#[test]
fn paths_of_several_assemblies_need_a_reference() {
    let (output, nodes, _) = run("paths.gfa", &[]);
    assert_eq!(output.status.code(), Some(1));
    assert!(nodes.is_empty());
    assert_eq!(
        String::from_utf8_lossy(&output.stderr),
        "gfa-to-tabix: error: the paths name 2 assemblies; pick the reference \
         with --reference, comma-separated for several: alt#1, ref#1\n"
    );
}

#[test]
fn one_assemblys_paths_name_the_reference() {
    let (output, nodes, _) = run("haplotype.gfa", &[]);
    assert!(output.status.success(), "{output:?}");
    assert_eq!(
        nodes,
        tsv(&[
            "HG002#1#chr1 0 4 1 0 SM:Z:HG002.1",
            "HG002#1#chr1 4 6 2 0 SM:Z:HG002.1",
            "HG002#1#chr2 0 3 3 0 SM:Z:HG002.1",
        ])
    );
}

#[test]
fn a_reference_list_puts_every_named_path_at_rank_0() {
    let (output, _, _) = run("genome.gfa", &[]);
    assert_eq!(output.status.code(), Some(1));
    let (output, nodes, _) = run("genome.gfa", &["--reference", "chr1,chr2"]);
    assert!(output.status.success(), "{output:?}");
    assert_eq!(
        nodes,
        tsv(&[
            "chr1 0 4 1 0 SM:Z:chr1",
            "chr1 4 6 2 0 SM:Z:chr1",
            "chr2 0 3 3 0 SM:Z:chr2",
        ])
    );
    let (_, nodes, _) = run("genome.gfa", &["--reference", "chr1"]);
    assert!(nodes.contains(&tsv(&["chr2 0 3 3 1 SM:Z:chr2"])), "{nodes}");
}

#[test]
fn a_named_reference_walks_first() {
    let (_, nodes, _) = run("paths.gfa", &["--reference", "alt"]);
    assert_eq!(
        nodes,
        tsv(&[
            "alt#1#ctg 0 4 1 0 SM:Z:alt.1,ref.1",
            "alt#1#ctg 4 5 3 0 SM:Z:alt.1",
            "alt#1#ctg 5 8 4 0 SM:Z:alt.1,ref.1",
            "ref#1#chr 4 6 2 1 SM:Z:ref.1",
        ])
    );
}

#[test]
fn w_lines_carry_their_own_start() {
    let (_, nodes, _) = run("walks.gfa", &["--reference", "ref#1"]);
    assert_eq!(
        nodes,
        tsv(&[
            "alt#1#ctg 14 15 3 1 SM:Z:alt.1",
            "ref#1#chr 0 4 1 0 SM:Z:ref.1,alt.1",
            "ref#1#chr 4 6 2 0 SM:Z:ref.1",
            "ref#1#chr 6 9 4 0 SM:Z:ref.1,alt.1",
        ])
    );
}

#[test]
fn the_path_whose_name_sorts_first_places_a_node_whatever_the_line_order() {
    let (output, nodes, links) = run("order.gfa", &["--reference", "ref"]);
    assert!(output.status.success());
    assert_eq!(
        nodes,
        tsv(&[
            "a#1#ctg 14 15 3 1 SM:Z:a.1,b.1",
            "ref#1#chr 0 4 1 0 SM:Z:ref.1,a.1,b.1",
            "ref#1#chr 4 6 2 0 SM:Z:ref.1",
            "ref#1#chr 6 9 4 0 SM:Z:ref.1,a.1,b.1",
        ])
    );
    assert!(links.contains("\t1+\t3+\t"), "{links}");
}

#[test]
fn an_unknown_reference_lists_the_paths() {
    let (output, nodes, _) = run("paths.gfa", &["--reference", "nope"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(nodes.is_empty());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("matches no path; have: ref#1#chr, alt#1#ctg"),
        "{stderr}"
    );
}

#[test]
fn a_reference_named_with_a_range_matches_its_path() {
    let (named, nodes, _) = run("paths.gfa", &["--reference", "alt#1#ctg"]);
    let (ranged, ranged_nodes, _) = run("paths.gfa", &["--reference", "alt#1#ctg:0-8"]);
    assert!(named.status.success() && ranged.status.success());
    assert_eq!(ranged_nodes, nodes);
}

#[test]
fn a_reference_on_an_rgfa_without_paths_says_the_tags_suffice() {
    let (output, _, _) = run("rgfa.gfa", &["--reference", "chr1"]);
    assert_eq!(output.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("--reference needs P or W lines"),
        "{stderr}"
    );
}

#[test]
fn anchored_files_an_allele_under_the_reference_it_hangs_from() {
    let (output, nodes, links) = run("rgfa.gfa", &["--layout", "anchored"]);
    assert!(output.status.success());
    assert_eq!(
        nodes,
        tsv(&[
            "chr1 0 13 s3 1 b#1#c 100 103",
            "chr1 0 8 s1 0 chr1 0 8",
            "chr1 8 13 s2 0 chr1 8 13",
        ])
    );
    assert_eq!(
        links,
        tsv(&[
            "chr1 0 13 s1+ s2+ chr1 0 8 0 chr1 8 13 0",
            "chr1 0 13 s1+ s3- chr1 0 8 0 b#1#c 100 103 1",
            "chr1 0 13 s3- s2+ b#1#c 100 103 1 chr1 8 13 0",
        ])
    );
}

// With --max-component 0, s3's one-node component keeps its coordinates, and
// each link to it gets a row there beside the one under the reference.
#[test]
fn anchored_leaves_a_component_over_max_component_on_its_own_coordinates() {
    let (output, nodes, links) = run(
        "rgfa.gfa",
        &["--layout", "anchored", "--max-component", "0"],
    );
    assert!(output.status.success());
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("1 of the graph's components is over --max-component 0")
            && stderr.contains("  1 nodes under chr1:0-13\n"),
        "{stderr}"
    );
    assert_eq!(
        nodes,
        tsv(&[
            "b#1#c 100 103 s3 1 b#1#c 100 103",
            "chr1 0 8 s1 0 chr1 0 8",
            "chr1 8 13 s2 0 chr1 8 13",
        ])
    );
    assert_eq!(
        links,
        tsv(&[
            "b#1#c 100 103 s1+ s3- chr1 0 8 0 b#1#c 100 103 1",
            "b#1#c 100 103 s3- s2+ b#1#c 100 103 1 chr1 8 13 0",
            "chr1 0 13 s1+ s2+ chr1 0 8 0 chr1 8 13 0",
            "chr1 0 13 s1+ s3- chr1 0 8 0 b#1#c 100 103 1",
            "chr1 0 13 s3- s2+ b#1#c 100 103 1 chr1 8 13 0",
        ])
    );
}

#[test]
fn max_component_none_files_every_component_under_the_reference() {
    let (_, default_nodes, default_links) = run("rgfa.gfa", &[]);
    let (output, nodes, links) = run("rgfa.gfa", &["--max-component", "none"]);
    assert!(output.status.success());
    assert_eq!((nodes, links), (default_nodes, default_links));
    let (output, _, _) = run("rgfa.gfa", &["--max-component", "all"]);
    assert_eq!(output.status.code(), Some(2));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("a node count or `none`"), "{stderr}");
}

#[test]
fn anchored_leaves_a_component_off_the_reference_on_its_own_coordinates() {
    let (_, nodes, links) = run("island.gfa", &["--layout", "anchored"]);
    assert!(nodes.contains(&tsv(&[
        "d#1#x 5 7 s4 2 d#1#x 5 7",
        "d#1#x 7 8 s5 2 d#1#x 7 8"
    ])));
    assert!(links.contains(&tsv(&["d#1#x 5 8 s4+ s5+ d#1#x 5 7 2 d#1#x 7 8 2"])));
    assert_eq!(links.lines().count(), 4);
}

#[test]
fn anchored_keeps_the_carriers_column_last() {
    let (_, nodes, _) = run("paths.gfa", &["--layout", "anchored", "--reference", "ref"]);
    assert_eq!(
        nodes,
        tsv(&[
            "ref#1#chr 0 4 1 0 ref#1#chr 0 4 SM:Z:ref.1,alt.1",
            "ref#1#chr 0 9 3 1 alt#1#ctg 4 5 SM:Z:alt.1",
            "ref#1#chr 4 6 2 0 ref#1#chr 4 6 SM:Z:ref.1",
            "ref#1#chr 6 9 4 0 ref#1#chr 6 9 SM:Z:ref.1,alt.1",
        ])
    );
}

#[test]
fn a_failed_run_leaves_no_partial_file() {
    let (output, nodes, _) = run("paths.gfa", &["--reference", "nope"]);
    assert_eq!(output.status.code(), Some(1));
    assert!(nodes.is_empty());
}

#[test]
fn anchored_files_a_zero_length_node_under_one_base() {
    let (_, nodes, links) = run("zero.gfa", &["--layout", "anchored"]);
    assert_eq!(
        nodes,
        tsv(&["chr1 10 11 y 1 alt 0 4", "chr1 10 11 z 0 chr1 10 10"])
    );
    assert_eq!(links, tsv(&["chr1 10 11 z+ y+ chr1 10 10 0 alt 0 4 1"]));
}

// Format 2 holds format 1's rows in one file, each with its kind after the
// interval and carriers as bits over #samples: alt.1 is bit 0, ref.1 bit 1.
#[test]
fn format_2_writes_nodes_and_links_to_one_file_with_carrier_bits() {
    let (output, files) = run_files(
        "paths.gfa",
        &["--layout", "contig", "--format", "2", "--reference", "ref"],
        &["graph", "segs"],
    );
    assert!(output.status.success());
    assert_eq!(files[1], "", "format 2 writes no node file");
    let graph = &files[0];
    let header_end = graph.match_indices('\n').nth(1).unwrap().0 + 1;
    let (header, rows) = graph.split_at(header_end);
    assert!(
        header.starts_with("#gfa-to-tabix\tformat:i:2\tlayout:Z:contig\tgraph:Z:"),
        "{header}"
    );
    assert!(header.ends_with("\n#samples\talt.1,ref.1\n"), "{header}");
    assert!(rows.contains(&tsv(&["alt#1#ctg 4 5 N 3 1 SB:H:1"])));
    assert!(rows.contains(&tsv(&["ref#1#chr 0 4 N 1 0 SB:H:3"])));
    assert!(rows.contains(&tsv(&["ref#1#chr 4 6 N 2 0 SB:H:2"])));
    assert!(rows.contains(&tsv(&[
        "ref#1#chr 0 4 L 1+ 3+ ref#1#chr 0 4 0 alt#1#ctg 4 5 1 SB:H:3 SB:H:1"
    ])));
    let (_, nodes, links) = run("paths.gfa", &["--layout", "contig", "--reference", "ref"]);
    assert_eq!(
        rows.lines().count(),
        nodes.lines().count() + links.lines().count()
    );
}

// The hash covers each segment's id and length, not the order of the S lines.
#[test]
fn format_2_names_the_graph_whatever_order_its_segments_come_in() {
    let header = |fixture: &str| {
        let (_, files) = run_files(fixture, &["--format", "2"], &["graph"]);
        files[0].lines().next().unwrap().to_string()
    };
    assert_eq!(header("rgfa.gfa"), header("rgfa_reordered.gfa"));
    assert_ne!(header("rgfa.gfa"), header("island.gfa"));
}
