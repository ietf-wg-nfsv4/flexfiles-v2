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
  section.tight table { font-size: 0.78em; }
  section table { margin-inline: auto; }
---

<!-- _footer: "" -->
<!-- Slide role: SEPARATOR (title) -->
<!-- _class: big -->

# Flex Files v2 + Proxy Server

## IETF 126, NFSv4 WG &mdash; status, structure, adoption

[draft-haynes-nfsv4-flexfiles-v2](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2/)
[draft-haynes-nfsv4-flexfiles-v2-proxy-server](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2-proxy-server/)

&nbsp;

Tom Haynes &mdash; @@DATE@@

---

<!-- Slide role: CONTENT
     Must-deliver:
     Four headline advancements the deck will unpack.  Rapid
     prototyping (reffs) proves the design in code.  New trust
     model (TRUST_STATEID) replaces v1's synthetic uid/gid fencing
     with revoke-now admission.  Proxy Server (PS) keeps unmodified
     clients as participants.  Drafts are complete and ready for
     review + adoption - the concrete procedural ask.  Each has its
     own slide later - this one sets the agenda. -->
# Major advancements

- **Rapid prototyping in userspace** &mdash; reffs, the only implementation to date
- **New trust model** &mdash; `TRUST_STATEID` revoke-now admission
- **Proxy Server** &mdash; unmodified clients participate
- **Drafts complete** &mdash; ready for review and adoption

---

<!-- Slide role: CONTENT
     Must-deliver:
     Three ops replace v1's synthetic uid/gid fencing.  Every DS in a
     layout holds an admission-table entry per stateid.  MDS remains
     the single state authority; no consensus, no Distributed Lock
     Manager (DLM). -->
# Trust-stateid: the revoke-now mechanism

| Op | When the MDS sends it | What it does |
|---|---|---|
| `TRUST_STATEID` | Layout issued to client | Push stateid to every DS in the layout *before* client I/O.  DS records it in an admission table; I/O with this stateid &rarr; accepted, any other &rarr; `NFS4ERR_BAD_STATEID`. |
| `REVOKE_STATEID` | Layout returned, recalled, or reissued | Clear the stateid from each DS's table.  Next write from that client **fails closed**. |
| `BULK_REVOKE_STATEID` | Client lease expires | One per affected DS; clears every entry for that client at once. |

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

**Reconstruction:** 120/120 within-tolerance recoveries byte-exact; 20/20 over-tolerance cells **fail cleanly** &mdash; zero silent bad data.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Surfacing the MTI gap ourselves converts the sharpest interop
     objection into an agenda item we control.  The draft has a
     registry but no MTI - two conforming implementations could
     share zero encodings.  Proposal: RS-Vandermonde as MTI for
     encoding-capable implementations; everything else optional.
     Also carried as item 1 on "What remains to settle". -->
# Encodings: the MTI gap

- The draft defines a encoding **registry**
- The draft defines **no mandatory-to-implement** encoding
- Two conforming implementations could share **zero encodings**
- **Proposal:** RS-Vandermonde as MTI for encoding-capable implementations
- Everything else optional
- WG input sought

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

(3-host bench, kernel client):

| Path | 4 KB write | 16 MB write |
|---|---:|---:|
| MDS-inband (no client EC) | 70 ms | 284 ms |
| **Via PS (EC translation)** | **528 ms** | **1734 ms** |

**The read:** translation costs 6&ndash;8x on writes, and the ~530 ms floor is **per-file lifecycle cost** &mdash; small-file workloads pay it per file.  MDS-inband is fast but serializes data through the MDS, giving up pNFS scaling.  **This is the quantified incentive for native client-side encoding support** &mdash; and the quantified price of compatibility until it exists.

---

<!-- Slide role: SEPARATOR (Implementation Status) -->
<!-- _class: big -->
# Implementation Status

---

<!-- Slide role: CONTENT
     Must-deliver:
     The only implementation of FFv2 to date, in userspace.
     Prototyping, not production.  Two backends on ONE wire format -
     the protocol doesn't dictate on-disk layout.  Shipped: repair,
     PS role.  Missing: a kernel client, and any other independent
     implementation - that's an explicit ask. -->
<!-- _class: "tight dense" -->
# Implementation status: reffs

The only implementation of FFv2 to date, in userspace, built to answer *"did the design survive contact with code?"*

| **What it is** | **What it covers** |
|---|---|
| User-space C | MDS + DS roles |
| Linux + FreeBSD + macOS | FFv1 + FFv2 layouts |
| **Prototyping, not production** | All CHUNK + trust-stateid ops |
|  | PS role |
|  | `ec_demo` userspace client |

