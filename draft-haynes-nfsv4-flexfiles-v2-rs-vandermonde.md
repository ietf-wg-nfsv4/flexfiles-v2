---
title: Reed-Solomon Vandermonde Encoding for the Flexible File Version 2 Layout Type
abbrev: FFv2 RS-Vandermonde
docname: draft-haynes-nfsv4-flexfiles-v2-rs-vandermonde-latest
category: std
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: [pNFS, flexfiles, erasure coding, Reed-Solomon]

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping, comments]

venue:
  group: Network File System Version 4
  type: Working Group
  mail: nfsv4@ietf.org
  arch: https://mailarchive.ietf.org/arch/browse/nfsv4/
  github: ietf-wg-nfsv4/flexfiles-v2
  latest: https://ietf-wg-nfsv4.github.io/flexfiles-v2/draft-haynes-nfsv4-flexfiles-v2-rs-vandermonde.html

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
  Plank97:
    title: A Tutorial on Reed-Solomon Coding for Fault-Tolerance in RAID-like Systems
    target: http://web.eecs.utk.edu/~jplank/plank/papers/CS-96-332.htm
    author:
    - ins: J. Plank
      name: J. Plank
    date: September 1997

--- abstract

This document specifies the Reed-Solomon Vandermonde encoding
(FFV2_ENCODING_RS_VANDERMONDE, value 4) for use with the
Flexible File Version 2 Layout Type.  The construction is
classical: a Vandermonde matrix over GF(2^8), normalized to a
systematic form.  For a (k+m, k) code, any k of the k+m
encoded shards suffice to reconstruct the original data.  This
document pins the interoperability parameters (irreducible
polynomial, primitive element, matrix normalization) that two
implementations MUST agree on to interoperate.

--- note_Note_to_Readers

This is an individual submission and does not reflect Working Group
consensus.  The "About This Document" section above has the current
discussion venue, latest rendering, and source location.

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

This document specifies the Reed-Solomon Vandermonde encoding
(FFV2_ENCODING_RS_VANDERMONDE, value 4).  The construction is
classical: a Vandermonde matrix over GF(2^8), normalized to a
systematic form (data shards pass through unchanged; only
parity is generated).  For a (k+m, k) code, any k of the k+m
encoded shards suffice to reconstruct the original data.  The
code tolerates the simultaneous loss of up to m shards.

This document defines the interoperability parameters
(irreducible polynomial, primitive element, matrix
normalization) that two implementations MUST agree on to
interoperate.

# Requirements Language

{::boilerplate bcp14-tagged}

# Definitions

The following terms are used with meanings defined in
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}:

- data server (DS), metadata server (MDS)
- encoding, stripe, shard
- k (number of data shards), m (number of parity shards)

Local terms defined in this document:

Vandermonde matrix:
:  A matrix in which each row is a geometric progression of the
   same base element, with a different base per row.

GF(2^8):
:  The Galois field with 256 elements, used for all encoding
   arithmetic in this document.

Systematic code:
:  An error-correcting code in which the original data shards
   appear unchanged as a subset of the encoded shards, in
   contrast to a non-systematic code in which all encoded shards
   are linear combinations of the data.

# Reed-Solomon Vandermonde Encoding

## Overview

Reed-Solomon (RS) codes are Maximum Distance Separable (MDS)
codes: for a (k+m, k) code, any k of the k+m encoded shards
suffice to recover the original data.  The code tolerates the
simultaneous loss of up to m shards.  {{Plank97}} is a tutorial
treatment of RS coding in RAID-like systems and is the
recommended background reading for implementers unfamiliar with
the construction used here.

## Galois Field Arithmetic

All RS operations are performed over GF(2^8), the Galois field
with 256 elements.  Each element is represented as a byte.

Irreducible Polynomial:
:  The field is constructed using the irreducible polynomial
x^8 + x^4 + x^3 + x^2 + 1 (0x11d in hexadecimal).  The primitive
element (generator) is g = 2, which has multiplicative order 255.

Addition:
:  Addition in GF(2^8) is bitwise XOR.

