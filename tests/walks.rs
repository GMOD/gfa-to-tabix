// --walks over walks-two-refs.gfa, every row checked by hand. Five nodes of
// 6 bp make the reference R#0#chr: 1 2 3 4 5 at 0, 6, 12, 18 and 24. Q#0#chr
// takes 6 in place of 2. With --chunk 10, nodes 1 and 2 lie in chunk 0-10, 3
// and 4 in 10-20, and 5 in 20-30; each chunk's rows are filed under its first
// base. H#1#h inserts 7 (3 bp) between 3 and 4,
// I#1#i inverts 2-3, D#1#d repeats 1-4, and U#1#u visits only 8 and 9.
// walks-two-refs-p.gfa says the same in P lines.

use std::fs;
use std::io::{Read, Write};
use std::process::{Command, Output};
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::Compression;
use flate2::read::MultiGzDecoder;
use flate2::write::GzEncoder;

struct Built {
    output: Output,
    walks: String,
    nodes: String,
    links: String,
}

fn build(fixture: &str, args: &[&str]) -> Built {
    static RUNS: AtomicUsize = AtomicUsize::new(0);
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-walks-{}-{}",
        std::process::id(),
        RUNS.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&dir).unwrap();
    let input = if fixture == "-" || fixture.starts_with('/') {
        fixture.to_string()
    } else {
        format!("{}/tests/data/{fixture}", env!("CARGO_MANIFEST_DIR"))
    };
    let output = Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .arg(input)
        .arg("-o")
        .arg(dir.join("out"))
        .args(["--walks", "--refs", "R,Q", "--chunk", "10"])
        .args(args)
        .output()
        .unwrap();
    let read = |kind: &str| {
        let mut text = String::new();
        if let Ok(file) = fs::File::open(dir.join(format!("out.{kind}.bed.gz"))) {
            MultiGzDecoder::new(file).read_to_string(&mut text).unwrap();
            assert!(dir.join(format!("out.{kind}.bed.gz.tbi")).exists());
        }
        text
    };
    let built = Built {
        walks: read("walks"),
        nodes: read("nodes"),
        links: read("links"),
        output,
    };
    let left: Vec<_> = fs::read_dir(&dir)
        .unwrap()
        .flatten()
        .map(|e| e.file_name())
        .collect();
    assert!(left.len() <= 6, "temporary files left behind: {left:?}");
    fs::remove_dir_all(&dir).unwrap();
    built
}

fn tsv(rows: &[&str]) -> String {
    rows.iter().map(|r| r.replace(' ', "\t") + "\n").collect()
}

fn rows_of(text: &str, anchor: &str, column: &str) -> String {
    text.lines()
        .filter(|line| {
            let cols: Vec<&str> = line.split('\t').collect();
            cols.len() > 3 && cols[0] == anchor && cols[3] == column
        })
        .map(|line| line.to_string() + "\n")
        .collect()
}

fn under(text: &str, anchor: &str) -> String {
    text.lines()
        .filter(|line| line.starts_with(&format!("{anchor}\t")))
        .map(|line| line.to_string() + "\n")
        .collect()
}

#[test]
fn each_reference_files_every_path_under_its_own_chunks() {
    let built = build("walks-two-refs.gfa", &[]);
    assert!(built.output.status.success());
    for anchor in ["R#0#chr", "Q#0#chr"] {
        assert_eq!(
            rows_of(&built.walks, anchor, "R#0#chr"),
            tsv(&[
                &format!("{anchor} 0 1 R#0#chr 0 0 0 2 2,2"),
                &format!("{anchor} 10 11 R#0#chr 0 12 1 2 6,2"),
                &format!("{anchor} 20 21 R#0#chr 0 24 2 1 10"),
            ])
        );
    }
}

#[test]
fn each_file_starts_with_the_chunk_size() {
    let built = build("walks-two-refs.gfa", &[]);
    assert!(built.walks.starts_with("#walks\tchunk:i:10\n"));
    assert!(built.nodes.starts_with("#nodes\tchunk:i:10\n"));
    assert!(built.links.starts_with("#links\tchunk:i:10\n"));
}

