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

The encoding process uses a (k+m) x k Vandermonde matrix, normalized
so that its top k rows form the identity matrix:

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
- Evaluation points: shard i (i = 0, 1, ..., k+m-1) uses
  alpha_i = i + 1 in GF(2^8) (values 1 through k+m, all
  non-zero and distinct)
- Vandermonde entries: V\[i\]\[j\] = alpha_i^j = (i+1)^j in GF(2^8)
  for i = 0..k+m-1, j = 0..k-1
- Matrix normalization: E = V * T^(-1) where T is the top k x k
  sub-matrix (rows for shards 0..k-1)
- Parameter bound: k + m MUST NOT exceed 255

These parameters fully determine the encoding matrix for any
(k, m) configuration in the permitted range.

### RS Interoperability Test Vector

The following worked example pins the encoding matrix and one
end-to-end encoding for the smallest useful geometry (k=2, m=1).
An implementation whose encoded output matches this example is
using the same GF(2^8) representation, the same evaluation-point
assignment, and the same matrix normalization as required by the
interoperability parameters above.

Evaluation points: `alpha_0 = 1`, `alpha_1 = 2`, `alpha_2 = 3`
(values 1, 2, 3 in GF(2^8)).

Vandermonde matrix V (3 rows x 2 columns):

~~~
V = [ [1, 1],    // row 0: (1^0, 1^1) = (1, 1)
      [1, 2],    // row 1: (2^0, 2^1) = (1, 2)
      [1, 3] ]   // row 2: (3^0, 3^1) = (1, 3)
~~~

Top k x k sub-matrix T = [[1, 1], [1, 2]] has determinant
`det(T) = 1*2 XOR 1*1 = 3` in GF(2^8).  The inverse of 3 in
GF(2^8) with irreducible polynomial `0x11d` is
`3^-1 = 0xF4` (verifiable: `(x+1) * (x^7+x^6+x^5+x^4+x^2) mod
(x^8+x^4+x^3+x^2+1) = 1`).  Applying `T_inv = (1/det) *
[[T[1][1], T[0][1]], [T[1][0], T[0][0]]]` (characteristic 2, so
no sign changes):

~~~
T_inv = [ [0xF5, 0xF4],
          [0xF4, 0xF4] ]
~~~

Systematic-normalized encoding matrix `E = V * T_inv`:

~~~
E = [ [0x01, 0x00],    // identity block for data shard 0
      [0x00, 0x01],    // identity block for data shard 1
      [0xF4, 0xF5] ]   // parity generator P = E[2]
~~~

For k=2, m=1 the parity generator is `P = [0xF4, 0xF5]`; the
parity shard is computed byte-wise as
`parity[j] = 0xF4 * data[0][j] XOR 0xF5 * data[1][j]` where the
multiplication is in GF(2^8) with polynomial `0x11d`.

Concrete byte-level test vector with `shard_len = 1`:

| data[0] | data[1] | parity  | Notes |
|---|---|---|---|
| `0x00`  | `0x00`  | `0x00`  | zero input                                                   |
| `0x01`  | `0x00`  | `0xF4`  | 0xF4 * 0x01 XOR 0xF5 * 0x00 = 0xF4                          |
| `0x00`  | `0x01`  | `0xF5`  | 0xF4 * 0x00 XOR 0xF5 * 0x01 = 0xF5                          |
| `0x01`  | `0x01`  | `0x01`  | 0xF4 XOR 0xF5 = 0x01 (the polynomial diff of adjacent bytes) |
{: #tbl-rs-test-vector title="RS Vandermonde test vector: k=2, m=1, single-byte shards"}

Implementations that produce different values for any row of
{{tbl-rs-test-vector}} disagree with this specification and will
not interoperate.

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