Multiplication:
:  Multiplication uses log/antilog tables.  For non-zero elements
a and b: a * b = exp(log(a) + log(b)), where the exp table is
doubled to 512 entries to avoid modular reduction on the index sum.

These are the classical constructions from Berlekamp (1968) and
Peterson & Weldon (1972).  The log/antilog table approach for GF(2^8)
multiplication predates all known patents on SIMD-accelerated GF
arithmetic.  Implementors considering SIMD acceleration of GF(2^8)
operations should be aware of US Patent 8,683,296 (StreamScale),
which covers certain SIMD-based GF multiplication techniques.

## Encoding Matrix

The systematic encoding matrix E has (k + m) rows and k columns.
The top k rows are always the k x k identity, so data shards pass
through unchanged.  The bottom m parity rows are chosen as
follows.

### At m = 1: single parity row

The single parity row is `[1, 1, ..., 1]`:

    E\[k\]\[j\] = 1    for j = 0, 1, ..., k-1

Encoded parity is the bitwise XOR of every data shard.  This
matches the P row of Linux md's RAID6 construction and the sole
parity row of FFV2_ENCODING_XOR_PARITY byte-for-byte; a receiver
that speaks either of those consumes RS_VANDERMONDE at m=1
without re-encoding.

### At m = 2: P + Q parity rows

The two parity rows are:

    E\[k\]\[j\]     = 1              for j = 0, 1, ..., k-1   (P row)
    E\[k+1\]\[j\]   = g^j            for j = 0, 1, ..., k-1   (Q row)

where g = 2 is the primitive element of GF(2^8) with polynomial
0x11d.  These are exactly the coefficients Linux md RAID6 uses
for its P and Q shards.  A receiver that speaks
FFV2_ENCODING_LINUX_MD_RAID at m <= 2 also consumes
RS_VANDERMONDE at m <= 2 byte-for-byte (and vice versa).

### At m >= 3: normalized Vandermonde bottom rows

The parity rows are the bottom m rows of a normalized
Vandermonde encoding matrix, constructed as follows.

1. Assign each of the k+m shards a distinct non-zero evaluation
   point in GF(2^8): shard i (for i = 0, 1, ..., k+m-1) is assigned
   the point alpha_i = i + 1.  This gives evaluation points
   1, 2, ..., k+m, all non-zero and distinct.  The value k+m MUST
   NOT exceed 255 so that all points fit in GF(2^8) \ {0}.

2. Construct a (k+m) x k Vandermonde matrix V where the row for
   shard i is the geometric progression of alpha_i:

       V\[i\]\[j\] = alpha_i^j = (i+1)^j    for j = 0, 1, ..., k-1

   Row i is (1, alpha_i, alpha_i^2, ..., alpha_i^(k-1)).  The
   exponent zero is defined as `x^0 = 1` for all `x` in GF(2^8),
   including x = 0 (this is the standard combinatorial
   convention; here `alpha_i` is never zero by step 1's
   construction, but the convention makes the V\[0\]\[0\] cell
   unambiguous).  Any k distinct rows form a k x k Vandermonde
   matrix on k distinct non-zero evaluation points, which is
   invertible over GF(2^8); this is the property that gives the
   code its Maximum Distance Separable (any k of k+m shards
   recover the data) guarantee.  The minimum useful geometry
   is `k >= 1` and `m >= 1` (`k = 0` gives no data and `m = 0`
   gives no redundancy); the maximum is bounded by `k + m <= 255`
   as stated in step 1.

3. Extract the top k x k sub-matrix T from V.  T is the Vandermonde
   on evaluation points alpha_0 = 1, alpha_1 = 2, ..., alpha_(k-1) = k.

4. Compute T_inv = T^(-1) using Gaussian elimination in GF(2^8).

5. Multiply: E = V * T_inv.  The result has an identity block on top
   (rows 0 through k-1) and the parity generation matrix P on the
   bottom (rows k through k+m-1).

The identity block makes the code systematic: data shards pass through
unchanged, and only the parity sub-matrix P is needed during encoding.
These bottom rows do not match any external encoding at m >= 3;
this encoding stands on its own at m >= 3.

