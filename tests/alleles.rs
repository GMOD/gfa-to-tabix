// alleles.gfa: chr1 is s1 s2 s3 s4 at 10 bp each. s2 -> s4 skips s3, and the
// 25 bp s5 on b#1#c sits between s1 and s2.

use std::fs;
use std::io::Read;
use std::process::Command;

use flate2::read::MultiGzDecoder;

const BINARY: &str = env!("CARGO_BIN_EXE_gfa-to-tabix");

fn alleles(layout: &str) -> (bool, String, String) {
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-alleles-{}-{layout}",
        std::process::id()
    ));
    fs::create_dir_all(&dir).unwrap();
    let prefix = dir.join("out");
    let gfa = format!("{}/tests/data/alleles.gfa", env!("CARGO_MANIFEST_DIR"));
    let index = Command::new(BINARY)
        .args([&gfa, "--layout", layout, "-o"])
        .arg(&prefix)
        .output()
        .unwrap();
    assert!(index.status.success());
    let output = Command::new(BINARY)
        .arg("alleles")
        .arg(&prefix)
        .output()
        .unwrap();
    let mut text = String::new();
    if let Ok(file) = fs::File::open(dir.join("out.alleles.bed.gz")) {
        MultiGzDecoder::new(file).read_to_string(&mut text).unwrap();
        assert!(dir.join("out.alleles.bed.gz.tbi").exists());
    }
    fs::remove_dir_all(&dir).unwrap();
    (
        output.status.success(),
        text,
        String::from_utf8_lossy(&output.stderr).into_owned(),
    )
}

#[test]
fn an_insertion_and_a_deletion_each_get_a_row() {
    let (ok, text, _) = alleles("contig");
    assert!(ok);
    let mut lines = text.lines();
    assert!(
        lines
            .next()
            .unwrap()
            .starts_with("#chrom\tstart\tend\tname")
    );
    let rows: Vec<&str> = lines.collect();
    assert_eq!(
        rows,
        [
            "chr1\t10\t11\t+25\t0\t+\t10\t11\t192,0,192\tins\t25\t25\t0\t25I\t1\tb\t0\t>s5",
            "chr1\t20\t30\t-10\t0\t.\t20\t30\t128,128,128\tdel\t-10\t0\t10\t10D\t.\t.\t0\t.",
        ]
    );
}

#[test]
fn the_anchored_layout_is_refused() {
    let (ok, text, stderr) = alleles("anchored");
    assert!(!ok);
    assert!(text.is_empty());
    assert!(stderr.contains("--layout contig"));
}

// The shapes a real graph's index has, written straight as the two BED files.
// Each once gave a wrong file rather than an error: an earlier version dropped
// 237 of HPRC's walks, AMY1's 41 kb insertion among them.
mod shapes {
    use std::collections::HashMap;
    use std::fs;
    use std::io::{Read, Write};
    use std::process::Command;
    use std::sync::atomic::{AtomicUsize, Ordering};

    use flate2::Compression;
    use flate2::read::MultiGzDecoder;
    use flate2::write::GzEncoder;

    use super::BINARY;

    const K: &str = "K12#1#chr";
    const S: &str = "Sakai#1#chr";
    const O: &str = "O157#1#chr";

    // id, chrom, start, end, rank
    type Segment = (&'static str, &'static str, u32, u32, u32);
    type Link = (&'static str, &'static str, &'static str, &'static str);
    type Row = HashMap<&'static str, String>;

    const SEGMENTS: [Segment; 26] = [
        ("s1", K, 0, 100, 0),
        ("s2", K, 100, 200, 0),
        ("s3", K, 200, 300, 0),
        ("s4", K, 300, 400, 0),
        ("s5", K, 400, 500, 0),
        ("s6", K, 600, 700, 0),
        ("s7", K, 800, 900, 0),
        ("s8", K, 1000, 1100, 0),
        ("s9", K, 1200, 1300, 0),
        ("s10", K, 1400, 1500, 0),
        ("s11", K, 1500, 1600, 0),
        ("s12", K, 1700, 1800, 0),
        ("s13", K, 1800, 1900, 0),
        ("a1", S, 1000, 1500, 1),
        ("c1", S, 2000, 2100, 1),
        ("d1", S, 3000, 3050, 1),
        ("f1", S, 4000, 4040, 1),
        ("f2", S, 4040, 4070, 2),
        ("g1", S, 5000, 5010, 1),
        ("g2", S, 5010, 5040, 1),
        ("g3", S, 5040, 5050, 1),
        ("h1", S, 6000, 6020, 1),
        ("k1", S, 7000, 7010, 1),
        ("k2", O, 0, 10, 1),
        ("k3", S, 7020, 7030, 1),
        ("k4", S, 7030, 7040, 1),
    ];

