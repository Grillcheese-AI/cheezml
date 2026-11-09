"""Build the CheezML site (docs/) from src/: one OWL ontology per module in Turtle, JSON-LD and RDF/XML, an HTML
page per module with an anchor per term, the context, the shapes, a frozen copy under docs/<version>/, and an index.

Usage: python -I tools/build_site.py <repo-root>
"""
import html
import json
import pathlib
import re
import shutil
import sys

import rdflib
from rdflib import BNode, Literal, Namespace, URIRef
from rdflib.collection import Collection
from rdflib.namespace import DCTERMS, OWL, RDF, RDFS, SKOS, XSD

ROOT = pathlib.Path(sys.argv[1])
SRC, OUT = ROOT / "src", ROOT / "docs"
VERSION, CREATED, MODIFIED = "v0.1", "2026-11-07", "2026-11-09"
BASE = "https://w3id.org/cheezml/"
LICENSE = URIRef("https://creativecommons.org/licenses/by/4.0/")
SCHEMA = Namespace("https://schema.org/")
VANN = Namespace("http://purl.org/vocab/vann/")
PREFIXES = {
    "cheez": BASE + "core#", "cubby": BASE + "cubby#", "mowm": BASE + "mowm#", "cube": BASE + "cubelang#",
    "prov": "http://www.w3.org/ns/prov#", "schema": "https://schema.org/", "time": "http://www.w3.org/2006/time#",
    "skos": str(SKOS), "dcterms": str(DCTERMS), "xsd": str(XSD), "rdfs": str(RDFS), "owl": str(OWL),
    "dec": "http://example.com/ns/dec#",
}
MODULES = {  # file stem -> (prefix, title, one-line description)
    "core": ("cheez", "CheezML core",
             "Records, hashes, the two clocks, thresholds with their calibration, check runs, certificates, decisions "
             "and retirement."),
    "cubby": ("cubby", "CheezML for CubbyLLM",
              "Conversation turns, answers and refusals with their reasons, proposers, helpers in a sandbox, and "
              "documents reviewed by a person."),
    "mowm": ("mowm", "CheezML for MoWM",
             "Worlds, routing decisions (route or spawn) and world splits at depth z + 1."),
    "cubelang": ("cube", "CheezML for CubeLang",
                 "Programs by hash and VM runs with their outcome (return, error or ask)."),
}
NS_TO_MODULE = {PREFIXES[p]: stem for stem, (p, _, _) in MODULES.items()}


def iri(curie):
    p, local = curie.split(":", 1)
    return URIRef(PREFIXES[p] + local)


def curies(cell):
    return re.findall(r"`([a-z]+:[A-Za-z0-9_]+)`", cell)


def module_of(u):
    s = str(u)
    for ns, stem in NS_TO_MODULE.items():
        if s.startswith(ns):
            return stem
    return None


def parse_tables(text):
    """Rows of the per-module term tables in vocabulary.md."""
    rows, mod = [], None
    for line in text.splitlines():
        m = re.match(r"## (core|cubby|mowm|cubelang) \(", line)
        if m:
            mod = m.group(1)
            continue
        if line.startswith("## "):
            mod = None
        if mod and line.startswith("| `"):
            c = [x.strip() for x in line.strip().strip("|").split("|")]
            rows.append(dict(module=mod, term=curies(c[0])[0], kind=c[1], definition=c[2], domain=c[3],
                             range=c[4], align=c[5]))
    return rows


def plain(cell):
    return re.sub(r"`([^`]*)`", r"\1", cell).strip()


def add_class_expr(g, subj, pred, cell):
    terms = [iri(t) for t in curies(cell)]
    if not terms:
        return
    if len(terms) == 1:
        g.add((subj, pred, terms[0]))
        return
    union, lst = BNode(), BNode()
    g.add((union, RDF.type, OWL.Class))
    Collection(g, lst, terms)
    g.add((union, OWL.unionOf, lst))
    g.add((subj, pred, union))


