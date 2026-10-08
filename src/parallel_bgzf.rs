// BGZF written by several threads: the stream is cut into blocks of a fixed
// size, and each batch of full blocks is deflated in parallel. A position in
// the stream is known as (block number, offset) at once; its virtual position
// once the blocks before it are written.

use std::collections::VecDeque;
use std::fs::File;
use std::io::{self, BufWriter, Write};
use std::mem;
use std::thread;

use flate2::{Compress, Compression, Crc, FlushCompress, Status};
use noodles_bgzf::VirtualPosition;

// htslib's block size, which leaves room for a stored block's overhead.
const BLOCK: usize = 0xff00;
const EOF: [u8; 28] = [
    0x1f, 0x8b, 0x08, 0x04, 0, 0, 0, 0, 0, 0xff, 0x06, 0, b'B', b'C', 0x02, 0, 0x1b, 0, 0x03, 0, 0,
    0, 0, 0, 0, 0, 0, 0,
];

pub type Position = (u64, u16);

pub struct Writer {
    file: BufWriter<File>,
    level: Compression,
    threads: usize,
    block: Vec<u8>,
    full: Vec<Vec<u8>>,
    written: u64,
    // compressed start of blocks first_start..=written
    starts: VecDeque<u64>,
    first_start: u64,
}

fn frame(compress: &mut Compress, data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(18 + BLOCK + 1024);
    out.extend_from_slice(&[
        0x1f, 0x8b, 0x08, 0x04, 0, 0, 0, 0, 0, 0xff, 0x06, 0, b'B', b'C', 0x02, 0, 0, 0,
    ]);
    compress.reset();
    let deflated = matches!(
        compress.compress_vec(data, &mut out, FlushCompress::Finish),
        Ok(Status::StreamEnd)
    );
    if !deflated || out.len() + 8 > 1 << 16 {
        out.truncate(18);
        Compress::new(Compression::none(), false)
            .compress_vec(data, &mut out, FlushCompress::Finish)
            .expect("a stored block fits");
    }
    let mut crc = Crc::new();
    crc.update(data);
    out.extend_from_slice(&crc.sum().to_le_bytes());
    out.extend_from_slice(&(data.len() as u32).to_le_bytes());
    let size = (out.len() - 1) as u16;
    out[16..18].copy_from_slice(&size.to_le_bytes());
    out
}

impl Writer {
    pub fn new(file: File, level: Compression, threads: usize) -> Writer {
        Writer {
            file: BufWriter::with_capacity(1 << 20, file),
            level,
            threads: threads.max(1),
            block: Vec::with_capacity(BLOCK),
            full: Vec::new(),
            written: 0,
            starts: VecDeque::from([0]),
            first_start: 0,
        }
    }

    pub fn position(&self) -> Position {
        (
            self.written + self.full.len() as u64,
            self.block.len() as u16,
        )
    }

    pub fn resolve(&self, (block, offset): Position) -> Option<VirtualPosition> {
        let start = *self
            .starts
            .get(block.checked_sub(self.first_start)? as usize)?;
        VirtualPosition::try_from((start, offset)).ok()
    }

    // Positions before `block` will not be resolved again.
    pub fn forget_before(&mut self, block: u64) {
        while self.first_start < block.min(self.written) {
            self.starts.pop_front();
            self.first_start += 1;
        }
    }

    // True when the call wrote blocks, so more positions resolve.
    pub fn write(&mut self, mut data: &[u8]) -> io::Result<bool> {
        let mut wrote = false;
        while !data.is_empty() {
            let take = (BLOCK - self.block.len()).min(data.len());
            self.block.extend_from_slice(&data[..take]);
            data = &data[take..];
            if self.block.len() == BLOCK {
                let block = mem::replace(&mut self.block, Vec::with_capacity(BLOCK));
                self.full.push(block);
                if self.full.len() >= 16 * self.threads {
                    self.write_full()?;
                    wrote = true;
                }
            }
        }
        Ok(wrote)
    }

    fn write_full(&mut self) -> io::Result<()> {
        let level = self.level;
        let per_thread = self.full.len().div_ceil(self.threads);
        let frames: Vec<Vec<u8>> = thread::scope(|scope| {
            let workers: Vec<_> = self
                .full
                .chunks(per_thread.max(1))
                .map(|blocks| {
                    scope.spawn(move || {
                        let mut compress = Compress::new(level, false);
                        blocks
                            .iter()
                            .map(|b| frame(&mut compress, b))
                            .collect::<Vec<_>>()
                    })
                })
                .collect();
            workers
                .into_iter()
                .flat_map(|w| w.join().expect("compressing a block panicked"))
                .collect()
        });
        self.full.clear();
        let mut position = *self.starts.back().expect("starts holds the next block");
        for frame in frames {
            self.file.write_all(&frame)?;
            position += frame.len() as u64;
            self.written += 1;
            self.starts.push_back(position);
        }
        Ok(())
    }

    // Writes every block, the last one short, so every position resolves.
    pub fn flush_all(&mut self) -> io::Result<()> {
        if !self.block.is_empty() {
            let block = mem::take(&mut self.block);
            self.full.push(block);
        }
        self.write_full()
    }

    pub fn finish(mut self) -> io::Result<()> {
        self.flush_all()?;
        self.file.write_all(&EOF)?;
        self.file.flush()
    }
}
