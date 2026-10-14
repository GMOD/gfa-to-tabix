use std::collections::HashMap;
use std::ops::Deref;

// Names numbered in the order they first appear
#[derive(Default)]
pub struct Interner {
    index: HashMap<Vec<u8>, u32>,
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
