# CheezML

One record vocabulary for CubbyLLM, MoWM and CubeLang. The name is a pun on XML.

A record is written by the host from what actually ran: an answer and its certificate, a refusal and its reason, a
MoWM routing choice, a world split, a rejected helper, a document field reviewed by a person. One checker reads any
of them.

**In plain words:** every answer comes with a receipt you can check, in the same format as every routing choice and
reviewed document behind it. Nothing in a record is a claim the system makes about itself.
- **Over a conventional model:** logs, if kept at all, come in a different shape per component and record what the
  model says it did. A CheezML record that disagrees with its own numbers fails validation.

**Status:** draft v0.1 (2026-11-09). Terms may change before the first release. A changed term is retired with a
note, never deleted.

## Identifiers

| Module | Prefix | Namespace | Ontology IRI |
|---|---|---|---|
| core | `cheez:` | `https://w3id.org/cheezml/core#` | `https://w3id.org/cheezml/core` |
| cubby | `cubby:` | `https://w3id.org/cheezml/cubby#` | `https://w3id.org/cheezml/cubby` |
| mowm | `mowm:` | `https://w3id.org/cheezml/mowm#` | `https://w3id.org/cheezml/mowm` |
| cubelang | `cube:` | `https://w3id.org/cheezml/cubelang#` | `https://w3id.org/cheezml/cubelang` |
| shapes | `shapes:` | `https://w3id.org/cheezml/shapes#` | `https://w3id.org/cheezml/shapes` |

- Versions are never in a namespace. Each ontology has an `owl:versionIRI` such as
  `https://w3id.org/cheezml/core/v0.1`.
- The JSON-LD context is `https://w3id.org/cheezml/context.jsonld`.
- Records and instances have `urn:uuid:` ids, never ids in a vocabulary namespace.
- Standard vocabularies are reused as published: PROV-O, schema.org, OWL-Time, SKOS and DCMI terms.

The site is served from `docs/` by GitHub Pages; w3id.org redirects to it, with content negotiation (HTML for a
browser, Turtle, JSON-LD or RDF/XML for a machine).

## The rules a record follows
- A record says only what ran. A check that never ran has no record.
- A certificate is a receipt, not a grade: no truth score, no status declared by hand, no prose rationale.
- Every threshold carries its calibration: the screen, the data, the encoder, the deployment and the date.
- Hashes, never blobs: no vectors, weights, programs or bytecode inside a record.
- Two clocks: valid time (when it held) and recorded time (when it was learned). A correction closes the old version.
- Retire, never delete.

## Layout
- `src/`: the source. `vocabulary.md` (the term tables and the SKOS code lists), `context.jsonld`, `shapes.ttl`,
  `examples/` (six records that conform, and in `negative/` ten that must fail) and `example-sources/`.
- `docs/`: the built site, one page and three RDF files per module, plus a frozen copy per version.
- `tools/`: the build and the checks.

## Build and check

Python 3 with `rdflib` (7.6 or later) and `pyshacl` (0.40 or later); `pyld` is optional, as a second JSON-LD reader.

```sh
python -I tools/build_examples.py src src/example-sources
python -I tools/validate.py src            # 6 examples conform, 10 broken ones fail with their message
python -I tools/build_site.py .
python -I tools/check_site.py .            # formats agree, every term used is declared and documented
```

## Names
CubbyLLM's releases take cheese names in alphabetical order, starting with Asiago. In documents, the protocols have
cheese names of their own: Comté (certificates), Maasdam (refusals and gaps), Mozza (MoWM world records), Paneer
(sandboxed helpers) and Raclette (conversation). Names never appear in an IRI or an identifier.

## Licence
The vocabulary, shapes, examples and documentation are under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).
The scripts in `tools/` are under the MIT licence.

Nicolas Cloutier, GrillCheese Research Lab.
