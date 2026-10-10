// Two call files worked out by hand. b1 spans 100 bp and s1 takes a 160 bp
// route through it; b2 is a pure insertion site, where `*` is the reference
// allele; s1 has no alignment over b3.

use std::fs;
use std::io::Read;
use std::process::Command;
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::read::MultiGzDecoder;

const BINARY: &str = env!("CARGO_BIN_EXE_gfa-to-tabix");

const REF: &str = "ref#1#chr\t100\t200\t3\t2\t>1>2:100:+:c:0:100
ref#1#chr\t300\t300\t3\t2\t*:0:+:c:0:0
ref#1#chr\t400\t450\t3\t2\t>5:50:+:c:0:50
";
const S1: &str = "ref#1#chr\t100\t200\t3\t2\t>1>3>2:160:+:c:0:160
ref#1#chr\t300\t300\t3\t2\t>8:25:-:c:0:25
ref#1#chr\t400\t450\t3\t2\t.
";

fn run(files: &[(&str, &str)]) -> (std::process::Output, String) {
    static RUNS: AtomicUsize = AtomicUsize::new(0);
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-paths-{}-{}",
        std::process::id(),
        RUNS.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&dir).unwrap();
    let mut command = Command::new(BINARY);
    command.arg("paths").arg("-o").arg(dir.join("out"));
    for (name, text) in files {
        fs::write(dir.join(name), text).unwrap();
        command.arg(dir.join(name));
    }
    let output = command.output().unwrap();
    let mut text = String::new();
    if let Ok(file) = fs::File::open(dir.join("out.bed.gz")) {
        MultiGzDecoder::new(file).read_to_string(&mut text).unwrap();
        assert!(dir.join("out.bed.gz.tbi").exists());
    }
    fs::remove_dir_all(&dir).unwrap();
    (output, text)
}

#[test]
fn a_row_per_bubble_and_sample() {
    let (output, text) = run(&[("ref.call.bed", REF), ("s1.call.bed", S1)]);
    assert!(output.status.success());
    let rows: Vec<&str> = text.lines().skip(1).collect();
    assert!(text.starts_with("#chrom\tstart\tend\tname\tscore\tstrand\t"));
    assert_eq!(
        rows,
        [
            "chr\t100\t200\t+60\t0\t+\t100\t200\t192,0,192\ts1\tins\t60\t160\t100\t2\t1\t>1>3>2",
            "chr\t100\t200\tref\t0\t+\t100\t200\t204,204,204\tref\tref\t0\t100\t100\t2\t1\t>1>2",
            "chr\t300\t301\t+25\t0\t-\t300\t301\t192,0,192\ts1\tins\t25\t25\t0\t2\t1\t>8",
            "chr\t300\t301\tref\t0\t+\t300\t301\t204,204,204\tref\tref\t0\t0\t0\t2\t1\t*",
            "chr\t400\t450\tno call\t0\t.\t400\t450\t191,170,64\ts1\tnocall\t0\t-1\t50\t1\t0\t.",
            "chr\t400\t450\tref\t0\t+\t400\t450\t204,204,204\tref\tref\t0\t50\t50\t1\t0\t>5",
        ]
    );
}

#[test]
fn files_of_different_lengths_are_refused() {
    let short = "ref#1#chr\t100\t200\t3\t2\t>1>2:100:+:c:0:100\n";
    let (output, text) = run(&[("ref.call.bed", REF), ("s1.call.bed", short)]);
    assert_eq!(output.status.code(), Some(1));
    assert!(text.is_empty());
    assert!(String::from_utf8_lossy(&output.stderr).contains("same order for every sample"));
}
