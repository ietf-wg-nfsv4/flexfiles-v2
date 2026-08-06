# Drafting style guide

Conventions for the flexible file v2 layout draft family:

- `flexfiles-v2` — `draft-haynes-nfsv4-flexfiles-v2` (this repository)
- `flexfiles-v2-proxy-server` — `draft-haynes-nfsv4-flexfiles-v2-proxy-server`
- `flexfiles-v2-delta-writes` — `draft-haynes-nfsv4-flexfiles-v2-delta-writes`

This file is the single source of truth; the companion repositories point
here rather than keeping their own copy.

Every rule below was derived from an editorial pass actually applied to
one of the three drafts, and cites the commit that established it.
Hashes resolve in whichever repository the pass ran in — most in this
one, but the proxy-server draft established several (`f4ddd3a1`,
`b5c36333`, `c4e53ddb`, `1760f672`). Where a sweep is
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

Later conversions, all found by pattern rather than by being on a list
(`c3b67d1d`):

| British | US |
|---|---|
| flavour(s) | flavor(s) |
| summaris(e/ed) | summariz… |
| synchronisation | synchronization |
| materialising | materializing |
| prioritise | prioritize |
| uninitialised | uninitialized |
| vectorised | vectorized |
| localis(e/es/ed) | localiz… |

**Match on the pattern, not the stem.** Two rounds of stem lists both
under-caught. The first sweep matched `behaviour` and missed
`behaviours` — an inflection problem, fixed by matching stems. The
second failure was worse: `flavour` was never on the list at all, and
neither were the eight above, so no stem could have found them. A word
list only finds the words someone already thought of. §11 greps `-our`
and `-ise` generically instead.

Exclude by **stem plus inflection**, not by whole word. A list of
`advertise|advertised` still reports `advertising`; `resource` matches
the `-our` pattern outright and needs its own exemption, as does any
`-wise` compound. The first version of this grep shipped with a
whole-word list and returned 11 hits, every one a false positive —
`resources`, `bytewise`, `exercising`, `advertising` — which is the
state that gets a check ignored.

Watch the leading `\b`. `\b(…|initialis|…)` does **not** match
`uninitialised` — there is no word boundary between `un` and
`initialis` — which is how two of those sat in the tree through every
prior sweep.

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

`surface` as a **transitive verb** ("surfaces the error to the caller",
"MAY surface the distinction in operator telemetry") is ordinary English
and is kept, as is the idiom "attack surface" and the adjective meaning
superficial ("the surface complaint … the structural objection").

The **noun** is banned by the table above, and so is the intransitive
("does not surface on the wire" → "does not appear on the wire").

`d0ab1060` retired 17 noun sites and the rule has been in the table ever
since — yet six more had accumulated by the next audit: the fore-channel
surface, the client-facing surface, the security surface, the proxy
server surface, and a plural reading as a verb. A banned word with no
sweep behind it comes back. §11 has the sweep. (`f4ddd3a1`, `98c0aa57`)

### 3.2 Naming register

Pick by role, not taste (`26cd8e05`):

| Context | Form |
|---|---|
| Headings, IANA registrations, abstract | Flexible File Version 2 Layout Type |
| Body prose | flexible file v2 layout |
| Body prose, the v1 layout | flexible file v1 layout |
| Body prose, true of either version | flexible file layout |
| When the sentence is about the wire value | `LAYOUT4_FLEX_FILES_V2` |

Never "flexible file v2 layout version 2" — the `v2` already carries the
version.

**"Flex Files" is not a form.** Neither is `flex-files`, `Flex File`, or
`flex files`. The base draft writes "flexible file v1 layout" 27 times
and never once writes "Flex Files"; four sites in the proxy-server draft
had drifted to four different spellings of it. (`1760f672`)

Reach for the version-agnostic row only when the statement is true of
both versions — a source layout that is not pNFS at all, client-side
mirroring as the family's availability mitigation. Dropping the version
because you are unsure which one applies is how "expose itself as a
flex-files data server" got written; a reader then cannot tell whether
the slot is a v1 or a v2 layout position.

```sh
grep -nE 'Flex[ -]Files?|flex[ -]files?' $D          # expect front matter only
```

Front matter is exempt and is the only expected hit: `title:` and
`abbrev:` carry "Flexible File Layout Version 2" and "Flex File Layout
v2", and the base draft says so in body prose — document-metadata
conventions do not participate in the body-prose vocabulary.

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

