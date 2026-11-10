# CheezML domains

Which domains CubbyLLM covers, and how CheezML grows with them. Draft of 2026-11-10, for Nick's review.

**In plain words:** each new field Cubby works in (finance, cars, biology…) gets a small add-on to the receipt
format, so a receipt in that field also says which official records and versions it relied on.
- **Over a conventional model:** a model's answer about a drug or a company never says which database release it
  came from. A CheezML receipt does, in every field, in the same checkable way.

## The rule: core first, a domain module only for what is unique to it

Most of what a domain needs is the same everywhere, so it goes in `core` once. A domain module adds only the
constraints that exist nowhere else.

**Asked for by domain, but belongs in core:**

| Need | Example from a domain | Core term (in v0.2) |
|---|---|---|
| A remote source read during a run: the endpoint, the query, the answer | a federated SPARQL call to UniProt; a live Wikidata lookup (order 0007) | `cheez:SourceRead`: endpoint, query hash, response hash, time, licence |
| The exact release of an ontology or dataset used | GO's release; FIBO's quarterly release; the WikiKGQA 2026 dump | `prov:used` a `cheez:Artifact` with its version and hash, coded `cheez:OntologyRelease` or `cheez:DatasetRelease` |
| The time the question was asked about, and the store state read | "who was CEO in 2019"; a shipment's status last Tuesday | `cheez:asOf` (the valid time evaluated) and `cheez:storeSnapshot` (the snapshot's hash) on the run |

The two clocks are already core: valid time (`time:Interval`) and recorded time (PROV's generation and
invalidation), with "dates too coarse" as a refusal reason. A temporal module is therefore not needed. Questions
about two periods (Allen's relations, order 0057) also stay in core.

**Module conventions:**
- **IRI:** `https://w3id.org/cheezml/<domain>#`, versioned like core (`owl:versionIRI` …`/<domain>/v0.1`). It
  imports core.
- **Prefix:** `cz` + the domain (`czfin:`, `czbio:`…), because short names like `bio:` already belong to other
  vocabularies.
- **No domain facts are minted.** Facts use the domain's own ontology (FIBO, AUTO, GO…). The module adds only
  record terms: which source and version, the domain's own checks, its refusal reasons, and its thresholds with
  their calibration.
- **Licences per source,** recorded before anything is downloaded. A restricted source (SNOMED CT) is cited by id
  and version only, and its content is never redistributed.
- **Each module ships with** shapes, examples and broken examples, through the same checks as core, plus one line
  in the w3id rules.
- **A domain counts as covered** only when its order's acceptance passes: 0 wrong on its question set.

## The list

**Status:** covered = acceptance passed; ordered = an order exists; candidate = not ordered yet.

| Domain | Module | Status | Order | Sources and ontologies (licence) | What the module adds |
|---|---|---|---|---|---|
| General knowledge | none (core) | ordered | 0055, 0054 | Wikidata, the WikiKGQA 2026 dump (CC0) | nothing beyond core |
| Conversation | `cubby` (exists) | ordered | 0059, 0010 | human dialogue sets (licences per set) | already in `cubby`: turns, dialogue acts, refusals |
| Documents and invoices | `cubby` (exists) | ordered | 0061 | the user's own documents | already in `cubby`: regions, suggestions, reviews, commits. Splits into `czdoc` when contracts or forms arrive |
| Finance | `czfin` | ordered (first) | 0058 | FIBO (MIT), GLEIF LEI records (public domain), Central Bank of Ireland fund register (to check) | the LEI record's version and its status on that date; FIBO's release; exception codes (lapsed LEI, status conflict, a missing manager link) |
| Automotive | `czauto` | ordered (second) | 0058 | AUTO (MIT), NHTSA vPIC and recalls, EPA fuel economy (licences to check) | the VIN decoder's version; the recall campaign's id and revision; model year and market |
| Industry and buildings | `czind` | ordered (after finance and automotive) | 0058 addendum | IOF released modules (MIT), Brick 1.4.4, OpenIM (licences to check) | the asset and sensor ids, the module release, the units checked |
| Supply chain and logistics | `czlog` | ordered (demo) | 0058 addendum | Ontology-Playground's Retail Supply Chain (MIT), rule-generated test records | shipment and stock states, lead times, all on core's two clocks; the demo's records labelled as generated |
| Story worlds | `czstory` | ordered | 0060 | LIGHT, CRD3 (licences first) | the story world's id, canon commits, soft checks labelled soft, rewinds |
| News, world watch, forecasts | `czwatch` | ordered | 0024, 0025, 0026 | news feeds, GDELT, official warnings (terms to check) | the feed and its fetch time; events by day; each forecast's issue time, resolution and outcome; branch ids |
| Emotion | none (export) | ordered | 0019, 0020 | EmotionML 1.0 (W3C) | no vocabulary: EmotionML stays an export format |
| Science and MoWM's axioms | `czsci` | candidate | none (MoWM's 14 axiom domains) | MoWM's axiom library | each axiom's id and formula hash, units, and how it was discovered (symbolic regression, distillation) |
| Law | `czlaw` | candidate | none | statutes with in-force dates; repeal maps (licences to check) | each provision's in-force interval, the repeal or replacement it follows, the jurisdiction |
| Biomedical | `czbio` | candidate | none | GO and UniProt (CC BY 4.0); SNOMED CT (licensed per country; Canada is a member) | the sub-graph releases used, the ontology versions, the federated endpoints read (through core's `cheez:SourceRead`). Health answers need their own review before any user sees one |

## Next steps
1. **Done in v0.2 (2026-11-10):** the three core terms (`cheez:SourceRead`, the ontology or dataset version,
   `cheez:asOf` with the store snapshot), with shapes, one new example and three broken ones.
2. `czfin` with order 0058's finance world, then `czauto`. Each new module adds one line to the w3id rules
   (`ids/cheezml/.htaccess`).
3. The candidates (`czsci`, `czlaw`, `czbio`) become modules only when an order covers them.