    const LINKS: [Link; 27] = [
        ("s1", "+", "a1", "+"), // an insertion
        ("a1", "+", "s2", "+"),
        ("s2", "+", "s4", "+"), // a clean skip of s3
        ("s2", "+", "c1", "+"), // a same-length allele
        ("c1", "+", "s4", "+"),
        ("s4", "+", "d1", "+"), // a rejoin stated backbone to allele
        ("s5", "-", "d1", "-"),
        ("s7", "-", "s6", "-"),  // the skip written backwards
        ("s8", "+", "s9", "-"),  // mixed orientation
        ("s9", "+", "s8", "+"),  // a back-link: a tandem duplication
        ("h1", "-", "s10", "-"), // an insertion stated toward the backbone
        ("h1", "+", "s11", "+"),
        ("s12", "+", "k1", "+"), // k1 k2 k3 leaves s12 and returns to it
        ("k1", "+", "k2", "+"),
        ("k2", "+", "k3", "+"),
        ("s12", "+", "k3", "-"), // in at k3's far end, a second route by k4
        ("k4", "+", "k3", "+"),
        ("k4", "-", "s13", "-"),
        ("s3", "-", "s4", "-"), // a back-link written backwards
        ("s5", "+", "f1", "+"),
        ("f1", "+", "f2", "+"),
        ("f2", "+", "s6", "+"),
        ("s6", "+", "g1", "+"), // a branch point
        ("g1", "+", "g2", "+"),
        ("g1", "+", "g3", "+"),
        ("g2", "+", "s7", "+"),
        ("g3", "+", "s7", "+"),
    ];

    fn gzip(path: &std::path::Path, rows: &[String]) {
        let mut out = GzEncoder::new(fs::File::create(path).unwrap(), Compression::fast());
        for row in rows {
            writeln!(out, "{row}").unwrap();
        }
        out.finish().unwrap();
    }

    // the same link, stated from its other end
    fn flip((src, so, tgt, to): Link) -> Link {
        let other = |o| if o == "+" { "-" } else { "+" };
        (tgt, other(to), src, other(so))
    }

    fn run() -> Vec<Row> {
        run_with(&SEGMENTS, &LINKS)
    }

    fn run_with(segments: &[Segment], links_in: &[Link]) -> Vec<Row> {
        static RUNS: AtomicUsize = AtomicUsize::new(0);
        const COLUMNS: [&str; 18] = [
            "chrom",
            "start",
            "end",
            "name",
            "score",
            "strand",
            "thickStart",
            "thickEnd",
            "itemRgb",
            "class",
            "delta",
            "altLen",
            "refLen",
            "CIGAR",
            "discoveryRank",
            "firstSeenIn",
            "nested",
            "segments",
        ];
        let dir = std::env::temp_dir().join(format!(
            "gfa-to-tabix-shapes-{}-{}",
            std::process::id(),
            RUNS.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir_all(&dir).unwrap();
        let by_id: HashMap<&str, _> = segments.iter().map(|s| (s.0, s)).collect();
        let segs: Vec<String> = segments
            .iter()
            .map(|(id, chrom, start, end, rank)| format!("{chrom}\t{start}\t{end}\t{id}\t{rank}"))
            .collect();
        // one row per link per endpoint, as the indexer writes it
        let mut links = Vec::new();
        for &(src, so, tgt, to) in links_in {
            let (a, b) = (by_id[src], by_id[tgt]);
            let rest = format!(
                "{src}{so}\t{tgt}{to}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}",
                a.1, a.2, a.3, a.4, b.1, b.2, b.3, b.4
            );
            links.push(format!("{}\t{}\t{}\t{rest}", a.1, a.2, a.3));
            links.push(format!("{}\t{}\t{}\t{rest}", b.1, b.2, b.3));
        }
        gzip(&dir.join("f.segs.bed.gz"), &segs);
        gzip(&dir.join("f.links.bed.gz"), &links);
        let output = Command::new(BINARY)
            .arg("alleles")
            .arg(dir.join("f"))
            .output()
            .unwrap();
        assert!(output.status.success(), "{output:?}");
        let mut text = String::new();
        MultiGzDecoder::new(fs::File::open(dir.join("f.alleles.bed.gz")).unwrap())
            .read_to_string(&mut text)
            .unwrap();
        fs::remove_dir_all(&dir).unwrap();
        let mut lines = text.lines();
        assert_eq!(
            lines.next().unwrap(),
            format!("#{}", COLUMNS.join("\t")),
            "the header is the 18-column contract"
        );
        lines
            .map(|l| {
                COLUMNS
                    .iter()
                    .copied()
                    .zip(l.split('\t').map(String::from))
                    .collect()
            })
            .collect()
    }

    fn pick<'a>(rows: &'a [Row], want: &[(&str, &str)]) -> Vec<&'a Row> {
        rows.iter()
            .filter(|r| want.iter().all(|(k, v)| r[k] == *v))
            .collect()
    }