- **Shipped:** wire-level single-shard reconstruction (`CHUNK_WRITE_REPAIR` + `CHUNK_REPAIRED`, 80-cell bench)
- **In progress:** PS-driven repair autopilot; cross-PS coherence for NFSv3 clients (known gap, fix shape documented)

**What does not yet exist:** a kernel client; an implementation outside the reffs/ec_demo family.  We are explicit about this &mdash; it is one of the asks.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Two very different on-disk layouts against the SAME wire
     protocol.  POSIX + XFS keeps chunks in sidecar files per inode;
     RocksDB LSM keeps them as keys in a log-structured store.  The
     claim: the protocol does not dictate on-disk layout - operators
     can pick the store that fits their media.  Full backend detail
     is in the backup slide. -->
# Two storage backends on one wire format

- **POSIX + XFS** &mdash; sidecar files per inode
- **RocksDB LSM** &mdash; chunks as keys in a log-structured store
- Same wire protocol on both
- **The claim:** the protocol does not dictate on-disk layout

---

<!-- Slide role: SEPARATOR (The structure question) -->
<!-- _class: big -->
# The structure question

---

<!-- Slide role: CONTENT
     Must-deliver:
     216 pages is on the large side for IESG review; usual expectation
     is <=120 per document.  231 is the raw count; 216 after stripping
     non-published WG-concern sections.  PS is already split at 62
     pages.  This slide is the NUMERICAL case for going multi-doc -
     independent of any philosophical position on Option A vs B. -->
# Page-count reality

|  | Current | IESG-review target |
|---|---:|---:|
| **FFv2 draft** | **216 pages** (231 raw &minus; non-published sections) | &le; 120 / doc |
| PS draft (already split) | 62 pages | &le; 120 / doc |

---

<!-- Slide role: CONTENT
     Must-deliver:
     Seven documents, none over ~90 pages.  Doc 4 (chunk substrate) is
     the anchor - ~4300 md lines of system model + chunk data
     structures + 11 CHUNK ops is where the page count lives.  Docs 6
     and 7 kept separate on purpose: encoding review goes where the
     expertise lives (FECFRAME reviewers, coding-theory folks) and any
     IPR clarification on a specific encoding does NOT block the
     framework or other encodings.  Doc 5 is the entry point for future
     encodings through the registry. -->
<!-- _class: "tight dense" -->
# Proposed multi-document breakdown

| # | Document | Est. pages |
|---|---|---:|
| 1 | Requirements & rationale | ~17 |
| 2 | Trusted-stateid control protocol | ~31 |
| 3 | FFv2 layout type | ~60 |
| 4 | **Chunk substrate & CHUNK operations** | **~90** |
| 5 | Encoding framework & registry | ~8 |
| 6 | RS-Vandermonde encoding | ~5 |
| 7 | Mojette encoding | ~5 |
| 8 | Proxy Server (already split) | 62 |

**Doc 4 is the anchor** &mdash; ~4300 md lines of chunk-substrate machinery is where the page count actually lives.  Extracting it drops Doc 3 (FFv2 layout) to ~60 pages.

Docs 6 and 7 kept separate: encoding review goes where the expertise lives; any IPR clarification on a specific encoding does not block the others.

---

<!-- Slide role: CONTENT
     Must-deliver:
     Three asks: (1) MTI - RS-Vandermonde as MTI for encoding-capable
     implementations closes the interop gap.  (2) Registry policy:
     authors propose Specification Required with Designated Expert
     per RFC 8126 - a position, not a question.  (3) Who implements,
     who reviews, on what clock - the energy-mapping question.
     Items 1 and 3 are questions; item 2 is a stated position ready
     to be defended. -->
# What we ask of the WG

**Read** &mdash; if you read nothing else: &sect;12 (system model + guarantees), &sect;8.11 (encoding negotiation), &sect;24&ndash;25 (chunk structures + ops).  The PS draft: &sect;4&ndash;6.

**Answer, on the list:**

1. **MTI.**  Should RS-Vandermonde be mandatory-to-implement for encoding-capable implementations?
2. **Registry policy.**  Specification Required with Designated Expert.
3. **Who will implement** &mdash; client, DS, or PS side &mdash; and on what horizon?  Who will review deeply?

---

<!-- Slide role: SEPARATOR (Adoption) -->
<!-- _class: big -->
# Call for Adoption

---

