use std::fs::{self, File};
use std::io::{self, Write};
use std::mem;

use flate2::read::MultiGzDecoder;

use noodles_bgzf::{self as bgzf, io::writer::CompressionLevel};
use noodles_core::Position;
use noodles_csi::binning_index::index::header::Builder;
use noodles_csi::binning_index::index::reference_sequence::bin::Chunk;
use noodles_tabix as tabix;

use crate::anchor::{Span, Spans};
use crate::gfa::Graph;
use crate::place::Node;

#[derive(Clone, Copy, PartialEq)]
pub enum Layout {
    Anchored,
    Contig,
}

pub struct Row {
    sequence: u32,
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

fn coordinates(sequence: &[u8], start: u64, end: u64) -> Vec<u8> {
    let mut line = sequence.to_vec();
    line.extend_from_slice(format!("\t{start}\t{end}").as_bytes());
    line
}

fn row(spans: &Spans, (sequence, start, end): Span, rest: &[u8]) -> Row {
    let mut line = coordinates(&spans.sequences[sequence as usize], start, end);
    line.push(b'\t');
    line.extend_from_slice(rest);
    line.push(b'\n');
    Row {
        sequence,
        start,
        end,
        line,
    }
}

// One row per interval a node is filed under. By contig that is its own
// coordinate: `sequence start end id rank [carriers]`. Anchored, the interval
// leads and the node's own coordinate follows the rank:
// `anchorSequence anchorStart anchorEnd id rank sequence start end [carriers]`.
pub fn node_rows(graph: &Graph, nodes: &[Option<Node>], spans: &Spans, layout: Layout) -> Vec<Row> {
    let mut rows = Vec::new();
    for ((id, node), filed) in graph.node_ids.iter().zip(nodes).zip(&spans.nodes) {
        let Some(node) = node else { continue };
        let rank = node.rank.to_string();
        let mut rest = Vec::new();
        push_fields(&mut rest, &[id, rank.as_bytes()]);
        if layout == Layout::Anchored {
            rest.push(b'\t');
            rest.extend_from_slice(&coordinates(&node.sequence, node.start, node.end));
        }
        if let Some(carriers) = &node.carriers {
            push_fields(&mut rest, &[b"", carriers]);
        }
        rows.extend(filed.iter().map(|&span| row(spans, span, &rest)));
    }
    rows
}

// Every link row states both of its nodes in full after the interval it is
// filed under. By contig a link gets one row under each node's coordinate.
// Anchored, it gets one row per reference sequence, under the interval that
// covers both nodes' anchors there. Returns the rows and the links left out
// because a node has no coordinate.
pub fn link_rows(
    graph: &Graph,
    nodes: &[Option<Node>],
    spans: &Spans,
    layout: Layout,
) -> (Vec<Row>, usize) {
    let mut rows = Vec::new();
    let mut skipped = 0;
    for link in &graph.links {
        let (source, target) = (link.source as usize, link.target as usize);
        let (Some(a), Some(b)) = (&nodes[source], &nodes[target]) else {
            skipped += 1;
            continue;
        };
        let source_id = [graph.node_ids[source].as_slice(), &link.source_strand].concat();
        let target_id = [graph.node_ids[target].as_slice(), &link.target_strand].concat();
        let (a_rank, b_rank) = (a.rank.to_string(), b.rank.to_string());
        let mut rest = Vec::new();
        push_fields(
            &mut rest,
            &[
                &source_id,
                &target_id,
                &coordinates(&a.sequence, a.start, a.end),
                a_rank.as_bytes(),
                &coordinates(&b.sequence, b.start, b.end),
                b_rank.as_bytes(),
            ],
        );
        if let (Some(a), Some(b)) = (&a.carriers, &b.carriers) {
            push_fields(&mut rest, &[b"", a, b]);
        }
        let ends = spans.links[source].iter().chain(&spans.links[target]);
        match layout {
            Layout::Contig => rows.extend(ends.map(|&span| row(spans, span, &rest))),
            Layout::Anchored => {
                let mut covering: Vec<Span> = Vec::new();
                for &(sequence, start, end) in ends {
                    match covering.iter_mut().find(|c| c.0 == sequence) {
                        Some(held) => {
                            held.1 = held.1.min(start);
                            held.2 = held.2.max(end);
                        }
                        None => covering.push((sequence, start, end)),
                    }
                }
                rows.extend(covering.into_iter().map(|span| row(spans, span, &rest)));
            }
        }
    }
    (rows, skipped)
}

// The order `LC_ALL=C sort -k1,1 -k2,2n` gives, whole line as the tiebreak.
pub fn sort(rows: &mut [Row], spans: &Spans) {
    let name = |row: &Row| spans.sequences[row.sequence as usize].as_slice();
    rows.sort_unstable_by(|a, b| (name(a), a.start, &a.line).cmp(&(name(b), b.start, &b.line)));
}

fn compressor(file: File) -> bgzf::io::Writer<File> {
    bgzf::io::writer::Builder::default()
        .set_compression_level(CompressionLevel::BEST)
        .build_from_writer(file)
}

// Writes the rows and their index beside each other, under temporary names
// until both are complete.
pub fn write(path: &str, rows: &[Row], spans: &Spans) -> Result<(), String> {
    let mut writer = Writer::create(path)?;
    for row in rows {
        writer.push(
            &spans.sequences[row.sequence as usize],
            row.start,
            row.end,
            &row.line,
        )?;
    }
    writer.finish()
}

// A bgzip-compressed BED file and its Tabix index, written row by row in
// sorted order. Until `finish`, both sit under `.partial` names, which a
// writer dropped unfinished removes.
pub struct Writer {
    path: String,
    partial: String,
    partial_index: String,
    writer: Option<bgzf::io::Writer<File>>,
    indexer: tabix::index::Indexer,
    before: bgzf::VirtualPosition,
}

impl Writer {
    pub fn create(path: &str) -> Result<Writer, String> {
        let partial = format!("{path}.partial");
        let writer = File::create(&partial)
            .map(bgzf::io::Writer::new)
            .map_err(|e| format!("{path}: {e}"))?;
        let mut indexer = tabix::index::Indexer::default();
        indexer.set_header(Builder::bed().build());
        Ok(Writer {
            path: path.to_string(),
            partial_index: format!("{path}.tbi.partial"),
            partial,
            before: writer.virtual_position(),
            writer: Some(writer),
            indexer,
        })
    }