    fn show(rows: &[&Row], keys: &[&str]) -> Vec<Vec<String>> {
        rows.iter()
            .map(|r| keys.iter().map(|k| r[k].clone()).collect())
            .collect()
    }

    #[test]
    fn each_shape_resolves() {
        let rows = run();

        // a gap between two backbone nodes is a deletion, and the CIGAR lets a
        // 63 kb allele draw at its own size; the second is stated backwards
        let deletions = pick(&rows, &[("class", "del"), ("segments", ".")]);
        assert_eq!(
            show(&deletions, &["start", "end", "name", "CIGAR", "refLen"]),
            [
                ["200", "300", "-100", "100D", "100"],
                ["700", "800", "-100", "100D", "100"],
            ]
        );

        // a mixed-orientation pair is an inversion breakpoint, not a skip
        assert!(pick(&rows, &[("class", "del"), ("start", "1100")]).is_empty());

        // a link back to an earlier node repeats the reference between them
        assert!(pick(&rows, &[("class", "del"), ("start", "1000")]).is_empty());
        assert!(pick(&rows, &[("class", "del"), ("end", "400")]).is_empty());

        // an insertion consumes no reference, so it is one base wide and its
        // size sits in the CIGAR
        assert_eq!(
            show(
                &pick(&rows, &[("class", "ins"), ("start", "100")]),
                &["end", "name", "CIGAR", "refLen"]
            ),
            [["101", "+500", "500I", "0"]]
        );

        // equal lengths are a substitution
        assert_eq!(
            show(
                &pick(&rows, &[("class", "sub")]),
                &["start", "end", "CIGAR", "delta"]
            ),
            [["200", "300", "100M", "0"]]
        );

        // altLen sums the route, and `segments` lists it in traversal order
        let route = pick(&rows, &[("segments", ">f1>f2")]);
        assert_eq!(
            show(&route, &["altLen", "refLen", "CIGAR"]),
            [["70", "100", "70M30D"]]
        );

        // discoveryRank is the lowest rank on the route, named by its sample
        assert_eq!(
            show(&route, &["discoveryRank", "firstSeenIn"]),
            [["1", "Sakai"]]
        );

        // a branch point makes the length one route among several
        assert_eq!(
            show(
                &pick(&rows, &[("start", "700"), ("nested", "1")]),
                &["segments"]
            ),
            [[">g1>g2"]]
        );

        // `L s5 - d1 -` leaves nothing departing d1 toward the backbone, so
        // only testing the arrival finds the exit, and the walk in from s5
        // retraces it, so the allele has one row
        assert_eq!(
            show(
                &pick(&rows, &[("class", "ins"), ("start", "400")]),
                &["start", "end", "class", "altLen", "segments"],
            ),
            [["400", "401", "ins", "50", ">d1"]]
        );

        // both of h1's links leave it for the backbone
        assert_eq!(
            show(
                &pick(&rows, &[("segments", ">h1")]),
                &["start", "end", "class", "altLen"],
            ),
            [["1500", "1501", "ins", "20"]]
        );
        assert!(pick(&rows, &[("segments", "<h1")]).is_empty());

        // the walk in at k3's far end takes another route, so it is another
        // allele, not k1 k2 k3 retraced
        assert_eq!(
            show(
                &pick(&rows, &[("start", "1800")]),
                &["end", "strand", "segments"],
            ),
            [["1801", "+", ">k1>k2>k3"], ["1900", "-", "<k3<k4"]]
        );

        // the walk in from s7 takes the other route, by g3, written in the
        // same direction as g1 g2
        assert_eq!(
            show(
                &pick(&rows, &[("start", "700"), ("class", "del")]),
                &["segments"]
            ),
            [["."], [">g1>g2"], [">g1>g3"]]
        );
    }

    fn all(rows: &[Row], keys: &[&str]) -> Vec<Vec<String>> {
        show(&rows.iter().collect::<Vec<_>>(), keys)
    }