def build_graphs(rows, skos_ttl):
    graphs = {}
    for stem, (prefix, title, desc) in MODULES.items():
        g = rdflib.Graph()
        for p, ns in PREFIXES.items():
            g.bind(p, ns)
        g.bind("vann", VANN)
        ont = URIRef(BASE + stem)
        g.add((ont, RDF.type, OWL.Ontology))
        g.add((ont, OWL.versionIRI, URIRef(f"{BASE}{stem}/{VERSION}")))
        g.add((ont, OWL.versionInfo, Literal(f"{VERSION[1:]} (draft)")))
        g.add((ont, DCTERMS.title, Literal(title, lang="en")))
        g.add((ont, DCTERMS.description, Literal(desc, lang="en")))
        g.add((ont, DCTERMS.created, Literal(CREATED, datatype=XSD.date)))
        g.add((ont, DCTERMS.modified, Literal(MODIFIED, datatype=XSD.date)))
        g.add((ont, DCTERMS.license, LICENSE))
        creator = BNode()
        g.add((ont, DCTERMS.creator, creator))
        g.add((creator, RDF.type, SCHEMA.Person))
        g.add((creator, SCHEMA.name, Literal("Nicolas Cloutier")))
        g.add((creator, SCHEMA.affiliation, Literal("GrillCheese Research Lab")))
        g.add((ont, VANN.preferredNamespacePrefix, Literal(prefix)))
        g.add((ont, VANN.preferredNamespaceUri, Literal(PREFIXES[prefix])))
        if stem != "core":
            g.add((ont, OWL.imports, URIRef(BASE + "core")))
        graphs[stem] = g
    for r in rows:
        g, s = graphs[r["module"]], iri(r["term"])
        is_class = r["kind"] == "class"
        if is_class:
            g.add((s, RDF.type, OWL.Class))
        else:
            rng = curies(r["range"])
            datatype = bool(rng) and all(x.startswith("xsd:") for x in rng)
            g.add((s, RDF.type, OWL.DatatypeProperty if datatype else OWL.ObjectProperty))
            add_class_expr(g, s, RDFS.domain, r["domain"])
            add_class_expr(g, s, RDFS.range, r["range"].split("(")[0])
            scheme = re.search(r"\(`([a-z]+:[A-Za-z]+)`\)", r["range"])
            if scheme:
                g.add((s, SKOS.scopeNote, Literal(f"Values come from the code list {scheme.group(1)}.", lang="en")))
        g.add((s, RDFS.isDefinedBy, URIRef(BASE + r["module"])))
        g.add((s, RDFS.label, Literal(r["term"].split(":")[1], lang="en")))
        g.add((s, SKOS.definition, Literal(plain(r["definition"]), lang="en")))
        for seg in [x.strip() for x in r["align"].split(";") if x.strip()]:
            if seg.startswith("⊑"):
                for t in curies(seg):
                    g.add((s, RDFS.subClassOf if is_class else RDFS.subPropertyOf, iri(t)))
            elif seg.startswith("specialises"):
                for t in curies(seg):
                    g.add((s, RDFS.subPropertyOf, iri(t)))
            elif seg.startswith("`skos:closeMatch`"):
                for t in curies(seg)[1:]:
                    g.add((s, SKOS.closeMatch, iri(t)))
                note = re.sub(r"^`skos:closeMatch` `[^`]+`\s*", "", seg).strip(" ()")
                if note:
                    g.add((s, SKOS.editorialNote, Literal(note, lang="en")))
            else:
                g.add((s, SKOS.editorialNote, Literal(plain(seg), lang="en")))
    codes = rdflib.Graph().parse(data=skos_ttl, format="turtle")
    for s, p, o in codes:
        stem = module_of(s)
        if stem is None:
            raise SystemExit(f"code-list triple with a subject outside CheezML: {s}")
        graphs[stem].add((s, p, o))
        if p == RDF.type and o in (SKOS.Concept, SKOS.ConceptScheme):
            graphs[stem].add((s, RDFS.isDefinedBy, URIRef(BASE + stem)))
    return graphs


