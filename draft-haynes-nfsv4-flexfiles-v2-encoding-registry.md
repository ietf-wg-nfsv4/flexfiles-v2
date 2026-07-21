---
title: Erasure Coding Type Registry for the Flexible File Version 2 Layout Type
abbrev: FFv2 Encoding Registry
docname: draft-haynes-nfsv4-flexfiles-v2-encoding-registry-latest
category: std
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: [pNFS, flexfiles, erasure coding, IANA registry]

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
  RFC8126:
  RFC8881:
  I-D.haynes-nfsv4-flexfiles-v2-requirements:
  I-D.haynes-nfsv4-flexfiles-v2-chunks:

informative:
  IANA-PEN:
    title: "Private Enterprise Numbers"
    target: https://www.iana.org/assignments/enterprise-numbers/
    author:
      - org: IANA
    date: false
  I-D.haynes-nfsv4-flexfiles-v2-layout:
  I-D.haynes-nfsv4-flexfiles-v2-proxy-server:
  I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde:
  I-D.haynes-nfsv4-flexfiles-v2-mojette:

--- abstract

This document establishes the "Flexible File Version 2 Layout
Type Erasure Coding Type Registry": a 32-bit value space
partitioned by intended-scope range (Standards Track,
Experimental, Vendor, Private) with per-range allocation
policies.  The registry is the framework through which the
Flexible File Version 2 Layout Type negotiates erasure
encodings between clients, Metadata Servers, and Data Servers.
This document also specifies how encodings compose in a single
file's mirror set (the "mixing of coding types" mechanic that
enables assimilation, migration, cross-encoding recovery, and
capability-heterogeneous striping) without requiring individual
encoding specifications to coordinate.

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
encoding-method-agnostic protocol surface.  This document
establishes the IANA registry through which erasure encodings
are allocated and specifies how multiple encodings compose
within a single file's mirror set.

Two mechanics live here:

1. The **Erasure Coding Type Registry** itself: a 32-bit value
   space partitioned into four ranges (Standards Track,
   Experimental, Vendor, Private) with distinct allocation
   policies per range.
2. **Mixing of coding types** within a single file's mirror
   set: how the layout XDR admits per-mirror encoding
   selection, and what use cases it enables (assimilation,
   migration between encodings, cross-encoding recovery,
   heterogeneous-pool striping).

Individual encoding specifications
({{I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde}},
{{I-D.haynes-nfsv4-flexfiles-v2-mojette}}, and future
encoding companion documents) register their allocated values
in the registry this document creates.

# Requirements Language

{::boilerplate bcp14-tagged}

# Definitions

The following terms are used with meanings defined in
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}:

- data server (DS), metadata server (MDS)
- encoding, stripe, shard, mirror
- k (number of data shards), m (number of parity shards)
- layout, `ffv2_layout4`, `ffv2_mirror4`, `ffv2_coding_type4`

Local terms defined in this document:

Erasure Coding Type Registry:
:  The IANA registry established by this document for
   `ffv2_coding_type4` values.

Standards Track range:
:  The 0x0000-0x00FF portion of the registry, allocated by
   IETF Review.

Experimental range:
:  The 0x0100-0x0FFF portion, allocated by Expert Review.

Vendor (open) range:
:  The 0x1000-0x7FFF portion, allocated First Come First
   Served with a published specification or patent reference.

Private/proprietary range:
:  The 0x8000-0xFFFE portion, requiring no IANA registration.

Designated Expert:
:  Per {{RFC8126}}, an individual designated by the IESG to
   review registration requests for the ranges of this registry
   that require expert review.

# Mixing of Coding Types

Multiple coding types can be present in a Flexible File Version 2
Layout Type layout.  The ffv2_layout4 has an array of ffv2_mirror4,
each of which has a ffv2_coding_type4.  Mixing coding types in a
single file's mirror set addresses several use cases:

- Assimilation of a non-erasure-coded file into an erasure-coded
  representation, or export of an erasure-coded file to a
  non-erasure-coded representation.

