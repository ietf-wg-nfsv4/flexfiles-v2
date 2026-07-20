---
marp: true
theme: default
paginate: true
size: 16:9
footer: "@@FOOTER@@"
style: |
  section { font-size: 24px; }
  section table { font-size: 0.85em; }
  section.big { font-size: 35px; }
  section.big table { font-size: 1em; }
  section.shrink85 pre { font-size: 0.85em !important; }
  section.shrink85 pre code { font-size: inherit !important; }
  section.dense table { font-size: 0.72em; }
  section.tight { font-size: 21px; }
---

<!-- _footer: "" -->
<!-- Slide role: SEPARATOR (title) -->
<!-- _class: big -->

# Flex Files v2 + Proxy Server

## IETF 126, NFSv4 WG

[draft-haynes-nfsv4-flexfiles-v2](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2/)
[draft-haynes-nfsv4-flexfiles-v2-proxy-server](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2-proxy-server/)

&nbsp;

&nbsp;

Tom Haynes &mdash; @@DATE@@

<!-- Presenter note: Note Well applies as always. If IPR questions arise
     re: Mojette encodings, the prepared answer is: "BCP 79 disclosure
     obligations are understood; the disclosure status question should go
     to the chairs and the datatracker IPR page, not be adjudicated at
     the mic." Do not improvise beyond that. -->

---

<!-- Slide role: CONTENT
     Must-deliver:
     FFv2 is three separable things: A (core) / B (EC) / C (PS).
     Core stands alone; EC layers on it; PS serves encoding-ignorant
     clients.  The document-structure question is the closer, not a
     rebuttal in the middle. -->
# This deck in one slide

**Flex Files v2 is three separable things.  This deck presents them in order.**

| | What | Who benefits |
|---|---|---|
| **A. A modernized Flex Files core** | revoke-now admission control, heterogeneous mirror sets, PASSTHROUGH, better error/stats reporting | **every** Flex Files deployment, mirror-only included |
| **B. An erasure-coding capability** | client-side EC over a chunk model with defined crash semantics | PB-scale + multi-rack deployments |
| **C. A Proxy Server (PS) companion** | repair offload + translation for encoding-ignorant clients | unmodified kernel clients; operators |

Then: implementation status (reffs) &rarr; the document-structure question &rarr; what we ask of the WG.

<!-- Presenter note: this ordering is deliberate. The core stands on its
     own merits; EC is presented as a capability layered on it. The
     one-document-vs-split question is presented at the END, once the
     audience has seen the machinery, as an open scoping question. -->

---

<!-- Slide role: CONTENT
     Must-deliver:
     v1 works; a decade in the field taught four gaps.  Lessons 1 + 4
     are core problems and motivate Part A.  Lessons 2 + 3 motivate
     the EC capability (Part B).  If asked "why not just fix v1?" -
     that IS Part A. -->
# Where v1 stands (RFC 8435) &mdash; and what the field taught

**Flex Files v1 won deployment for one reason:** data servers are plain NFS servers.  Loose coupling; any NFSv3/v4 server participates.

**Four lessons from a decade in the field:**

1. **Fencing is a hack.**  Synthetic uid/gid manipulation to fence a client is racy and awkward &mdash; and there is **no way to stop a rogue or dead writer *now***; you wait on lease expiry or recall acks.
2. **Mirror-only economics fail at PB scale.**  3x storage for 2-failure tolerance is unaffordable for archives.
3. **Heterogeneous pools are inexpressible.**  One file cannot span pools with different capabilities (NFSv3-only, encoding-capable) in one layout.
4. **Error visibility is thin.**  Operators want richer per-DS error and latency reporting than v1's LAYOUTERROR/LAYOUTSTATS carry.

Lesson 1 and 4 are core problems.  Lessons 2 and 3 motivate the EC capability.

---

<!-- Slide role: CONTENT
     Must-deliver:
     The core asks MODEST new work of the DS (3 ops + admission table).
     The +11 CHUNK ops are the EC price, NOT the core price.  Point at
     the DS-requirements row when saying it.  Never claim "DS stays
     just NFS." -->
<!-- _class: dense -->
# v1 &rarr; v2 at a glance

| Dimension | FFv1 (RFC 8435) | FFv2 core (A) | + EC capability (B) |
|---|---|---|---|
| Fencing / admission | synthetic uid/gid; wait for lease/recall | `TRUST_STATEID` push; **revoke-now** | same |
| Data protection | client-side mirroring only | mirroring + heterogeneous mirror sets + PASSTHROUGH | + RS / Mojette erasure coding |
| Writer-death semantics | fencing races; torn mirrors possible | revocation window bounded by fan-out RTT | + chunk rollback: **no mixed stripes, ever** |
| Error / stats reporting | ff_ioerr / ff_iostats | richer ffv2 variants | + per-block CRC32 |
| **DS requirements** | **unmodified NFS server** | **+3 ops** (trust-stateid family) + admission table | **+11 CHUNK ops** + per-block state machine + ~40 B/block durable metadata |
| Client requirements | mirror writes | unchanged for mirror use | encode/decode + chunk lifecycle (or use the PS) |

