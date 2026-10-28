// `build` over the hand-checked fixtures. paths.gfa: ref#1#chr walks 1 2 4,
// so the reference sample is `ref` and the bubble at 4-6 is the one snarl
// below. reversed.gfa is paths.gfa with ref#1#chr reading 2 reversed. rgfa.gfa
// names its backbone a bare `chr1`, so it has no sample. A stand-in gfatools on
// PATH answers for the real one.

use std::fs;
use std::io::{Read, Write};
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};
use std::process::{Command, Output, Stdio};
use std::sync::atomic::{AtomicUsize, Ordering};

use flate2::read::MultiGzDecoder;

const BINARY: &str = env!("CARGO_BIN_EXE_gfa-to-tabix");

const SNARLS: &str = "##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
ref#1#chr\t5\t>1>4\tCC\tG\t60\t.\tAT=>1>2>4,>1>3>4;LV=0
";

fn fixture(name: &str) -> String {
    format!("{}/tests/data/{name}", env!("CARGO_MANIFEST_DIR"))
}

fn scratch() -> PathBuf {
    static RUNS: AtomicUsize = AtomicUsize::new(0);
    let dir = std::env::temp_dir().join(format!(
        "gfa-to-tabix-build-{}-{}",
        std::process::id(),
        RUNS.fetch_add(1, Ordering::Relaxed)
    ));
    fs::create_dir_all(&dir).unwrap();
    dir
}

// A gfatools that keeps what it reads in stdin.gfa and runs `script`.
fn fake_gfatools(dir: &Path, script: &str) {
    let path = dir.join("gfatools");
    let stdin = dir.join("stdin.gfa");
    fs::write(
        &path,
        format!("#!/bin/sh\n/bin/cat > '{}'\n{script}\n", stdin.display()),
    )
    .unwrap();
    fs::set_permissions(&path, fs::Permissions::from_mode(0o755)).unwrap();
}

fn build(dir: &Path, args: &[&str], stdin: Option<&str>) -> Output {
    let mut child = Command::new(BINARY)
        .arg("build")
        .args(args)
        .env("PATH", dir)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .unwrap();
    let mut pipe = child.stdin.take().unwrap();
    if let Some(path) = stdin {
        pipe.write_all(&fs::read(path).unwrap()).unwrap();
    }
    drop(pipe);
    child.wait_with_output().unwrap()
}

fn read(path: &Path) -> String {
    fs::read_to_string(path).unwrap()
}

fn gunzip(path: &Path) -> String {
    let mut text = String::new();
    MultiGzDecoder::new(fs::File::open(path).unwrap())
        .read_to_string(&mut text)
        .unwrap();
    text
}

const PLUGIN: &str = r#"  "plugins": [
    {
      "name": "GraphGenomeView",
      "storePlugin": "GraphGenomeView",
      "esmUrl": "https://jbrowse.org/plugins/jbrowse-plugin-graphgenomeviewer/latest/dist/jbrowse-plugin-graphgenomeviewer.esm.js"
    }
  ],"#;

