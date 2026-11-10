"""Check the built site: every module parses in all three formats to the same graph; every CheezML IRI used by the
context, the shapes or the examples is declared in exactly one module, in the module its namespace names; every
declared term has a definition and an HTML anchor; the frozen copy of the current version matches it; each earlier
frozen version still parses and still names itself.

Usage: python -I tools/check_site.py <repo-root>
"""
import json
import pathlib
import re
import sys

import rdflib
from rdflib.compare import isomorphic
from rdflib.namespace import OWL, RDF, SKOS

ROOT = pathlib.Path(sys.argv[1])
DOCS, SRC = ROOT / "docs", ROOT / "src"
BASE = "https://w3id.org/cheezml/"
NS = {"core": BASE + "core#", "cubby": BASE + "cubby#", "mowm": BASE + "mowm#", "cubelang": BASE + "cubelang#"}
DECL = {OWL.Class, OWL.ObjectProperty, OWL.DatatypeProperty, SKOS.Concept, SKOS.ConceptScheme}
problems = []

declared, versions = {}, {}
for stem, ns in NS.items():
    g = rdflib.Graph().parse(DOCS / f"{stem}.ttl", format="turtle")
    for fmt, ext in (("json-ld", "jsonld"), ("xml", "rdf")):
        other = rdflib.Graph().parse(DOCS / f"{stem}.{ext}", format=fmt)
        if not isomorphic(g, other):
            problems.append(f"{stem}.{ext} is not the same graph as {stem}.ttl")
    ont = rdflib.URIRef(BASE + stem)
    version = str(g.value(ont, OWL.versionIRI) or "").rsplit("/", 1)[-1]
    versions[stem] = version
    if not (DOCS / version / f"{stem}.ttl").exists():
        problems.append(f"no frozen copy of {stem} at {version}/")
    else:
        frozen = rdflib.Graph().parse(DOCS / version / f"{stem}.ttl", format="turtle")
        if not isomorphic(g, frozen):
            problems.append(f"{version}/{stem}.ttl differs from {stem}.ttl")
    for old in sorted(d for d in DOCS.iterdir() if d.is_dir() and re.fullmatch(r"v[0-9]+(\.[0-9]+)*", d.name)):
        if old.name == version:
            continue
        og = rdflib.Graph().parse(old / f"{stem}.ttl", format="turtle")
        if og.value(ont, OWL.versionIRI) != rdflib.URIRef(f"{BASE}{stem}/{old.name}"):
            problems.append(f"{old.name}/{stem}.ttl does not name itself {BASE}{stem}/{old.name}")
        prior = g.value(ont, OWL.priorVersion)
        if prior is None:
            problems.append(f"{stem} has an earlier frozen version but no owl:priorVersion")
    page = (DOCS / f"{stem}.html").read_text(encoding="utf-8")
    for s, _, t in g.triples((None, RDF.type, None)):
        if t not in DECL or not str(s).startswith(BASE):
            continue
        if not str(s).startswith(ns):
            problems.append(f"{s} is declared in {stem}, outside its namespace")
        if s in declared and declared[s] != stem:
            problems.append(f"{s} is declared in both {declared[s]} and {stem}")
        declared[s] = stem
        if not (g.value(s, SKOS.definition) or g.value(s, SKOS.prefLabel)):
            problems.append(f"{s} has no definition or label")
        if f'id="{str(s)[len(ns):]}"' not in page:
            problems.append(f"{s} has no anchor in {stem}.html")

used = set()
ctx = json.loads((SRC / "context.jsonld").read_text(encoding="utf-8"))["@context"]
prefix = {k: v for k, v in ctx.items() if isinstance(v, str) and v.startswith(BASE)}
for key in ctx:
    if ":" in key and key.split(":")[0] in prefix:
        used.add(rdflib.URIRef(prefix[key.split(":")[0]] + key.split(":", 1)[1]))
shapes = rdflib.Graph().parse(SRC / "shapes.ttl", format="turtle")
graphs = [shapes] + [rdflib.Graph().parse(p, format="json-ld") for p in sorted((SRC / "examples").glob("*.jsonld"))]
for g in graphs:
    for t in g:
        for x in t:
            if isinstance(x, rdflib.URIRef) and any(str(x).startswith(n) for n in NS.values()):
                used.add(x)
# the SPARQL rules in the shapes name terms inside strings (the broken examples are left out on purpose)
for q in re.findall(r"(?:cheez|cubby|mowm|cube):[A-Za-z][A-Za-z0-9_]*", (SRC / "shapes.ttl").read_text("utf-8")):
    p, local = q.split(":")
    used.add(rdflib.URIRef(NS["cubelang" if p == "cube" else {"cheez": "core"}.get(p, p)] + local))

missing = sorted(str(u) for u in used if u not in declared)
for m in missing:
    problems.append(f"used but not declared: {m}")

print(f"current version: {sorted(set(versions.values()))}; declared terms: {len(declared)}; CheezML IRIs used by context, shapes and examples: {len(used)}")
print("\n".join(problems) if problems else "SITE CHECK: ALL PASS")
sys.exit(1 if problems else 0)