**Stated plainly:** the core asks modest new work of the DS.  The EC capability is where the DS stops being an unmodified server.  We think the capability earns it &mdash; Part B makes that case with measurements.

<!-- Presenter note: owning the DS-cost row up front removes the single
     most damaging mic question ("the deck says DS stays just NFS, but
     the draft adds 14 ops"). Never claim "DS stays just NFS." -->

---

<!-- Slide role: SEPARATOR (Part A) -->
<!-- _class: big -->
# Part A &mdash; the Flex Files v2 core

*value for every deployment, mirror-only included*

---

<!-- Slide role: CONTENT
     Must-deliver:
     Three ops replace v1's synthetic uid/gid fencing.  Every DS in a
     layout holds an admission-table entry per stateid.  MDS remains
     the single state authority; no consensus, no distrbuted lock manager - distrbuted lock manager - DLM. -->
# Trust-stateid: the revoke-now mechanism

| Op | When the MDS sends it | What it does |
|---|---|---|
| `TRUST_STATEID` | Layout issued to client | Push stateid to every DS in the layout *before* client I/O.  DS records it in an admission table; I/O with this stateid &rarr; accepted, any other &rarr; `NFS4ERR_BAD_STATEID`. |
| `REVOKE_STATEID` | Layout returned, recalled, or reissued | Clear the stateid from each DS's table.  Next write from that client **fails closed**. |
| `BULK_REVOKE_STATEID` | Client lease expires | One per affected DS; clears every entry for that client at once. |

Replaces v1's synthetic uid/gid fencing.  No consensus protocol, no Distributed Lock Manager (DLM) &mdash; the MDS remains the single state authority; DSes are admission gates.

---

<!-- Slide role: CONTENT
     Must-deliver:
     The corruption window is one parallel fan-out RTT - NOT lease
     expiry and NOT A's cooperation.  This mechanism has value for
     MIRROR-ONLY deployments; it does not depend on erasure coding. -->
# Revoke-now, walked through

Writer A is mid-write on DSes D1..D6; the MDS decides A must yield (recall, lease event, or admin action):

1. MDS sends `CB_LAYOUTRECALL` to A
2. MDS sends `REVOKE_STATEID(A)` to D1..D6 **in parallel**
3. A's in-flight writes are rejected with `NFS4ERR_BAD_STATEID` &mdash; **before** any mirror or parity is corrupted
4. MDS issues the new layout and sends `TRUST_STATEID(B)` to D1..D6
5. B's writes are accepted

**The corruption window is bounded by step 2's fan-out latency** &mdash; not by A's cooperation, not by lease expiry.

This mechanism is valuable to **mirror-only** deployments.  It does not depend on erasure coding.

---

<!-- Slide role: CONTENT
     Must-deliver:
     PASSTHROUGH preserves v1's plain-NFS story inside v2.
     Heterogeneous mirrors enable live migration between pool
     generations.  Core cost = 3 ops + admission table.  Zero chunk
     machinery in Part A. -->
# The rest of the core

- **PASSTHROUGH encoding** &mdash; a pool of plain NFSv3/NFSv4 servers participates as-is; the v1 deployment story is preserved inside v2.
- **Heterogeneous mirror sets** &mdash; mirror instances of one file may live on pools with different capabilities; enables live migration between pool generations.
- **Refreshed error + stats reporting** &mdash; ffv2_ioerr / ffv2_iostats carry what operators asked for.
- **Tight-coupling control protocol** (draft &sect;6.4) &mdash; capability discovery, control sessions, crash recovery on both sides.

**What the core costs:** 3 new DS operations + an admission table.  A new layout type to parse.  No chunk machinery, no encoding logic, no per-block metadata.

<!-- Presenter note: if pressed "could Part A progress on its own?" the
     answer is yes-technically; whether it SHOULD is the structure
     question at the end of the deck.  Don't pre-answer it. -->

---

<!-- Slide role: SEPARATOR (Part B) -->
<!-- _class: big -->
# Part B &mdash; the erasure-coding capability

*for the deployments that mirror economics have priced out*

---

<!-- Slide role: CONTENT
     Must-deliver:
     EC is an economics story before it's a math story.  PB archives,
     multi-rack, latency-sensitive reads - mirror can't pay for any of
     these at scale. -->
# Why erasure coding

**PB-scale archives** &mdash; HEP raw data, sequencing pipelines, observatory imagery
- Mirror at 3x storage is unaffordable
- RS(8,2) at 1.25x tolerates 2 simultaneous DS losses

**Multi-rack / multi-AZ deployments**
- Mirror across 3 racks: 3x storage for 2-rack tolerance
- RS(6,3) across 9 racks: 1.5x storage for 3-rack tolerance

**Latency-sensitive reads at scale**
- Read any k of (k+m) shards; m "free" stragglers to skip per file
- Mirror gives "fast or slow mirror"; EC gives k-of-(k+m) margin

---

<!-- Slide role: CONTENT
     Must-deliver:
     Client-side avoids server bandwidth bottleneck; encode compute
     scales with writers, not DSes.  The cost is real - 11 ops on the
     DS.  Unmodified clients aren't left behind; they use the PS.
     If asked "nobody does this" - answer "correct, that's why
     sec 12/24/25 and reffs exist." -->
# Why *client-side* EC &mdash; and what it costs

**The case:**
- Client writes k+m shards **directly to DSes** &mdash; server-side EC bottlenecks on one server's bandwidth
- Encode happens **once at the source**; encoding compute scales with the writer population, not the DS count
- Repair distributes across surviving clients and Proxy Servers

**The cost:**
- The DS gains the CHUNK machinery: 11 operations, a per-block state machine, ~40 B/block durable metadata, per-block CRC32
- Encoding-capable clients gain encode/decode + chunk lifecycle; **unmodified clients use the Proxy Server path (Part C) &mdash; at a measured cost we show there**

**No shipping network filesystem does client-side EC with overwrite at the protocol level.**  That is why the draft now carries a formal system model (&sect;12) and why reffs exists: the novel part is specified, not asserted.

<!-- Presenter note: pre-empting the prior-art objection by owning it is
     stronger than waiting for a reviewer to raise it. The answer to "nobody
     does this" is "correct - that's why sections 12, 24, 25 exist and
     why we built it twice before asking for adoption." -->

---

<!-- Slide role: CONTENT
     Must-deliver:
     State machine gives defined crash semantics.  Readers NEVER see
     PENDING.  Lease-driven rollback keeps stripes clean.  Concurrent
     writers CAS-serialize: loser gets NFS4ERR_DELAY, retries
     read-merge-rewrite. -->
# The chunk model: defined crash semantics

Per (inode, block-offset) on the DS:

```
              CHUNK_WRITE            CHUNK_FINALIZE           CHUNK_COMMIT
     EMPTY ----------------> PENDING ---------------> FINALIZED ------------> COMMITTED
       ^                        |                        |
       |                        |  CHUNK_ROLLBACK        |  CHUNK_ROLLBACK
       +------------------------+------------------------+
```

- Readers see only **FINALIZED / COMMITTED** state &mdash; never PENDING
- Lease-driven rollback sweeps a dead writer's PENDING/FINALIZED blocks back to EMPTY; **COMMITTED work survives session expiry by design**
- Concurrent writers on one block serialize via a **CAS guard** (`chunk_guard4`); the loser gets `NFS4ERR_DELAY` and retries read-merge-rewrite &mdash; same shape as software-RAID CAS *(full trace: backup)*

---

<!-- Slide role: CONTENT
     Must-deliver:
     Section 12 gives the guarantees formally.  Per-chunk
     linearizability on COMMITTED.  No multi-chunk atomicity is an
     EXPLICIT NON-GOAL - own it, don't defend around it.  O(1) round
     trips, no consensus, bounded repair. -->
# Draft &sect;12 states the guarantees formally

- per-chunk linearizability on COMMITTED state
- **no** multi-chunk atomicity (explicit non-goal)
- O(1) round trips on the data path
- no consensus rounds, no DLM
- bounded repair termination.

---

<!-- Slide role: CONTENT
     Must-deliver:
     v1 gives 4-of-6 MIXED (the write hole).  v2 gives 0-of-10 MIXED.
     Never a mixed stripe.  The failure mode is LOUD (-EIO), not
     silent corruption. -->
# Writer dies mid-stripe: the write hole, measured

6 kill points &times; {v1 NFSv3, v2 CHUNK} = 12 runs; re-run 10/10 on second testbed.

**v1: 4 of 6 cells produce MIXED** &mdash; partial-overwrite leak visible to readers.  The write hole.

**v2: 0 of 6 (and 0 of 10 on re-run) produce MIXED.**  Every outcome is one of:

| Kill point | Outcome | Mechanism |
|---|---|---|
| Before any `CHUNK_WRITE` | prior contents intact | COMMITTED blocks untouched |
| Mid-write, before COMMIT | clean, loud `-EIO` | all touched blocks rolled to EMPTY on lease expiry |
| After COMMIT | new contents durable | FINALIZE + COMMIT made the write survive |

**Never a mixed stripe.**  The failure mode is loud, not silent.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Fixed setup cost dominates small sizes; absorbed by 1 MB.
     RS 4+2 approx. equals plain mirror at 1 MB (113 vs 116 ms).
     Reconstruction: 120/120 byte-exact, 20/20 fail cleanly,
     zero silent bad data. -->
<!-- _class: tight -->
# EC performance: where the cost lives

Median write, single client, 5 runs per cell *(full tables + read side: backup)*:

| Size | Plain | RS 4+2 | Moj-sys 4+2 | RS 8+2 | Moj-sys 8+2 |
|---|---:|---:|---:|---:|---:|
| 4 KB | 26 ms | 48 ms | 46 ms | 51 ms | 50 ms |
| 64 KB | 33 ms | 54 ms | 53 ms | 57 ms | 56 ms |
| 256 KB | 49 ms | 69 ms | 66 ms | 71 ms | 67 ms |
| 1 MB | 116 ms | 113 ms | 113 ms | 110 ms | 105 ms |

**The read:** EC carries a near-fixed per-write setup cost (encode + parity RPCs + coordination) that dominates at small sizes and is **absorbed below fan-out/RTT noise by 1 MB**.  Both geometries and both encodings show the same collapse; at 1 MB Moj-sys 8+2 lands **9% below plain mirror**.  Encode compute is not the limiter at any size we measured.

Caveat we state before you do: rows move different byte counts (RS 4+2 = 1.5x payload; mirror = replica count &times; payload), so cross-row comparisons measure *redundancy scheme*, not encode cost.  The within-row trend is the encode-cost claim.

**Reconstruction:** 120/120 within-tolerance recoveries byte-exact; 20/20 over-tolerance cells **fail cleanly** &mdash; zero silent bad data.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Three encodings implemented today.  Registry exists.  MTI does
     NOT.  That's the open item.  Propose RS-Vandermonde as MTI for
     encoding-capable implementations; everything else optional.
     WG input sought. -->
# Encodings: three today, a registry forever

One `struct ec_encoding` interface; three encodings implemented and benchmarked:

- **Reed-Solomon, Vandermonde GF(2^8)** &mdash; conservative baseline; interop parameters pinned in draft &sect;11.4.6 (polynomial 0x11d, generator, evaluation points, normalization)
- **Mojette systematic / non-systematic** &mdash; projection encodings; data shards *are* the data (systematic)

**Patent posture:** pre-2000 textbook sources cited in headers (Reed & Solomon 1960, Berlekamp 1968, Peterson & Weldon 1972); Jerasure/GF-Complete/ISA-L internals avoided.  Scalar arithmetic: slower, correct, reproducible from the literature.

**Open question we want answered in this room:** the draft defines a encoding **registry** but no **mandatory-to-implement** encoding.  Two conforming implementations could share none.  Proposal on the table: **RS-Vandermonde as Minimum To Implement (MTI)** for encoding-capable implementations; everything else optional.  WG input sought.

<!-- Presenter note: surfacing the MTI gap ourselves converts the
     sharpest interop objection into an agenda item we control. -->

---

<!-- Slide role: SEPARATOR (Part C) -->
<!-- _class: big -->
# Part C &mdash; the Proxy Server

*so unmodified clients are not left behind*

---

<!-- Slide role: CONTENT
     Must-deliver:
     PS has three jobs: (1) repair offload, (2) translation for
     encoding-ignorant clients, (3) encoding migration on an existing
     file.  One registered role authenticated via PROXY_REGISTRATION. -->
# What the PS is

**Three jobs, one registered role** (`PROXY_REGISTRATION`; Kerberos machine principal or mTLS):

1. **Repair offload** &mdash; reconstruct shards onto a fresh DS without client CPU/bandwidth
2. **Translation** &mdash; unmodified NFSv4.2/NFSv3 clients mount the PS, see plain reads/writes; PS encodes/decodes against the real DSes
3. **Encoding migration** &mdash; add a mirror in encoding Y to a file striped in encoding X, without touching clients

---

<!-- Slide role: CONTENT
     Must-deliver:
     Translation costs 6-8x on writes.  ~530 ms floor is per-file
     lifecycle - small-file workloads pay it per file.  This is the
     QUANTIFIED price of compatibility AND the incentive for native
     client-side EC. -->
# **Measured cost of the translation path**

(3-host bench, kernel client; full tables: backup):

| Path | 4 KB write | 16 MB write |
|---|---:|---:|
| MDS-inband (no client EC) | 70 ms | 284 ms |
| **Via PS (EC translation)** | **528 ms** | **1734 ms** |

**The read:** translation costs 6&ndash;8x on writes, and the ~530 ms floor is **per-file lifecycle cost** &mdash; small-file workloads pay it per file.  MDS-inband is fast but serializes data through the MDS, giving up pNFS scaling.  **This is the quantified incentive for native client-side encoding support** &mdash; and the quantified price of compatibility until it exists.

<!-- Presenter note: this reframing is deliberate. Tom's original framing
     ("proves server-side EC is costly") invites the counter "but the PS
     IS your path for every real client today." Owning that reading
     first defuses it. -->
---

<!-- Slide role: SEPARATOR (Implementation Status) -->
<!-- _class: big -->
# Implementation Status

---

<!-- Slide role: CONTENT
     Must-deliver:
     Second implementation, independent of Linux kernel server.
     User-space, prototyping not production.  Two backends on ONE
     wire format - the protocol doesn't dictate fragmentation.
     Shipped: repair, PS role.  Missing: a kernel client - that's
     an explicit ask. -->
# Implementation status: reffs

A second implementation, independent of the Linux kernel server, built to answer *"did the design survive contact with code?"*

- User-space C; Linux + macOS; **prototyping, not production**
- MDS + DS roles; FFv1 + FFv2 layouts; all CHUNK + trust-stateid ops; PS role; `ec_demo` userspace client
- **Two storage backends on one wire format** (POSIX+XFS sidecar files; RocksDB LSM) &mdash; the protocol does not force a fragmentation regime
- Shipped: wire-level single-shard reconstruction (`CHUNK_WRITE_REPAIR` + `CHUNK_REPAIRED`, 80-cell bench)
- In progress: PS-driven repair autopilot; cross-PS coherence for NFSv3 clients (known gap, fix shape documented)

**What does not yet exist:** a kernel client; an implementation outside the reffs/ec_demo family.  We are explicit about this &mdash; it is one of the asks.

---

<!-- Slide role: SEPARATOR (The structure question) -->
<!-- _class: big -->
# The structure question

---

<!-- Slide role: CONTENT
     Must-deliver:
     The TWO-layout-type variant is OFF the table under either option.
     Both options keep one layout type + one registry + chunk /
     MIRRORED / PASSTHROUGH in the core.  What IS contested: where do
     encoding SPECS live. -->
# The structure question, framed precisely

**Not on the table (under either position): a second layout type.**  Per-segment and per-mirror-instance encoding live *inside* one layout type's XDR.  Single-file heterogeneity &mdash; a file mid-migration holding instances in two encodings, or spanning pools of unlike capability &mdash; requires exactly that.  Both options below keep **one layout type, one `ffv2_coding_type4` registry, and the chunk substrate + MIRRORED + PASSTHROUGH in the core document.**

**What is genuinely contested: where encoding *specifications* live.**

| | Option A &mdash; one document | Option B &mdash; core + scheme documents |
|---|---|---|
| RS-Vandermonde | in-document (&sect;11.4) | short companion document, proposed **MTI**, advances with core |
| Mojette | in-document (&sect;11.5) | independent scheme document, arriving via the registry |
| Registry's role | entry path for *future* encodings | entry path for **every** encoding beyond the core |

The next two slides give each option's case at full strength.

<!-- Presenter note: this framing deliberately retires the two-layout-type
     variant up front so the room argues about the real question. Neither
     option slide is the chairs' position; the questions slide is. -->

---

<!-- Slide role: CONTENT
     Must-deliver:
     One-document case: reviewed as a whole, no reference web,
     ships complete today, "later" has a base rate of never.
     Precedent: RFC 5664 objects, RFC 8435 FFv1. -->
# Option A &mdash; one document: the case

- **Reviewed as a whole.**  Encoding behavior interacts with guards, shard sizing, repair selection, and the &sect;12 correctness model.  One document puts the complete machine in front of every reviewer &mdash; no interface seam to specify wrong, no gap for cross-document drift.
- **Specified once, no reference web.**  This WG's live experience with a coordinated document cluster shows cross-document normative coupling is where its scarce coordination effort goes.  One document: one WGLC, one IESG action, one IANA moment, zero placeholder dependencies.
- **Ships complete.**  RS and Mojette are implemented, benchmarked, and interoperability-pinned *today*; in-document text converts that maturity into day-one normative coverage.
- **"Later" has a base rate.**  In a backlogged WG, a deferred scheme document carries real risk of becoming a never-published one; embedding is the delivery vehicle with a known clock.
- **Precedent:** the pNFS objects layout (RFC 5664) carried its RAID algorithms in-document; Flex Files v1 (RFC 8435) carried all of its data-protection machinery in one document.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Split case: agnosticism becomes TESTABLE (an independent encoding
     arriving via the registry proves it).  Scheme docs version on
     their natural clocks.  Review routes to the right expertise.
     Precedent: pNFS block/SCSI/NVMe chain and the FECFRAME family. -->
<!-- _class: tight -->
# Option B &mdash; core + scheme documents: the case

- **The agnosticism claim becomes testable.**  An interface proven only by encodings co-designed alongside it is asserted, not demonstrated.  A encoding arriving *independently* through the registry &mdash; without reopening the core &mdash; is the only available proof that FFv2 is encoding-method agnostic.  Under Option B, Mojette's arrival **is** that proof event.
- **Layers version on their natural clocks.**  Coding theory moves on a research clock (LRC 2012, Clay 2018, ...); NFS wire semantics move on a decade clock.  Scheme documents let encodings evolve without reopening &mdash; or waiting on &mdash; the core.
- **Review goes where the expertise lives.**  GF(2^8) arithmetic and projection geometry can be routed to coding-theory-competent reviewers (the FECFRAME/RMT community); stateid machinery to pNFS reviewers.  A stalled encoding review stalls nothing else.
- **Precedent, twice:** pNFS's own lineage added flavors against a stable substrate &mdash; block (RFC 5663) &rarr; SCSI (RFC 8154) &rarr; NVMe (**RFC 9561, nine pages, 2024**); and **FECFRAME (RFC 6363)**, the IETF's one prior erasure-coding standardization, used a framework plus per-scheme documents (Raptor 5053, LDPC 5170, **Reed-Solomon 5510**, RaptorQ 6330) accreting for years without the framework reopening.
- **Coordination topology matters:** framework&rarr;scheme is a one-way reference plus a registry &mdash; a benign shape, distinct from bidirectional coupling between co-developed documents.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Four inputs the chairs need: composition generality, MTI question,
     energy mapping, registry policy (if Option B).  The structure
     decision follows these answers - not the other way around. -->
# What would settle it &mdash; input the chairs need

1. **Composition generality.**  Who runs deployments needing single-file cross-encoding states &mdash; static (a file spanning unlike pools) or transitional (mid-migration, lazy encoding)?  This is why both options keep one layout type, and it weights Option A's reviewed-as-a-whole argument.
2. **MTI.**  Should RS-Vandermonde be mandatory-to-implement for encoding-capable implementations?  (Closes the encoding interop gap under *either* option.)
3. **Energy mapping.**  Who will implement &mdash; and who will *review* &mdash; the core, RS, and Mojette respectively, on what clock?  Option B's value scales with independent encoding energy; Option A's with unified review energy.
4. **If Option B:** registry policy (Specification Required with Designated Expert?) and whether the RS companion advances jointly with the core.

Under either option, trust-stateid, the chunk substrate, and mirror-side write-hole protection ship on the same clock.  **The structure decision follows these answers &mdash; not the other way around.**

<!-- Presenter note: if pressed for the chairs' view, the answer is that
     the chairs are collecting exactly these four inputs and will not
     pre-decide structure from the front of the room. -->

---

<!-- Slide role: CONTENT
     Must-deliver:
     Three asks: (1) is Part A wanted on its own merits?
     (2) answer the four structure inputs.  (3) who implements,
     who reviews deeply.  Document structure follows the answers. -->
# What we ask of the WG

**Read** &mdash; if you read nothing else: &sect;12 (system model + guarantees), &sect;8.11 (encoding negotiation), &sect;24&ndash;25 (chunk structures + ops).  The PS draft: &sect;4&ndash;6.

**Answer, on the list:**

1. Is the **core** (Part A: trust-stateid, PASSTHROUGH, heterogeneous mirrors) work the WG wants, on its own merits?
2. The **four structure inputs** on the previous slide &mdash; composition cases you actually run, the MTI question, energy mapping, and (if schemes separate) registry policy.
3. **Who will implement** &mdash; client, DS, or PS side &mdash; and on what horizon?  Who will review deeply?

**Document structure follows from the answers** &mdash; not the other way around.

---

<!-- Slide role: SEPARATOR (Adoption) -->
<!-- _class: big -->
# Call for Adoption

---

<!-- Slide role: CONTENT
     Must-deliver:
     Five reasons this wasn't ready before.  Each closed since.
     The "Why now" slide mirrors these bullets in order so the room
     sees each gap answered.  Don't apologize for the wait; frame it
     as work that had to happen. -->
# Why not before

- Draft was not yet complete
- Use cases underspecified
- Requirements not framed
- No implementation experience
- No legacy-client story

---

<!-- Slide role: CONTENT
     Must-deliver:
     Same order as "Why not before" so the room sees each gap
     closed.  End with the concrete procedural ask: Call for
     Adoption at this meeting.  Don't hedge - the room already saw
     the substance in Parts A/B/C. -->
# Why now

- Draft is complete (-06 current; -07 planned after WG feedback)
- Use cases identified (&sect;2, &sect;3) and grounded in operator workloads
- Requirements framed &mdash; workload-driven, not speculative
- Implementation experience: reffs (see slide 22)
- Legacy-client story: PS draft (`draft-haynes-nfsv4-flexfiles-v2-proxy-server`)

Comments from IETF 122&ndash;124 addressed through revisions -04..-06.
**Requesting Call for Adoption at this meeting.**

---

<!-- Slide role: CONTENT
     Must-deliver:
     Two drafts today because that's how they were authored.
     Whether they stay two or fold into one is the structure
     question the WG will answer (slides 24-27).  Adoption does not
     lock the shape. -->
# Time to adopt

Two drafts today &mdash; folding into one is the **structure question above**.  Adoption does not lock the shape.

- [`draft-haynes-nfsv4-flexfiles-v2`](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2/)
- [`draft-haynes-nfsv4-flexfiles-v2-proxy-server`](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2-proxy-server/)

---

<!-- Slide role: SEPARATOR (Backups) -->
<!-- _class: big -->
# Backups

---

<!-- Slide role: CONTENT
     Must-deliver:
     CAS trace for the hardest sub-shard case (two writers, same
     4 KiB block, 1 KiB halves).  30/30 validated.  Retry-loop
     backoff/fairness under sustained contention is an open normative
     item - mention only if asked. -->
# Backup: concurrent writers &mdash; full CAS trace

Two writers, *same* 4 KiB block, 1 KiB halves (the hardest sub-shard RMW case):

```
   Writer A (SA)                     Writer B (SB)                    DS state
     |--CHUNK_WRITE(off=0, A)------------------------------------->  EMPTY -> PENDING(SA)
     |<-OK                              |
     |                                  |--CHUNK_WRITE(off=0, B)-->  PENDING(SA), SB != SA
     |                                  |<-NFS4ERR_DELAY
     |--CHUNK_FINALIZE(off=0)---------------------------------------> PENDING(SA) -> FINALIZED(SA)
     |--CHUNK_COMMIT(off=0)-----------------------------------------> FINALIZED(SA) -> COMMITTED(SA)
     |                                  |--CHUNK_READ(off=0)------->  returns bytes(A)
     |                                  |  (re-encode B's half over A's)
     |                                  |--CHUNK_WRITE(off=0, A|B, guard)-> guard matches; PENDING(SB)
     |                                  |--FINALIZE -> COMMIT ------> COMMITTED(SB)
```

`chunk_guard4` CAS at write time: writer presents the `{gen, client}` it read; DS compare-and-swaps.  Mismatch &rarr; `NFS4ERR_DELAY`, client retries read-merge-rewrite.  Validated 30/30.

**Known open item:** no normative backoff/fairness rule for the retry loop under sustained contention.  Candidate text exists; WG input welcome.

---

<!-- Slide role: CONTENT
     Must-deliver:
     At 1 MB, RS beats striping baseline because 6 RPCs beat 10 -
     NOT because encoding is free.  Defensible claim: encoding
     compute is not the limiter; fan-out shape and bytes are. -->
# Backup: the 1 MB comparison, with bytes on the wire

| Encoding | Write median | Payload on wire | RPC fan-out |
|---|---:|---:|---:|
| Plain mirror | 116 ms | replica &times; 1 MB | replica count |
| Stripe 10+0 | 125 ms | 1.0 MB | 10 |
| RS 4+2 | 113 ms | 1.5 MB | 6 |
| Mojette-sys 4+2 | 113 ms | 1.5 MB | 6 |

At 1 MB, encode compute is fully absorbed inside the fan-out latency window; RS/Mojette medians land below the striping baseline **because six RPCs beat ten on this topology**, not because encoding is free.  The defensible claim: **encoding compute is not the limiter**; fan-out shape dominates small sizes, bytes dominate large ones.

At 4 KB: stripe adds +8 ms over plain (fan-out alone); RS adds +14 ms over stripe (encode + 2 parity RPCs).

---

<!-- Slide role: CONTENT
     Must-deliver:
     Plain has zero failure tolerance; every EC row survives 2 losses.
     Wire bytes tell the true story: at 1 MB Moj-sys 8+2 moves 1.25 MB
     in 105 ms (11.9 KB/ms) vs plain's 1.0 MB in 116 ms (8.6 KB/ms) -
     EC does more system work per ms and delivers durability on top. -->
<!-- _class: "tight dense" -->
# Backup: durability + wire throughput

| Size | Plain | RS 4+2 | Moj-sys 4+2 | RS 8+2 | Moj-sys 8+2 |
|---|---:|---:|---:|---:|---:|
| 4 KB | 26 ms | 48 ms | 46 ms | 51 ms | 50 ms |
| 64 KB | 33 ms | 54 ms | 53 ms | 57 ms | 56 ms |
| 256 KB | 49 ms | 69 ms | 66 ms | 71 ms | 67 ms |
| 1 MB | 116 ms | 113 ms | 113 ms | 110 ms | 105 ms |
| **tolerates** | **0 losses** | **2 losses** | **2 losses** | **2 losses** | **2 losses** |

**At 1 MB, wire bytes moved per ms:**

| Encoding | User | Wire | ms | KB/ms | Tolerates |
|---|---:|---:|---:|---:|---:|
| Plain | 1.00 MB | 1.00 MB | 116 | 8.6 | 0 |
| RS 4+2 | 1.00 MB | 1.50 MB | 113 | 13.3 | 2 |
| Moj-sys 4+2 | 1.00 MB | 1.50 MB | 113 | 13.3 | 2 |
| RS 8+2 | 1.00 MB | 1.25 MB | 110 | 11.4 | 2 |
| Moj-sys 8+2 | 1.00 MB | 1.25 MB | 105 | 11.9 | 2 |

---

<!-- Slide role: CONTENT
     Must-deliver:
     Full realnet numbers.  6-8x write penalty across every size.
     Per-file floor at ~530 ms.  C variants within ~10% of each
     other - DS fan-out count is in the noise on this topology. -->
<!-- _class: "tight dense" -->
# Backup: PS realnet tables (full)

Write median (ms): Linux client &rarr; PS &rarr; MDS + 10 DSes

| Size | C-1DS | C-4mir | C-FFv2 | B (PS EC) | B vs C-1DS |
|---|---:|---:|---:|---:|---:|
| 4 KB | 70 | 64 | 66 | 528 | 8x |
| 64 KB | 74 | 74 | 68 | 539 | 7x |
| 1 MB | 93 | 85 | 82 | 600 | 6.5x |
| 4 MB | 123 | 125 | 122 | 836 | 6.8x |
| 16 MB | 284 | 269 | 277 | 1734 | 6x |

Read median (ms):

| Size | C-1DS | B (PS EC) | ratio |
|---|---:|---:|---:|
| 4 KB | 42 | 165 | 4x |
| 1 MB | 70 | 198 | 2.8x |
| 16 MB | 309 | 476 | 1.5x |

---

<!-- Slide role: CONTENT
     Must-deliver:
     Reading the PS realnet tables:
     C variants track each other - MDS-inband path dominates the C
     side.  DS fan-out count is in the noise on this topology.  The
     528-558 ms near-flat 4 KB-256 KB write cost is a per-file
     lifecycle floor: LAYOUTGET + encode setup + (k+m) fan-out +
     FINALIZE + COMMIT + LAYOUTRETURN, all paid per file, regardless
     of payload. -->
# Backup: PS realnet &mdash; what the tables say

- C variants within ~10% of each other at every size &mdash; the MDS-inband path dominates
- DS fan-out count is in the noise on this topology
- The 528&ndash;558 ms near-flat 4 KB&ndash;256 KB write cost is per-file lifecycle: LAYOUTGET, encode setup, (k+m) fan-out, FINALIZE, COMMIT, LAYOUTRETURN

---

<!-- Slide role: CONTENT
     Must-deliver:
     90/9/1 workload split parameterizes the requirements.  This is
     ONE vendor's observed mix; WG input on representativeness.
     If your workloads differ, say so on the list. -->
# Backup: workload classes the requirements derive from

| Workload class | Observed share&dagger; | What it needs from the layout |
|---|---:|---|
| Single writer + many readers | 90% | low-latency degraded reads; per-reader scaling |
| Multi-writer, no sustained contention | 9% | per-stateid admission without DLM; sub-stripe RMW |
| HPC disjoint regions | 1% | scale-out per-rank fan-out, throughput floor |
| In-place mutation (DBs, journaled FS) | &mdash; | per-page overwrites without metadata-commit storms |
| Streaming append (logs, time-series) | &mdash; | per-append cost flat as rate grows |

&dagger; **One vendor's observed deployment mix.**  WG input sought on representativeness &mdash; these shares parameterize the requirements, so if your deployments differ, say so on the list.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Split forces mirror side to either adopt v2 admission (conceding
     the machinery is shared) or stay on v1 uid-fencing (giving up
     modern control).  Same table read the other way: the argument
     for extracting shared machinery into a substrate document. -->
