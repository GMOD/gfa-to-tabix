// fold.gfa: chr is b1 [0,100) b2 [110,200) b3 [200,300) b4 [300,400). The link
// b1 -> b2 skips 10 bp, and a1 is a 10 bp insertion beside it: both fold under
// 50. a2a and a2b are 60 bp each, contiguous, between b3 and b4: the 120 bp
// allele stays and merges into one segment named a2a. b2 and b3 join end to
// end with no other link between them, so they merge too, into b2.

use std::fs;
use std::io::Read;
use std::process::Command;

use flate2::read::MultiGzDecoder;

const BINARY: &str = env!("CARGO_BIN_EXE_gfa-to-tabix");

fn fold(below: &str) -> (bool, String, String) {
    let dir =
        std::env::temp_dir().join(format!("gfa-to-tabix-fold-{}-{below}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let gfa = format!("{}/tests/data/fold.gfa", env!("CARGO_MANIFEST_DIR"));
    let output = Command::new(BINARY)
        .args(["fold", &gfa, "--below", below, "--layout", "contig", "-o"])
        .arg(dir.join("out"))
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
    let (segs, links) = (read("segs"), read("links"));
    fs::remove_dir_all(&dir).unwrap();
    (output.status.success(), segs, links)
}

#[test]
fn small_alleles_and_skips_fold_and_a_big_allele_merges() {
    let (ok, segs, links) = fold("50");
    assert!(ok);
    assert_eq!(
        segs,
        "chr\t0\t100\tb1\t0\n\
         chr\t110\t300\tb2\t0\n\
         chr\t300\t400\tb4\t0\n\
         seqA\t2000\t2120\ta2a\t1\n"
    );
    assert!(!links.contains("a1"));
    assert!(!links.contains("a2b"));
    assert!(!links.contains("b1+\tb2+"));
    assert!(!links.contains("b3"));
    assert!(links.contains("b2+\ta2a+"));
    assert!(links.contains("b2+\tb4+"));
    assert!(links.contains("a2a+\tb4+"));
    assert_eq!(links.lines().count(), 6);
}

#[test]
fn a_small_threshold_keeps_the_small_allele() {
    let (ok, segs, _) = fold("5");
    assert!(ok);
    assert_eq!(segs.lines().count(), 5);
    assert!(segs.contains("a1\t1"));
}

#[test]
fn below_is_required() {
    let output = Command::new(BINARY)
        .args(["fold", "x.gfa", "-o", "x"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
}
