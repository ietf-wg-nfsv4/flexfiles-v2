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
XOR -- the additive group of GF(2)^W where W is the element width
in bits.  Encoders and decoders MUST use XOR; modular integer
addition is not equivalent and is not interoperable.  XOR has no
carry chain, is its own inverse (so the residual subtraction in
reconstruction is identical to the forward accumulation), and
scales straightforwardly to wider SIMD lanes (NEON, SSE, AVX, AVX-512)
without requiring multiplicative Galois field operations.  The
element width W is an implementation choice; 64-bit elements are
the conventional choice and align well with NEON, SSE2, and AVX2
vector widths.

## Grid Structure

Data is arranged as a P x Q grid of unsigned integer elements,
where P is the number of columns and Q is the number of rows.
For k data shards of S bytes each with W-byte elements:

~~~
P = S / W       (columns per row)
Q = k           (rows = data shards)
~~~

## Directions

A direction is a pair of coprime integers (p_i, q_i).  Implementations
SHOULD use q_i = 1 for all directions {{PARREIN}}.  For n = k + m total
shards, n directions are generated with non-zero p values symmetric
around zero:

- For n = 4: p = {-2, -1, 1, 2}
- For n = 6: p = {-3, -2, -1, 1, 2, 3}

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

Reconstruction is possible if and only if the Katz criterion
{{KATZ}} holds:

~~~
SUM(i=1..n) |q_i| >= Q    OR    SUM(i=1..n) |p_i| >= P
~~~

When all q_i = 1, the q-sum simplifies to n >= Q.

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

Reconstruction cost is O(m * k) -- a fundamental advantage over RS
at wide geometries (k >= 8).

## Non-Systematic Mojette

In the non-systematic form (FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC),
all k + m shards are projections.  Every read requires the full
inverse transform.  This provides constant performance regardless of
failure count, but at higher baseline read cost than systematic.

## Mojette Shard Sizes

Unlike RS, Mojette parity shard sizes vary by direction:

| Direction (p, q) | Bins (B) for P=512, Q=4 | Size (bytes, 64-bit elements) |
|---
| (-3, 1) | 521 | 4168 |
| (-2, 1) | 518 | 4144 |
| (-1, 1) | 515 | 4120 |
| (1, 1) | 515 | 4120 |
| (2, 1) | 518 | 4144 |
| (3, 1) | 521 | 4168 |
{: title="Mojette projection sizes for 4+2, 4KB shards, 64-bit elements"}

When using CHUNK operations, the chunk_size is a nominal stride; the
last chunk in a parity shard MAY be shorter than the stride.

# IANA Considerations

This document registers the following values in the "Flexible
File Version 2 Layout Type Encoding Type Registry" established
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
