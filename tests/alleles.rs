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
