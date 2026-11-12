#!/usr/bin/env python3
"""Breaks the reading of P line names one way, in place, for mutants.sh.

Usage: mutate.py MUTANT src/gfa.rs
       mutate.py --list
"""
import sys

MUTANTS = {
    # a bracket's stated end is never checked
    "no-end-check": (
        ".filter(|piece| colon.is_none() && !spans(piece))",
        ".filter(|piece| piece.at > usize::MAX - 1 && colon.is_none() && !spans(piece))",
    ),
    # a `:a-b` beneath a fourth field is read
    "colon-beneath-fourth": (
        "        (_, Some(start)) => Ok((path, start)),",
        "        (_, Some(start)) => match suffix(path, b':')\n"
        "            .filter(|cut| colon.is_none() && fourth.is_some() && bp > 0 && spans(cut))\n"
        "        {\n"
        "            Some(cut) => Ok((&path[..cut.at], start + cut.start)),\n"
        "            None => Ok((path, start)),\n"
        "        },",
    ),
    # a fourth field leaves the name and adds nothing
    "fourth-dropped": ("[&colon, &bracket, &fourth]", "[&colon, &bracket, &None]"),
    # a fourth field beside a bracket adds nothing
    "fourth-not-summed": (
        "[&colon, &bracket, &fourth]",
        "[&colon, &bracket, if bracket.is_some() { &None } else { &fourth }]",
    ),
    # a path of fewer than three fields is listed whole, as before ADR 0014
    "haplotype-2a": (
        "        _ => sample(path),\n    }\n}\n\nimpl Graph {",
        "        _ => path,\n    }\n}\n\nimpl Graph {",
    ),
}
if sys.argv[1] == "--list":
    print(" ".join(MUTANTS))
else:
    old, new = MUTANTS[sys.argv[1]]
    text = open(sys.argv[2]).read()
    if text.count(old) != 1:
        sys.exit(f"mutate.py: {sys.argv[1]}: src/gfa.rs no longer holds the text this mutant changes")
    open(sys.argv[2], "w").write(text.replace(old, new))