## Encoding

Given k data shards, each of shard_len bytes, encoding produces m
parity shards, each also shard_len bytes:

~~~
For each byte position j in [0, shard_len):
  For each parity shard i in [0, m):
    parity[i][j] = sum over s in [0, k) of P[i][s] * data[s][j]
~~~

where the sum and product are in GF(2^8).  All shards (data and
parity) are the same size.

## Decoding

When one or more shards are lost (up to m), reconstruction proceeds
by matrix inversion:

1. Select k available shards (from the k+m total).

2. Form a k x k sub-matrix S of the encoding matrix E by selecting the
   rows corresponding to the available shards.

3. Compute S_inv = S^(-1) using Gaussian elimination in GF(2^8).

4. Multiply S_inv by the vector of available shard data at each byte
   position to recover the original k data shards.

5. If any parity shards are also missing, regenerate them by
   re-encoding from the recovered data shards.

The reconstruction cost is dominated by the matrix inversion, which
is O(k^3) in GF(2^8) multiplications.

## RS Interoperability Requirements

For two implementations of FFV2_ENCODING_RS_VANDERMONDE to
interoperate, they MUST agree on all of the following parameters.
Any deviation produces a different encoding matrix and renders
data unrecoverable by a different implementation.

- Irreducible polynomial: x^8 + x^4 + x^3 + x^2 + 1 (0x11d)
- Primitive element: g = 2
- Top k rows of E: the k x k identity matrix (systematic
  data-shard pass-through)
- At m = 1: parity row is `[1, 1, ..., 1]` (all-ones)
- At m = 2: parity rows are `[1, 1, ..., 1]` (P) and
  `[1, g, g^2, ..., g^(k-1)]` (Q) with g = 2 in GF(2^8)
- At m >= 3: evaluation points alpha_i = i + 1 for
  i = 0, 1, ..., k+m-1 (values 1 through k+m); Vandermonde
  entries V\[i\]\[j\] = alpha_i^j = (i+1)^j in GF(2^8);
  parity rows are the bottom m rows of E = V * T^(-1) where
  T is the top k x k sub-matrix (rows for shards 0..k-1)
- Parameter bound: k + m MUST NOT exceed 255

