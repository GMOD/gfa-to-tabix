use std::collections::VecDeque;
use std::fs::{self, File};
use std::io::{self, Write};
use std::mem;
use std::rc::Rc;

use flate2::read::MultiGzDecoder;

use noodles_bgzf::{self as bgzf, io::writer::CompressionLevel};
use noodles_core::Position;
use noodles_csi::binning_index::index::header::Builder;
use noodles_csi::binning_index::index::reference_sequence::bin::Chunk;
use noodles_tabix as tabix;

use crate::anchor::{Span, Spans, widen};
use crate::gfa::{Graph, strand};
use crate::parallel_bgzf;
use crate::place::Node;

#[derive(Clone, Copy, PartialEq, clap::ValueEnum)]
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

impl Row {
    pub fn text(&self) -> String {
        String::from_utf8_lossy(self.line.strip_suffix(b"\n").unwrap_or(&self.line)).into_owned()
    }
}

fn push_fields(line: &mut Vec<u8>, fields: &[&[u8]]) {
    for (i, field) in fields.iter().enumerate() {
        if i > 0 {
            line.push(b'\t');
        }
        line.extend_from_slice(field);
    }
}

fn push_coordinates(line: &mut Vec<u8>, sequence: &[u8], start: u64, end: u64) {
    line.extend_from_slice(sequence);
    write!(line, "\t{start}\t{end}").expect("a Vec takes every write");
}

fn row(spans: &Spans, (sequence, start, end): Span, rest: &[u8]) -> Row {
    let name = &spans.sequences[sequence as usize];
    let mut line = Vec::with_capacity(name.len() + 44 + rest.len());
    push_coordinates(&mut line, name, start, end);
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

// One row per interval a node is filed under. By contig that is its
// coordinate: `sequence start end id rank [carriers]`. Anchored, the interval
// leads and the node's coordinate follows the rank:
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
            push_coordinates(&mut rest, &node.sequence, node.start, node.end);
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
        let mut rest = Vec::new();
        for (id, reversed) in [
            (source, link.source_reversed),
            (target, link.target_reversed),
        ] {
            rest.extend_from_slice(&graph.node_ids[id]);
            rest.push(strand(reversed));
            rest.push(b'\t');
        }
        push_coordinates(&mut rest, &a.sequence, a.start, a.end);
        write!(rest, "\t{}\t", a.rank).expect("a Vec takes every write");
        push_coordinates(&mut rest, &b.sequence, b.start, b.end);
        write!(rest, "\t{}", b.rank).expect("a Vec takes every write");
        if let (Some(a), Some(b)) = (&a.carriers, &b.carriers) {
            push_fields(&mut rest, &[b"", a, b]);
        }
        let ends = spans.links[source].iter().chain(&spans.links[target]);
        match layout {
            Layout::Contig => rows.extend(ends.map(|&span| row(spans, span, &rest))),
            Layout::Anchored => {
                let mut covering: Vec<Span> = Vec::new();
                for &span in ends {
                    widen(&mut covering, span);
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

// A whole BED line, newline included, and the interval it is filed under
pub struct Line {
    pub chrom: Vec<u8>,
    pub start: u64,
    pub end: u64,
    pub text: Vec<u8>,
}

// Sorts the lines as `sort` does the rows, then writes them after `header`.
pub fn write_lines(path: &str, header: &[u8], lines: &mut [Line]) -> Result<(), String> {
    lines.sort_unstable_by(|a, b| (&a.chrom, a.start, &a.text).cmp(&(&b.chrom, b.start, &b.text)));
    let mut writer = Writer::create(path)?;
    writer.header(header)?;
    for line in lines.iter() {
        writer.push(&line.chrom, line.start, line.end, &line.text)?;
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
    sink: Option<parallel_bgzf::Writer>,
    indexer: tabix::index::Indexer,
    before: StreamPos,
    // rows written whose virtual positions are not known yet
    pending: VecDeque<Pending>,
}

// (block, offset): where a row starts or ends in the uncompressed stream
type StreamPos = (u64, u16);

struct Pending {
    sequence: Rc<str>,
    start: u64,
    end: u64,
    from: StreamPos,
    to: StreamPos,
}

impl Writer {
    // Compresses on every core, at bgzip's default level.
    pub fn create(path: &str) -> Result<Writer, String> {
        let partial = format!("{path}.partial");
        let threads = std::thread::available_parallelism().map_or(4, |n| n.get());
        let sink = File::create(&partial)
            .map(|file| parallel_bgzf::Writer::new(file, flate2::Compression::new(6), threads))
            .map_err(|e| format!("{path}: {e}"))?;
        let mut indexer = tabix::index::Indexer::default();
        indexer.set_header(Builder::bed().build());
        Ok(Writer {
            path: path.to_string(),
            partial_index: format!("{path}.tbi.partial"),
            partial,
            before: sink.position(),
            sink: Some(sink),
            indexer,
            pending: VecDeque::new(),
        })
    }

    fn write(&mut self, data: &[u8]) -> Result<StreamPos, String> {
        let sink = self.sink.as_mut().expect("writer is open until finish");
        sink.write(data)
            .map_err(|e| format!("{}: {e}", self.path))?;
        Ok(sink.position())
    }

    // A line before the rows. It starts with `#`, the index's comment prefix,
    // so Tabix readers return it as the header.
    pub fn header(&mut self, line: &[u8]) -> Result<(), String> {
        self.before = self.write(line)?;
        Ok(())
    }

    // `line` ends in a newline.
    pub fn push(
        &mut self,
        sequence: &[u8],
        start: u64,
        end: u64,
        line: &[u8],
    ) -> Result<(), String> {
        let after = self.write(line)?;
        let sequence = match self.pending.back() {
            Some(last) if last.sequence.as_bytes() == sequence => last.sequence.clone(),
            _ => Rc::from(String::from_utf8_lossy(sequence)),
        };
        self.pending.push_back(Pending {
            sequence,
            start,
            end,
            from: self.before,
            to: after,
        });
        self.before = after;
        self.index_written()
    }

    // Indexes the pending rows whose blocks are written.
    fn index_written(&mut self) -> Result<(), String> {
        let path = &self.path;
        let sink = self.sink.as_mut().expect("writer is open until finish");
        while let Some(row) = self.pending.front() {
            let (Some(from), Some(to)) = (sink.resolve(row.from), sink.resolve(row.to)) else {
                break;
            };
            let position = |n: u64| {
                Position::try_from(n as usize).map_err(|e| format!("{path}: coordinate {n}: {e}"))
            };
            let (sequence, start, end) = (&row.sequence, row.start, row.end);
            self.indexer
                .add_record(sequence, position(start + 1)?, position(end.max(start + 1))?, Chunk::new(from, to))
                .map_err(|e| {
                    format!(
                        "{path}: cannot index {sequence}:{start}-{end}: {e}. A Tabix index holds coordinates up to 512 Mb"
                    )
                })?;
            self.pending.pop_front();
        }
        sink.forget_before(self.pending.front().map_or(self.before.0, |row| row.from.0));
        Ok(())
    }

    pub fn finish(mut self) -> Result<(), String> {
        let path = self.path.clone();
        let fail = |e: std::io::Error| format!("{path}: {e}");
        self.sink
            .as_mut()
            .expect("writer is open until finish")
            .flush_all()
            .map_err(fail)?;
        self.index_written()?;
        let sink = self.sink.take().expect("writer is open until finish");
        sink.finish().map_err(fail)?;
        if !self.pending.is_empty() {
            return Err(format!("{path}: rows left unindexed"));
        }
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