CSS = """
:root{--bg:#fbfaf6;--fg:#23201a;--muted:#6b6457;--rule:#e4ded1;--accent:#a8650b;--code:#f3efe4}
@media (prefers-color-scheme:dark){:root{--bg:#191712;--fg:#ece6d8;--muted:#a59d8c;--rule:#3a352b;--accent:#e9a23b;
--code:#262219}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.55 system-ui,-apple-system,
"Segoe UI",Roboto,sans-serif}main{max-width:52rem;margin:0 auto;padding:2rem 1rem 4rem}h1,h2,h3{line-height:1.25;
text-wrap:balance}h1{font-size:1.9rem;margin:.2rem 0 .4rem}h2{font-size:1.3rem;margin-top:2.4rem;padding-bottom:.3rem;
border-bottom:1px solid var(--rule)}h3{font-size:1.05rem;margin:1.6rem 0 .3rem;scroll-margin-top:1rem}
a{color:var(--accent)}code{font:.88em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--code);
padding:.05em .3em;border-radius:3px;overflow-wrap:anywhere}.muted{color:var(--muted)}.badge{display:inline-block;
font-size:.75rem;letter-spacing:.04em;text-transform:uppercase;border:1px solid var(--rule);border-radius:3px;
padding:.05rem .4rem;color:var(--muted)}dl{display:grid;grid-template-columns:max-content 1fr;gap:.2rem 1rem;
margin:.4rem 0}dt{color:var(--muted)}dd{margin:0}.term{border-left:2px solid var(--rule);padding-left:.9rem}
table{border-collapse:collapse;width:100%}td,th{text-align:left;padding:.35rem .5rem;border-bottom:1px solid
var(--rule);vertical-align:top}.wrap{overflow-x:auto}nav a{margin-right:.8rem}
"""


def page(title, body):
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1">'
            f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
            f'<body><main><nav class="muted"><a href="./">CheezML</a>'
            + "".join(f'<a href="{m}.html">{m}</a>' for m in MODULES)
            + f"</nav>{body}</main></body></html>\n")


def short(g, u):
    if isinstance(u, BNode):
        members = list(Collection(g, g.value(u, OWL.unionOf))) if g.value(u, OWL.unionOf) else []
        return " or ".join(short(g, m) for m in members) or "(anonymous)"
    s = str(u)
    for p, ns in PREFIXES.items():
        if s.startswith(ns):
            local = s[len(ns):]
            stem = NS_TO_MODULE.get(ns)
            label = f"<code>{p}:{html.escape(local)}</code>"
            return f'<a href="{stem}.html#{local}">{label}</a>' if stem else label
    return f"<code>{html.escape(s)}</code>"


def module_html(stem, g):
    prefix, title, desc = MODULES[stem]
    ns = PREFIXES[prefix]
    links = " · ".join(f'<a href="{stem}.{e}">{e}</a>' for e in ("ttl", "jsonld", "rdf"))
    body = [f'<p class="badge">draft {VERSION}</p><h1>{html.escape(title)}</h1><p>{html.escape(desc)}</p>',
            f"<dl><dt>Ontology IRI</dt><dd><code>{BASE}{stem}</code></dd><dt>Namespace</dt><dd><code>{ns}</code> "
            f"(prefix <code>{prefix}:</code>)</dd><dt>This version</dt><dd><code>{BASE}{stem}/{VERSION}</code></dd>"
            f"<dt>Formats</dt><dd>{links}</dd><dt>Licence</dt><dd><a href=\"{LICENSE}\">CC BY 4.0</a></dd></dl>"]

    def terms_of(*types):
        out = set()
        for t in types:
            out |= {s for s in g.subjects(RDF.type, t) if str(s).startswith(ns)}
        return sorted(out, key=lambda u: str(u).lower())

    def term_block(s, kind):
        local = str(s)[len(ns):]
        rows = []
        for label, pred in (("Domain", RDFS.domain), ("Range", RDFS.range), ("Subclass of", RDFS.subClassOf),
                            ("Subproperty of", RDFS.subPropertyOf), ("In scheme", SKOS.inScheme),
                            ("Close match", SKOS.closeMatch)):
            vals = [short(g, o) for o in g.objects(s, pred)]
            if vals:
                rows.append(f"<dt>{label}</dt><dd>{', '.join(vals)}</dd>")
        for label, pred in (("Note", SKOS.scopeNote), ("Editorial note", SKOS.editorialNote)):
            for o in g.objects(s, pred):
                rows.append(f"<dt>{label}</dt><dd>{html.escape(str(o))}</dd>")
        text = g.value(s, SKOS.definition) or g.value(s, SKOS.prefLabel) or ""
        return (f'<section class="term"><h3 id="{local}">{prefix}:{local} <span class="badge">{kind}</span></h3>'
                f"<p>{html.escape(str(text))}</p><dl><dt>IRI</dt><dd><code>{s}</code></dd>{''.join(rows)}</dl>"
                f"</section>")

    for heading, types, kind in (("Classes", (OWL.Class,), "class"),
                                 ("Properties", (OWL.ObjectProperty, OWL.DatatypeProperty), "property"),
                                 ("Code lists", (SKOS.ConceptScheme,), "code list"),
                                 ("Codes", (SKOS.Concept,), "code")):
        ts = terms_of(*types)
        if ts:
            body.append(f"<h2>{heading}</h2>" + "".join(term_block(s, kind) for s in ts))
    return page(f"{title} {VERSION}", "".join(body))


