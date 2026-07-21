---
title: Mojette Transform Encoding for the Flexible File Version 2 Layout Type
abbrev: FFv2 Mojette
docname: draft-haynes-nfsv4-flexfiles-v2-mojette-latest
category: std
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: [pNFS, flexfiles, erasure coding, Mojette]

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping, comments]

author:
 -
    ins: T. Haynes
    name: Thomas Haynes
    organization: Hammerspace
    email: loghyr@gmail.com

normative:
  RFC4506:
  RFC5661:
  RFC8881:
  I-D.haynes-nfsv4-flexfiles-v2-requirements:
  I-D.haynes-nfsv4-flexfiles-v2-chunks:
  I-D.haynes-nfsv4-flexfiles-v2-encoding-registry:

informative:
  PARREIN:
    title: "Multiple Description Coding Using Exact Discrete Radon Transform"
    author:
      - name: B. Parrein
      - name: N. Normand
      - name: J.-P. Guedon
    date: 2001
    seriesinfo:
      IEEE: "Data Compression Conference (DCC)"
  NORMAND:
    title: "A Geometry Driven Reconstruction Algorithm for the Mojette Transform"
    author:
      - name: N. Normand
      - name: A. Kingston
      - name: P. Evenou
    date: 2006
    seriesinfo:
      LNCS: "4245, pp. 122-133, DGCI 2006"
  KATZ:
    title: "Questions of Uniqueness and Resolution in Reconstruction from Projections"
    author:
      - name: M. Katz
    date: 1978
    seriesinfo:
      Springer: ""

--- abstract

This document specifies the Mojette Transform encoding for use
with the Flexible File Version 2 Layout Type in both systematic
(FFV2_ENCODING_MOJETTE_SYSTEMATIC, value 2) and non-systematic
(FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC, value 3) forms.  The
transform is based on discrete geometry: 1D projections of a 2D
grid along selected directions.  Reconstruction is possible when
the Katz criterion holds.  Interoperability parameters (bin
convention, direction selection, element operation) are pinned
to what two implementations MUST agree on.

--- note_Note_to_Readers

Discussion of this draft takes place on the NFSv4 working group
mailing list (nfsv4@ietf.org), which is archived at
[](https://mailarchive.ietf.org/arch/search/?email_list=nfsv4).
Source code and issues list can be found at
[](https://github.com/ietf-wg-nfsv4/flexfiles-v2).

Working Group information can be found at
[](https://github.com/ietf-wg-nfsv4).

--- middle

# Introduction

The Flexible File Version 2 Layout Type
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}} defines an
encoding-method-agnostic protocol surface.  The Metadata Server
negotiates a (k, m) erasure-coding geometry via the Erasure
Coding Type Registry
{{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}, and
encoding-capable clients drive the CHUNK operations
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}} to write and read
encoded shards to storage devices.

This document specifies the Mojette Transform encoding.  The
transform operates on a 2D grid of fixed-width XOR-combined
elements, computing 1D projections along selected directions.
Given enough projections, the original grid can be
reconstructed exactly.  The Mojette Transform is registered
under two forms:

- FFV2_ENCODING_MOJETTE_SYSTEMATIC (value 2): the first k
  shards are the original data rows; the remaining m shards
  are projections.  Healthy reads require no decoding.
- FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC (value 3): all k+m
  shards are projections.  Every read requires the full
  inverse transform.

The unifying property is the Katz reconstruction criterion:
given a set of directions whose absolute-value sum meets the
grid dimension, the original data is recoverable.

# Requirements Language

{::boilerplate bcp14-tagged}

# Definitions

The following terms are used with meanings defined in
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}:

- data server (DS), metadata server (MDS)
- encoding, stripe, shard
- k (number of data shards), m (number of parity shards)

Local terms defined in this document:

Mojette Transform:
:  An erasure-coding transform that computes 1D XOR
   projections of a 2D grid along selected discrete geometric
   directions.

Direction:
:  A pair of coprime integers (p, q) specifying a discrete
   line through the grid.

Projection:
:  The sequence of bins resulting from applying a direction to
   the grid; each bin is an XOR of all grid cells intersected
   by the corresponding line.

Bin:
:  A single element of a projection, corresponding to one
   discrete line through the grid.

