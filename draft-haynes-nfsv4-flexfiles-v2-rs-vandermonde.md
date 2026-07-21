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

1. Construct a (k+m) x k Vandermonde matrix V where V\[i\]\[j\] = j^i
   in GF(2^8).

2. Extract the top k x k sub-matrix T from V.

3. Compute T_inv = T^(-1) using Gaussian elimination in GF(2^8).

4. Multiply: E = V * T_inv.  The result has an identity block on top
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
is O(k^2) in GF(2^8) multiplications.

## RS Interoperability Requirements

For two implementations of FFV2_ENCODING_RS_VANDERMONDE to
interoperate, they MUST agree on all of the following parameters.
Any deviation produces a different encoding matrix and renders
data unrecoverable by a different implementation.

- Irreducible polynomial: x^8 + x^4 + x^3 + x^2 + 1 (0x11d)
- Primitive element: g = 2
- Vandermonde evaluation points: V\[i\]\[j\] = j^i in GF(2^8)
- Matrix normalization: E = V * (V\[0..k-1\])^(-1)

These four parameters fully determine the encoding matrix for any
(k, m) configuration.

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
File Version 2 Layout Type Encoding Type Registry" established
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