    fn sorted(rows: &[Row]) -> Vec<Vec<(&str, &str)>> {
        let mut lines: Vec<Vec<(&str, &str)>> = rows
            .iter()
            .map(|r| {
                let mut line: Vec<(&str, &str)> = r.iter().map(|(k, v)| (*k, v.as_str())).collect();
                line.sort();
                line
            })
            .collect();
        lines.sort();
        lines
    }

    #[test]
    fn neither_link_direction_nor_order_changes_the_rows() {
        let flipped: Vec<Link> = LINKS.iter().rev().copied().map(flip).collect();
        assert_eq!(sorted(&run()), sorted(&run_with(&SEGMENTS, &flipped)));
    }

    // a1 branches to b and c, which meet again at a4. Before canonical walks,
    // stating one of these links the other way round changed the row count.
    const BRANCH: [Segment; 6] = [
        ("s1", K, 0, 100, 0),
        ("s2", K, 100, 200, 0),
        ("a1", S, 0, 10, 1),
        ("b", "T#1#chr", 0, 30, 2),
        ("c", "U#1#chr", 0, 50, 2),
        ("a4", S, 60, 70, 1),
    ];
    const BRANCH_LINKS: [Link; 6] = [
        ("s1", "+", "a1", "+"),
        ("a1", "+", "b", "+"),
        ("a1", "+", "c", "+"),
        ("b", "+", "a4", "+"),
        ("c", "+", "a4", "+"),
        ("a4", "+", "s2", "+"),
    ];

    #[test]
    fn every_choice_of_link_directions_gives_the_same_rows() {
        let rows = run_with(&BRANCH, &BRANCH_LINKS);
        assert_eq!(
            all(&rows, &["start", "end", "segments"]),
            [["100", "101", ">a1>b>a4"]]
        );
        for mask in 1..1 << BRANCH_LINKS.len() {
            let links: Vec<Link> = BRANCH_LINKS
                .iter()
                .enumerate()
                .map(|(i, &l)| if mask & 1 << i != 0 { flip(l) } else { l })
                .collect();
            assert_eq!(
                sorted(&run_with(&BRANCH, &links)),
                sorted(&rows),
                "flipped {mask:06b}"
            );
        }
    }

    #[test]
    fn each_backbone_exit_at_the_stop_node_is_an_allele() {
        let segments = [
            ("s1", K, 0, 10, 0),
            ("s2", K, 10, 20, 0),
            ("s3", K, 20, 30, 0),
            ("x1", S, 0, 16, 1),
        ];
        for exit in [("x1", "+", "s3", "+"), ("s3", "-", "x1", "-")] {
            let links = [("s1", "+", "x1", "+"), ("x1", "+", "s2", "+"), exit];
            assert_eq!(
                all(
                    &run_with(&segments, &links),
                    &["start", "end", "name", "segments"]
                ),
                [["10", "11", "+16", ">x1"], ["10", "20", "+6", ">x1"]]
            );
        }
    }

    #[test]
    fn a_walk_goes_past_another_sequences_backbone() {
        let segments = [
            ("t1", K, 0, 10, 0),
            ("t2", K, 10, 20, 0),
            ("u1", "K12#1#plasmid", 0, 10, 0),
            ("m1", S, 0, 5, 1),
            ("m2", S, 5, 12, 1),
        ];
        let links = [
            ("t1", "+", "m1", "+"),
            ("m1", "+", "u1", "+"),
            ("m1", "+", "m2", "+"),
            ("m2", "+", "t2", "+"),
        ];
        assert_eq!(
            all(
                &run_with(&segments, &links),
                &["chrom", "start", "end", "altLen", "segments"]
            ),
            [["chr", "10", "11", "12", ">m1>m2"]]
        );
    }

    // a duplication of s1, like a backbone link back to an earlier node
    #[test]
    fn leaving_and_returning_to_one_node_is_no_deletion() {
        let segments = [
            ("s1", K, 0, 100, 0),
            ("s2", K, 100, 200, 0),
            ("a1", S, 0, 10, 1),
        ];
        let links = [
            ("s1", "+", "s2", "+"),
            ("s1", "+", "a1", "+"),
            ("s1", "-", "a1", "-"),
        ];
        assert!(run_with(&segments, &links).is_empty());
    }

    #[test]
    fn a_missing_pair_is_named() {
        let output = Command::new(BINARY)
            .args(["alleles", "/nonexistent/nope"])
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(1));
        assert!(String::from_utf8_lossy(&output.stderr).contains("missing"));
    }
}