Katz criterion:
:  A necessary and sufficient condition for reconstructing the
   original grid from a set of projections: the absolute-value
   sum of direction p-components (or q-components) meets or
   exceeds the corresponding grid dimension.

Systematic form:
:  A variant in which the first k shards are the original data
   rows and the remaining m shards are projections.

Non-systematic form:
:  A variant in which all k+m shards are projections; the
   original data is never stored directly.

# Mojette Transform Encoding

## Overview

The Mojette Transform is an erasure coding technique based on discrete
geometry rather than algebraic field operations.  It computes 1D
projections of a 2D grid along selected directions.  Given enough
projections, the original grid can be reconstructed exactly.

The transform operates on fixed-width words combined with bitwise
XOR -- the additive group of `(GF(2))^(W*8)` where W is the
element width in bytes.  Encoders and decoders MUST use XOR;
modular integer addition is not equivalent and is not
interoperable.  XOR has no carry chain, is its own inverse (so
the residual subtraction in reconstruction is identical to the
forward accumulation), and scales straightforwardly to wider
SIMD lanes (NEON, SSE, AVX, AVX-512) without requiring
multiplicative Galois field operations.

For interoperability, this specification pins the element width
to `W = 8` bytes (64 bits) for both
FFV2_ENCODING_MOJETTE_SYSTEMATIC and
FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC in this revision.  All
implementations MUST use W = 8; a future revision (or a distinct
registered encoding type) may lift the fixed width, at which
point it becomes a wire-visible parameter.  Fixing W now
removes the interop hazard the review flagged (the same shard
input, XOR'd at W = 4 vs W = 8, produces different bin values
that appear "close but wrong" to a mismatched decoder).

## Grid Structure

Data is arranged as a P x Q grid of unsigned integer elements,
where P is the number of columns and Q is the number of rows.
For k data shards of S bytes each with W-byte elements:

~~~
P = S / W       (columns per row)
Q = k           (rows = data shards)
~~~

## Directions

A direction is a pair of coprime integers (p_i, q_i).  This
specification pins all directions to q_i = 1 for both Mojette
encoding types (systematic and non-systematic) in this
revision.  Non-unity q_i values may be introduced by a future
distinct registered encoding type.

For n = k + m total shards (Mojette non-systematic) or m parity
shards (Mojette systematic), the direction set is determined by
the following mandatory algorithm on the shard count N (N = n for
non-systematic, N = m for systematic):

~~~
If N is even (N = 2t):
    directions = { (p, 1) : p in {-t, -t+1, ..., -1, 1, 2, ..., t} }
    // Symmetric around zero; |directions| = 2t = N.
If N is odd (N = 2t + 1):
    directions = { (p, 1) : p in {-t, -t+1, ..., -1, 1, 2, ..., t, t+1} }
    // Asymmetric by including one additional positive magnitude
    // to make |directions| = 2t + 1 = N.
~~~

Direction slots are then sorted by `p_i` ascending (most-negative
p first, most-positive p last) to give the canonical direction
order.  The direction in slot i is used to compute the projection
for shard slot (k + i) in systematic form, or for shard slot i in
non-systematic form.  Examples:

- N = 4 (even): p = {-2, -1, 1, 2}
- N = 6 (even): p = {-3, -2, -1, 1, 2, 3}
- N = 3 (odd):  p = {-1, 1, 2}
- N = 5 (odd):  p = {-2, -1, 1, 2, 3}

Two implementations that follow this algorithm on the same N
generate identical direction sets in identical slot order and
therefore identical shard layouts.  Implementations MUST NOT
diverge from this algorithm (e.g., by using a different
tie-breaking rule for odd N) without registering a distinct
encoding type.

## Forward Transform (Encoding)

For each direction (p_i, q_i), the forward transform computes a 1D
projection.  Each bin XORs the grid elements that lie on a discrete
line through the grid.  This specification adopts the bin
convention of {{NORMAND}}: a grid cell at (row, col) maps to bin

~~~
b = row * p + col * q - off
~~~

where off is chosen so that the smallest reachable bin index is 0
(off = min over all (row, col) in [0, Q) x [0, P) of row * p + col * q).
All implementations MUST use this convention -- the alternative
"transposed" convention `b = col * p - row * q + off` produces a
different bin ordering and is not interoperable.

