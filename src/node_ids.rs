// A GFA's segment ids to dense indexes, so that what the walk writer holds
// per node follows the number of segments and not the largest id. Ids map
// through pages of 1024, allocated only where a segment's id falls: the
// directory costs 4 bytes per 1024 ids, at most 8 MB below 2^31, and each
// page 4 KB.

const PAGE_BITS: u32 = 10;
const PAGE: usize = 1 << PAGE_BITS;
const NONE: u32 = u32::MAX;

// What an id maps to: a segment's index, or one of these
pub const NO_SEGMENT: u32 = NONE;
pub const ZERO_BP: u32 = NONE - 1;

#[derive(Default)]
pub struct NodeIds {
    pages: Vec<u32>,
    slots: Vec<u32>,
    // by index: the segment's GFA id
    ids: Vec<u32>,
}

impl NodeIds {
    // The index of segment `id`, NO_SEGMENT where it has no S line, ZERO_BP
    // where it has 0 bp
    pub fn index(&self, id: u32) -> u32 {
        match self.pages.get((id >> PAGE_BITS) as usize) {
            Some(&page) if page != NONE => self.slots[page as usize * PAGE + id as usize % PAGE],
            _ => NO_SEGMENT,
        }
    }

    fn set(&mut self, id: u32, value: u32) {
        let p = (id >> PAGE_BITS) as usize;
        if p >= self.pages.len() {
            self.pages.resize(p + 1, NONE);
        }
        if self.pages[p] == NONE {
            self.pages[p] = (self.slots.len() / PAGE) as u32;
            self.slots.resize(self.slots.len() + PAGE, NO_SEGMENT);
        }
        self.slots[self.pages[p] as usize * PAGE + id as usize % PAGE] = value;
    }

    // Gives segment `id` the next index, or marks it 0 bp; false where it
    // already has an S line
    pub fn add(&mut self, id: u32, zero_bp: bool) -> bool {
        if self.index(id) != NO_SEGMENT {
            false
        } else if zero_bp {
            self.set(id, ZERO_BP);
            true
        } else {
            self.set(id, self.ids.len() as u32);
            self.ids.push(id);
            true
        }
    }

    // Renumbers the segments in id order, so that indexes sort as ids do;
    // returns each old index's new one
    pub fn sort(&mut self) -> Vec<u32> {
        let mut order: Vec<u32> = (0..self.ids.len() as u32).collect();
        order.sort_unstable_by_key(|&k| self.ids[k as usize]);
        let mut new = vec![0; order.len()];
        for (rank, &old) in order.iter().enumerate() {
            new[old as usize] = rank as u32;
        }
        let ids = std::mem::take(&mut self.ids);
        for (old, &id) in ids.iter().enumerate() {
            self.set(id, new[old]);
        }
        self.ids = order.iter().map(|&old| ids[old as usize]).collect();
        new
    }

    // The GFA id of each index
    pub fn ids(&self) -> &[u32] {
        &self.ids
    }
}

// `values` reordered so that the value at each old index moves to `new[old]`
pub fn permute<T: Copy>(values: &[T], new: &[u32]) -> Vec<T> {
    let mut out = values.to_vec();
    for (old, &value) in values.iter().enumerate() {
        out[new[old] as usize] = value;
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ids_far_apart_map_to_dense_indexes_in_id_order() {
        let mut nodes = NodeIds::default();
        assert!(nodes.add(2147483647, false));
        assert!(nodes.add(5, true));
        assert!(nodes.add(1, false));
        assert!(!nodes.add(1, false));
        let new = nodes.sort();
        assert_eq!(new, [1, 0]);
        assert_eq!(nodes.ids(), [1, 2147483647]);
        assert_eq!(
            [1, 5, 2147483647, 2, 1 << 20].map(|id| nodes.index(id)),
            [0, ZERO_BP, 1, NO_SEGMENT, NO_SEGMENT]
        );
        assert_eq!(nodes.slots.len(), 2 * PAGE);
        assert_eq!(permute(&['b', 'a'], &new), ['a', 'b']);
    }
}
