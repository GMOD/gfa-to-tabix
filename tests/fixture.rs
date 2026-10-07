// Every row worked out by hand over graphs small enough to check on paper.
//
// rgfa.gfa: s1 (8 bp) and s2 (5 bp, length from LN) lie on chr1 at rank 0, and
// s3 (3 bp) on b#1#c at 100, rank 1.
// island.gfa adds s4 and s5 on d#1#x, linked to each other and to nothing else.
// paths.gfa: ref#1#chr walks 1 2 4 and alt#1#ctg walks 1 3 4; node lengths are
// 4, 2, 1, 3. walks.gfa says the same in W lines, alt first, starting at 10.

use std::fs;
use std::io::Read;
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::read::MultiGzDecoder;

fn run(fixture: &str, args: &[&str]) -> (Output, String, String) {
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
    let (nodes, links) = (read("segs"), read("links"));
    fs::remove_dir_all(&dir).unwrap();
    (output, nodes, links)
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
fn paths_place_nodes_with_the_first_path_as_reference() {
    let (output, nodes, links) = run("paths.gfa", &[]);
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
    let (_, nodes, _) = run("paths.gfa", &["--layout", "anchored"]);
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