# Backup: what a split costs the mirror side

| Primitive | What the split costs |
|---|---|
| `TRUST_STATEID` / `REVOKE_STATEID` / `BULK_REVOKE_STATEID` | The mirror side either **adopts** v2's revoke-now (conceding the machinery is shared) or **falls back** to v1 uid-fencing (giving up modern admission control). |
| Layout-stateid lifecycle | Shared by all pNFS families; but each layout type needs its own spec stanza, IANA assignment, kernel parser.  Two types vs one is a real ongoing cost. |

This table is the compact form of the sharing argument &mdash; it is also, read the other way, the argument for extracting the shared machinery into a substrate document.  Both readings are legitimate; that is precisely the structure question.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Per-inode metadata: ~10 KB per 1 MB file at 4 KB chunks.
     ONE chunk_store per inode regardless of writer count.  Overhead
     scales with FILES, not concurrent writers.  A superblock is the
     migration unit. -->
# Backup: reffs backends detail

**POSIX + XFS** &mdash; sequential-append `ino_<N>.dat` per inode + 40 B/block records in `<state_dir>/chunks/<ino>.meta` (write-temp / fdatasync / rename).  FTL-friendly sequential access at chunk granularity.

**RocksDB LSM** &mdash; same `.dat` files for bulk data; chunk metadata as `chk:<ino>:<offset>` keys, WAL + sync, WriteBatch coalescing multi-block compounds.  Compaction is the design point, not a pathology.

| Axis | RAM | POSIX | RocksDB |
|---|:--:|:--:|:--:|
| Metadata (inode, dir, layout, chunk) | y | y | y |
| Data (file bytes) | y | y | (POSIX `.dat`) |

Per-inode metadata cost: 256 blocks &times; 40 B = ~10 KB per 1 MB file at 4 KB chunks.  One `chunk_store` per inode **regardless of writer count** &mdash; overhead scales with files, not with concurrent writers.

A superblock is a migration unit: `tar` the `sb_<id>/` directory and move it.