**Operation names are nouns. Do not conjugate them.** A plural is a
noun and is fine — "OPENs are dealt with by the metadata server",
"subsequent client LAYOUTGETs receive L1", "CHUNK_WRITEs" — because it
fills a noun slot. A finite verb is not: write *issues a fresh
LAYOUTGET*, not "re-LAYOUTGETs"; *issues LAYOUTRETURN*, not
"LAYOUTRETURNs as usual"; *has not yet issued `OPEN(CLAIM_PROXY)`*, not
"has not yet OPEN'd". Naming the operation you mean is usually more
precise than the contraction was. (`c4e53ddb`)

The cost is not only register. "Reporting client LAYOUTERRORs the
metadata server" shipped in a figure legend for want of a *to* — a
missing preposition is invisible while the reader is still deciding
whether the all-caps token is the verb. (`4f770bbd`)

An operation name inflected as a verb inside ASCII artwork is fine, as
is `XOR'd`: XOR is an ordinary English verb, not only a wire name.

```sh
grep -nE "re-[A-Z_]{3,}|[A-Z][A-Z_]{3,}'(d|ed)\b" $D   # conjugated ops
```

Two mechanical forms only: the `re-` prefix and the `'d` contraction.
Do not add `'s` to that alternation — possessives swamp it (19 of 21
hits were `CHUNK_ROLLBACK's`, `XOR_PARITY's`, and friends), and a check
that reports mostly noise stops being read.

The third form has no regex: a bare conjugated plural. "The client
LAYOUTRETURNs as usual" and "subsequent client LAYOUTGETs receive L1"
are the same characters, and only the sentence says which is the verb.
Catch that one by reading.

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

### 5.5 Terminal punctuation in ordered lists

Punctuate by grammar, not by taste. Read the lead-in and the first item
together and ask whether they form one sentence.

**Stem-completing** — the lead-in ends in a colon and each item is a
predicate or phrase that finishes it, so the whole list is one sentence.
Lowercase each item, semicolon after each, `and` before the last,
period on the last:

```
For each new or refreshed layout segment, the metadata server:

1. chooses the layout stateid (as it would without tight coupling);
2. identifies the trusted stateid capable storage devices …; and
3. fans out TRUST_STATEID to each such storage device ….
```

**Independent** — each item has its own subject, or runs to more than
one sentence. Capitalize and end every item with a period. The
five-step abort sequence in the proxy-server draft is the worked
example: each step opens with a title sentence and continues with
`MUST` prose.

Two tells that you have the wrong one:

- An item that already contains a semicolon cannot be semicolon-joined
  — the reader cannot see which one separates items. Make the list
  independent instead. (`b5c36333`)
- A stem-completing item whose tail is a parenthetical aside about
  another document is not a step. Lift it to a paragraph after the
  list, then punctuate what remains.

Capitalized items with no terminal punctuation are neither, and are the
state a list drifts into. Nine such items sat in one proxy-server
section, and nine more across two delta-writes algorithm lists;
everything else in the family already followed the rule above.

The check: an ordered item should end with `;`, `; and`, or `.`
A bare `and` at the end of an item wants `; and`.

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

grep -nE '\b(defence|analyse|licence|centre)[a-z]*'            $D   # no shared pattern
grep -onE '[A-Za-z]{4,}(ise|ised|ises|ising|isation|isations)\b|[a-z]{3,}our[a-z]*' $D \
  | grep -viE ':((enterpris|compris|advertis|compromis|promis|exercis|revis|devis|advis|supervis|surpris|franchis|merchandis|improvis|disguis|rais|prais|nois)(e|es|ed|ing)|precise|concise|[a-z]*wise|resources?)$'
