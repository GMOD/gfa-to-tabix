// A snarl VCF worked out by hand. Top level only, so the LV=1 record is out; an
// overlapping top-level record is dropped; a reverse step on an interior
// segment is an inversion; a one-traversal snarl needs --min-alleles 1.

use std::fs;
use std::io::Read;
use std::process::{Command, Output};

use flate2::read::MultiGzDecoder;

const BINARY: &str = env!("CARGO_BIN_EXE_gfa-to-tabix");

const VCF: &str = "##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
K#1#c\t11\t>1>4\tACG\tA,ACGTT\t60\t.\tAT=>1>2>4,>1>3>4,>1>5>4;LV=0
K#1#c\t12\t>2>3\tC\tT\t60\t.\tAT=>2>3,>2>9>3;LV=1
K#1#c\t12\t>7>8\tC\tT\t60\t.\tAT=>7>8,>7>9>8;LV=0
K#1#c\t21\t>8>9\tA\tG\t60\t.\tAT=>8>10>9,>8<11>9;LV=0
K#1#c\t31\t>12>13\tA\tT\t60\t.\tAT=>12>13;LV=0
chr2\t5\t>1>2\tT\t.\t60\t.\tAT=>1>2,>1>3>2;LV=0
";

fn run(extra: &[&str]) -> (Output, String) {
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-bubbles-{}-{}",
        std::process::id(),
        extra.len()
    ));
    fs::create_dir_all(&dir).unwrap();
    fs::write(dir.join("s.vcf"), VCF).unwrap();
    let output = Command::new(BINARY)
        .arg("bubbles")
        .arg("--snarls")
        .arg(dir.join("s.vcf"))
        .arg("-o")
        .arg(dir.join("out"))
        .args(extra)
        .output()
        .unwrap();
    let mut text = String::new();
    if let Ok(file) = fs::File::open(dir.join("out.bubbles.bed.gz")) {
        MultiGzDecoder::new(file).read_to_string(&mut text).unwrap();
        assert!(dir.join("out.bubbles.bed.gz.tbi").exists());
    }
    fs::remove_dir_all(&dir).unwrap();
    (output, text)
}

#[test]
fn top_level_snarls_become_bubble_rows() {
    let (output, text) = run(&[]);
    assert!(output.status.success());
    assert_eq!(
        text,
        "K#1#c\t10\t13\t5\t3\t0\t1\t5\t.\t.\t.\t1@10,4\n\
         K#1#c\t20\t21\t4\t2\t1\t1\t1\t.\t.\t.\t8@20,9\n\
         chr2\t4\t5\t3\t2\t0\t1\t1\t.\t.\t.\t1@4,2\n"
    );
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("6 records, 5 top level, 3 bubbles"));
    assert!(stderr.contains("1 dropped as overlapping"));
}

#[test]
fn min_alleles_keeps_a_lone_traversal() {
    let (_, text) = run(&["--min-alleles", "1"]);
    assert!(text.contains("K#1#c\t30\t31\t2\t1\t0\t1\t1\t.\t.\t.\t12@30,13\n"));
}

#[test]
fn both_options_are_required() {
    let output = Command::new(BINARY)
        .args(["bubbles", "-o", "x"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
}