#[test]
fn a_plain_gfa_with_snarls_maps_the_assembly_onto_its_sample() {
    let dir = scratch();
    let snarls = dir.join("snarls.vcf");
    fs::write(&snarls, SNARLS).unwrap();
    let prefix = dir.join("my-graph.v1");
    let output = build(
        &dir,
        &[
            &fixture("paths.gfa"),
            "-o",
            prefix.to_str().unwrap(),
            "--assembly",
            "hg",
            "--snarls",
            snarls.to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    assert_eq!(
        read(&dir.join("my-graph.v1.graph.json")),
        r#"{
  "schema": 1,
  "reference": "ref",
  "index": "my-graph.v1",
  "contig": "my-graph.v1.contig",
  "tier": {
    "prefix": "my-graph.v1.fold50",
    "foldBelowBp": 50
  },
  "bubbles": "my-graph.v1.bubbles.bed.gz",
  "alleles": "my-graph.v1.alleles.bed.gz"
}
"#
    );
    let bubbles = r#"
        "uri": "my-graph.v1.bubbles.bed.gz",
        "assemblyNameToPanSN": {
          "hg": "ref"
        }
      }"#;
    assert_eq!(
        read(&dir.join("my-graph.v1.config.json")),
        format!(
            r#"{{
  "$schema": "https://jbrowse.org/jb2/schema/v5/config.json",
{PLUGIN}
  "tracks": [
    {{
      "type": "GraphTrack",
      "trackId": "my_graph_v1_graph",
      "name": "my-graph.v1 graph",
      "assemblyNames": [
        "hg"
      ],
      "adapter": {{
        "type": "RgfaTabixAdapter",
        "uri": "my-graph.v1",
        "assemblyNameToPanSN": {{
          "hg": "ref"
        }},
        "coarse": {{
          "uri": "my-graph.v1.fold50",
          "foldBelowBp": 50
        }}
      }},
      "displayDefaults": {{
        "showLabels": "none"
      }},
      "displays": [
        {{
          "type": "LinearGraphDisplay",
          "displayId": "my_graph_v1_graph-LinearGraphDisplay"
        }},
        {{
          "type": "LinearBasicDisplay",
          "displayId": "my_graph_v1_graph-LinearBasicDisplay"
        }}
      ]
    }},
    {{
      "type": "AlignmentsTrack",
      "trackId": "my_graph_v1_alleles",
      "name": "my-graph.v1 alleles",
      "assemblyNames": [
        "hg"
      ],
      "adapter": {{
        "type": "BedTabixAdapter",
        "uri": "my-graph.v1.alleles.bed.gz"
      }}
    }},
    {{
      "type": "FeatureTrack",
      "trackId": "my_graph_v1_bubbles",
      "name": "my-graph.v1 bubbles",
      "assemblyNames": [
        "hg"
      ],
      "adapter": {{
        "type": "MinigraphBubbleAdapter",{bubbles}
    }},
    {{
      "type": "QuantitativeTrack",
      "trackId": "my_graph_v1_bubble_score",
      "name": "my-graph.v1 segments per bubble",
      "assemblyNames": [
        "hg"
      ],
      "adapter": {{
        "type": "MinigraphBubbleAdapter",{bubbles}
    }}
  ]
}}
"#
        )
    );
    assert_eq!(
        gunzip(&dir.join("my-graph.v1.bubbles.bed.gz")),
        "ref#1#chr\t4\t6\t4\t2\t0\t1\t2\t.\t.\t.\t1@4,4\n"
    );
    for kind in [
        "segs",
        "links",
        "contig.segs",
        "contig.links",
        "fold50.segs",
        "fold50.links",
        "alleles",
    ] {
        assert!(dir.join(format!("my-graph.v1.{kind}.bed.gz.tbi")).exists());
    }
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_segment_the_reference_reads_reversed_is_written_forward() {
    let dir = scratch();
    let snarls = dir.join("snarls.vcf");
    fs::write(
        &snarls,
        SNARLS.replace("CC\tG\t60\t.\tAT=>1>2>4", "GG\tG\t60\t.\tAT=>1<2>4"),
    )
    .unwrap();
    let prefix = dir.join("out");
    let output = build(
        &dir,
        &[
            &fixture("reversed.gfa"),
            "-o",
            prefix.to_str().unwrap(),
            "--snarls",
            snarls.to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    let links = gunzip(&dir.join("out.links.bed.gz"));
    assert!(links.contains("\t1+\t2+\t"), "{links}");
    assert!(links.contains("\t2+\t4+\t"), "{links}");
    assert!(!links.contains('-'), "{links}");
    assert!(!gunzip(&dir.join("out.contig.links.bed.gz")).contains('-'));
    assert_eq!(
        gunzip(&dir.join("out.bubbles.bed.gz")),
        "ref#1#chr\t4\t6\t4\t2\t0\t1\t2\t.\t.\t.\t1@4,4\n"
    );
    assert_eq!(
        gunzip(&dir.join("out.fold50.segs.bed.gz")),
        "ref#1#chr\t0\t9\t1\t0\tref#1#chr\t0\t9\n"
    );
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn without_gfatools_an_rgfa_from_stdin_builds_with_no_bubbles() {
    let dir = scratch();
    let output = build(
        &dir,
        &["-", "-o", dir.join("out").to_str().unwrap()],
        Some(&fixture("rgfa.gfa")),
    );
    assert!(output.status.success(), "{output:?}");
    assert!(String::from_utf8_lossy(&output.stderr).contains(
        "note: gfatools is not on PATH, so no bubble file or bubble tracks for this graph"
    ));
    assert!(!dir.join("out.bubbles.bed.gz").exists());
    assert_eq!(
        read(&dir.join("out.graph.json")),
        r#"{
  "schema": 1,
  "reference": null,
  "index": "out",
  "contig": "out.contig",
  "tier": {
    "prefix": "out.fold10000",
    "foldBelowBp": 10000
  },
  "bubbles": null,
  "alleles": "out.alleles.bed.gz"
}
"#
    );
    assert_eq!(
        read(&dir.join("out.config.json")),
        format!(
            r#"{{
  "$schema": "https://jbrowse.org/jb2/schema/v5/config.json",
{PLUGIN}
  "tracks": [
    {{
      "type": "GraphTrack",
      "trackId": "out_graph",
      "name": "out graph",
      "assemblyNames": [
        "reference"
      ],
      "adapter": {{
        "type": "RgfaTabixAdapter",
        "uri": "out",
        "coarse": {{
          "uri": "out.fold10000",
          "foldBelowBp": 10000
        }}
      }},
      "displayDefaults": {{
        "showLabels": "none"
      }},
      "displays": [
        {{
          "type": "LinearGraphDisplay",
          "displayId": "out_graph-LinearGraphDisplay"
        }},
        {{
          "type": "LinearBasicDisplay",
          "displayId": "out_graph-LinearBasicDisplay"
        }}
      ]
    }},
    {{
      "type": "AlignmentsTrack",
      "trackId": "out_alleles",
      "name": "out alleles",
      "assemblyNames": [
        "reference"
      ],
      "adapter": {{
        "type": "BedTabixAdapter",
        "uri": "out.alleles.bed.gz"
      }}
    }}
  ]
}}
"#
        )
    );
    assert_eq!(
        gunzip(&dir.join("out.segs.bed.gz")),
        "chr1\t0\t13\ts3\t1\tb#1#c\t100\t103\n\
         chr1\t0\t8\ts1\t0\tchr1\t0\t8\n\
         chr1\t8\t13\ts2\t0\tchr1\t8\t13\n"
    );
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn gfatools_reads_the_graph_and_its_bubbles_are_sorted() {
    let dir = scratch();
    fake_gfatools(
        &dir,
        "printf 'chr1\\t8\\t8\\t2\\t1\\t0\\t0\\t0\\t-1\\t-1\\t-1\\ts1,s2\\t*\\t*\\n\
         b#1#c\\t100\\t103\\t1\\t1\\t0\\t3\\t3\\t-1\\t-1\\t-1\\ts3\\t*\\t*\\n'",
    );
    let output = build(
        &dir,
        &[
            &fixture("rgfa.gfa"),
            "-o",
            dir.join("out").to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    assert_eq!(
        read(&dir.join("stdin.gfa")),
        read(Path::new(&fixture("rgfa.gfa")))
    );
    assert_eq!(
        gunzip(&dir.join("out.bubbles.bed.gz")),
        "b#1#c\t100\t103\t1\t1\t0\t3\t3\t-1\t-1\t-1\ts3\t*\t*\n\
         chr1\t8\t8\t2\t1\t0\t0\t0\t-1\t-1\t-1\ts1,s2\t*\t*\n"
    );
    assert!(read(&dir.join("out.graph.json")).contains("\"bubbles\": \"out.bubbles.bed.gz\""));
    assert_eq!(
        read(&dir.join("out.config.json"))
            .matches("\"type\": \"MinigraphBubbleAdapter\"")
            .count(),
        2
    );
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_failing_gfatools_fails_the_build() {
    let dir = scratch();
    fake_gfatools(&dir, "echo 'bad graph' >&2; exit 3");
    let output = build(
        &dir,
        &[
            &fixture("rgfa.gfa"),
            "-o",
            dir.join("out").to_str().unwrap(),
        ],
        None,
    );
    assert_eq!(output.status.code(), Some(1));
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(stderr.contains("gfatools bubble failed"), "{stderr}");
    assert!(stderr.contains("bad graph"), "{stderr}");
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_plain_gfa_needs_no_gfatools() {
    let dir = scratch();
    fake_gfatools(&dir, "echo 'should not finish' >&2; exit 3");
    let output = build(
        &dir,
        &[
            &fixture("paths.gfa"),
            "-o",
            dir.join("out").to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    assert!(String::from_utf8_lossy(&output.stderr).contains("note: no --snarls given"));
    let manifest = read(&dir.join("out.graph.json"));
    assert!(manifest.contains("\"bubbles\": null"));
    assert!(manifest.contains("\"prefix\": \"out.fold50\""));
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_reference_past_512_mb_gets_csi_indexes_and_tracks_that_read_them() {
    let dir = scratch();
    let gfa = dir.join("big.gfa");
    fs::write(
        &gfa,
        "S\t1\t*\tLN:i:600000000\nS\t2\tACGT\nL\t1\t+\t2\t+\t0M\nP\tref#1#chr\t1+,2+\t*\n",
    )
    .unwrap();
    let output = build(
        &dir,
        &[
            gfa.to_str().unwrap(),
            "-o",
            dir.join("out").to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    for file in ["segs", "links", "contig.segs", "fold50.segs"] {
        assert!(
            dir.join(format!("out.{file}.bed.gz.csi")).exists(),
            "{file}"
        );
        assert!(
            !dir.join(format!("out.{file}.bed.gz.tbi")).exists(),
            "{file}"
        );
    }
    // no allele reaches past 512 Mb, so the allele file keeps a .tbi
    assert!(dir.join("out.alleles.bed.gz.tbi").exists());
    let config = read(&dir.join("out.config.json"));
    assert!(
        config.contains("\"uri\": \"out\",\n        \"csi\": true,"),
        "{config}"
    );
    assert_eq!(config.matches("\"csi\"").count(), 1, "{config}");
    fs::remove_dir_all(&dir).unwrap();
}

// The first untagged S line comes after 100,000 tagged ones, past where an
// earlier version stopped looking and took the graph for an rGFA.
#[test]
fn a_late_untagged_segment_makes_a_plain_gfa() {
    let dir = scratch();
    fake_gfatools(&dir, "echo 'should not finish' >&2; exit 3");
    let n = 100_001;
    let mut gfa = String::new();
    for i in 0..n {
        gfa += &format!("S\ts{i}\tA");
        if i < n - 1 {
            gfa += &format!("\tSN:Z:chr\tSO:i:{i}\tSR:i:0");
        }
        gfa += "\n";
    }
    let steps: Vec<String> = (0..n).map(|i| format!("s{i}+")).collect();
    gfa += &format!("P\tref\t{}\t*\n", steps.join(","));
    let graph = dir.join("late.gfa");
    fs::write(&graph, gfa).unwrap();
    let output = build(
        &dir,
        &[
            graph.to_str().unwrap(),
            "-o",
            dir.join("out").to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    assert!(read(&dir.join("out.graph.json")).contains("\"prefix\": \"out.fold50\""));
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_partly_tagged_graph_with_no_paths_skips_gfatools() {
    let dir = scratch();
    fake_gfatools(&dir, "echo 'should not finish' >&2; exit 3");
    let graph = dir.join("partly.gfa");
    fs::write(
        &graph,
        "S\ta\tAAAA\tSN:Z:chr\tSO:i:0\tSR:i:0\nS\tb\tCC\nL\ta\t+\tb\t+\t0M\n",
    )
    .unwrap();
    let output = build(
        &dir,
        &[
            graph.to_str().unwrap(),
            "-o",
            dir.join("out").to_str().unwrap(),
        ],
        None,
    );
    assert!(output.status.success(), "{output:?}");
    let stderr = String::from_utf8_lossy(&output.stderr);
    assert!(
        stderr.contains("not every S line has an SN tag"),
        "{stderr}"
    );
    assert!(read(&dir.join("out.graph.json")).contains("\"bubbles\": null"));
    fs::remove_dir_all(&dir).unwrap();
}

#[test]
fn a_graph_and_an_output_prefix_are_required() {
    let output = Command::new(BINARY)
        .args(["build", "x.gfa"])
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(2));
}