The full forward transform along direction (p, q) is then:

~~~
Projection(b, p, q) = XOR over all (row, col) where
                       row * p + col * q - off = b
                       of Grid[row][col]
~~~

The number of bins B in a projection is:

~~~
B(p, q, P, Q) = |p| * (Q - 1) + |q| * (P - 1) + 1
~~~

For q = 1, this simplifies to:

~~~
B = abs(p) * (Q - 1) + P
~~~

The byte size of the projection is B * W.

## Katz Reconstruction Criterion

Reconstruction from a set of `n` projections is possible if and
only if the Katz criterion {{KATZ}} holds over those `n`
projections:

~~~
SUM(i=1..n) |q_i| >= Q    OR    SUM(i=1..n) |p_i| >= P
~~~

With q_i = 1 pinned for every direction (see the Directions
section above), the q-sum simplifies to n >= Q.

For the non-systematic form, `n = k + m` and every direction
counts toward the criterion.  The criterion holds for the
initial encoding (design-time check on the direction set) and
must continue to hold after any losses; the surviving
projections must satisfy Katz over the same grid dimensions
(P, Q).

For the systematic form, the raw data rows act as
"projections at direction (p=0, q=1)": row `r` is `Grid[r]` and
contributes `q = 1` toward the q-sum of the Katz criterion.
For an arbitrary loss pattern with `r` data-row losses and `s`
parity-projection losses (with `r + s <= m`), the surviving set
comprises `k - r` data rows (each `q_i = 1`) and `m - s` parity
projections.  Decoding proceeds by:

1. Subtracting the contributions of the `k - r` surviving data
   rows from the `m - s` surviving parity projections (the
   "residual").
2. Applying the corner-peeling algorithm over the residual to
   recover the `r` missing rows.

Step 2 succeeds if and only if the Katz criterion holds over
the `m - s` residual projections against the `r x P` unknown
sub-grid.  Substituting: the criterion reduces to
`m - s >= r` (q-sum, since q_i = 1 for every parity direction
and the unknown-grid Q is r) OR the analogous p-sum condition
over the residual.  Because the mandatory direction algorithm
above generates `m` projections with distinct nonzero p values,
the p-sum condition also holds for any loss pattern with
`r + s <= m`; the systematic form therefore achieves MDS-like
recovery up to `m` combined data-row and parity-projection
losses.

## Inverse Transform (Decoding)

The choice of inverse algorithm is purely an implementer concern:
all correct inverses produce byte-identical plaintext from the same
shards and bin layout, so the choice has no on-the-wire impact.
Two well-known algorithms apply.

The corner-peeling algorithm:

1. Count how many unknown elements contribute to each bin.
2. Find any bin with exactly one contributor (singleton).
3. Recover the element, XOR it back through all projections.
4. Repeat until all elements are recovered.

Corner peeling runs in O(n * P * Q) and is the simplest correct
inverse.  Implementations MAY instead use the geometry-driven
inverse of {{NORMAND}}, which precomputes a recurrence over the
sorted projection slopes and walks each line once: it eliminates
the inner singleton search and runs substantially faster on the
parameter ranges typical of flexible file v2 layout deployments (high redundancy,
wide stripes), with no change to the shards or to the
reconstructed plaintext.

## Systematic Mojette

In the systematic form (FFV2_ENCODING_MOJETTE_SYSTEMATIC), the first
k shards are the original data rows and the remaining m shards are
projections.  Healthy reads require no decoding.

Reconstruction of missing data rows proceeds via the
corner-peeling algorithm of {{NORMAND}}:

1. Load available parity projections.
2. Subtract contributions of present data rows (residual).
3. Corner-peel the residual to recover missing rows.

Reconstruction cost is `O(m*k*P*Q)` grid ops (the peeling walk
touches each grid element in the r×P sub-grid once per
projection) -- a fundamental advantage over RS
at wide geometries (k >= 8), whose matrix-inversion cost is
`O(k^3)` in the shard dimension.

## Non-Systematic Mojette

In the non-systematic form (FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC),
all k + m shards are projections.  Every read requires the full
inverse transform.  This provides constant performance regardless of
failure count, but at higher baseline read cost than systematic.

