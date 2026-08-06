# Drafting style guide

Conventions for the flexible file v2 layout draft family:

- `flexfiles-v2` — `draft-haynes-nfsv4-flexfiles-v2` (this repository)
- `flexfiles-v2-proxy-server` — `draft-haynes-nfsv4-flexfiles-v2-proxy-server`
- `flexfiles-v2-delta-writes` — `draft-haynes-nfsv4-flexfiles-v2-delta-writes`

This file is the single source of truth; the companion repositories point
here rather than keeping their own copy.

Every rule below was derived from an editorial pass actually applied to
this draft, and cites the commit that established it. Where a sweep is
known to be incomplete, that is recorded rather than hidden — see
[Sweep hygiene](#sweep-hygiene).

A rule applies to **draft prose**: body text, definition lists, tables,
figure captions, and prose inside XDR comments. It does not apply to
wire identifiers, anchors, reference tokens, or quoted titles. Those
exceptions are stated per rule.

---

## 1. Voice

**Write what is, not how it came to be.** The reader has no access to the
review thread, the previous revision, or the rename history.

- No reviewer attribution in normative prose. Not "the review flagged",
  "as noted", "we changed". Attribute a requirement to its consequence.
  (`e248992f`)
- No design history. Rewrite "the prior draft's X language is withdrawn"
  as a direct statement of the current rule; a reader without the version
  history gains nothing from it. Rename history belongs in the commit
  message. (`26f55277`, `3938b306`)
- No future-work tails. Drop "…, which this revision does not".
  (`a22a02a0`)
- No editorial hedges on codepoints. Never mark a value "provisional",
  "TBD", or "pending a collision scan" — every codepoint in a draft is
  provisional, and IANA Considerations is where allocation policy lives.
  (`337b4df0`)
- Do not talk down to the reader. Delete parentheticals restating an
  obvious arithmetic or logical fact. (`d119d76c`)
- State a property once, at its definition site. Do not restate it in
  every operation that touches it, and do not pad an error clause with
  example error codes. (`28ef23c6`, `e09f46d7`, `e536bdda`)

> **Exception.** Reviewer attribution and design history are *intentional*
> inside `removeInRFC="true"` material — the naming reviewer note, Design
> Rationale: Rejected Alternatives, and Implementation Status. Those are
> stripped before publication.

> **Exception.** Boilerplate that is load-bearing at one site is not
> boilerplate there. The `co_id` opacity note was deleted from three
> operations but kept in the CHUNK_READ recovery prose, where it carries a
> normative consequence.

**Before → after** (`e248992f`):

```
the interop hazard the review flagged
->
Fixing W in this revision prevents an interoperability hazard: …
```

---

## 2. Spelling

**Use US English.** Never change spelling inside a quoted RFC or I-D
title, an I-D reference token, an XDR identifier, or a registered
constant.

Confirmed conversions (`b05182aa`, `3bc64ae5`):

| British | US |
|---|---|
| honour | honor |
| favour | favor |
| behaviour(s) | behavior(s) |
| defence(s) | defense(s) |
| serialis(e/ation/ing) | serializ… |
| organisation | organization |
| initialisation | initialization |
| normalis(e) | normaliz(e) |
| optimis(e/ing) | optimiz… |
| minimis(e) | minimiz(e) |
| standardis(e/ed/ation) | standardiz… |
| neighbour(s) | neighbor(s) |

`analysis` is **not** a British spelling — US and UK share it. Only
`analyse` differs.

**Match on the stem, not the word.** The first sweep matched `behaviour`
and missed `behaviours`, requiring a second commit; the stragglers still
in the tree are all inflected forms.

---

## 3. Terminology and abbreviations

### 3.1 Banned in prose

| Do not write | Write instead | Commit |
|---|---|---|
| `MDS` | metadata server | `efefb054`, `2143cece` |
| `MDS` (coding sense) | Maximum Distance Separable | `2143cece` |
| `DS` / `DSes` | data server / data servers | `efefb054` |
| `FFv2` / `FFv1` | flexible file v2 layout / v1 layout | `2143cece` |
| `inband`, `metadata-server-inband` | I/O through the metadata server | `efefb054` |
| `CHUNK_*`, `CHUNK_ESCROW_*` | CHUNK operations, CHUNK_ESCROW operations | `e71519f3` |
| `runway` | what the operation actually does | `beb310db` |
| `reflected GETATTR`, `InBand` | describe the mechanism | `c7a135a6` |
| "the X surface" (noun) | the flag / path / protocol / set / risk | `d0ab1060` |
| `repair client` | repair actor | `d6284391` |
| "no-tombstone model" | describe the behavior directly | `89542762` |

> **Exception — wire identifiers keep their names.** `NFS4ERR_STALE_MDS_EPOCH`,
> `EXCHGID4_FLAG_USE_PNFS_MDS`, `FFV2_FLAGS_NO_IO_THRU_MDS`,
> `CHUNK_GUARD_CLIENT_ID_MDS`, and the real operation names
> (`CHUNK_WRITE`, `CHUNK_ESCROW_INSTALL`, …).

> **Exception — tables and artwork.** `MDS`, `DS`, and `FFv2` short forms
> are permitted in table cells and in ASCII figures, where column width
> and box width dominate, and in `removeInRFC` appendix material. The ban
> is on *prose*: body text, definition-list bodies, and prose inside XDR
> comments. (`efefb054` left the ASCII-art diagrams untouched for exactly
> this reason.)

> **Exception — registry globs.** `FFV2_ENCODING_*` and `NFS4ERR_*` stay
> where the sentence genuinely means every value in a registry, e.g. "any
> `FFV2_ENCODING_*` value other than `FFV2_ENCODING_PASSTHROUGH`".

`surface` as a **verb** ("surfaces the error to the caller") is ordinary
English and is kept, as is the idiom "attack surface".

### 3.2 Naming register

Pick by role, not taste (`26cd8e05`):

| Context | Form |
|---|---|
| Headings, IANA registrations, abstract | Flexible File Version 2 Layout Type |
| Body prose | flexible file v2 layout |
| When the sentence is about the wire value | `LAYOUT4_FLEX_FILES_V2` |

Never "flexible file v2 layout version 2" — the `v2` already carries the
version.

### 3.3 Role nouns are lowercase

`metadata server`, `data server`, `proxy server` are lowercase in prose.
Title case only in section headings, figure/diagram labels, and table
headers. (`5ac947ca`)

### 3.4 Expand acronyms at first inline use

Spell out at the first occurrence in the body, not in a heading thousands
of lines later: "the Galois Field GF(2^8) family". (`9b769922`)
Abbreviate thereafter only if the abbreviation is not banned by §3.1.

### 3.5 Definitions section

Strictly alphabetical, with two carve-outs (`f1f0eef4`):

1. The layer triad `block` / `shard` / `chunk` stays at the top; the
   explanatory paragraphs after it depend on layer order.
2. Parenthetical prefixes sort under the head noun: `(file) data` sorts
   at *d*, `(file) metadata` at *m* — matching RFC 8881.

### 3.6 Precision of comparative claims

Do not write "and vice versa" for an asymmetric relation. Separate the
levels at which a claim holds — wire format versus semantics.
(`066cc48e`)

---

## 4. Identifier naming

| Kind | Rule | Commit |
|---|---|---|
| Struct types | `ffv2_<name>4`. When a field's type changes relative to RFC 8435, **fork** the struct under an `ffv2_` name rather than mutating the inherited one. | `377742e8` |
| Field prefixes | Carry the full `ffv2` stem plus struct initials: `ffv2dv_`, `ffv2da_`, `ffv2lu_`. A bare `f` plus initials is not used. On collision, take one letter per word of the struct name. | `f197effa`, `8ada8899` |
| Enums | The type name must agree with the prefix of its values: `ffv2_encoding_type4` because every value is `FFV2_ENCODING_*`. The rename does not stop at the enum: the union switching on it, that union's field prefix, and the member carrying it move too, or the mismatch just relocates one level up. | `9258b9e7`, `69f822225425` |
| Constants | `FFV2_` screaming caps, never the field-prefix form. Name after the client-visible mechanism, not a vague descriptor. | `377742e8` |
| Error codes | `NFS4ERR_<TERM>` matching current vocabulary. Rename identifier **and** section anchor together; the numeric value never changes. | `c8f9a638` |
| Attributes | `fattr4_<name>` / `FATTR4_<NAME>` — no `ffv2_` infix, even for attributes this document introduces. Follow the sibling attribute's shape. | `f51577fc` |
| Field names | Describe the type carried: `chrr_owners` because the array is `chunk_owner4<>`. When a `bool` widens to a bitmask, rename it `_flags`. | `eb2fe282` |

**"coding" → "encoding" is partial, not global.** Use "encoding type" for
this document's per-mirror encoding selection. Do **not** rewrite "erasure
coding" (established literature term), quoted paper titles, or
`fattr4_coding_block_size`. (`9258b9e7`, `c8f9a638`)

---

## 5. Lists and structure

### 5.1 No markdown emphasis, anywhere

Do not use `**bold**` or `*italic*` — not in prose, not as a list-item
lead, not as a pseudo-heading. The `.txt` render turns them into literal
punctuation noise. (`561c4de8`, then `c88aa26d`, `5737b199`, `cf8b19b1`)

If a bullet opens with a bold or italic term acting as its name, it is a
named list: convert it to a definition list.

```
-  **Provenance.**  The chunk_owner4 records which transaction …
```
becomes
```
Provenance:

: the chunk_owner4 ({{sec-chunk_owner4}}) records which
  transaction produced the chunk.  …
```

Note the body is lowercased — the term supplies the sentence opening.
The same applies to `- Name: body` bullets where the colon is naming
rather than emphasising.

### 5.2 Definition-list syntax

Two forms are in use. **Form A** (compact, ~306 sites) — term line, then
`:` plus two spaces, continuation indented 3:

```
cg_gen_id:
:  A per-chunk monotonic generation counter, tracked by the data
   server.  Each chunk's gen_id starts at 0 …
```

**Form B** (blank line, ~114 sites) — term line, blank line, `:` plus one
space, continuation indented 2:

```
Atomicity:

: the chunk_guard4 compare-and-swap guard ({{sec-chunk_guard4}})
  sequences concurrent writers and rejects torn-write attempts.
```

**A body containing anything other than one paragraph MUST use Form B**
(`d28fd1c2`, a commit that exists solely to fix a mis-render):

- end the intro sentence with a period, not a colon;
- leave a blank line before the first nested term;
- indent every nested block into the outer body — nested terms and their
  `:` markers align to the outer body indent, continuations at +2.

```
Predecessor-guided rollback discovery:

: A caller preparing a CHUNK_ROLLBACK against a COMMITTED
  chunk inspects the corresponding chrr_predecessors entry
  to decide whether CHUNK_ROLLBACK will succeed.

  PRESENT:

  : name the disclosed owner triple in the cra_chunks entry
    of the subsequent CHUNK_ROLLBACK.  …
```

### 5.3 Choosing the construct

| Use | When |
|---|---|
| **Definition list** | Named items, each mapping to one paragraph (± a nested block): field descriptions, per-error meanings, enum-arm dispositions, named properties. *If you are tempted to write a name in bold or before a colon at the head of a bullet, it is a definition list.* |
| **Real subsection** (`###` + `{#anchor}`) | The named branch's body is multiple paragraphs, or contains a list that must nest under the name, or is likely to be cross-referenced. Also whenever one section describes two distinct things — split it. (`e251143e`, `a273ea99`, `6636aca7`, `18e9f21c`) |
| **Table** | The same small set of fields repeats across every member of a closed set (value → description → section xref) and coverage must be provably complete. Partial prose stubs are the anti-pattern. (`e495ed17`) |
| **Category reference, no list** | The members belong to a registry that will grow. Write the category plus an xref to the canonical table. (`d65df906`, `c1432f7b`) |
| **Plain bullets** | Unnamed parallel clauses and if-then rule bullets. |
| **Ordered list** | True sequences, steps, and numbered normative properties. Never converted by the sweeps. |
| **`~~~` fence** | Real code, XDR, and diagrams only. A rule with two math expressions is prose with backticks, not pseudocode. (`e1884b25`) |

Keep the enumeration where the list *is* the information: Implementation
Status manifests, IANA/XDR per-algorithm entries, and groupings that are a
property rather than a registry category ("systematic encodings").

Replace `(a)`/`(b)`/`(c)` letter labels with named sub-cases — sibling
entries each having an "(a)" makes cross-references ambiguous. Fix the
referring prose too. (`37540dfc`)

### 5.4 Unnumbered sections

Every `###` under an unnumbered parent needs its own IAL on the following
line, or xml2rfc errors out and produces no output (`4ac2c64d`):

```
### Algorithm cost
{:numbered="false"}
```

Table and figure captions use the IAL form on the line right after the
block:

```
{: #tbl-encoding-type-sections title="Encoding type value to section mapping"}
```

---

## 6. Cross-references

**Drop a parenthetical `{{sec-…}}` that points back at the section
defining the operation you just named.** Keep it only when a cue word
makes the xref the object of the sentence: `see`, `defined in`,
`described in`, `specified in`, `per`, `at`. (`071cdd0b`, 144 sites
dropped)

```
Like CHUNK_READ ({{sec-CHUNK_READ}}) and CHUNK_WRITE
({{sec-CHUNK_WRITE}}), CHUNK_COMMIT carries …
->
Like CHUNK_READ and CHUNK_WRITE, CHUNK_COMMIT carries …
```

Kept: `(see {{sec-CHUNK_LOCK}})`, `per {{sec-TRUST_STATEID}}`,
`at {{sec-repair-selection}}`. An xref whose target differs from the
operation just named is never a tautology and is always kept.

**Add** an xref when a passage states a rule at one layer while the
invariant it implements lives elsewhere, or when a procedure leaves an
outcome unnamed — quoting the invariant inline so the reader need not
chase it. (`ed088fa8`, `fcd0f07a`)

**Cite an external I-D once**, at its definitions entry, and declare the
policy there; thereafter cite only when pointing at a specific rule or
section inside it. Consolidation is bidirectional — strip decorative
citations, supply load-bearing ones. (`d9aeb3e2`)

**Headings name the concept readers arrive for, not the constant that
happens to be introduced. Rename the title; never the anchor** — inbound
xrefs must keep resolving. (`89312f57`, `d6284391`)

---

## 7. Hyphenation and source formatting

**Do not hyphenate compound modifiers built from the draft's own domain
terms**, even before a noun: `tight coupling`, `trusted stateid`, `byte
range`, `single writer`, `layout type`, `encoding type`, `proxy server`.
Ordinary-English compounds keep their hyphens: `per-chunk`, `on-disk`,
`in-flight`, `end-to-end`, `read-only`, `well-known`. (`5f248ea0`)

> **Exception.** Anchors and xrefs are identifiers, not prose.
> `sec-tight-coupling-control` keeps its hyphens — rewriting a slug
> corrupts every xref to it.

**Never break a source line immediately after a hyphen inside a compound
word.** In the `.txt` render, a line ending `non-` followed by a line
starting `PASSTHROUGH` emits `non- PASSTHROUGH` — a space injected inside
the compound. Keep the compound on one source line even if it runs long.
(`c2d512ac`, 34 sites)

Body prose is otherwise wrapped at roughly 70 columns. Front matter,
tables, URLs, and artwork are exempt.

---

## 8. Math and notation

- **Space letter arithmetic**: `k + m`, `k + 1`, `i + 1`. Bare-number
  geometry labels are scheme names, not sums, and stay unspaced: `4+2`,
  `8+2`. The operative test is *a letter on either side gets spaces*.
  Never touch content inside `~~~` fences or backticks. (`d4dcf4c7`)
- **Prose is not C**: write `stable_how = FILE_SYNC`, not `==`.
  (`d4dcf4c7`) This holds **inside backticks too** — a backticked
  condition in running text is still prose, not code. Only a `~~~`
  fence or a `///` XDR line keeps `==`. The base draft has zero `==`
  outside its XDR; treat any other hit as a finding rather than
  assuming the backticks make it code.
- **Never backslash-escape brackets.** `\[` / `\]` leak into the `.txt`
  render. Put display equations in `~~~` fences and inline math in
  backticks — brackets are literal inside both. (`2e056276`)

---

## 9. XDR blocks and figures

- In a multi-line XDR comment, a continuation line must not end with
  `*/`; put the close on its own `///  */` line. Single-line
  `/* text */` is fine. (`25991d8b`)
- **No trailing inline comments on XDR declaration lines**, and **figure
  captions are exactly `XDR for <type-name>`** with no parenthetical
  gloss. An attempt to annotate `escrow_id4` as `/* 128 bits */` and
  gloss its caption was reverted three minutes later; the concern was
  addressed in prose instead. If a reader would ask "why 16?", answer it
  in a definition or a cross-reference — not in the XDR block or its
  caption. (`96cd5272` reverted by `c69b81c2`, then `0bf1b727`)

---

## 10. Sweep hygiene

The history records more incomplete sweeps than wrong rules. When
applying a rule mechanically:

1. **Order matters.** Join hyphen-split lines *before* running the
   unhyphenation sweep — six sites escaped `5f248ea0` purely because they
   were split across the hyphen at the time. Likewise run spelling sweeps
   *after* prose rewrites, not before: `26f55277` introduced `MUST honour`
   that `b05182aa` then had to fix.
2. **Match on stems**, not exact words (see §2).
3. **Re-read after a regex substitution.** Collapsing a phrase across
   wrapped lines leaves duplicated words that the regex cannot see.
4. **Verify with a counter-grep**, and record the exceptions you are
   deliberately keeping.

### Known residue

The textual residue in the base draft was cleared in `62406cdc` —
British stragglers, two duplicated words from the `owner triple` sweep,
one line broken mid-compound, and three body-prose `FFv2` uses.

Outstanding:

| Item | Where |
|---|---|
| The companion drafts have not been swept at all | see their `STYLE.md` |

---

## 11. Pre-commit checks

```sh
D=draft-haynes-nfsv4-flexfiles-v2.md      # or the companion draft

grep -nE '\b(behaviour|honour|favour|defence|serialis|organis|initialis|normalis|optimis|minimis|standardis|neighbour|analyse|licence|centre)[a-z]*' $D
grep -nE '\b(MDS|DS|DSes|FFv1|FFv2)\b' $D          # expect only identifiers, tables, artwork
grep -niE 'inband|CHUNK_\*|repair client'          $D
grep -nE '\*\*[^*]+\*\*|(^|[^*])\*[^* ][^*]*\*'    $D   # emphasis
grep -nE '\\\[|\\\]'                               $D   # escaped brackets
grep -nE '[a-z_] == '                              $D   # C-style equality
grep -nE '[a-z]-$'                                 $D   # line ends mid-compound (ignore hits inside ~~~ artwork)
grep -nE '^\s*[-*] \*\*'                           $D   # bullet-with-bold
```

### Unexpanded abbreviations

The greps above catch the *known* banned short forms. New ones keep
arriving from adjacent contexts — `CSM` leaked out of a section anchor,
`SB` and `WG` out of implementation and meeting-room vocabulary — so
sweep for all-caps tokens in prose rather than waiting to read one:

```sh
python3 - "$D" <<'EOF'
import re, sys
from collections import Counter
lines = open(sys.argv[1]).read().split('\n')
fence = False; count = Counter(); first = {}
for n, l in enumerate(lines, 1):
    if l.startswith('~~~'):
        fence = not fence; continue
    if fence or l.lstrip().startswith(('|', '///')):
        continue                      # artwork, tables, XDR
    s = re.sub(r'`[^`]*`', '', l)     # drop code spans
    s = re.sub(r'\{\{[^}]*\}\}', '', s)  # drop xrefs and citations
    for m in re.finditer(r'(?<![A-Za-z_/0-9])[A-Z]{2,6}(?:es|s)?(?![A-Za-z_0-9])', s):
        count[m.group(0)] += 1
        first.setdefault(m.group(0), n)
for t, k in count.most_common():
    print(f"{t:10} {k:4}  first@{first[t]}")
EOF
```

Triage the output; most hits are expected:

- BCP 14 keywords: `MUST`, `MAY`, `SHOULD`, `NOT`.
- Operation, enum, and flag names: `OPEN`, `MOVE`, `CHUNK`, `PUTFH`,
  `COMMIT`, `DONE`, …
- Terms RFCs do not expand: `NFS`, `RPC`, `XDR`, `RFC`, `IANA`, `IETF`,
  `TCP`, `DNS`, `POSIX`, `ACL`, `SSD`, `HDD`, `SHA`.

Anything else is a real abbreviation and needs §3.4 treatment: expand at
first **inline** use — a heading does not count — and cite the defining
section or RFC where one exists. An abbreviation used only inside ASCII
figures is fine if it is defined in Definitions; `PS` is the worked
example of that split.

Then build — the rendering check is part of the convention, not
incidental. Every commit in this series records a green run:

```sh
make            # kramdown-rfc -> xml2rfc txt + html
make -s lint
```