    // `line` ends in a newline.
    pub fn push(
        &mut self,
        sequence: &[u8],
        start: u64,
        end: u64,
        line: &[u8],
    ) -> Result<(), String> {
        let path = &self.path;
        let writer = self.writer.as_mut().expect("writer is open until finish");
        writer.write_all(line).map_err(|e| format!("{path}: {e}"))?;
        let after = writer.virtual_position();
        let sequence = String::from_utf8_lossy(sequence);
        let position = |n: u64| {
            Position::try_from(n as usize).map_err(|e| format!("{path}: coordinate {n}: {e}"))
        };
        self.indexer
            .add_record(&sequence, position(start + 1)?, position(end.max(start + 1))?, Chunk::new(self.before, after))
            .map_err(|e| {
                format!(
                    "{path}: cannot index {sequence}:{start}-{end}: {e}. A Tabix index holds coordinates up to 512 Mb"
                )
            })?;
        self.before = after;
        Ok(())
    }

    pub fn finish(mut self) -> Result<(), String> {
        let path = self.path.clone();
        let fail = |e: std::io::Error| format!("{path}: {e}");
        let writer = self.writer.take().expect("writer is open until finish");
        writer.finish().map_err(fail)?;
        let indexer = mem::take(&mut self.indexer);
        // A reader downloads the whole index, so recompress it at the best level.
        let mut default_level = tabix::io::Writer::new(Vec::new());
        default_level.write_index(&indexer.build()).map_err(fail)?;
        let compressed = default_level.into_inner().finish().map_err(fail)?;
        let mut index_writer = File::create(&self.partial_index)
            .map(compressor)
            .map_err(fail)?;
        io::copy(
            &mut MultiGzDecoder::new(compressed.as_slice()),
            &mut index_writer,
        )
        .map_err(fail)?;
        index_writer.finish().map_err(fail)?;
        let index_path = format!("{path}.tbi");
        fs::rename(&self.partial, &path).map_err(fail)?;
        fs::rename(&self.partial_index, &index_path).map_err(|e| format!("{index_path}: {e}"))?;
        self.partial.clear();
        self.partial_index.clear();
        Ok(())
    }
}

impl Drop for Writer {
    fn drop(&mut self) {
        if !self.partial.is_empty() {
            let _ = fs::remove_file(&self.partial);
            let _ = fs::remove_file(&self.partial_index);
        }
    }
}
