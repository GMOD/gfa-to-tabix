use std::collections::HashMap;
use std::hash::{BuildHasherDefault, Hasher};
use std::ops::Deref;

// Node ids and names hash well by multiplication alone.
#[derive(Default)]
pub struct IdHasher(u64);

impl Hasher for IdHasher {
    fn finish(&self) -> u64 {
        self.0 ^ (self.0 >> 32)
    }
    fn write(&mut self, bytes: &[u8]) {
        for &b in bytes {
            self.0 = (self.0.rotate_left(8) ^ u64::from(b)).wrapping_mul(0x9e37_79b9_7f4a_7c15);
        }
    }
    fn write_u32(&mut self, n: u32) {
        self.0 = (self.0 ^ u64::from(n)).wrapping_mul(0x9e37_79b9_7f4a_7c15);
    }
}

pub type FastMap<K, V> = HashMap<K, V, BuildHasherDefault<IdHasher>>;

// Names numbered in the order they first appear
#[derive(Default)]
pub struct Interner {
    index: FastMap<Vec<u8>, u32>,
    names: Vec<Vec<u8>>,
}

impl Interner {
    pub fn id(&mut self, name: &[u8]) -> u32 {
        if let Some(&id) = self.index.get(name) {
            return id;
        }
        let id = self.names.len() as u32;
        self.index.insert(name.to_vec(), id);
        self.names.push(name.to_vec());
        id
    }

    pub fn get(&self, name: &[u8]) -> Option<u32> {
        self.index.get(name).copied()
    }

    pub fn into_names(self) -> Vec<Vec<u8>> {
        self.names
    }
}

impl Deref for Interner {
    type Target = [Vec<u8>];

    fn deref(&self) -> &[Vec<u8>] {
        &self.names
    }
}