grep -nE '\b(MDS|DS|DSes|FFv1|FFv2)\b' $D          # expect only identifiers, tables, artwork
grep -niE 'inband|CHUNK_\*|repair client'          $D
grep -nE '\*\*[^*]+\*\*|(^|[^*])\*[^* ][^*]*\*'    $D   # emphasis
grep -nE '\\\[|\\\]'                               $D   # escaped brackets
grep -nE '[a-z_] == '                              $D   # C-style equality
grep -nE '[a-z]-$'                                 $D   # line ends mid-compound (ignore hits inside ~~~ artwork)
grep -nE '^\s*[-*] \*\*'                           $D   # bullet-with-bold
grep -niE 'surfac' $D | grep -viE 'attack surface'      # see below
```

### Unterminated ordered-list items

Per §5.5, every ordered item ends with `;`, `; and`, or `.` — this
walks the items and prints the ones that do not (skipping fences):

```sh
python3 - "$D" <<'EOF'
import re, sys
lines = open(sys.argv[1]).read().split('\n')
fence = False; items = []; cur = None
for n, l in enumerate(lines, 1):
    if l.startswith('~~~'):
        fence = not fence; continue
    if fence:
        continue
    m = re.match(r'^\d+\.\s+(\S.*)$', l)
    if m:
        if cur: items.append(cur)
        cur = [n, m.group(1)]
    elif cur is not None:
        if not l.strip():
            continue                       # blank line inside an item
        if re.match(r'^\s+\S', l): cur[1] += ' ' + l.strip()
        else: items.append(cur); cur = None
if cur: items.append(cur)
for n, t in items:
    if not t.rstrip().endswith(('.', '.)', ';', '; and')):
        print(f"L{n}: {t[:70]}")
EOF
```

Two false positives to expect. A multi-paragraph item must not be closed
by its own blank line — hence the `continue` above; without it every
item with a nested fence or a second paragraph reports as unterminated.
And a wrapped decimal opening a line ("… 250 >\n100.  Because …") matches
the item pattern. kramdown does not mis-render that one — a continuation
line inside a paragraph never starts a list — so it needs no fix; ignore
it, or rewrap the prose to stop it recurring.

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

### Overused `surface`

Machine-drafted prose reaches for this word far past what English wants.
A density comparison found it once — 9 uses in ~3,300 lines of the
proxy-server draft against 13 in ~15,900 of the base, and all five bad
ones were in the denser draft — but do not lean on that signal. After
the fix the base is the denser of the two, on legitimate verbs alone. A
high count is not a finding; triage every hit.

Ask what the word is doing in each:

| Use | Verdict | Example |
|---|---|---|
| Transitive verb, object present | keep | "MUST surface `NFS4ERR_PAYLOAD_LOST`" |
| "surface as `NFS4ERR_…`" (manifest) | keep | "both surface as `NFS4ERR_BAD_STATEID`" |
| "attack surface" | keep | idiom |
| Adjective, = superficial | keep | "the surface complaint" |
| **Noun** | **replace** | "the security surface added by this document" |
| **Intransitive** | **replace** | "behavior that does not surface on the wire" |

The noun rewrites that worked: *the fore-channel surface* → the
fore-channel protocol; *the mechanism's sole client-facing surface* →
the only part of the mechanism a client ever sees; *the security
surface added by this document* → the security-relevant behavior this
document adds; *the proxy server surface implemented in reffs* → what
reffs implements. Intransitive → "appear on the wire", except where it
governs a noun that is not a place ("does not surface as new wire
protocol" does not parse; write "requires no new wire protocol").

Watch for a noun sitting right after an identifier, where it first
reads as a verb — "byte-identical output on the `…_SYSTEMATIC` and
`…_NON_SYSTEMATIC` surfaces" meant *for* those two encoding types.

### Rendered width and leaked xrefs

Two things only the built `.txt` can tell you. Check it, not the source
— artwork indent differs by block, so a source-length guess both misses
real hits and invents fake ones (a source sweep once reported 32
over-wide lines where the render had 9):

```sh
T=${D%.md}.txt
awk 'length>72 {printf "%d [%d] %s\n", NR, length, $0}' $T
grep -n '{{' $T          # xrefs that leaked instead of resolving
```

RFC text is 72 columns. Long artwork usually needs the fix applied to
the whole block, not the one line: wrap an XDR comment (§9), move an
array bound to a continuation line, or shed a couple of columns from a
figure's indent uniformly. A long URI in a reference is the one
acceptable overflow — it cannot be wrapped.

`{{…}}` inside a `~~~` fence is **not** processed by kramdown, so it
reaches the published text as literal braces. Name the target in words
instead; the base draft had four of these shipping in its XDR comments.

Then build — the rendering check is part of the convention, not
incidental. Every commit in this series records a green run:

```sh
make            # kramdown-rfc -> xml2rfc txt + html
make -s lint
```