def index_html(frozen=False):
    rows = "".join(f'<tr><td><a href="{m}.html">{m}</a></td><td><code>{PREFIXES[p]}</code></td>'
                   f"<td>{html.escape(d)}</td></tr>" for m, (p, _, d) in MODULES.items())
    body = f"""<p class="badge">draft {VERSION}</p><h1>CheezML</h1>
<p>One record vocabulary for <a href="https://github.com/Grillcheese-AI/CubbyLLM">CubbyLLM</a>, MoWM and CubeLang:
an answer and its certificate, a refusal and its reason, a routing choice, a world split, a rejected helper, a
document field reviewed by a person. Each record is written by the host from what actually ran, so it can only say
what happened.</p>
<p><strong>In plain words:</strong> every answer comes with a receipt you can check, in the same format as every
routing choice and reviewed document behind it. Nothing in a record is a claim the system makes about itself: no
truth score, no status declared by hand, no prose rationale.</p>
<h2>Modules</h2><div class="wrap"><table><tr><th>Module</th><th>Namespace</th><th>Covers</th></tr>{rows}</table></div>
<h2>Files</h2><ul><li><a href="context.jsonld">context.jsonld</a>: the JSON-LD 1.1 context
(<code>{BASE}context.jsonld</code>)</li><li><a href="shapes.ttl">shapes.ttl</a>: SHACL shapes for the six record
types (<code>{BASE}shapes</code>)</li><li><a href="examples/">examples/</a>: six records that conform, and ten broken
ones that must fail</li><li>{'' if frozen else f'<a href="{VERSION}/">{VERSION}/</a>: this version, frozen'}</li></ul>
<h2>Status</h2><p>Draft {VERSION}, {MODIFIED}. Terms may still change before the first release; changed terms are
retired with a note, never deleted. Source and tests:
<a href="https://github.com/Grillcheese-AI/cheezml">github.com/Grillcheese-AI/cheezml</a>.</p>
<p class="muted">Nicolas Cloutier, GrillCheese Research Lab. <a href="{LICENSE}">CC BY 4.0</a>.</p>"""
    return page("CheezML", body)


def write_set(dest, graphs, frozen=False):
    dest.mkdir(parents=True, exist_ok=True)
    for stem, g in graphs.items():
        (dest / f"{stem}.ttl").write_text(g.serialize(format="turtle"), encoding="utf-8")
        (dest / f"{stem}.jsonld").write_text(g.serialize(format="json-ld", indent=2), encoding="utf-8")
        (dest / f"{stem}.rdf").write_text(g.serialize(format="xml"), encoding="utf-8")
        (dest / f"{stem}.html").write_text(module_html(stem, g), encoding="utf-8")
    shutil.copy(SRC / "context.jsonld", dest / "context.jsonld")
    shutil.copy(SRC / "shapes.ttl", dest / "shapes.ttl")
    (dest / "index.html").write_text(index_html(frozen), encoding="utf-8")
    ex = dest / "examples"
    if ex.exists():
        shutil.rmtree(ex)
    shutil.copytree(SRC / "examples", ex)
    listing = "".join(f'<li><a href="{p.relative_to(ex).as_posix()}">{p.relative_to(ex).as_posix()}</a></li>'
                      for p in sorted(ex.rglob("*.jsonld")))
    (ex / "index.html").write_text(page("CheezML examples", "<h1>Examples</h1><p>Files under negative/ are built to "
                                        f"fail validation.</p><ul>{listing}</ul>"), encoding="utf-8")


def main():
    text = (SRC / "vocabulary.md").read_text(encoding="utf-8")
    skos_ttl = re.search(r"```turtle\n(.*?)```", text, re.S).group(1)
    graphs = build_graphs(parse_tables(text), skos_ttl)
    if OUT.exists():
        shutil.rmtree(OUT)
    write_set(OUT, graphs)
    write_set(OUT / VERSION, graphs, frozen=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    for stem, g in graphs.items():
        print(f"{stem}: {len(g)} triples")


if __name__ == "__main__":
    main()
