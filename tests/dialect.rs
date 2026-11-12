// Every GFA of docs/walks-container/dialect built as walk files and as a
// node and link index, against expected.tsv beside them: the lines its rows
// name as `path@fragStart`, its `#haplotype` lines, the refusal, and the
// fixture whose files it must match byte for byte.

use std::collections::{BTreeMap, BTreeSet};
use std::fs;
use std::io::Read;
use std::path::{Path, PathBuf};
use std::process::{Command, Output};

use flate2::read::MultiGzDecoder;

fn dialect() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("docs/walks-container/dialect")
}

struct Walks {
    output: Output,
    data: Vec<u8>,
    directory: Vec<u8>,
}

fn run(args: &[&str], out: &Path) -> Output {
    Command::new(env!("CARGO_BIN_EXE_gfa-to-tabix"))
        .args(args)
        .arg("-o")
        .arg(out)
        .output()
        .unwrap()
}

fn walks(fixture: &str, refs: &str, dir: &Path) -> Walks {
    let out = dir.join(fixture);
    let gfa = dialect().join(fixture);
    let output = run(
        &[
            gfa.to_str().unwrap(),
            "--walks",
            "--refs",
            refs,
            "--tile",
            "10",
        ],
        &out,
    );
    let file = |suffix: &str| {
        fs::read(dir.join(format!("{fixture}.{refs}.walks.gz{suffix}"))).unwrap_or_default()
    };
    Walks {
        output,
        data: file(""),
        directory: file(".idx"),
    }
}

fn stderr(output: &Output) -> String {
    String::from_utf8_lossy(&output.stderr).into_owned()
}

fn lines_and_haplotypes(data: &[u8]) -> (String, String) {
    let mut bytes = Vec::new();
    MultiGzDecoder::new(data).read_to_end(&mut bytes).unwrap();
    let text = String::from_utf8_lossy(&bytes);
    let mut lines = BTreeSet::new();
    let mut haplotypes = Vec::new();
    for line in text.lines() {
        let cols: Vec<&str> = line.split('\t').collect();
        if cols[0] == "#haplotype" {
            haplotypes.push(cols[1]);
        } else if matches!(cols.get(3), Some(&("ref" | "walk" | "abridged"))) {
            lines.insert((cols[4], cols[5].parse::<u64>().unwrap()));
        }
    }
    let lines: Vec<String> = lines
        .into_iter()
        .map(|(path, start)| format!("{path}@{start}"))
        .collect();
    (
        lines.join(" "),
        if haplotypes.is_empty() {
            "-".into()
        } else {
            haplotypes.join(",")
        },
    )
}

#[test]
fn every_dialect_fixture_builds_or_is_refused_as_its_table_says() {
    let dir = std::env::temp_dir().join(format!("gfa-to-tabix-dialect-{}", std::process::id()));
    fs::create_dir_all(&dir).unwrap();
    let table = fs::read_to_string(dialect().join("expected.tsv")).unwrap();
    let rows: BTreeMap<&str, Vec<&str>> = table
        .lines()
        .skip(1)
        .map(|row| row.split('\t').collect::<Vec<_>>())
        .map(|cols| (cols[0], cols))
        .collect();
    let fixtures: BTreeSet<String> = fs::read_dir(dialect())
        .unwrap()
        .flatten()
        .map(|entry| entry.file_name().into_string().unwrap())
        .filter(|name| name.ends_with(".gfa"))
        .collect();
    assert_eq!(
        fixtures.iter().map(String::as_str).collect::<Vec<_>>(),
        rows.keys().copied().collect::<Vec<_>>(),
        "expected.tsv has a row for each fixture"
    );
    for (&fixture, cols) in rows.iter().filter(|(_, cols)| cols[2] != "skip") {
        let (refs, expected, haplotypes, index, twin) =
            (cols[1], cols[3], cols[4], cols[5], cols[6]);
        let built = walks(fixture, refs, &dir);
        if cols[2] == "refused" {
            assert_eq!(built.output.status.code(), Some(1), "{fixture}");
            assert!(built.data.is_empty(), "{fixture} left a file");
            let stderr = stderr(&built.output);
            assert!(stderr.contains(expected), "{fixture}: {stderr}");
        } else {
            assert!(
                built.output.status.success(),
                "{fixture}: {}",
                stderr(&built.output)
            );
            if cols[2] == "ok" && expected != "." {
                assert_eq!(
                    lines_and_haplotypes(&built.data),
                    (expected.to_string(), haplotypes.to_string()),
                    "{fixture}"
                );
            }
        }
        if twin != "." {
            let other = walks(twin, rows[twin][1], &dir);
            assert!(!built.data.is_empty(), "{fixture}");
            assert!(
                built.data == other.data,
                "{fixture} and {twin}: walk files differ"
            );
            assert!(
                built.directory == other.directory,
                "{fixture} and {twin}: directories differ"
            );
        }
        let gfa = dialect().join(fixture);
        let indexed = run(
            &[gfa.to_str().unwrap(), "--reference", refs],
            &dir.join(format!("{fixture}.index")),
        );
        if index == "ok" {
            assert!(
                indexed.status.success(),
                "{fixture} index: {}",
                stderr(&indexed)
            );
        } else {
            assert_eq!(indexed.status.code(), Some(1), "{fixture} index");
            let stderr = stderr(&indexed);
            assert!(stderr.contains(index), "{fixture} index: {stderr}");
        }
    }
    fs::remove_dir_all(&dir).unwrap();
}