These parameters fully determine the encoding matrix for any
(k, m) configuration in the permitted range.  The m <= 2 case
was chosen (revision from earlier drafts) to make
RS_VANDERMONDE byte-for-byte interoperable with
FFV2_ENCODING_LINUX_MD_RAID at m <= 2, so that a receiver
that speaks either encoding consumes the other's output
without re-encoding.  See the wire-compat cross-references in
{{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}
`sec-encoding-linux-md-raid-annex`.

### RS Interoperability Test Vectors

The following worked examples pin the encoding matrix and
end-to-end encodings for two representative geometries: k=2 m=1
(exercises the S.1 m=1 rule -- all-ones parity row) and k=3 m=2
(exercises the S.1 m=2 rule -- P + Q parity rows).  An
implementation whose encoded output matches these tables is
using the same GF(2^8) representation and the same parity-row
construction as required by the interoperability parameters
above.

#### k=2, m=1

Encoding matrix `E`:

~~~
E = [ [0x01, 0x00],    // identity block for data shard 0
      [0x00, 0x01],    // identity block for data shard 1
      [0x01, 0x01] ]   // parity row P = [1, 1]
~~~

The parity shard is the bitwise XOR of both data shards:
`parity[j] = data[0][j] XOR data[1][j]`.

Concrete byte-level test vector with `shard_len = 1`:

| data[0] | data[1] | parity  | Notes |
|---|---|---|---|
| `0x00`  | `0x00`  | `0x00`  | zero input             |
| `0x01`  | `0x00`  | `0x01`  | 0x01 XOR 0x00 = 0x01   |
| `0x00`  | `0x01`  | `0x01`  | 0x00 XOR 0x01 = 0x01   |
| `0x01`  | `0x01`  | `0x00`  | 0x01 XOR 0x01 = 0x00   |
| `0x80`  | `0x80`  | `0x00`  | 0x80 XOR 0x80 = 0x00   |
{: #tbl-rs-test-vector-k2m1 title="RS Vandermonde test vector: k=2, m=1"}

#### k=3, m=2

Encoding matrix `E`:

~~~
E = [ [0x01, 0x00, 0x00],   // identity block for data shard 0
      [0x00, 0x01, 0x00],   // identity block for data shard 1
      [0x00, 0x00, 0x01],   // identity block for data shard 2
      [0x01, 0x01, 0x01],   // P row = [1, 1, 1]
      [0x01, 0x02, 0x04] ]  // Q row = [g^0, g^1, g^2] with g = 2
~~~

The two parity shards are computed byte-wise as:

    P[j] = data[0][j] XOR data[1][j] XOR data[2][j]
    Q[j] = 1 * data[0][j] XOR 2 * data[1][j] XOR 4 * data[2][j]

where the multiplication is in GF(2^8) with polynomial `0x11d`.

Concrete byte-level test vector with `shard_len = 1`:

| data[0] | data[1] | data[2] | P     | Q     | Notes                          |
|---|---|---|---|---|---|
| `0x00`  | `0x00`  | `0x00`  | `0x00`| `0x00`| zero input                     |
| `0x01`  | `0x02`  | `0x03`  | `0x00`| `0x09`| 1 XOR (2*2) XOR (4*3) = 1 XOR 4 XOR 12 = 9 |
| `0x80`  | `0x00`  | `0x00`  | `0x80`| `0x80`| Q = 1 * 0x80 = 0x80            |
| `0x00`  | `0x80`  | `0x00`  | `0x80`| `0x1d`| Q = 2 * 0x80 = 0x100 -> reduce by 0x11d -> 0x1d |
| `0x00`  | `0x00`  | `0x80`  | `0x80`| `0x3a`| Q = 4 * 0x80 = (2 * 0x1d) = 0x3a              |
| `0x37`  | `0x91`  | `0xac`  | `0x0a`| `0x82`| general non-degenerate case    |
{: #tbl-rs-test-vector-k3m2 title="RS Vandermonde test vector: k=3, m=2"}

Implementations that produce different values for any row of
either table disagree with this specification and will not
interoperate.

#### m >= 3 test vectors

Not included here.  Implementations that need m >= 3
interoperability with RS_VANDERMONDE SHOULD cross-check against
a reference implementation (e.g. the reffs
`lib/ec/tests/rs_test.c` roundtrip suite) because the
normalized-Vandermonde parity rows at m >= 3 are not easily
hand-computed.  The MDS property (any k of k+m shards recover
the data) is verified by roundtrip; the specific parity bytes
follow from the construction in the "m >= 3" subsection above.

## RS Shard Sizes

All RS shards (data and parity) are exactly shard_len bytes.  This
simplifies the CHUNK operation protocol: chunk_size is exactly the
shard size for all mirrors.

| Configuration | File Size | Shard Size | Total Storage | Overhead |
|---
| 4+2 | 4 KB | 1 KB | 6 KB | 50% |
| 4+2 | 1 MB | 256 KB | 1.5 MB | 50% |
| 8+2 | 4 KB | 512 B | 5 KB | 25% |
| 8+2 | 1 MB | 128 KB | 1.25 MB | 25% |
{: title="RS shard sizes for common configurations"}

# IANA Considerations

This document registers the following value in the "Flexible
File Version 2 Layout Type Erasure Coding Type Registry" established
by {{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}:

| Encoding Type Name | Value | RFC | How | Minor Versions |
| ---
| FFV2_ENCODING_RS_VANDERMONDE | 4 | RFCTBD10 | L | 2 |

# Security Considerations

The chunk-level security considerations of
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}} apply to any encoding
registered in the Erasure Coding Type Registry, including this
one.

Reed-Solomon Vandermonde is not a cryptographic construction.
An adversary who can observe or modify k or more shards can
recover or corrupt the original data.  Confidentiality and
integrity of shards in flight are provided by the transport
security mechanisms defined in
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}}, not by the encoding
itself.

# Acknowledgments
{:numbered="false"}

See the Acknowledgments section of
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}.

--- back