// Node 2 is off Q. R, H, I and D visit it; D#1#d sorts first and reaches it
// at 6, and again at 30.
#[test]
fn a_node_is_rank_0_on_its_reference_and_takes_the_first_named_path_elsewhere() {
    let built = build("walks-two-refs.gfa", &[]);
    assert_eq!(
        under(&built.nodes, "R#0#chr"),
        tsv(&[
            "R#0#chr 0 1 1 0 R#0#chr 0 6 LN:i:6",
            "R#0#chr 0 1 2 0 R#0#chr 6 12 LN:i:6",
            "R#0#chr 0 1 6 1 Q#0#chr 6 12 LN:i:6",
            "R#0#chr 10 11 3 0 R#0#chr 12 18 LN:i:6",
            "R#0#chr 10 11 4 0 R#0#chr 18 24 LN:i:6",
            "R#0#chr 10 11 7 1 H#1#h 118 121 LN:i:3",
            "R#0#chr 20 21 5 0 R#0#chr 24 30 LN:i:6",
        ])
    );
    assert!(
        built
            .nodes
            .contains(&tsv(&["Q#0#chr 0 1 2 1 D#1#d 6 12 LN:i:6"]))
    );
}

#[test]
fn an_inversion_walks_reference_nodes_backwards() {
    let built = build("walks-two-refs.gfa", &[]);
    // <3 is 2*3+1; <2 steps back one node with the reverse bit, -1.
    assert_eq!(
        rows_of(&built.walks, "Q#0#chr", "I#1#i"),
        tsv(&[
            "Q#0#chr 0 1 I#1#i 0 0 0 1 2",
            "Q#0#chr 10 11 I#1#i 0 6 1 3 7,-1,4",
            "Q#0#chr 20 21 I#1#i 0 24 2 1 10",
        ])
    );
    assert!(
        built
            .links
            .contains(&tsv(&["Q#0#chr 10 11 2+ 3+ D#1#d 6 12 1 Q#0#chr 12 18 0"]))
    );
}

#[test]
fn a_walk_back_into_a_chunk_starts_a_new_piece_there() {
    let built = build("walks-two-refs.gfa", &[]);
    assert_eq!(
        rows_of(&built.walks, "R#0#chr", "D#1#d"),
        tsv(&[
            "R#0#chr 0 1 D#1#d 0 0 0 2 2,2",
            "R#0#chr 0 1 D#1#d 0 24 2 2 2,2",
            "R#0#chr 10 11 D#1#d 0 12 1 2 6,2",
            "R#0#chr 10 11 D#1#d 0 36 3 2 6,2",
            "R#0#chr 20 21 D#1#d 0 48 4 1 10",
        ])
    );
}

#[test]
fn settle_keeps_a_short_run_in_the_chunk_the_path_is_in() {
    let built = build("walks-two-refs.gfa", &["--settle", "7"]);
    assert_eq!(
        rows_of(&built.walks, "R#0#chr", "I#1#i"),
        tsv(&["R#0#chr 0 1 I#1#i 0 0 0 5 2,5,-1,4,2"])
    );
}

#[test]
fn the_cap_continues_a_piece_in_a_row_that_restarts_from_an_absolute_id() {
    let built = build("walks-two-refs.gfa", &["--cap", "2"]);
    assert_eq!(
        rows_of(&built.walks, "R#0#chr", "H#1#h"),
        tsv(&[
            "R#0#chr 0 1 H#1#h 100 100 0 2 2,2",
            "R#0#chr 10 11 H#1#h 100 112 1 2 6,8",
            "R#0#chr 10 11 H#1#h 100 121 2 1 8",
            "R#0#chr 20 21 H#1#h 100 127 3 1 10",
        ])
    );
}

#[test]
fn a_link_between_pieces_is_filed_under_both_chunks() {
    let built = build("walks-two-refs.gfa", &[]);
    let links = under(&built.links, "R#0#chr");
    for chunk in ["0 1", "10 11"] {
        for link in [
            "2+ 3+ R#0#chr 6 12 0 R#0#chr 12 18 0",
            "1- 4- R#0#chr 0 6 0 R#0#chr 18 24 0",
        ] {
            assert!(
                links.contains(&tsv(&[&format!("R#0#chr {chunk} {link}")])),
                "{chunk} {link}"
            );
        }
    }
    assert!(!links.contains("R#0#chr\t0\t1\t3+\t4+"));
}