<!-- Slide role: CONTENT
     Must-deliver:
     Side-by-side: what was missing at IETF 124, what is present at
     IETF 126.  Each row is a gap that has closed since IETF 124.
     Don't apologize for the wait - frame as work that had to happen.
     End with: IETF 122-124 comments addressed through -04..-06, and
     the concrete procedural ask (Call for Adoption at this meeting). -->
<!-- _class: tight -->
# Why now &mdash; what changed since IETF 124

|  | IETF 124 | IETF 126 |
|---|---|---|
| Draft complete | **X** | -06 current; -07 planned after WG feedback |
| Use cases | underspecified | identified (&sect;2, &sect;3); operator workloads |
| Requirements | not framed | framed; workload-driven |
| Implementation experience | none | reffs (userspace prototype) |
| Legacy-client story | none | PS draft (`draft-haynes-nfsv4-flexfiles-v2-proxy-server`) |

Comments from IETF 122&ndash;124 addressed through revisions -04..-06.
**Requesting Call for Adoption at this meeting.**

---

<!-- Slide role: CONTENT
     Must-deliver:
     The concrete ask: adoption of both drafts.  The sequencing
     question the room needs to weigh: adopt-then-split preserves
     momentum but leaves the split as post-adoption work; split-
     then-adopt commits to the multi-doc shape before adoption.
     Authors don't push a preference on order; the room's view is
     the load-bearing signal. -->
# Time to adopt

- [`draft-haynes-nfsv4-flexfiles-v2`](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2/)
- [`draft-haynes-nfsv4-flexfiles-v2-proxy-server`](https://datatracker.ietf.org/doc/draft-haynes-nfsv4-flexfiles-v2-proxy-server/)

**Do we want to adopt and then split?**

**Or do we split and then adopt?**

---

<!-- Slide role: SEPARATOR (Backups) -->
<!-- _class: big -->
# Backups

---

<!-- Slide role: CONTENT
     Must-deliver:
     At 1 MB, RS/Moj 4+2 beats striping baseline because 6 RPCs beat
     10; 8+2 beats it at fan-out parity because the extra 25%
     payload absorbs under RTT.  Defensible claim: encoding compute
     is not the limiter; fan-out shape and bytes-in-flight are. -->
# Backup: the 1 MB comparison, with bytes on the wire

| Encoding | Write median | Payload on wire | RPC fan-out |
|---|---:|---:|---:|
| Plain mirror | 116 ms | replica &times; 1 MB | replica count |
| Stripe 10+0 | 125 ms | 1.0 MB | 10 |
| RS 4+2 | 113 ms | 1.5 MB | 6 |
| Mojette-sys 4+2 | 113 ms | 1.5 MB | 6 |
| RS 8+2 | 110 ms | 1.25 MB | 10 |
| Mojette-sys 8+2 | 105 ms | 1.25 MB | 10 |

At 1 MB, encode compute is fully absorbed inside the fan-out latency window.  RS/Moj 4+2 (6 RPCs, 1.5 MB wire) land below the striping baseline **because six RPCs beat ten on this topology**; 8+2 (10 RPCs, 1.25 MB wire) beats striping at fan-out parity because the extra 25% payload absorbs under RTT.  The defensible claim: **encoding compute is not the limiter**; fan-out shape and bytes-in-flight dominate the curve.

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
     Read side: small sizes EC pays ~2x plain (RTT dominates).  At
     256 KB gap narrows to 25-30%.  At 1 MB EC BEATS plain -
     RS/Moj-sys 4+2 at ~80 ms vs plain 95 ms (~16% faster); 8+2 at
     73 ms (~23% faster).  Parallel reads of k shards beat one
     serial read of the full payload.  Same source as write matrix:
     n=5 medians, dreamer NEON v2, post-fix. -->
<!-- _class: "tight dense" -->
# Backup: read side, full matrix

Median read, single client, 5 runs per cell:

| Size | Plain | RS 4+2 | Moj-sys 4+2 | RS 8+2 | Moj-sys 8+2 |
|---|---:|---:|---:|---:|---:|
| 4 KB | 11 ms | 26 ms | 26 ms | 26 ms | 26 ms |
| 64 KB | 17 ms | 30 ms | 31 ms | 31 ms | 31 ms |
| 256 KB | 32 ms | 41 ms | 42 ms | 40 ms | 39 ms |
| 1 MB | 95 ms | 80 ms | 79 ms | 73 ms | 73 ms |

**At 1 MB, EC reads beat plain:** parallel reads of `k` shards (each ~payload/`k` bytes) beat one serial read of the full payload.  Moj-sys 8+2 lands **23% below plain** at 1 MB.
