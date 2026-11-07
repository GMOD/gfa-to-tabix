import sys
p = sys.argv[1] + '/src/walks.rs'
s = open(p).read()
old_start = s.index("// Calls `place` with the reference pass each reference step")
old_end = s.index("// Chains the records of each contig in start order")
s = s[:old_start] + """// Places a step only on a node the reference passes once, at that pass;
// a step on a node it passes more than once is route interior
fn visits_along(along: &Along, mut place: impl FnMut(usize, Visit)) {
    let reference = along.reference;
    for i in (0..along.handles.len()).filter(|&i| along.on(i) && !reference.revisited.get(along.id(i))) {
        place(i, reference.first_visit(along.id(i)));
    }
}

""" + s[old_end:]
open(p, 'w').write(s)