- Online migration between encodings, for example from a
  Reed-Solomon Vandermonde encoding to a Mojette systematic
  encoding when a read-access-pattern change makes the new encoding
  a better fit.  Both representations remain addressable through
  the layout throughout the transition.

- Cross-encoding recovery: when one encoding loses data to a
  correlated failure mode (an encoding implementation bug, a
  memory-corruption pattern that affects parity shards
  identically), a second mirror in a different encoding provides
  an independent recovery surface.

- Client-capability routing: a Proxy Server
  ({{I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}) sees the full
  mirror set and chooses between encodings on behalf of clients
  that do not implement every encoding the file is represented in.

Consider a layout that exposes a file in two encodings
simultaneously: a PASSTHROUGH mirror over the original byte
stream and a Reed-Solomon Vandermonde mirror with 8 active data
shards (plus 2 parity and 2 spare data servers).  Both
representations are active and addressable through the layout
simultaneously.  This is the transition-window pattern: a file
may transiently span encodings while it is being assimilated
from a non-FFv2 source or migrated between encodings.  Steady
state is homogeneous; the multi-encoding window is what the
protocol must accommodate.

## Steady-state heterogeneous mirrors

The transition-window patterns above (assimilation, migration,
repair) are the most visible motivations for heterogeneous
mirror sets, but they are not the only ones.  A file's mirror
set MAY be heterogeneous in steady state -- where no transition
is in progress and no transition is planned -- when the
deployment's storage pools have different encoding capabilities
and the file is too large to fit in any single pool.

Consider an operator with three 100-TB storage pools.  Pool A
is a Flexible File v1 export speaking only NFSv3 (capable of
FFV2_ENCODING_PASSTHROUGH only); Pool B is a Flexible File v2
deployment whose data servers have implemented only
FFV2_ENCODING_RS_VANDERMONDE; Pool C similarly has data
servers that have implemented only FFV2_ENCODING_MOJETTE_SYSTEMATIC.
A 250-TB file cannot fit in any single pool.  Striping the
file across all three pools is forced by capacity arithmetic:
250 > 100.  And because each pool's data servers can only
respond to the chunk operations of its own encoding, the layout
for this file MUST name a different `ffv2_coding_type4` per
mirror covering each stripe segment.  The heterogeneity is
not a transition window; it is the permanent structural
consequence of striping across heterogeneous capability pools.

In this steady-state case, no proxy-server-mediated transition
machinery is involved.  The client receives a layout
enumerating the mirrors at different `ffv2m_coding` values and
routes chunk operations to the appropriate data server per
segment (or, if the client cannot speak one of the encodings,
requests proxy mediation per the proxy-server draft's section
"Encoding Translation for Encoding-Ignorant Clients").  The layout
machinery that supports this case is exactly the per-mirror
encoding naming primitive: no additional protocol elements are
required to express it.

The transient case (one file moving between encodings) and the
steady-state case (one file permanently striped across
heterogeneous pools) share a single wire primitive: an
`ffv2l_mirrors` array that admits mixed `ffv2_coding_type4`
values.

# IANA Considerations

## Erasure Coding Type Registry

IANA is requested to create a new registry titled
"Flexible File Version 2 Layout Type Erasure Coding Type Registry"
in the "Network File System version 4 (NFSv4) Parameters"
group.

The registry uses a 32-bit value space partitioned into ranges
based on the intended scope of the encoding type:

 | Range | Purpose | Allocation Policy |
 | ---
 | 0x0000                | Reserved (uninitialised) | -- |
 | 0x0001-0x00FF         | Standards Track | IETF Review |
 | 0x0100-0x0FFF         | Experimental | Expert Review |
 | 0x1000-0x7FFF         | Vendor (open) | First Come First Served |
 | 0x8000-0xFFFE         | Private/proprietary | No registration required |
 | 0xFFFF                | Reserved | -- |
 | 0x00010000-0xFFFFFFFF | Reserved (upper range) | Reserved for future partition |
{: title="Erasure Coding Type Value Ranges (32-bit space)"}

The upper 16 bits of the 32-bit value space (0x00010000 through
0xFFFFFFFF) are reserved for future range extensions.  A receiver
that observes an `ffv2_coding_type4` value in the reserved region
MUST treat it as an unsupported encoding type
(NFS4ERR_CODING_NOT_SUPPORTED).  Value 0x0000 is reserved as the
uninitialised-field sentinel and MUST NOT be allocated to an
encoding.

Standards Track (0x0000-0x00FF):
:  Encoding types intended for broad interoperability.  The
specification MUST include a complete mathematical description
sufficient for independent interoperable implementations.
Allocated by IETF Review {{RFC8126}}.

Experimental (0x0100-0x0FFF):
:  Encoding types under development or evaluation.  An Internet-Draft
is sufficient for allocation.  The specification SHOULD include
enough detail for interoperability testing.  Allocated by Expert
Review {{RFC8126}}.

Vendor (open) (0x1000-0x7FFF):
:  Encoding types with a published specification or patent reference.
Interoperability is expected among implementations that license or
implement the specification.  The registration MUST include either a
math specification or a patent reference.  Allocated First Come
First Served {{RFC8126}}.

Private/proprietary (0x8000-0xFFFE):
:  Encoding types for use within a single vendor's ecosystem.
No IANA registration is required.  Interoperability with other
implementations is not expected; accidental codepoint collisions
between independent vendors are possible and are managed
operationally rather than by protocol mechanism.  The encoding
type name SHOULD include an organizational identifier (e.g.,
`FFV2_ENCODING_ACME_FOOBAR`).  A client that encounters a
value in this range from an unrecognized server SHOULD treat
it as an unsupported encoding type
(`NFS4ERR_CODING_NOT_SUPPORTED`).

Reserved (0xFFFF):
:  Reserved for future use; MUST NOT be allocated.

This partitioning prevents contention for small numbers in the
Standards Track range and provides a clear signal to clients
about what level of interoperability to expect.

### Initial registrations

The initial registrations for this registry are defined in
companion documents:

- FFV2_ENCODING_PASSTHROUGH (value 1) and
  FFV2_ENCODING_MIRRORED (value 5): registered by
  {{I-D.haynes-nfsv4-flexfiles-v2-layout}}.
- FFV2_ENCODING_MOJETTE_SYSTEMATIC (value 2) and
  FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC (value 3): registered
  by {{I-D.haynes-nfsv4-flexfiles-v2-mojette}}.
- FFV2_ENCODING_RS_VANDERMONDE (value 4): registered by
  {{I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde}}.

Additional encoding types are added via companion documents
targeting the appropriate range per this registry's allocation
policies.

### Designated Expert guidelines

The Designated Expert reviewing registrations in the Experimental
range (0x0100-0x0FFF) SHOULD consider:

- Completeness of the specification: does it enable an
  independent implementation to interoperate with the
  registering implementation?
- Overlap with existing registrations: does the proposed
  encoding duplicate the behavior of an already-registered
  encoding, or does it add a distinct capability?
- Progression intent: is the registrant planning to advance
  the specification to Standards Track?

Registrations in the Vendor range (0x1000-0x7FFF) do not require
Expert Review beyond the First Come First Served allocation
mechanism, but the registrant MUST provide a citable
specification or patent reference.

# Security Considerations

This document defines a registry framework and does not
introduce wire-protocol operations of its own.  The
chunk-level security considerations of
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}} apply to any encoding
registered in this registry.

Individual encoding registrations bear the responsibility for
their own security analysis (algorithmic robustness against
misuse, patent status disclosure, etc.), reviewed per the
allocation policy of the range they target.

Registration in the Private/proprietary range (0x8000-0xFFFE)
carries an implicit security consideration: because these
values are not centrally coordinated, a value that appears in
one deployment's traffic MAY collide with an unrelated encoding
in another deployment.  Implementations SHOULD reject
Private-range values from unrecognized servers rather than
attempt to interpret them.

# Acknowledgments
{:numbered="false"}

See the Acknowledgments section of
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}.

--- back