## Mojette Shard Sizes and Layout

**Slot-to-direction mapping.**  The canonical shard layout for
Mojette is:

- Systematic (FFV2_ENCODING_MOJETTE_SYSTEMATIC): shard slots
  `0..k-1` carry the k data rows (row r in slot r); shard
  slots `k..k+m-1` carry the m parity projections in the
  canonical direction order defined in the Directions
  section above (direction slot i occupies shard slot
  `k + i`).
- Non-systematic (FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC): shard
  slots `0..k+m-1` carry the n = k + m parity projections in
  the canonical direction order (direction slot i occupies
  shard slot i).

**Bin ordering within a projection.**  Within a projection
shard the bins are serialized in ascending bin-index order
(bin 0 first, bin B-1 last), with no gap or header.  Each bin
value is `W = 8` bytes wide; the W-byte element is serialized
in big-endian byte order (the same order the data-row shards
present their W-byte grid elements in).

**Projection sizes.**  Unlike RS, Mojette parity shard sizes
vary by direction:

| Direction (p, q) | Bins (B) for P=512, Q=4 | Size (bytes, W=8) |
|---
| (-3, 1) | 521 | 4168 |
| (-2, 1) | 518 | 4144 |
| (-1, 1) | 515 | 4120 |
| (1, 1) | 515 | 4120 |
| (2, 1) | 518 | 4144 |
| (3, 1) | 521 | 4168 |
{: title="Mojette projection sizes for 4+2, 4KB shards, W=8"}

**Chunk sizing for variable-length projections.**  When a
projection shard is written via `CHUNK_WRITE` /
`CHUNK_FINALIZE` / `CHUNK_COMMIT`, the shard is divided into
chunks by the following mapping.  Let `shard_bytes = B * W` be
the projection shard's total byte size (where B is the number
of bins from the B formula above, applied to the shard's
direction (p, q) and the grid dimensions (P, Q)):

- `num_chunks = ceil(shard_bytes / chunk_size)`
- Chunk `j` (for j = 0..num_chunks-1) covers the shard byte
  range `[j * chunk_size, min((j+1) * chunk_size, shard_bytes))`.
- The final chunk (chunk `num_chunks - 1`) MAY be shorter than
  `chunk_size` if `shard_bytes` is not a multiple of
  `chunk_size`; all other chunks are exactly `chunk_size`
  bytes.

The `chunk_size` value is a per-mirror parameter and does not
vary across the parity projections of a single file, even
though the shard sizes vary.  For a file with parity
projections of sizes `S_i = B_i * W`, the number of chunks per
shard is `ceil(S_i / chunk_size)` per shard; a reader that
requests chunk offset `>= S_i` on shard i receives
`NFS4ERR_PAYLOAD_LOST` (per {{I-D.haynes-nfsv4-flexfiles-v2-chunks}})
with a short read reporting the shard's true byte length.

# IANA Considerations

This document registers the following values in the "Flexible
File Version 2 Layout Type Erasure Coding Type Registry" established
by {{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}:

| Encoding Type Name | Value | RFC | How | Minor Versions |
| ---
| FFV2_ENCODING_MOJETTE_SYSTEMATIC | 2 | RFCTBD10 | L | 2 |
| FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC | 3 | RFCTBD10 | L | 2 |

# Security Considerations

The chunk-level security considerations of
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}} apply to any encoding
registered in the Erasure Coding Type Registry, including this
one.

The Mojette Transform is not a cryptographic construction.  An
adversary who can observe or modify k or more shards can recover
or corrupt the original data.  Confidentiality and integrity of
shards in flight are provided by the transport security
mechanisms defined in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}},
not by the encoding itself.

# Acknowledgments
{:numbered="false"}

The Mojette Transform encoding specification in this document --
including the algebra, the bin convention, the projection
sizing, and the reconstruction algorithms -- draws on the work
of Nicolas Normand, Benoit Parrein, and the discrete geometry
research group at the University of Nantes, and was contributed
to the Flexible File Version 2 effort by Pierre Evenou.

For general acknowledgments, see the Acknowledgments section
of {{I-D.haynes-nfsv4-flexfiles-v2-requirements}}.

--- back