#[test]
fn a_path_off_every_reference_is_counted_and_left_out() {
    let built = build("walks-two-refs.gfa", &[]);
    let stderr = String::from_utf8_lossy(&built.output.stderr);
    assert!(
        stderr.contains("1 paths visit no R node and are left out"),
        "{stderr}"
    );
    assert!(!built.walks.contains("U#1#u"));
    assert!(!built.nodes.contains("\t8\t"));
    assert!(!built.links.contains("8+"));
}

#[test]
fn p_lines_give_the_rows_w_lines_do() {
    let w = build("walks-two-refs.gfa", &[]);
    let p = build("walks-two-refs-p.gfa", &[]);
    assert!(p.output.status.success());
    assert_eq!(p.walks, w.walks);
    assert_eq!(p.nodes, w.nodes);
    assert_eq!(p.links, w.links);
}

#[test]
fn the_order_of_the_paths_changes_no_row() {
    let gfa = fs::read_to_string(format!(
        "{}/tests/data/walks-two-refs.gfa",
        env!("CARGO_MANIFEST_DIR")
    ))
    .unwrap();
    let (paths, rest): (Vec<&str>, Vec<&str>) = gfa.lines().partition(|l| l.starts_with('W'));
    let reversed: Vec<&str> = paths.iter().rev().copied().collect();
    let rotated: Vec<&str> = paths[2..].iter().chain(&paths[..2]).copied().collect();
    let orders = [
        [rest.clone(), reversed.clone()].concat(),
        [rest.clone(), rotated].concat(),
        // paths before the S lines take a second read
        [reversed, rest].concat(),
    ];
    let plain = build("walks-two-refs.gfa", &[]);
    for (i, lines) in orders.iter().enumerate() {
        let path =
            std::env::temp_dir().join(format!("walks-two-refs-{}-{i}.gfa", std::process::id()));
        fs::write(&path, lines.join("\n") + "\n").unwrap();
        let shuffled = build(path.to_str().unwrap(), &[]);
        fs::remove_file(&path).unwrap();
        assert!(shuffled.output.status.success(), "order {i}");
        assert_eq!(shuffled.walks, plain.walks, "order {i}");
        assert_eq!(shuffled.nodes, plain.nodes, "order {i}");
        assert_eq!(shuffled.links, plain.links, "order {i}");
    }
}

#[test]
fn gzipped_input_gives_the_same_rows() {
    let gfa = fs::read(format!(
        "{}/tests/data/walks-two-refs.gfa",
        env!("CARGO_MANIFEST_DIR")
    ))
    .unwrap();
    let path = std::env::temp_dir().join(format!("walks-two-refs-{}.gfa.gz", std::process::id()));
    let mut encoder = GzEncoder::new(fs::File::create(&path).unwrap(), Compression::default());
    encoder.write_all(&gfa).unwrap();
    encoder.finish().unwrap();
    let gzipped = build(path.to_str().unwrap(), &[]);
    fs::remove_file(&path).unwrap();
    let plain = build("walks-two-refs.gfa", &[]);
    assert!(gzipped.output.status.success());
    assert_eq!(gzipped.walks, plain.walks);
    assert_eq!(gzipped.nodes, plain.nodes);
    assert_eq!(gzipped.links, plain.links);
}

#[test]
fn sequences_adds_each_nodes_bases() {
    let built = build("walks-two-refs.gfa", &["--sequences"]);
    assert!(
        built
            .nodes
            .contains(&tsv(&["R#0#chr 10 11 7 1 H#1#h 118 121 LN:i:3 SQ:Z:GGG"]))
    );
}

#[test]
fn walks_reads_a_file_not_stdin() {
    let built = build("-", &[]);
    assert_eq!(built.output.status.code(), Some(1));
    assert!(String::from_utf8_lossy(&built.output.stderr).contains("needs a file"));
}

#[test]
fn an_unknown_reference_lists_the_samples() {
    let built = build("walks-two-refs.gfa", &["--refs", "R,X"]);
    assert_eq!(built.output.status.code(), Some(1));
    assert!(
        String::from_utf8_lossy(&built.output.stderr)
            .contains("--refs X matches no path's sample; have: R, Q, H, I, D, U")
    );
    assert!(built.walks.is_empty());
}
