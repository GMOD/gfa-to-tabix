use std::fs::File;
use std::io::{self, Write};

use flate2::read::MultiGzDecoder;

use noodles_bgzf::{self as bgzf, io::writer::CompressionLevel};
use noodles_core::Position;
use noodles_csi::binning_index::index::header::Builder;
use noodles_csi::binning_index::index::reference_sequence::bin::Chunk;
use noodles_tabix as tabix;

use crate::gfa::Graph;
use crate::place::Node;

pub struct Row {
    sequence: Vec<u8>,
    start: u64,
    end: u64,
    line: Vec<u8>,
}

fn push_fields(line: &mut Vec<u8>, fields: &[&[u8]]) {
    for (i, field) in fields.iter().enumerate() {
        if i > 0 {
            line.push(b'\t');
        }
        line.extend_from_slice(field);
    }
}

fn span(node: &Node) -> [Vec<u8>; 2] {
    [
        node.start.to_string().into_bytes(),
        node.end.to_string().into_bytes(),
    ]
}

pub fn node_rows(graph: &Graph, nodes: &[Option<Node>]) -> Vec<Row> {
    let mut rows = Vec::new();
    for (id, node) in graph.node_ids.iter().zip(nodes) {
        let Some(node) = node else { continue };
        let [start, end] = span(node);
        let rank = node.rank.to_string();
        let mut line = Vec::new();
        push_fields(
            &mut line,
            &[&node.sequence, &start, &end, id, rank.as_bytes()],
        );
        if let Some(carriers) = &node.carriers {
            push_fields(&mut line, &[b"", carriers]);
        }
        line.push(b'\n');
        rows.push(Row {
            sequence: node.sequence.clone(),
            start: node.start,
            end: node.end,
            line,
        });
    }
    rows
}

// Each link gets one row under each of its two nodes, so a region query finds
// it from either side. Returns the rows and the links left out because a node
// has no coordinate.
pub fn link_rows(graph: &Graph, nodes: &[Option<Node>]) -> (Vec<Row>, usize) {
    let mut rows = Vec::new();
    let mut skipped = 0;
    for link in &graph.links {
        let (Some(source), Some(target)) =
            (&nodes[link.source as usize], &nodes[link.target as usize])
        else {
            skipped += 1;
            continue;
        };
        let source_id = [
            graph.node_ids[link.source as usize].as_slice(),
            &link.source_strand,
        ]
        .concat();
        let target_id = [
            graph.node_ids[link.target as usize].as_slice(),
            &link.target_strand,
        ]
        .concat();
        let [source_start, source_end] = span(source);
        let [target_start, target_end] = span(target);
        let (source_rank, target_rank) = (source.rank.to_string(), target.rank.to_string());
        let mut record = Vec::new();
        push_fields(
            &mut record,
            &[
                &source_id,
                &target_id,
                &source.sequence,
                &source_start,
                &source_end,
                source_rank.as_bytes(),
                &target.sequence,
                &target_start,
                &target_end,
                target_rank.as_bytes(),
            ],
        );
        if let (Some(a), Some(b)) = (&source.carriers, &target.carriers) {
            push_fields(&mut record, &[b"", a, b]);
        }
        record.push(b'\n');
        for (node, start, end) in [
            (source, &source_start, &source_end),
            (target, &target_start, &target_end),
        ] {
            let mut line = Vec::new();
            push_fields(&mut line, &[&node.sequence, start, end, b""]);
            line.extend_from_slice(&record);
            rows.push(Row {
                sequence: node.sequence.clone(),
                start: node.start,
                end: node.end,
                line,
            });
        }
    }
    (rows, skipped)
}

// The order `LC_ALL=C sort -k1,1 -k2,2n` gives, whole line as the tiebreak.
pub fn sort(rows: &mut [Row]) {
    rows.sort_unstable_by(|a, b| {
        (&a.sequence, a.start, &a.line).cmp(&(&b.sequence, b.start, &b.line))
    });
}

fn compressor(file: File) -> bgzf::io::Writer<File> {
    bgzf::io::writer::Builder::default()
        .set_compression_level(CompressionLevel::BEST)
        .build_from_writer(file)
}

pub fn write(path: &str, rows: &[Row]) -> Result<(), String> {
    let fail = |e: std::io::Error| format!("{path}: {e}");
    let mut writer = File::create(path).map(compressor).map_err(fail)?;
    let mut indexer = tabix::index::Indexer::default();
    indexer.set_header(Builder::bed().build());
    let mut before = writer.virtual_position();
    for row in rows {
        writer.write_all(&row.line).map_err(fail)?;
        let after = writer.virtual_position();
        let position = |n: u64| {
            Position::try_from(n as usize).map_err(|e| format!("{path}: coordinate {n}: {e}"))
        };
        indexer
            .add_record(
                &String::from_utf8_lossy(&row.sequence),
                position(row.start + 1)?,
                position(row.end.max(row.start + 1))?,
                Chunk::new(before, after),
            )
            .map_err(|e| {
                format!(
                    "{path}: cannot index {}:{}-{}: {e}",
                    String::from_utf8_lossy(&row.sequence),
                    row.start,
                    row.end
                )
            })?;
        before = after;
    }
    writer.finish().map_err(fail)?;
    // noodles writes the index at its default compression level; a graph
    // track downloads the whole index, so recompress it at the best one.
    let mut default_level = tabix::io::Writer::new(Vec::new());
    default_level.write_index(&indexer.build()).map_err(fail)?;
    let compressed = default_level.into_inner().finish().map_err(fail)?;
    let index_path = format!("{path}.tbi");
    let index_fail = |e: std::io::Error| format!("{index_path}: {e}");
    let mut index_writer = File::create(&index_path)
        .map(compressor)
        .map_err(index_fail)?;
    io::copy(
        &mut MultiGzDecoder::new(compressed.as_slice()),
        &mut index_writer,
    )
    .map_err(index_fail)?;
    index_writer.finish().map_err(index_fail)?;
    Ok(())
}
