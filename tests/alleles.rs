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

    use flate2::Compression;
    use flate2::read::MultiGzDecoder;
    use flate2::write::GzEncoder;

    use super::BINARY;

    const K: &str = "K12#1#chr";
    const S: &str = "Sakai#1#chr";

    // id, chrom, start, end, rank
    const SEGMENTS: [(&str, &str, u32, u32, u32); 17] = [
        ("s1", K, 0, 100, 0),
        ("s2", K, 100, 200, 0),
        ("s3", K, 200, 300, 0),
        ("s4", K, 300, 400, 0),
        ("s5", K, 400, 500, 0),
        ("s6", K, 600, 700, 0),
        ("s7", K, 800, 900, 0),
        ("s8", K, 1000, 1100, 0),
        ("s9", K, 1200, 1300, 0),
        ("a1", S, 1000, 1500, 1),
        ("c1", S, 2000, 2100, 1),
        ("d1", S, 3000, 3050, 1),
        ("f1", S, 4000, 4040, 1),
        ("f2", S, 4040, 4070, 2),
        ("g1", S, 5000, 5010, 1),
        ("g2", S, 5010, 5040, 1),
        ("g3", S, 5040, 5050, 1),
    ];

    const LINKS: [(&str, &str, &str, &str); 17] = [
        ("s1", "+", "a1", "+"), // an insertion
        ("a1", "+", "s2", "+"),
        ("s2", "+", "s4", "+"), // a clean skip of s3
        ("s2", "+", "c1", "+"), // a same-length allele
        ("c1", "+", "s4", "+"),
        ("s4", "+", "d1", "+"), // a rejoin stated backbone to allele
        ("s5", "-", "d1", "-"),
        ("s7", "-", "s6", "-"), // the skip written backwards
        ("s8", "+", "s9", "-"), // mixed orientation
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

    fn run() -> Vec<HashMap<&'static str, String>> {
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
        let dir = std::env::temp_dir().join(format!("gfa-to-tabix-shapes-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let by_id: HashMap<&str, _> = SEGMENTS.iter().map(|s| (s.0, s)).collect();
        let segs: Vec<String> = SEGMENTS
            .iter()
            .map(|(id, chrom, start, end, rank)| format!("{chrom}\t{start}\t{end}\t{id}\t{rank}"))
            .collect();
        // one row per link per endpoint, as the indexer writes it
        let mut links = Vec::new();
        for (src, so, tgt, to) in LINKS {
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

    fn pick<'a>(
        rows: &'a [HashMap<&'static str, String>],
        want: &[(&str, &str)],
    ) -> Vec<&'a HashMap<&'static str, String>> {
        rows.iter()
            .filter(|r| want.iter().all(|(k, v)| r[k] == *v))
            .collect()
    }

    fn show(rows: &[&HashMap<&'static str, String>], keys: &[&str]) -> Vec<Vec<String>> {
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
        // only testing the arrival finds the exit
        let mut rejoin = show(
            &pick(&rows, &[("class", "ins"), ("start", "400")]),
            &["start", "end", "class", "altLen"],
        );
        rejoin.dedup();
        assert_eq!(rejoin, [["400", "401", "ins", "50"]]);
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
