---
title: Parallel NFS (pNFS) Flexible File Layout Version 2
abbrev: Flex File Layout v2
docname: draft-haynes-nfsv4-flexfiles-v2-latest
category: std
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: Internet-Draft

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping, comments]

venue:
  group: Network File System Version 4
  type: Working Group
  mail: nfsv4@ietf.org
  arch: https://mailarchive.ietf.org/arch/browse/nfsv4/
  github: ietf-wg-nfsv4/flexfiles-v2
  latest: https://ietf-wg-nfsv4.github.io/flexfiles-v2/draft-haynes-nfsv4-flexfiles-v2.html

author:
 -
    ins: T. Haynes
    name: Thomas Haynes
    organization: Hammerspace
    email: loghyr@gmail.com

normative:
  I-D.haynes-nfsv4-flexfiles-v2-delta-writes:
  RFC4121:
  RFC4506:
  RFC5531:
  RFC5662:
  RFC7530:
  RFC7861:
  RFC7862:
  RFC7863:
  RFC8126:
  RFC8178:
  RFC8434:
  RFC8435:
  RFC8881:
  RFC9289:

informative:
  Plank97:
    title: A Tutorial on Reed-Solomon Coding for Fault-Tolerance in RAID-like System
    target: http://web.eecs.utk.edu/~jplank/plank/papers/CS-96-332.htm
    author:
    - ins: J. Plank
      name: J. Plank
    date: September 1997
  IANA-PEN:
    title: "Private Enterprise Numbers"
    target: https://www.iana.org/assignments/enterprise-numbers/
    author:
      - org: IANA
    date: false
  RFC1813:
  RFC1950:
  RFC2083:
  RFC3720:
  RFC4519:
  RFC4960:
  RFC5905:
  RFC7942:
  FIPS-180-4:
    title: Secure Hash Standard (SHS)
    author:
      - org: National Institute of Standards and Technology
    date: August 2015
    seriesinfo:
      NIST: "FIPS PUB 180-4"
    target: https://doi.org/10.6028/NIST.FIPS.180-4
  BLAKE3-SPEC:
    title: "BLAKE3: one function, fast everywhere"
    author:
      - name: J. O'Connor
      - name: J.-P. Aumasson
      - name: S. Neves
      - name: Z. Wilcox-O'Hearn
    date: January 2020
    target: https://github.com/BLAKE3-team/BLAKE3-specs/blob/master/blake3.pdf
  ITU-V42:
    title: "Error-correcting Procedures for DCEs Using Asynchronous-to-Synchronous Conversion"
    author:
      - org: International Telecommunication Union
    date: March 2002
    seriesinfo:
      ITU-T: "Recommendation V.42"
  IEEE802-3:
    title: "IEEE Standard for Ethernet"
    author:
      - org: IEEE
    date: 2022
    seriesinfo:
      IEEE: "802.3-2022"
  OPENZFS-FLETCHER4:
    title: "OpenZFS On-Disk Format Specification, Section 2.2.4: Fletcher"
    author:
      - org: OpenZFS
    target: https://openzfs.github.io/openzfs-docs/Basic%20Concepts/Checksums.html
    date: false
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
  LINUX-RAID6:
    title: "Linux kernel software RAID (md/raid6) -- lib/raid6"
    author:
      - name: H. P. Anvin
      - org: Linux kernel contributors
    target: https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/lib/raid6
    date: false
  DCACHE:
    title: "dCache -- a distributed storage system"
    author:
      - org: dCache collaboration (DESY, Fermilab, NDGF)
    target: https://dcache.org/
    date: false

--- abstract

Parallel NFS (pNFS) allows a separation between the metadata (onto a
metadata server) and data (onto a storage device) for a file.  The
Flexible File Version 2 Layout Type is defined in this document as
an extension to pNFS that allows the use of storage devices that
require only a limited degree of interaction with the metadata
server and use already-existing protocols.  Data protection is also
added to provide integrity.  Both Client-side mirroring and the
erasure coding algorithms are used for data protection.

--- note_Note_to_Readers

This is an individual submission and does not reflect Working Group
consensus.  The "About This Document" section above has the current
discussion venue, latest rendering, and source location.

--- middle

# Introduction

In Parallel NFS (pNFS) (see Section 12 of {{RFC8881}}), the metadata
server returns layout type structures that describe where file data is
located.  There are different layout types for different storage systems
and methods of arranging data on storage devices.  {{RFC8435}} defined
the Flexible File Version 1 Layout Type used with file-based data
servers that are accessed using the NFS protocols: NFSv3 {{RFC1813}},
NFSv4.0 {{RFC7530}}, NFSv4.1 {{RFC8881}}, and NFSv4.2 {{RFC7862}}.

A metadata server that supports the Flexible File Version 2 Layout
Type MUST be an NFSv4.2 server.  The new operations defined by this
document for the metadata server (the TRUST_STATEID family on the
metadata server / storage device control session, and the
CB_CHUNK_REPAIR back-channel callback to clients) are NFSv4.2
operations and have no representation in NFSv4.1 or earlier minor
versions.  Storage devices can speak NFSv3, NFSv4.1, or NFSv4.2, but
some encoding types and coupling configurations narrow that choice;
see {{sec-ff_device_addr4}} for the exact rules.

To provide a global state model equivalent to that of the files
layout type, a back-end control protocol might be implemented between
the metadata server and NFSv4.1+ storage devices.  An implementation
can either define its own proprietary mechanism or it could define a
control protocol in a Standards Track document.  The requirements for
a control protocol are specified in {{RFC8881}} and clarified in
{{RFC8434}}.

The control protocol described in this document is based on NFS.  It
does not provide for knowledge of stateids to be passed between the
metadata server and the storage devices.  Instead, the storage
devices are configured such that the metadata server has full access
rights to the data file system and then the metadata server uses
synthetic ids to control client access to individual data files.

In traditional mirroring of data, the server is responsible for
replicating, validating, and repairing copies of the data file.  With
client-side mirroring, the metadata server provides a layout that
presents the available mirrors to the client.  The client then picks
a mirror to read from and ensures that all writes go to all mirrors.
The client only considers the write transaction to have succeeded if
all mirrors are successfully updated.  In case of error, the client
can use the LAYOUTERROR operation to inform the metadata server,
which is then responsible for the repairing of the mirrored copies of
the file.

This client side mirroring provides for replication of data but does
not provide for integrity of data.  In the event of an error, a user
would be able to repair the file by silvering the mirror contents.
I.e., they would pick one of the mirror instances and replicate it to
the other instance locations.

However, lacking integrity checks, silent corruptions are not able to
be detected and the choice of what constitutes the good copy is
difficult.  This document defines the Flexible File Version 2 Layout
Type, an independent layout type that adds error-detection integrity
(checksum) for erasure coding.  It does not modify the Flexible File
Version 1 Layout Type ({{RFC8435}}); the two coexist.  Data blocks are
transformed into a header and a chunk.  This document also introduces
new operations that allow the client to roll back writes to the data
file.

Using the process detailed in {{RFC8178}}, the revisions in this
document become an extension of NFSv4.2 {{RFC7862}}.  They are built on
top of the external data representation (XDR) {{RFC4506}} generated
from {{RFC7863}}.

This document defines `LAYOUT4_FLEX_FILES_V2`, a new and independent
layout type that coexists with the Flexible File Version 1 Layout Type
(`LAYOUT4_FLEX_FILES`, {{RFC8435}}).  The two layout types are
wire-format-incompatible: a flexible file v1 layout receiver
cannot parse flexible file v2 layout bytes, and a flexible file
v2 layout receiver cannot parse flexible file v1 layout bytes.
Semantically, however, the flexible file v2 layout is a superset
of the flexible file v1 layout: any flexible file v1 layout has
a natural flexible file v2 layout representation using a single
FFV2_ENCODING_PASSTHROUGH mirror (see
{{sec-encoding-passthrough}}), with the flexible file v1 layout's
data servers mapped into ffv2_stripes4 and the flexible file v1
layout's layout-level ffl_stripe_unit mapped into per-mirror
ffv2m_striping_unit_size and ffv2m_striping.  The reverse does
not hold: flexible file v2 layouts that use any CHUNK-based
encoding (any FFV2_ENCODING_* value other than
FFV2_ENCODING_PASSTHROUGH) have no flexible file v1 layout
representation, because the flexible file v1 layout has neither
the chunk envelope (chunk_guard4, per-chunk checksum) nor the
per-mirror encoding choice that those encodings require.  A
server MAY support both layout types simultaneously; a client
selects the desired layout type in its LAYOUTGET request.

# Requirements Language

{::boilerplate bcp14-tagged}

#  Motivation {#sec-motivation}

Workloads that need both the throughput of parallel pNFS
data servers and the durability of erasure coding have
driven the work in this draft.  The deployments span
scientific-instrumentation pipelines that produce
petabytes of detector data per year, training-checkpoint
files written hot from machine-learning jobs, archive
workloads in which a single file may hold the only copy of
an experiment's result, and ordinary production
filesystems where read patterns evolve across a file's
lifetime.  These deployments are documented in detail in
{{sec-use-cases}}; the protocol shape that follows is the
result of looking at them and asking what a pNFS layout
type would have to provide.

The first thing the deployments share is that erasure
coding moves work off the data servers that are already
the bottleneck in the write-heavy parallel case.
Server-side erasure coding makes each data server compute
its share of the parity transform on every write,
multiplying the per-write CPU cost by (k + m) across the
storage tier and serialising on the data server's limited
compute.  Client-side erasure coding shifts that compute
to the writers, which scale horizontally with the
workload, and lets the data servers stay close to their
strength -- storing and serving bytes.  Flexible file v1
layout ({{RFC8435}}) already chose client-side compute by
placing replication at the writer; this draft extends that
choice to client-side erasure coding.  Benchmark
measurements summarised in {{sec-implementation-status}}
confirm that the resulting overhead is competitive with
server-side encoding on realistic workloads and that the
encoding compute scales with the writer population rather
than with the data-server count.

Client-side erasure coding has a corollary that protocol
designers cannot avoid: when a client fans a stripe out
across multiple data servers and fails mid-write, no
single data server has whole-transaction visibility.  The
state left behind on each data server is a partial
fragment of a write that may or may not have completed
elsewhere.  A server-side coordinator that holds the whole
stripe -- the flexible file v1 case -- can resilver from a
surviving copy without any client involvement.  In the v2
case there is no such coordinator, and the on-wire
protocol specifies how the partial state is reconciled.
This is the load-bearing constraint that shapes the rest
of the design.

A natural-looking answer is to add a distributed-consensus
protocol between the data servers and have them agree on
which write committed.  That answer is rejected here.
Distributed consensus is operationally expensive,
introduces a synchronisation cost on every write, and
makes the data servers themselves stateful peers in a way
that closes off the simpler implementations the protocol
is designed to accommodate.  Instead, this draft uses two
narrowly-scoped primitives that together provide just
enough on-wire reconciliation: the chunk_guard4
compare-and-swap (CAS) and the CB_CHUNK_REPAIR callback.

Every CHUNK_WRITE carries a cohort header (a 64-bit
writer-chosen chunk_cohort_id4 plus the writer's 32-bit
layout-granted client id) once for the batch, and the
data server performs a per-chunk compare-and-swap against
its own chunk_guard4 (a 32-bit per-chunk generation
counter plus the last writer's client id) when the client
sets cwa_guard on receipt.  If two writers race for the
same chunk, exactly one wins on each data server, the
loser receives NFS4ERR_CHUNK_GUARDED for that chunk, and
the chunks the loser intended to write are left
unchanged.  No data server needs to consult its peers;
the CAS is local.  The cost on the metadata server is
bounded by the 12-byte cohort header per CHUNK_WRITE
plus a 32-bit per-layout client identifier
({{sec-chunk_guard4}}, {{sec-ffv2-mirror4}}).
Independent collisions on different chunks resolve
independently; there is no file-wide lock and no global
ordering across writes.

When the per-chunk CAS detects that a stripe ended up
non-atomic -- some shards under writer A's guard, others
under writer B's, or a writer crashed mid-fan-out -- the
metadata server selects a repair actor via
CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}), and that actor
drives the repair: it acquires CHUNK_LOCK on the affected
range, reads the surviving shards, decodes through the
erasure transform, writes the reconstructed shards via
CHUNK_WRITE_REPAIR, and clears the errored state via
CHUNK_REPAIRED.  The repair actor may be a client, a data
server (in a tightly coupled deployment), or a proxy server;
exactly one holds the chunk-range lock per repair episode
so the data servers still do not coordinate among themselves.
The repair-actor selection rule is given in
{{sec-repair-selection}}.

These two primitives -- the per-chunk CAS and the
callback-driven repair -- replace what would otherwise
require a distributed-consensus protocol.  The CAS handles
the common case at local cost, where independent writers
racing for different chunks resolve independently and
concurrent writers on the same chunk get a clean win/loss
decision.  CB_CHUNK_REPAIR handles the rare case of
partial-failure non-atomicity with a single coordinator
selected per repair episode.  The cost model is asymmetric
on purpose: the hot path pays for an 8-byte header and a
local CAS; the cold path pays for a selected actor and a
small number of round-trips.

The CHUNK operation set in this draft is the minimum
sufficient to drive the chunk state machine
({{sec-system-model-chunk-state}}) plus the repair flow
above.  CHUNK_WRITE places PENDING content; CHUNK_FINALIZE
signals that the writer is done with a generation;
CHUNK_COMMIT promotes that generation to durable, globally
visible state; CHUNK_READ retrieves it; CHUNK_HEADER_READ
provides the fast probe that lets repair coordinators and
recovering writers inspect chunk metadata without reading
payloads.  CHUNK_LOCK, CHUNK_UNLOCK, CHUNK_ERROR,
CHUNK_REPAIRED, CHUNK_WRITE_REPAIR, and CHUNK_ROLLBACK
together drive the repair flow.  Each operation does one
well-scoped job; the complexity is in the state machine
the operations drive, not in the operation set itself.
Each of these primitives closes a specific gap in the
lifecycle or the repair path.  The detailed treatment of
the operation set is in {{sec-new-ops}}.

The same design discipline shapes the rest of the
specification.  The protocol describes wire format and
server obligations; it does not pin a data-server
backend, a control protocol between metadata server and
data server, a checksum algorithm, or a file-attribute
representation on the data server.  Different
implementations resolve these choices differently and
remain conformant.  TRUST_STATEID
({{sec-tight-coupling-control}}) is one such control
protocol that this draft defines; storage devices with
their own established control protocols are conformant
without implementing it.  The tagged checksum4
({{sec-checksum4}}) lets the metadata server pick any
registered checksum algorithm per file.  The
authorization-outcome parity rule
({{sec-state-locking}}) lets data servers that do not
expose a POSIX file namespace satisfy the tight coupling
requirements without materialising POSIX uid/gid bits.

A protocol-level consequence of placing erasure coding at
the client is that the layout is able to describe a
file's storage shape over its full lifetime -- including
the transition windows when the file is being assimilated
from a non-erasure-coded source, re-encoded from one
encoding to another, or recovered from a correlated encoding
failure through a mirror under a different encoding.
This draft allows a single file's layout to contain
mirrors under different encodings.  The
heterogeneous-mirror capability is not a steady-state
expectation; most files have one encoding most of the
time.  It is the protocol shape that lets transitions
happen while the file remains readable.  The deployment
cases that drive the allowance are catalogued in
{{sec-use-cases}}.

Scope note: the consistency goal of flexible file v2
layout is RAID consistency across the shards that make
up an encoded stripe, not POSIX write ordering across
arbitrary application writes.  The protocol does not
attempt to make overlapping application writes from
different clients atomic; that is the province of file
locking ({{RFC8881}} Section 12) and of application-level
coordination.  What the protocol does guarantee is that
the shards comprising a given stripe agree on which
write produced them -- expressed on the wire as agreement
on the chunk_guard4 value of every chunk that carries
those shards -- so that readers and repair actors never
observe a half-applied stripe.  Readers who need
cross-write ordering beyond a single stripe MUST use the
existing NFSv4 locking primitives.

#  Use Cases {#sec-use-cases}

The protocol is designed around three workload classes.  The
labels below reflect the relative frequency of each class in
installations that choose flexible file v2 layout for its combination of
integrity and performance; individual deployments may diverge.

Single writer, multiple readers (the common case):
:  A file written by one client and subsequently read by many.
   Examples include artifacts deposited by batch jobs, container
   images, and media files.  The protocol is optimized for this
   case; see {{sec-system-model-progress}}.

Multiple writers without sustained contention (occasional):
:  Files with multiple concurrent writers where races on the same
   chunk are rare.  Examples include shared-directory append-only
   logs and distributed builds.  The chunk_guard4 CAS primitive and
   per-chunk locking cover this case without penalizing the common
   single writer path.

Multiple writers, disjoint regions (rare):
:  High-performance computing (HPC) checkpoint workloads, in which
   many ranks write disjoint regions of the same file in lockstep.
   The protocol relies on block alignment to keep per-chunk
   contention rare despite overall high writer count.  Contention
   that does occur is resolved via the deterministic tiebreaker
   rule defined in {{sec-chunk_guard4}}.  Deployments that use an
   XOR-based erasure encoding (see {{sec-mojette-encoding}}) and
   expect frequent small edits from this workload class MAY use the
   optional delta-write protocol defined in
   {{I-D.haynes-nfsv4-flexfiles-v2-delta-writes}}, which lets the
   client forward per-projection XOR deltas directly to each data
   server, avoiding client-side read-modify-write of the full
   stripe on the small-edit path.

Scale targets include multi-thousand-client deployments (on the
order of tens of thousands of concurrent clients for HPC
checkpointing), parallel-filesystem replacements, and multi-rack
shared-storage clusters.  The repair protocol (see
{{sec-repair-selection}}) is designed to let such deployments
tolerate data-server failures and concurrent writer races without
blocking the critical path for the first two workload classes.

#  Definitions

block:

:  the application's view of file data.  A block is a unit of file
content as observed by an NFS client at the POSIX layer or by the
local file system.  A chunk's payload, after any decoding the client
performs, is presented to the application as one or more blocks.

shard:

:  the encoding's view.  A shard is a single piece of an encoded stripe
produced by an erasure-coding (or replication) transformation.  A
stripe of k data shards plus m parity shards is the unit an encoding
encodes and decodes.  The word "shard" only has meaning while the
encoding is reasoning about a stripe; once a shard is at rest on a data
server it is, by virtue of having been transmitted, the payload of a
chunk.

chunk:

:  the protocol's unit of file data on the wire, carrying an
envelope that distinguishes it from a block: a compare-and-swap
guard (chunk_guard4 -- atomicity, see {{sec-chunk_guard4}}), a
checksum (per-chunk integrity), a provenance identifier
(chunk_owner4, see {{sec-chunk_owner4}}), a lifecycle state
(PENDING / FINALIZED / COMMITTED via the chunk state machine,
see {{sec-system-model-chunk-state}}), and per-chunk locking that
survives stateid revocation through lock escrow.  A chunk is the
addressable unit named in the CHUNK operations defined in this
document and durably persisted by a data server.  A chunk's
payload may be a block (mirrored layout) or a shard
(erasure-coded layout); the wire protocol does not distinguish.
The chunk size MAY differ from the size of the block or shard it
carries.  See {{sec-system-model-chunk-not-block}} for the
load-bearing role each envelope property plays in the protocol's
consistency story.

The three terms describe the same data at three different layers and
should be used accordingly.  The encoding transforms blocks into shards;
the wire protocol transmits shards as chunk payloads; the data server
persists chunks.  On read the path reverses.

A protocol-internal note: the chunk state machine
({{sec-system-model-chunk-state}}) and several CHUNK operations
refer to the per-chunk-offset state records as "blocks" (PENDING /
FINALIZED / COMMITTED / errored).  This is a finer-grained use of
the word, internal to the data server's chunk metadata, and should
not be confused with the application-layer "block" defined above.
Where ambiguity matters, this document writes "chunk-state block"
or relies on context (operation names, state names) to disambiguate.

client-side erasure coding:

:  Erasure coding in which the encode and decode transforms are
   performed on the pNFS client, and encoded shards are written
   directly to the data servers (rather than being computed at
   a server-side coordinator).  This is the deployment shape
   Flexible File Version 2 Layout Type is designed for; the
   chunk substrate and CHUNK operations that make it safe are
   specified in {{sec-system-model}} and {{sec-new-ops}}.
   Contrast: server-side erasure coding, where a coordinator
   holds the entire stripe and produces parity, is out of scope
   for this document.

client-side mirroring:

:  a feature in which the client, not the server, is responsible for
updating all of the mirrored copies of a layout segment.

compare-and-swap (CAS):

:  an atomic primitive from concurrent programming in which an
update is conditional on a prior observed value: the operation
succeeds only if the current value matches an expected prior value,
and otherwise fails so the caller can retry.  In this document, the
chunk_guard4 mechanism (see {{sec-chunk_guard4}}) implements CAS at
the chunk level; the "expected prior value" is the chunk_guard4 the
writer observed at read time, and the "fail" outcome is
NFS4ERR_CHUNK_GUARDED.

control communication requirements:

:  the specification for information on layouts, stateids, file metadata,
and file data that must be communicated between the metadata server and
the storage devices.  There is a separate set of requirements for each
layout type.

control protocol:

:  the particular mechanism that an implementation of a layout type would
use to meet the control communication requirement for that layout type.
This need not be a protocol as normally understood.  In some cases,
the same protocol may be used as a control protocol and storage protocol.

(file) data:

:  that part of the file system object that contains the data to be read
or written.  It is the contents of the object rather than the attributes
of the object.

data block:

:  A block (as defined above) in the client's cache for a file.

data file:

:  The data portion of the file, stored on the data server.

data server:

:  a pNFS server that provides the file's data when the file system
object is accessed over a file-based protocol.

erasure coding:

:  A data protection scheme where a stripe of data is encoded into
shards (k data shards and m parity shards) so that the original
content can be reconstructed from any sufficient subset of the
shards.  Shards are transmitted as the payload of CHUNK operations
and stored on different data servers.

escrow (lock escrow, metadata-server escrow):

:  a state in which a chunk lock is held by the metadata server on
behalf of an as-yet-unselected future owner.  When the metadata
server revokes a client's stateid while the client still holds
chunk locks, the locks are not dropped (which would expose the
chunks to concurrent writers) but are transferred to the metadata
server itself, marked by the reserved cg_client_id value
CHUNK_GUARD_CLIENT_ID_MDS (see {{sec-chunk_guard_mds}}).  The
metadata server holds the locks in escrow until a repair actor
adopts them via CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT (driven by
CB_CHUNK_REPAIR).  A "metadata-server escrow owner" is the metadata server
acting in this placeholder role; "in escrow" describes a lock in
this state.  Escrow preserves the lock-continuity invariant
across stateid revocation: at no point during the revocation
sequence is a chunk simultaneously locked and unowned.

fencing:

:  the process by which the metadata server prevents the storage devices
from processing I/O from a specific client to a specific file.

file layout type:

:  a layout type in which the storage devices are accessed via the NFS
protocol (see Section 5.12.4 of {{RFC8881}}).

gid:

:  the group id, a numeric value that identifies to which group a file
belongs.

layout:

:  the information a client uses to access file data on a storage device.
This information includes specification of the protocol (layout type)
and the identity of the storage devices to be used.

layout iomode:

:  a grant of either read-only or read/write I/O to the client.

layout segment:

:  a sub-division of a layout.  That sub-division might be by the layout
iomode (see Sections 3.3.20 and 12.2.9 of {{RFC8881}}), a striping pattern
(see Section 13.3 of {{RFC8881}}), or requested byte range.

layout stateid:

:  a 128-bit quantity returned by a server that uniquely defines the
layout state provided by the server for a specific layout that describes
a layout type and file (see Section 12.5.2 of {{RFC8881}}).  Further,
Section 12.5.3 of {{RFC8881}} describes differences in handling between
layout stateids and other stateid types.

layout type:

:  a specification of both the storage protocol used to access the data
and the aggregation scheme used to lay out the file data on the underlying
storage devices.

loose coupling:

:  when the control protocol is a storage protocol.

(file) metadata:

:  the part of the file system object that contains various descriptive
data relevant to the file object, as opposed to the file data itself.
This could include the time of last modification, access time, EOF
position, etc.

metadata server:

:  the pNFS server that provides metadata information for a file system
object.  It is also responsible for generating, recalling, and revoking
layouts for file system objects, for performing directory operations,
and for performing I/O operations to regular files when the clients
direct these to the metadata server itself.

mirror:

:  a copy of a layout segment.  Note that if one copy of the mirror is
updated, then all copies must be updated.

non-systematic encoding:

:  An erasure coding scheme in which the encoded shards do not contain
verbatim copies of the original data.  Every read requires decoding,
even when no shards are lost.  The Mojette non-systematic transform is
an example.

proxy server:

:  a peer of the metadata server, defined in
{{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}} (hereafter "the
proxy server draft"), that admits client I/O on the metadata
server's behalf -- either as a translator for clients that
cannot speak the file's native encoding, or as a proxy-mediated
data path during whole-file move and repair operations.  A
proxy server may have additional roles.  This document cites
the proxy server draft only when referencing a specific rule
or section within it; other mentions of "proxy server" or "the
proxy server draft" in this document refer to the same reference
without repeating the citation.

recalling a layout:

:  a graceful recall, via a callback, of a specific layout by the metadata
server to the client.  Graceful here means that the client would have
the opportunity to flush any WRITEs, etc., before returning the layout
to the metadata server.

replication of data:

:  Data replication is making and storing multiple copies of data in
different locations.

resilvering:

:  the act of rebuilding a mirrored copy of a layout segment from a
known good copy of the layout segment.  Note that this can also be done
to create a new mirrored copy of the layout segment.

revoking a layout:

:  an invalidation of a specific layout by the metadata server.
Once revocation occurs, the metadata server will not accept as valid any
reference to the revoked layout, and a storage device will not accept
any client access based on the layout.

rsize:

:  the data transfer buffer size used for READs.

stateid:

:  a 128-bit quantity returned by a server that uniquely defines the set
of locking-related state provided by the server.  Stateids may designate
state related to open files, byte range locks, delegations, or layouts.

storage device:

:  the target to which clients may direct I/O requests when they hold
an appropriate layout.  See Section 2.1 of {{RFC8434}} for further
discussion of the difference between a data server and a storage device.

storage protocol:

:  the protocol used by clients to do I/O operations to the storage
device.  Each layout type specifies the set of storage protocols.

systematic encoding:

:  An erasure coding scheme in which the first k of the k+m encoded
shards are identical to the original k data blocks.  A healthy read
(no failures) requires no decoding -- the data shards are read directly.
Decoding is triggered only when data shards are missing.  Reed-Solomon
Vandermonde and Mojette systematic are examples.

tight coupling:

:  an arrangement in which the control protocol is one designed
specifically for control communication.  It may be either a proprietary
protocol adapted specifically to a particular metadata server or a
protocol based on a Standards Track document.  The specific
tight coupling variant defined by this document, in which the
control protocol is the TRUST_STATEID family, is referred to as
trusted stateid tight coupling (see {{sec-tight-coupling-control}}).

trusted stateid tight coupling:

:  the specific tight coupling control protocol defined in this
document, consisting of the operations TRUST_STATEID, REVOKE_STATEID,
and BULK_REVOKE_STATEID.  Within the scope of this document,
unqualified references to "tight coupling" or "tightly coupled" refer
to trusted stateid tight coupling unless the context explicitly
discusses the general concept.  Other tight coupling control
protocols (proprietary or future Standards Track) may exist but
are not covered by this specification.

uid:

:  the user id, a numeric value that identifies which user owns a file.

write hole:

:  A write hole is a data corruption scenario where either two clients
are trying to write to the same chunk or one client is overwriting an
existing chunk of data.

wsize:

:  the data transfer buffer size used for WRITEs.

## Naming the layout type (reviewer note)
{:removeInRFC="true"}

The layout type defined by this document is referred to by several
forms in the surrounding prose.  This note fixes the vocabulary so
the reader (and the sweep in the source) can keep them straight.
It follows the register RFC 8435 established for its own layout
type: a formal title-case name for headings and IANA registrations,
a lowercase running-text form, and separate XDR / struct-prefix
identifiers.  The parallel is exact -- everywhere RFC 8435 says
"flexible file layout" this document says "flexible file v2
layout", and everywhere RFC 8435 says "Flexible File Layout Type"
this document says "Flexible File Version 2 Layout Type".

Formal name (headings, IANA registrations, the abstract):
"Flexible File Version 2 Layout Type".  This is the form to
use when naming the layout type as such -- for example, the
Section 5 heading, the IANA registry title, and the sentence
that introduces the layout type in the abstract.  A short
formal variant "Flexible File Version 2 Layout" drops "Type"
when "Type" would be redundant with the surrounding noun
(as in the IANA-registered creation-hint name).

Running-text form (body prose): "flexible file v2 layout".
This is the form for sentences that mention the layout in
passing rather than naming it as an object of definition --
"the flexible file v2 layout supports multipathing to multiple
storage devices", "the flexible file v2 layout does not use
lou_body".  It parallels RFC 8435's lowercase "flexible file
layout" and is preferred over the title-case form for
sentences where the emphasis is on the mechanism, not the
name.  Do NOT write "flexible file v2 layout version 2" -- the
"v2" already carries the version, and appending "version 2"
is a rendering hazard.

Short form (narrow tables and reviewer-aid appendix material
where cell width or repetition would otherwise dominate):
"FFv2", with "FFv1" reserved for the predecessor defined by
{{RFC8435}}.  The short forms are NOT appropriate in body
prose, headings, IANA registrations, or the abstract; body
prose that would otherwise repeat the layout name uses the
running-text form above.  Their scoped use is in tables where
"flexible file v2 layout" would break the column layout (e.g.,
the four-variant wire-path comparison table in the
Implementation Status appendix).

XDR identifier: `LAYOUT4_FLEX_FILES_V2`.  This is the name
assigned to the layout type by the layout-type registry
({{RFC8434}}) and is the constant a receiver compares against
when dispatching on layout type.  It parallels
`LAYOUT4_FLEX_FILES` for the predecessor layout type
({{RFC8435}}).  Use the XDR identifier whenever the sentence
is about the value that appears on the wire; use the
"Flexible File Version 2 Layout Type" formal name whenever
the sentence is about the layout type as a specification.

Struct-name prefix: `ffv2_` (as in `ffv2_layout4`,
`ffv2_mirror4`, `ffv2_stripes4`).  This parallels RFC 8435's
`ff_` prefix (as in `ff_layout4`, `ff_device_addr4`).  The
per-struct field prefix follows the RFC 8435 pattern of
struct-initials plus underscore: `ffv2l_` for
`ffv2_layout4`, `ffv2m_` for `ffv2_mirror4`, `ffv2ds_` for
`ffv2_data_server4`, and so on.

Document title and file abbreviation: the front-matter title is
"Parallel NFS (pNFS) Flexible File Layout Version 2" and the
`abbrev` used in the running header is "Flex File Layout v2".
These are document-metadata conventions and do not participate
in the body-prose vocabulary; the running text follows the
forms above, not the front-matter forms.

#  Coupling of Storage Devices

A server implementation may choose either a loosely coupled model or a
tightly coupled model between the metadata server and the storage devices.
{{RFC8434}} describes the general problems facing pNFS implementations.
This document details how the new flexible file v2 layout addresses
these issues.  To implement the tightly coupled model, a control protocol
has to be defined.  As the flexible file v2 layout imposes no special
requirements on the client, the control protocol will need to provide:

1. management of both security and LAYOUTCOMMITs and

2. a global stateid model and management of these stateids.

When implementing the loosely coupled model, the only control protocol
will be a version of NFS, with no ability to provide a global stateid
model or to prevent clients from using layouts inappropriately.  To enable
client use in that environment, this document specifies how security,
state, and locking are managed.

The loosely and tightly coupled locking models defined in Section 2.3
of {{RFC8435}} apply equally to this layout type, including the use of
anonymous stateids with loosely coupled storage devices, the handling
of lock and delegation stateids, and the mandatory byte range lock
requirements for the tightly coupled model.

##  LAYOUTCOMMIT

Regardless of the coupling model, the metadata server has the
responsibility, upon receiving a LAYOUTCOMMIT (see Section 18.42 of
{{RFC8881}}) to ensure that the semantics of pNFS are respected (see
Section 3.1 of {{RFC8434}}).  These do include a requirement that data
written to a data storage device be stable before the occurrence of
the LAYOUTCOMMIT.

It is the responsibility of the client to make sure the data file is
stable before the metadata server begins to query the storage devices
about the changes to the file.  If any WRITE to a storage device did not
result with stable_how equal to FILE_SYNC, a LAYOUTCOMMIT to the metadata
server MUST be preceded by a COMMIT to the storage devices written to.
Note that if the client has not done a COMMIT to the storage device, then
the LAYOUTCOMMIT might not be synchronized to the last WRITE operation
to the storage device.

##  Fencing Clients from the Storage Device {#sec-Fencing-Clients}

With loosely coupled storage devices, the metadata server uses synthetic
uids (user ids) and gids (group ids) for the data file, where the uid
owner of the data file is allowed read/write access and the gid owner
is allowed read-only access.  As part of the layout (see ffv2ds_user
and ffv2ds_group in {{sec-ffv2_layout}}), the client is provided
with the user and group to be used in the Remote Procedure Call
(RPC) {{RFC5531}} credentials needed to access the data file.
Fencing off of clients is achieved by the metadata server changing
the synthetic uid and/or gid owners of the data file on the storage
device to implicitly revoke the outstanding RPC credentials.  A
client presenting the wrong credential for the desired access will
get an NFS4ERR_ACCESS error.

With this loosely coupled model, the metadata server is not able to fence
off a single client; it is forced to fence off all clients.  However,
as the other clients react to the fencing, returning their layouts and
trying to get new ones, the metadata server can hand out a new uid and
gid to allow access.

It is RECOMMENDED to implement common access control methods at the
storage device file system to allow only the metadata server root
(super user) access to the storage device and to set the owner of all
directories holding data files to the root user.  This approach provides
a practical model to enforce access control and fence off cooperative
clients, but it cannot protect against malicious clients; hence, it
provides a level of security equivalent to AUTH_SYS.  It is RECOMMENDED
that the communication between the metadata server and storage device
be secure from eavesdroppers and man-in-the-middle protocol tampering.
The security measure could be physical security (e.g., the servers
are co-located in a physically secure area), encrypted communications,
or some other technique.

With tightly coupled storage devices, the metadata server
and the storage device agree on the authorization decision
for each client access: a client allowed by the metadata
server to read or write a file is allowed the same access
at the storage device, and a client denied at the metadata
server is denied at the storage device.  How the storage
device reaches that decision is not constrained by this
specification.  Some storage devices replicate the user,
group, mode bits, and ACL of the metadata file onto a
POSIX-shaped local representation of the data file and let
their native filesystem enforce the decision; others (such
as storage devices backed by an object store, a
control-protocol-driven backend, or a backend with no
exposed file namespace) consult the control protocol
directly without ever materializing a POSIX file
representation.  Both approaches are conformant; the
specification's requirement is the authorization-outcome
parity, not the mechanism that produces it.

The client authenticates with the storage device and
receives the same authorization outcome it would have
received via the metadata server.  In the case of tight
coupling, fencing is the responsibility of the control
protocol and is not described in detail in this document.
Implementations of the tightly coupled locking model (see
{{sec-state-locking}}) will need a way to prevent access by
certain clients to specific files by invalidating the
corresponding stateids on the storage device; in such a
scenario, the client receives NFS4ERR_BAD_STATEID.

The client need not know the model used between the metadata server and
the storage device.  It need only react consistently to any errors in
interacting with the storage device.  It SHOULD both return the layout
and error to the metadata server and ask for a new layout.  At that point,
the metadata server can either hand out a new layout, hand out no layout
(forcing the I/O through it), or deny the client further access to
the file.

###  Implementation Notes for Synthetic uids/gids

The selection method for the synthetic uids and gids to be used for
fencing in loosely coupled storage devices is strictly an implementation
issue.  That is, an administrator might restrict a range of such ids
available to the Lightweight Directory Access Protocol (LDAP) 'uid' field
{{RFC4519}}.  The administrator might also be able to choose an id that
would never be used to grant access.  Then, when the metadata server had
a request to access a file, a SETATTR would be sent to the storage device
to set the owner and group of the data file.  The user and group might
be selected in a round-robin fashion from the range of available ids.

Those ids would be sent back as ffv2ds_user and ffv2ds_group to the
client, who would present them as the RPC credentials to the storage
device.  When the client is done accessing the file and the metadata
server knows that no other client is accessing the file, it can
reset the owner and group to restrict access to the data file.

When the metadata server wants to fence off a client, it changes the
synthetic uid and/or gid to the restricted ids.  Note that using a
restricted id ensures that there is a change of owner and at least one
id available that never gets allowed access.

Under an AUTH_SYS security model, synthetic uids and gids of 0 SHOULD be
avoided.  These typically either grant super access to files on a storage
device or are mapped to an anonymous id.  In the first case, even if the
data file is fenced, the client might still be able to access the file.
In the second case, multiple ids might be mapped to the anonymous ids.

###  Example of using Synthetic uids/gids

The user loghyr creates a file "ompha.c" on the metadata server, which
then creates a corresponding data file on the storage device.

The metadata server entry may look like:

~~~ shell
-rw-r--r--    1 loghyr  staff    1697 Dec  4 11:31 ompha.c
~~~
{: #fig-meta-ompha title="Metadata's view of ompha.c"}

On the storage device, the file may be assigned some unpredictable
synthetic uid/gid to deny access:

~~~ shell
-rw-r-----    1 19452   28418    1697 Dec  4 11:31 data_ompha.c
~~~
{: #fig-data-ompha title="Data's view of ompha.c"}

When the file is opened on a client and accessed, the user will try to
get a layout for the data file.  Since the layout knows nothing about
the user (and does not care), it does not matter whether the user loghyr
or garbo opens the file.  The client has to present an uid of 19452
to get write permission.  If it presents any other value for the uid,
then it must give a gid of 28418 to get read access.

Further, if the metadata server decides to fence the file, it SHOULD
change the uid and/or gid such that these values neither match earlier
values for that file nor match a predictable change based on an earlier
fencing.

~~~ shell
-rw-r-----    1 19453   28419    1697 Dec  4 11:31 data_ompha.c
~~~
{: #fig-fenced-ompha title="Fenced Data's view of ompha.c"}

The set of synthetic gids on the storage device SHOULD be selected such
that there is no mapping in any of the name services used by the storage
device, i.e., each group SHOULD have no members.

If the layout segment has an iomode of LAYOUTIOMODE4_READ, then the
metadata server SHOULD return a synthetic uid that is not set on the
storage device.  Only the synthetic gid would be valid.

The client is thus solely responsible for enforcing file permissions
in a loosely coupled model.  To allow loghyr write access, it will send
an RPC to the storage device with a credential of 1066:1067.  To allow
garbo read access, it will send an RPC to the storage device with a
credential of 1067:1067.  The value of the uid does not matter as long
as it is not the synthetic uid granted when getting the layout.

While pushing the enforcement of permission checking onto the client
may seem to weaken security, the client may already be responsible
for enforcing permissions before modifications are sent to a server.
With cached writes, the client is always responsible for tracking who is
modifying a file and making sure to not coalesce requests from multiple
users into one request.

##  State and Locking Models {#sec-state-locking}

The coupling model in effect for a given metadata-server /
storage-device pair is not negotiated over the NFS protocol.
The metadata server determines the coupling model from
out-of-band signals: administrative configuration, the
choice and capabilities of the control protocol between
the metadata server and the storage device, the storage
device's data-path protocol version, and the storage
device's backend architecture.  At the NFS protocol level,
the metadata server's expectations of the storage device
follow these classifications:

-  Storage devices implementing the NFSv3 or NFSv4.0
   protocols on the data path are treated as loosely
   coupled.

-  NFSv4.1+ storage devices that do not return the
   EXCHGID4_FLAG_USE_PNFS_DS flag in EXCHANGE_ID indicate
   that they are to be treated as loosely coupled.  From
   the locking viewpoint, they are treated in the same way
   as NFSv4.0 storage devices.

-  NFSv4.1+ storage devices that identify themselves with
   the EXCHGID4_FLAG_USE_PNFS_DS flag set in EXCHANGE_ID
   can potentially be tightly coupled.  They use a back-end
   control protocol to implement the global stateid model
   described in {{RFC8881}}.

Tight coupling additionally requires a control protocol
between the metadata server and the storage device,
discovered or advertised out-of-band as described above.

Some storage devices cannot operate under the loosely
coupled model at all.  The loose coupling model in this
specification relies on the storage device authorizing
client access against synthetic uid and gid values
({{sec-Fencing-Clients}}), which presupposes that the data
file has a local representation on the storage device
against which POSIX-style ownership checks can be applied.
Storage devices whose backend has no exposed file namespace
-- for example, object-store-backed data servers, or data
servers driven entirely through a control protocol against
a non-POSIX backend -- do not have that local representation
and MUST operate in the tightly coupled model with a
control protocol that conveys the authorization decision
directly.  A metadata server deploying with such a storage
device cannot fall back to loose coupling.

###  Loosely Coupled Locking Model

When locking-related operations are requested, they are primarily dealt
with by the metadata server, which generates the appropriate stateids.
When an NFSv4 version is used as the data access protocol, the metadata
server may make stateid-related requests of the storage devices.  However,
it is not required to do so, and the resulting stateids are known only
to the metadata server and the storage device.

Given this basic structure, locking-related operations are handled
as follows:

-  OPENs are dealt with by the metadata server.  Stateids are
   selected by the metadata server and associated with the client
   ID describing the client's connection to the metadata server.
   The metadata server may need to interact with the storage device to
   locate the file to be opened, but no locking-related functionality
   need be used on the storage device.

-  OPEN_DOWNGRADE and CLOSE only require local execution on the
   metadata server.

-  Advisory byte range locks can be implemented locally on the
   metadata server.  As in the case of OPENs, the stateids associated
   with byte range locks are assigned by the metadata server and only
   used on the metadata server.

-  Delegations are assigned by the metadata server that initiates
   recalls when conflicting OPENs are processed.  No storage device
   involvement is required.

-  TEST_STATEID and FREE_STATEID are processed locally on the
   metadata server, without storage device involvement.

All I/O operations to the storage device are done using the anonymous
stateid.  Thus, the storage device has no information about the openowner
and lockowner responsible for issuing a particular I/O operation.
As a result:

-  Mandatory byte range locking cannot be supported because the
   storage device has no way of distinguishing I/O done on behalf of
   the lock owner from those done by others.

-  Enforcement of share reservations is the responsibility of the
   client.  Even though I/O is done using the anonymous stateid, the
   client MUST ensure that it has a valid stateid associated with the
   openowner.

In the event that a stateid is revoked, the metadata server is responsible
for preventing client access, since it has no way of being sure that
the client is aware that the stateid in question has been revoked.

As the client never receives a stateid generated by a storage device,
there is no client lease on the storage device and no prospect of lease
expiration, even when access is via NFSv4 protocols.  Clients will
have leases on the metadata server.  In dealing with lease expiration,
the metadata server may need to use fencing to prevent revoked stateids
from being relied upon by a client unaware of the fact that they have
been revoked.

###  Tightly Coupled Locking Model

When locking-related operations are requested, they are primarily dealt
with by the metadata server, which generates the appropriate stateids.
These stateids MUST be made known to the storage device using control
protocol facilities.  This document defines one such control protocol
-- the TRUST_STATEID, REVOKE_STATEID, and BULK_REVOKE_STATEID
operations in {{sec-tight-coupling-control}} -- for deployments in
which the storage devices are NFSv4.2 servers willing to implement
the new operations.  A storage device with its own established
back-end control protocol that provides the equivalent functional
capabilities is conformant under this specification without
implementing the TRUST_STATEID family; see
{{sec-tight-coupling-control}} for the conformance framing.

When using the TRUST_STATEID control protocol defined in
{{sec-tight-coupling-control}}, the metadata server and a storage
device establish that they can use it via a two-part handshake,
both parts of which MUST succeed before the metadata server may
issue TRUST_STATEID against that storage device for production
traffic:

Capability probe:
:  At control-session setup the metadata
   server sends a TRUST_STATEID against the anonymous stateid
   (see {{sec-tight-coupling-probe}}).  A storage device that
   supports tight coupling MUST reject the probe with
   NFS4ERR_INVAL; a storage device that does not support tight
   coupling returns NFS4ERR_NOTSUPP and the metadata server
   falls back to loose coupling.  The metadata server records
   result per storage device by setting the
   FFV2_COUPLING_TRUSTED_STATEID bit in ffv2dv_coupling on
   success (leaving the bit clear on NFS4ERR_NOTSUPP).

Control-session gating:
:  The metadata server presents
   EXCHGID4_FLAG_USE_PNFS_MDS at EXCHANGE_ID when it opens the
   control session to the storage device
   (see {{sec-tight-coupling-control-session}}).  The storage
   device MUST reject any incoming TRUST_STATEID,
   REVOKE_STATEID, or BULK_REVOKE_STATEID that does not arrive
   on such a session with NFS4ERR_PERM.  This is the
   authorization mechanism that distinguishes the metadata
   server from ordinary pNFS clients, which connect with
   EXCHGID4_FLAG_USE_PNFS_DS or EXCHGID4_FLAG_USE_NON_PNFS and
   are therefore structurally unable to invoke these operations.

Given this basic structure, locking-related operations are handled
as follows:

-  OPENs are dealt with primarily on the metadata server.  Stateids
   are selected by the metadata server and associated with the client
   ID describing the client's connection to the metadata server.
   The metadata server needs to interact with the storage device to
   locate the file to be opened and to make the storage device aware of
   the association between the metadata-server-chosen stateid and the
   client and openowner that it represents.  OPEN_DOWNGRADE and CLOSE
   are executed initially on the metadata server, but the state change
   MUST be propagated to the storage device.

-  Advisory byte range locks can be implemented locally on the
   metadata server.  As in the case of OPENs, the stateids associated
   with byte range locks are assigned by the metadata server and are
   available for use on the metadata server.  Because I/O operations
   are allowed to present lock stateids, the metadata server needs the
   ability to make the storage device aware of the association between
   the metadata-server-chosen stateid and the corresponding open stateid
   it is associated with.

-  Mandatory byte range locks can be supported when both the metadata
   server and the storage devices have the appropriate support.  As in
   the case of advisory byte range locks, these are assigned by the
   metadata server and are available for use on the metadata server.
   To enable mandatory lock enforcement on the storage device, the
   metadata server needs the ability to make the storage device aware
   of the association between the metadata-server-chosen stateid and
   the client, openowner, and lock (i.e., lockowner, byte range, and
   lock-type) that it represents.  Because I/O operations are allowed
   to present lock stateids, this information needs to be propagated to
   all storage devices to which I/O might be directed rather than only
   to storage device that contain the locked region.

-  Delegations are assigned by the metadata server that initiates
   recalls when conflicting OPENs are processed.  Because I/O operations
   are allowed to present delegation stateids, the metadata server
   requires the ability:

   1.  to make the storage device aware of the association between
       the metadata-server-chosen stateid and the filehandle and
       delegation type it represents

   2.  to break such an association.

-  TEST_STATEID is processed locally on the metadata server, without
   storage device involvement.

-  FREE_STATEID is processed on the metadata server, but the metadata
   server requires the ability to propagate the request to the
   corresponding storage devices.

Scope of this document.  The wire-level control-protocol
operations this document defines -- TRUST_STATEID,
REVOKE_STATEID, and BULK_REVOKE_STATEID
({{sec-tight-coupling-control}}) -- carry only the association
between a layout stateid, the ffv2m_client_id the metadata
server assigned to the client, and (for TRUST_STATEID) the
iomode, expiry, and principal.  They do NOT carry openowner,
lockowner, byte range, lock-type, the identity of an
associated open stateid, or delegation-type.

The bullets above (OPEN state, advisory byte range lock state,
mandatory byte range lock state, and delegation state)
enumerate the associations the storage device would need in
order to enforce POSIX-conformant OPEN, byte range locking,
and delegation semantics against per-client identity rather
than against the loose coupling synthetic uid/gid.  These are
inherited from the general tight coupling locking model in
Section 2.3 of {{RFC8435}}.  Trusted-stateid tight coupling as
defined by this document satisfies these associations only
for the layout stateid; a deployment that requires mandatory
byte range locking, delegation recall, or the finer-grained
open/lock stateid associations MUST use a back-end control
protocol between the metadata server and the storage device
that carries this state.  Such a back-end control protocol is
out of scope for this document.

A deployment that does not need those finer-grained
associations -- for example, a flexible file v2 layout
deployment whose per-file access-control decisions live entirely
on the metadata server
and whose storage devices see only chunk-level CAS on layout
stateids -- is conformant with the trusted stateid tight coupling
model using only the TRUST_STATEID family.  That
scope covers the layout stateid and, transitively via
ffv2m_client_id, the writer identity carried on CHUNK
operations.

Because the client will possess and use stateids valid on the storage
device, there will be a client lease on the storage device, and the
possibility of lease expiration does exist.  The best approach for the
storage device is to retain these locks as a courtesy.  However, if it
does not do so, control protocol facilities need to provide the means
to synchronize lock state between the metadata server and storage device.

Clients will also have leases on the metadata server that are subject
to expiration.  In dealing with lease expiration, the metadata server
would be expected to use control protocol facilities enabling it to
invalidate revoked stateids on the storage device.  In the event the
client is not responsive, the metadata server may need to use fencing
to prevent revoked stateids from being acted upon by the storage device.

##  Tight Coupling Control Protocol {#sec-tight-coupling-control}

When an NFSv4.2 storage device participates in a tightly coupled
deployment, the metadata server and the storage devices need a
control protocol that:

1.  registers the layout stateid with each storage device so the
    storage device can validate client I/O independently; and

2.  revokes trust promptly when the metadata server withdraws the
    client's authorization -- for example, on CB_LAYOUTRECALL
    timeout, lease expiry, or layout return after error.

This specification defines one such control protocol, designated
trusted stateid tight coupling, as three new NFSv4.2 operations:
TRUST_STATEID ({{sec-TRUST_STATEID}}), REVOKE_STATEID
({{sec-REVOKE_STATEID}}), and BULK_REVOKE_STATEID
({{sec-BULK_REVOKE_STATEID}}).  These operations are sent by the
metadata server to each storage device over a dedicated control
session (see {{sec-tight-coupling-control-session}}) and MUST NOT
be sent by pNFS clients.

Other tight coupling control protocols may exist or be defined
elsewhere.  Existing pNFS server implementations with established
back-end control protocols -- for example, dCache {{DCACHE}},
which has its own control protocol between its metadata
service and its data servers -- satisfy the tightly coupled
locking model
({{sec-state-locking}}) through their own mechanisms and are
conformant under this specification provided they meet the
functional capabilities described there.  Such implementations
need not adopt the TRUST_STATEID family, and their interoperability
with the TRUST_STATEID family is outside the scope of this
document.

A storage device that does not implement TRUST_STATEID is treated
as not supporting trusted stateid tight coupling specifically; the
capability probe in {{sec-tight-coupling-probe}} detects this and
the metadata server falls back to loose coupling
({{sec-tight-coupling-compat}}) or, if the storage device's own
control protocol is in use, that protocol governs.  Within the
remainder of {{sec-tight-coupling-control}} and its subsections,
unqualified references to "tight coupling" or "tightly coupled"
refer to the trusted stateid variant defined here.

The receiver of these operations is any server the metadata
server delegates client-I/O admission to.  In this document that
is the storage device (data server).  The same mechanism applies to
a proxy server -- a proxy server may or may not additionally act
as a data server, but in either role it needs the metadata server
to register a layout stateid before it can admit client I/O.
Where this section says "storage device," read it as "storage
device, or proxy server"; the flag check and the three operations
are identical for both roles.

###  Capability Discovery {#sec-tight-coupling-probe}

A storage device indicates support for trusted stateid tight
coupling implicitly, by processing TRUST_STATEID rather than
returning NFS4ERR_NOTSUPP.  (A storage device that supports a
non-TRUST_STATEID form of tight coupling but not the
trusted stateid variant defined here will return NFS4ERR_NOTSUPP
on this probe; from this specification's perspective it is
treated the same as a storage device that does not support tight
coupling at all.)  The metadata server probes each storage device
during control-session setup:

~~~
SEQUENCE + PUTROOTFH + TRUST_STATEID(
    tsa_layout_stateid = ANONYMOUS_STATEID,
    tsa_client_id      = 0,
    tsa_iomode         = LAYOUTIOMODE4_READ,
    tsa_expire         = 0,
    tsa_principal      = "")
~~~
{: #fig-trust-stateid-probe title="TRUST_STATEID capability probe"}

The anonymous stateid is used deliberately: a correctly implemented
storage device MUST reject it (see {{sec-TRUST_STATEID}}), so the
probe cannot accidentally register garbage in the trust table.  The
metadata server interprets the probe response as follows:

NFS4ERR_NOTSUPP:
:  trusted stateid tight coupling is not supported on this
   storage device.  The metadata server leaves the
   FFV2_COUPLING_TRUSTED_STATEID bit clear in ffv2dv_coupling
   for this storage device.  If ffv2dv_coupling has no other
   tight coupling bits set for this storage device, the
   metadata server falls back to the synthetic-uid model
   (anonymous stateid plus fencing).

NFS4ERR_INVAL:
:  trusted stateid tight coupling is supported.  The anonymous
   stateid was correctly rejected.  The metadata server sets the
   FFV2_COUPLING_TRUSTED_STATEID bit in ffv2dv_coupling for this
   storage device.

NFS4_OK:
:  the storage device accepted an anonymous stateid into
   its trust table.  This is a storage device bug.  The metadata
   server MAY treat the capability as confirmed to avoid
   downgrading to loose coupling, but it MUST immediately issue
   REVOKE_STATEID to remove the bogus entry.

The capability is recorded per storage device, not per file.
Partial support across a mirror set is permitted: each
ffv2_device_versions4 entry returned by GETDEVICEINFO carries
its own ffv2dv_coupling value, set independently.

###  Control Session {#sec-tight-coupling-control-session}

The metadata server establishes an NFSv4.2 session to each
tight coupling capable storage device at startup.  On this session
the metadata server acts as the storage device's client and
presents EXCHGID4_FLAG_USE_PNFS_MDS in its EXCHANGE_ID args.

The storage device MUST verify that any incoming TRUST_STATEID,
REVOKE_STATEID, or BULK_REVOKE_STATEID compound arrives on a
session whose owning client presented EXCHGID4_FLAG_USE_PNFS_MDS
in its EXCHANGE_ID args.  Requests that arrive on any other
session MUST be rejected with NFS4ERR_PERM.  This is the sole
access control on these operations; a pNFS client connecting to
the storage device does not present EXCHGID4_FLAG_USE_PNFS_MDS
and therefore cannot invoke them.

The EXCHGID4_FLAG_USE_PNFS_MDS check replaces any path- or
filehandle-level gating.  TRUST_STATEID operates on a filehandle
that may be any file on the storage device, and the metadata
server is the sole authority that can legitimately speak this
protocol.

Because the EXCHGID4_FLAG_USE_PNFS_MDS check relies on the
owning client's self-declaration at EXCHANGE_ID time, the
storage device cannot by itself distinguish a legitimate
metadata server from any other host that sets the flag.  The
wire protocol provides no primitive that binds a request to a
particular pNFS role; the flag is a hint whose operational
meaning is only as strong as the deployment's authentication
or isolation choice.

The deployment requirement is that only entities the
deployment considers legitimate metadata servers can (a)
establish a control session with EXCHGID4_FLAG_USE_PNFS_MDS
against the storage device and (b) invoke TRUST_STATEID,
REVOKE_STATEID, or BULK_REVOKE_STATEID on it.  Deployments
have historically satisfied this requirement using one or more
of the following mechanisms; the wire protocol does not
prescribe which is chosen:

- RPCSEC_GSS with a machine principal that the storage device
  has been configured to accept as a metadata server.  The
  storage device validates the principal against a local
  policy list before accepting the flag.

- TLS ({{RFC9289}}) with a client certificate that the storage
  device has been configured to accept as a metadata server.
  The storage device validates the certificate against a local
  policy list before accepting the flag.

- Network-path isolation: the control-session path runs on a
  network segment (dedicated management VLAN, private link,
  or similar) that pNFS clients cannot reach, so only
  configured metadata servers can open a session at all.

- Operating-system-level filesystem access control on the
  storage device: the underlying export that backs the pNFS
  data files is configured so that only the metadata server's
  OS identity (typically root, or a dedicated privileged uid)
  can access it.  A pNFS client that reaches the storage
  device but presents any other uid receives permission
  errors before it can invoke any operation, control-plane
  or otherwise.

A single host MAY legitimately act in multiple pNFS roles
against the same storage device -- for example, an entity
that is a metadata server for one export and a plain pNFS
client for another.  The wire protocol does not distinguish
these roles at the operation level; the deployment is
responsible for arranging that the storage device can tell
them apart, typically by using distinct credentials or
distinct sessions for the two roles (each session presents
EXCHGID4_FLAG_USE_PNFS_MDS according to the role the entity
is acting in on that session).

The security consequences of these choices -- what an
unauthenticated attacker can invoke if none of the mechanisms
above is deployed, and what an authenticated caller can still
achieve by misrepresenting role -- are discussed in
{{sec-security-trust-stateid}}.

###  Flow at LAYOUTGET {#sec-tight-coupling-layoutget}

For each new or refreshed layout segment, the metadata server:

1.  chooses the layout stateid (as it would without tight coupling);

2.  identifies the trusted stateid capable storage devices in
    the mirror set (those for which ffv2dv_coupling has the
    FFV2_COUPLING_TRUSTED_STATEID flag set);

3.  fans out TRUST_STATEID to each such storage device,
    specifying the layout stateid, the layout iomode, a
    tsa_expire derived from the metadata server's lease (see
    {{sec-tight-coupling-lease}}), and the client's authenticated
    identity in tsa_principal;

4.  waits for all fan-outs to complete (or reach their per-storage-device timeout) before returning the layout.

If every storage device in the mirror set rejects the TRUST_STATEID
fan-out, the metadata server MUST NOT return the layout; instead it
returns NFS4ERR_LAYOUTTRYLATER.  If some storage devices accept and
others reject, the metadata server MAY return a layout covering
only the accepting storage devices, provided the accepting subset
still meets the minimum servable coverage for the file's
encoding: at least one replica for FFV2_ENCODING_PASSTHROUGH or
FFV2_ENCODING_MIRRORED, or at least k of the k+m storage
devices for an erasure-coded encoding at (k, m) parameters.
If it does not, the metadata server MUST NOT return a partial
layout and instead returns NFS4ERR_LAYOUTTRYLATER as in the
all-reject case.  A storage device that returns
NFS4ERR_DELAY is retried until either success or the metadata
server's LAYOUTGET-response budget is exhausted.  If a storage
device returns NFS4ERR_NOTSUPP at this time (having accepted
the probe earlier), the metadata server MUST clear the
FFV2_COUPLING_TRUSTED_STATEID flag in ffv2dv_coupling for this
storage device.  If no tight coupling flags remain set for
this device, the metadata server falls back to the
synthetic-uid model and re-issues the layout accordingly.

###  Principal Binding and the Kerberos Gap {#sec-tight-coupling-principal}

The flexible file v1 layout has a known gap: a client authenticated
to the metadata server with Kerberos has no way to present the same
authenticated identity to the storage device, because flexible file
v1 layouts carry only ffds_user / ffds_group (POSIX uid/gid for
AUTH_SYS).  A strict Kerberos deployment on the flexible file v1
layout must either allow AUTH_SYS from the metadata server's subnet
or accept that the flexible file v1 layout's data path is not
Kerberos-protected.

The tsa_principal field in TRUST_STATEID closes that gap.  When a
client authenticates to the metadata server as a Kerberos
principal (e.g., alice@REALM), the metadata server passes that
principal name to each storage device in tsa_principal.  The
storage device then enforces a two-part check on each CHUNK
operation that presents the layout stateid:

a.  the stateid is in the trust table and has not expired; and

b.  the caller's authenticated identity (the RPCSEC_GSS display
    name on the CHUNK compound) matches tsa_principal.

Both conditions MUST hold.  On principal mismatch the storage
device MUST return NFS4ERR_ACCESS -- the semantics are "you do
not have an authorized layout for this file", which matches the
existing fencing error and avoids the confusion of
NFS4ERR_WRONGSEC (which directs the client to re-authenticate
with a different flavor) or NFS4ERR_BAD_STATEID (which directs
the client to return the layout).

The metadata server MUST populate tsa_principal with the
RPCSEC_GSS display name of the authenticated client when the
client authenticated to the metadata server via RPCSEC_GSS.  The
metadata server MUST set tsa_principal to the empty string only
for AUTH_SYS and TLS clients (for which there is no server-verified per-user identity).  Setting tsa_principal to the empty
string for an RPCSEC_GSS client disables the principal check on
the storage device and silently re-opens the flexible file v1 layout
Kerberos gap; it is a metadata server bug, not a protocol option.

If tsa_principal is the empty string, no principal check applies.
This is the expected setting for AUTH_SYS and TLS clients:

-  AUTH_SYS clients have no server-verified identity.  The
   storage device's stateid check and the AUTH_SYS uid/gid on the
   data file together constitute the authorization.  In a tightly
   coupled deployment the data file's owner/group need not match
   the metadata file's, since ffv2ds_user and ffv2ds_group are
   ignored (see {{sec-ffv2-mirror4}}).

-  TLS clients have transport-layer authentication via mutual TLS
   ({{RFC9289}}).  The TLS layer authenticates the client machine;
   the stateid check confirms the metadata server authorized that
   machine to access this file.  The machine-level authentication
   is handled beneath the RPC layer and is not reflected in
   tsa_principal.  Opportunistic TLS (STARTTLS without certificate
   verification) provides encryption but not authentication, and
   therefore has the same authorization properties as plain
   AUTH_SYS.

When a client's I/O is routed through a proxy server -- that
is, the layout the metadata server returns to the client has
FFV2_DS_FLAGS_PROXY set on the proxy's ffv2_data_server4 entry --
the storage device observes CHUNK operations arriving from the
proxy server's address rather than from the client directly.  The tsa_principal the metadata server
populates in TRUST_STATEID is the principal the storage device
will observe on those CHUNK operations, and {{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}'s credential-forwarding rules (in particular rule 1,
"Credential pass-through") require the proxy server to forward the
client's credentials verbatim on every CHUNK operation it issues
on the client's behalf.  Therefore:

-  For an RPCSEC_GSS client whose I/O is proxied through a proxy server,
   the metadata server MUST set tsa_principal to the client's
   RPCSEC_GSS display name (identical to the non-proxied case).
   The storage device's principal check on CHUNK operations will
   match against the client's principal on the forwarded
   compound, not the proxy server's service identity.

-  For an AUTH_SYS client whose I/O is proxied through a proxy server,
   the metadata server MUST set tsa_principal to the empty
   string (identical to the non-proxied case).  The proxy server forwards
   the client's AUTH_SYS uid/gid; the storage device's stateid
   check plus the forwarded AUTH_SYS uid/gid constitute the
   authorization.

The metadata server MUST NOT set tsa_principal to the proxy server's own
service principal.  Doing so would require the proxy server to
authenticate to the storage device as itself (bypassing
credential forwarding) which is explicitly prohibited by rule 4 of {{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}} ("proxy server service identity is for the
control plane only").

###  Client-Detected Trust Gap {#sec-tight-coupling-trust-gap}

A window exists between a successful TRUST_STATEID fan-out and
the client's first I/O to the storage device.  A transient failure
may cause the storage device to forget or reject the entry before
the client's first CHUNK_WRITE arrives.  The client cannot
distinguish this case from legitimate revocation; both surface as
NFS4ERR_BAD_STATEID on the storage device.

The recovery path:

1.  The client sends LAYOUTERROR(layout_stateid, device_id,
    NFS4ERR_BAD_STATEID) to the metadata server.

2.  The metadata server retries TRUST_STATEID against the
    reporting storage device.  If the retry succeeds, the
    metadata server returns NFS4_OK for LAYOUTERROR.  The client
    retries the original I/O.

3.  If the retry fails -- the storage device is unreachable or
    returns a hard error -- the metadata server issues
    CB_LAYOUTRECALL for that device and the client returns the
    layout segment covering that storage device.  The client is
    expected to re-request via LAYOUTGET.

This is the same LAYOUTERROR path used for NFS4ERR_ACCESS or
NFS4ERR_PERM in the fencing model (see {{sec-Fencing-Clients}}),
with the metadata server's action being "retry TRUST_STATEID"
instead of "rotate uid/gid".

###  Lease and Renewal {#sec-tight-coupling-lease}

tsa_expire in a TRUST_STATEID request is a wall-clock expiry
instant expressed as an nfstime4.  The metadata server MUST set
tsa_expire to the current wall-clock time plus the metadata
server's client lease period.

Clock-synchronization assumption: the metadata server and each
storage device MUST maintain wall-clock synchronization within
one lease period, e.g., via NTP {{RFC5905}} or an equivalent
mechanism.  Under this assumption, a tsa_expire computed by the
metadata server and evaluated by the storage device is
interpreted consistently within the storage device's local
clock.  Deployments unable to guarantee sub-lease-period clock
synchronization MUST either (a) shorten the effective TRUST_STATEID
lease so it exceeds the worst-case skew by at least 2x, or (b)
route I/O through the metadata server as the fallback path (no
tight coupling control session, no TRUST_STATEID) so lease
enforcement stays on the metadata server's clock alone.  A storage device that
detects sustained clock divergence from the metadata server
(e.g., via periodic wall-clock exchange as part of its
tight coupling control-session heartbeats) SHOULD log the
divergence and MAY refuse further TRUST_STATEID entries with
NFS4ERR_DELAY until the divergence is corrected.

The metadata server MUST re-issue TRUST_STATEID for an entry
before tsa_expire while the corresponding layout is outstanding.
The RECOMMENDED trigger is: when an entry is within half the
lease period of its tsa_expire, re-issue TRUST_STATEID with a
refreshed tsa_expire.  Renewing on every SEQUENCE that keeps the
layout stateid alive is correct but produces
metadata-server-to-storage-device traffic proportional to the
client's SEQUENCE rate, which is undesirable in steady state.

If an entry expires on the storage device before the metadata
server renews it -- for example, because the metadata server is
partitioned from the storage device for longer than the lease
period -- the storage device MUST return NFS4ERR_BAD_STATEID to
the client on the next CHUNK operation.  The client returns the
layout to the metadata server and re-requests.  This is the same
recovery path as the trust gap described above.

###  Storage Device Crash Recovery {#sec-tight-coupling-ds-crash}

A storage device MAY persist its trust table across restarts.  An
implementation that does so MUST also persist its server-instance
identity, returning the same eir_server_owner.so_minor_id on
EXCHANGE_ID after the restart (per {{RFC8881}} S18.35), so that
clients and the metadata server observe the device as
continuously available and the persisted trust entries remain
valid against the layout stateids that were issued before the
restart.

A storage device that does NOT persist its trust table empties
the table on restart and MUST present a new server instance
(incremented so_minor_id) so that clients detect the restart.
The remainder of this section describes the recovery path for
the volatile case.

The client detects a volatile storage device restart via
NFS4ERR_BADSESSION or NFS4ERR_STALE_CLIENTID on its data server
session.  The client returns the affected layout segment to the
metadata server via LAYOUTRETURN and re-requests via LAYOUTGET.
The metadata server then fans out fresh TRUST_STATEID operations
to the recovered storage device.

Planned storage device restarts (software upgrade, etc.) SHOULD
drain in-flight CHUNK operations before shutting down.

###  Metadata Server Crash Recovery {#sec-tight-coupling-mds-crash}

A metadata server MAY persist all its trust-management state
across restarts.  An implementation that does so MUST also
persist its server-instance identity, returning the same
eir_server_owner.so_minor_id on EXCHANGE_ID after the restart
(per {{RFC8881}} S18.35), so that storage devices observe the
metadata server as continuously available and accept incoming
TRUST_STATEID and REVOKE_STATEID operations against the existing
trust entries without revalidation.  No grace period is required.

A metadata server that presents a new server instance
(incremented so_minor_id) on restart follows the recovery path
in the remainder of this section.

When the metadata server restarts as a new instance, its control
sessions to the storage devices are lost.  Trust entries remain
on the storage devices until tsa_expire, but the metadata server
is no longer renewing them; the entries are effectively orphaned
until the metadata server completes grace.

When the metadata server reconnects to a storage device with a
new boot epoch -- that is, the EXCHANGE_ID returns a new server
owner on the storage device's view of the metadata server -- the
storage device SHOULD mark all trust entries established under
the prior metadata-server epoch as pending-revalidation.  While an
entry is pending-revalidation:

-  I/O that presents the entry's stateid MUST receive
   NFS4ERR_DELAY, not NFS4ERR_BAD_STATEID.  NFS4ERR_DELAY tells
   the client to retry with the same stateid -- the metadata
   server is recovering and may yet revalidate the entry.
   NFS4ERR_BAD_STATEID would instead cause the client to return
   the layout immediately, producing a thundering herd against
   the metadata server during grace.

-  An entry remains pending-revalidation until the metadata
   server either re-issues TRUST_STATEID for it (which transitions
   it back to trusted) or until the entry's tsa_expire elapses
   (which removes it).

The metadata server's recovery sequence is:

1.  Reconnect to each storage device and establish a fresh
    control session.

2.  Optionally issue BULK_REVOKE_STATEID with an all-zeros
    clientid to each storage device.  This clears the prior trust
    table eagerly; skipping this step is correct, because orphan
    entries expire via tsa_expire.

3.  Enter grace and accept RECLAIM operations from clients.  For
    each reclaimed layout, fan out TRUST_STATEID to the relevant
    storage devices.

4.  Exit grace.  Clients that did not reclaim in time have their
    state revoked; the metadata server issues REVOKE_STATEID or
    BULK_REVOKE_STATEID on their behalf.

Metadata servers SHOULD persist the set of outstanding
TRUST_STATEID entries (clientid, layout stateid, storage device
address, tsa_expire) to stable storage.  With this persistence
the metadata server can re-issue TRUST_STATEID for all known
entries immediately upon reconnecting to each storage device,
before clients begin reclaiming.  This shrinks the window during
which the storage device returns NFS4ERR_DELAY for client I/O.
Persistence is a latency optimization, not a correctness
requirement: the re-layout path handles recovery in all cases.

###  Backward Compatibility {#sec-tight-coupling-compat}

-  NFSv3 storage devices are unchanged.  They are always treated
   as loosely coupled; TRUST_STATEID does not exist on NFSv3
   servers.

-  NFSv4.2 storage devices for which the TRUST_STATEID probe
   returns NFS4ERR_NOTSUPP are treated as loosely coupled;
   fencing is the only revocation mechanism, the same as for
   NFSv3.

-  NFSv4.2 storage devices for which the probe returns
   NFS4ERR_INVAL support tight coupling; the metadata server uses
   TRUST_STATEID at LAYOUTGET and REVOKE_STATEID or
   BULK_REVOKE_STATEID for revocation instead of fencing.

A single deployment MAY contain a mix of tight-coupled and
loose-coupled storage devices; each is negotiated independently
via the probe.

#  Device Addressing and Discovery

Data operations to a storage device require the client to know the
network address of the storage device.  The NFSv4.1+ GETDEVICEINFO
operation (Section 18.40 of {{RFC8881}}) is used by the client to
retrieve that information.

##  ffv2_device_addr4 {#sec-ff_device_addr4}

The ffv2_device_addr4 data structure (see {{fig-ff_device_addr4}})
is returned by the server as the layout type specific opaque field
da_addr_body in the device_addr4 structure by a successful GETDEVICEINFO
operation for LAYOUT_FLEX_FILES_V2.

ffv2_device_addr4 and ffv2_device_versions4 are the flexible
file v2 layout counterparts to ff_device_addr4 and
ff_device_versions4 in {{RFC8435}}.  The two structures are
similar in shape but carry a flexible-file-v2-specific enrichment:
the boolean ffdv_tightly_coupled from RFC 8435 has been widened
to the uint32_t bitfield ffv2dv_coupling, which lets a storage
device advertise more than one coupling capability at the same
time ({{sec-tight-coupling-control}}).  Because the field type
has changed, the flexible file v2 layout structs are named
distinctly to avoid confusion with the RFC 8435 originals.

~~~ xdr
   /*
    * ffv2dv_coupling flags -- bitwise-OR of the values below.
    *
    * A zero value (no flags set) indicates the loose coupling
    * synthetic-uid model of RFC 8435: the client presents an
    * anonymous stateid and a synthetic uid issued by the
    * metadata server, and the storage device validates access
    * via that synthetic uid (see {{sec-Fencing-Clients}}).  The constant
    * FFV2_COUPLING_SYNTHETIC_UIDS is provided as a
    * documentation aid.
    *
    * FFV2_COUPLING_TIGHTLY_COUPLED indicates that the storage
    * device participates in tight coupling with the metadata
    * server via a back-end control protocol between the
    * metadata server and the data servers; the
    * specific mechanism is deployment-configured and outside
    * the scope of this document.
    *
    * FFV2_COUPLING_TRUSTED_STATEID indicates that the storage
    * device implements the TRUST_STATEID, REVOKE_STATEID, and
    * BULK_REVOKE_STATEID operations defined in
    * {{sec-tight-coupling-control}}.
    *
    * The two tight coupling flags are orthogonal: a storage
    * device MAY set either, both, or neither.  See
    * {{sec-tight-coupling-control}} for the semantics of each
    * combination.
    */
   const FFV2_COUPLING_SYNTHETIC_UIDS  = 0x00000000;
   const FFV2_COUPLING_TIGHTLY_COUPLED = 0x00000001;
   const FFV2_COUPLING_TRUSTED_STATEID = 0x00000002;

   struct ffv2_device_versions4 {
           uint32_t        ffv2dv_version;
           uint32_t        ffv2dv_minorversion;
           uint32_t        ffv2dv_rsize;
           uint32_t        ffv2dv_wsize;
           uint32_t        ffv2dv_coupling;
   };
~~~
{: #fig-ff_device_versions4 title="ffv2_device_versions4"}

~~~ xdr
   struct ffv2_device_addr4 {
           multipath_list4       ffv2da_netaddrs;
           ffv2_device_versions4 ffv2da_versions<>;
   };
~~~
{: #fig-ff_device_addr4 title="ffv2_device_addr4"}

The ffv2da_netaddrs field is used to locate the storage device.  It
MUST be set by the server to a list holding one or more of the device
network addresses.

The ffv2da_versions array allows the metadata server to present choices
as to NFS version, minor version, and coupling capabilities to the
client.  The ffv2dv_version and ffv2dv_minorversion represent the NFS
protocol to be used to access the storage device.  This layout
specification defines the semantics for ffv2dv_versions 3 and 4.  If
ffv2dv_version equals 3, then the server MUST set ffv2dv_minorversion to
0 and ffv2dv_coupling to FFV2_COUPLING_SYNTHETIC_UIDS.  The client MUST
then access the storage device using the NFSv3 protocol {{RFC1813}}.
If ffv2dv_version equals 4, then the server MUST set ffv2dv_minorversion
to 1 or 2, and the client MUST access the storage device using NFSv4
with the specified minor version.

Three additional constraints narrow the valid set of
(ffv2dv_version, ffv2dv_minorversion, ffv2dv_coupling) tuples
in specific cases:

-  When a mirror's encoding type uses CHUNK operations (that
   is, any FFV2_ENCODING_* value other than
   FFV2_ENCODING_PASSTHROUGH), the corresponding storage device
   MUST be advertised with ffv2dv_version = 4 and
   ffv2dv_minorversion = 2.  CHUNK operations are NFSv4.2 ops
   defined in this document; NFSv3 and NFSv4.1 storage devices
   cannot serve a non-PASSTHROUGH mirror.

-  When ffv2dv_coupling has the FFV2_COUPLING_TRUSTED_STATEID
   flag set, the storage device MUST be advertised with
   ffv2dv_version = 4 and ffv2dv_minorversion = 2.  The
   TRUST_STATEID family of operations is defined as NFSv4.2;
   NFSv4.1 storage devices cannot participate in
   trusted stateid tight coupling.

-  When a mirror's encoding type uses CHUNK operations, the
   corresponding storage device MUST be advertised with
   ffv2dv_coupling having at least one tight coupling flag set
   (FFV2_COUPLING_TIGHTLY_COUPLED or
   FFV2_COUPLING_TRUSTED_STATEID, or both).  The chunk
   lifecycle depends on the metadata-server-registered layout
   stateid and the per-client identity conveyed to the data
   server ({{sec-CHUNK_WRITE}}); a synthetic-uid-only storage
   device has neither the trust-table entry required to
   validate a presented stateid nor the client-id binding
   required to authorize the writer, and therefore cannot
   serve a non-PASSTHROUGH mirror.

PASSTHROUGH is the only encoding that admits loose coupling
(FFV2_COUPLING_SYNTHETIC_UIDS); every non-PASSTHROUGH encoding
requires ffv2dv_version = 4, ffv2dv_minorversion = 2, and at
least one tight coupling flag set in ffv2dv_coupling.
PASSTHROUGH itself may be advertised under any of the
following (ffv2dv_version, ffv2dv_minorversion) tuples:
(3, 0), (4, 1), or (4, 2); the first two of these tuples
are valid only for PASSTHROUGH under
FFV2_COUPLING_SYNTHETIC_UIDS, because they precede or lack
the NFSv4.2 features on which the CHUNK operations and the
TRUST_STATEID family depend.

Note that while the client might determine that it cannot use any of
the configured combinations of ffv2dv_version, ffv2dv_minorversion, and
ffv2dv_coupling, when it gets the device list from the metadata
server, there is no way to indicate to the metadata server as to
which device it is version incompatible.  However, if the client
waits until it retrieves the layout from the metadata server, it can
at that time clearly identify the storage device in question (see
{{sec-version-errors}}).

The ffv2dv_rsize and ffv2dv_wsize are used to communicate the maximum
rsize and wsize supported by the storage device.  As the storage
device can have a different rsize or wsize than the metadata server,
the ffv2dv_rsize and ffv2dv_wsize allow the metadata server to
communicate that information on behalf of the storage device.

ffv2dv_coupling informs the client which tight coupling
capabilities the storage device supports.  The two
tight coupling flags are orthogonal:

- FFV2_COUPLING_TIGHTLY_COUPLED asserts that the deployment
  has a back-end control protocol between the metadata server
  and the data servers (the RFC 8435 general tight coupling
  concept); this document does not specify what that protocol
  is or how it operates.  A dCache {{DCACHE}} deployment, for
  example, would set this flag based on its own metadata-server
  / pool control plane.

- FFV2_COUPLING_TRUSTED_STATEID asserts that the storage
  device implements the TRUST_STATEID, REVOKE_STATEID, and
  BULK_REVOKE_STATEID operations defined in this document
  ({{sec-tight-coupling-control}}).  This is the tight coupling
  mechanism this specification adds; a storage
  device MUST NOT advertise this flag until the metadata
  server has confirmed the capability via the probe in
  {{sec-tight-coupling-probe}}.

A storage device MAY advertise either, both, or neither
flag.  When both are set, the deployment supports two
tight coupling paths concurrently and MAY use either for a
given operation.  When neither is set (ffv2dv_coupling equals
FFV2_COUPLING_SYNTHETIC_UIDS), the storage device is loosely
coupled and the RFC 8435 synthetic-uid model applies (see
{{sec-Fencing-Clients}}).

If ffv2dv_coupling has no tight coupling flag set, then the
client MUST commit writes to the storage devices for the file
before sending a
LAYOUTCOMMIT to the metadata server.  That is, the writes MUST be
committed by the client to stable storage via issuing WRITEs with
stable_how == FILE_SYNC or by issuing a COMMIT after WRITEs with
stable_how != FILE_SYNC (see Section 3.3.7 of {{RFC1813}}).

##  Storage Device Multipathing

The flexible file v2 layout supports multipathing to multiple
storage device addresses.  Storage-device-level multipathing is used
for bandwidth scaling via trunking and for higher availability of use
in the event of a storage device failure.  Multipathing allows the
client to switch to another storage device address that may be that
of another storage device that is exporting the same data stripe
unit, without having to contact the metadata server for a new layout.

To support storage device multipathing, ffv2da_netaddrs contains an
array of one or more storage device network addresses.  This array
(data type multipath_list4) represents a list of storage devices
(each identified by a network address), with the possibility that
some storage device will appear in the list multiple times.

The client is free to use any of the network addresses as a
destination to send storage device requests.  If some network
addresses are less desirable paths to the data than others, then the
metadata server SHOULD NOT include those network addresses in
ffv2da_netaddrs.  If less desirable network addresses exist to provide
failover, the RECOMMENDED method to offer the addresses is to provide
them in a replacement device-ID-to-device-address mapping or a
replacement device ID.  When a client finds no response from the
storage device using all addresses available in ffv2da_netaddrs, it
SHOULD send a GETDEVICEINFO to attempt to replace the existing
device-ID-to-device-address mappings.  If the metadata server detects
that all network paths represented by ffv2da_netaddrs are unavailable,
the metadata server SHOULD send a CB_NOTIFY_DEVICEID (if the client
has indicated it wants device ID notifications for changed device
IDs) to change the device-ID-to-device-address mappings to the
available addresses.  If the device ID itself will be replaced, the
metadata server SHOULD recall all layouts with the device ID and thus
force the client to get new layouts and device ID mappings via
LAYOUTGET and GETDEVICEINFO.

Generally, if two network addresses appear in ffv2da_netaddrs, they
will designate the same storage device.  When the storage device is
accessed over NFSv4.1 or a higher minor version, the two storage
device addresses will support the implementation of client ID or
session trunking (the latter is RECOMMENDED) as defined in {{RFC8881}}.
The two storage device addresses will share the same server owner or
major ID of the server owner.  It is not always necessary for the two
storage device addresses to designate the same storage device with
trunking being used.  For example, the data could be read-only, and
the data consist of exact replicas.

#  Flexible File Version 2 Layout Type

The original layouttype4 introduced in {{RFC5662}} is extended as shown in
{{fig-orig-layout}}.  The layout_content4 and layout4 structures are
reused unchanged from {{RFC5662}}; the layouttype4 enum is extended
with the new LAYOUT4_FLEX_FILES_V2 value.  The full enum and
surrounding structures below are reproduced for reader
convenience; only the new constant LAYOUT4_FLEX_FILES_V2 is part
of the XDR extracted from this document (see
{{fig-orig-layout-extract}}).

~~~ xdr
       enum layouttype4 {
           LAYOUT4_NFSV4_1_FILES   = 1,
           LAYOUT4_OSD2_OBJECTS    = 2,
           LAYOUT4_BLOCK_VOLUME    = 3,
           LAYOUT4_FLEX_FILES      = 4,
           LAYOUT4_SCSI            = 5,
           LAYOUT4_FLEX_FILES_V2   = 6
       };

       struct layout_content4 {
           layouttype4             loc_type;
           opaque                  loc_body<>;
       };

       struct layout4 {
           offset4                 lo_offset;
           length4                 lo_length;
           layoutiomode4           lo_iomode;
           layout_content4         lo_content;
       };
~~~
{: #fig-orig-layout title="The original layout type (illustrative; reused from RFC 5662 with extension)"}

The extracted XDR contribution for this extension is the new
layouttype4 constant alone:

~~~ xdr
   /// const LAYOUT4_FLEX_FILES_V2 = 6;
~~~
{: #fig-orig-layout-extract title="New layouttype4 value (extracted)"}

This document defines structures associated with the layouttype4
value LAYOUT4_FLEX_FILES_V2.  {{RFC8881}} specifies the loc_body structure
as an XDR type "opaque".  The opaque layout is uninterpreted by the
generic pNFS client layers but is interpreted by the flexible file
layout type implementation.  This section defines the structure of
this otherwise opaque value, ffv2_layout4.

## ffv2_encoding_type4

~~~ xdr
   /// enum ffv2_encoding_type4 {
   ///     FFV2_ENCODING_PASSTHROUGH             = 1,
   ///     FFV2_ENCODING_MOJETTE_SYSTEMATIC      = 2,
   ///     FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC  = 3,
   ///     FFV2_ENCODING_RS_VANDERMONDE          = 4,
   ///     FFV2_ENCODING_MIRRORED                = 5,
   ///     FFV2_ENCODING_XOR_PARITY              = 6,
   ///     FFV2_ENCODING_LINUX_MD_RAID           = 7
   /// };
~~~
{: #fig-ffv2_encoding_type4 title="The encoding type"}

The ffv2_encoding_type4 (see {{fig-ffv2_encoding_type4}}) encompasses
a new IANA registry for 'Flexible File Version 2 Layout Type Erasure Coding
Type Registry'.  I.e., instead of defining a new Layout Type for
each erasure coding, we define a new Erasure Encoding Type.  The
encoding types this document defines fall into two groups:

-  FFV2_ENCODING_PASSTHROUGH is the non-chunked, non-integrity
   on-ramp from flexible file v1 layout.  It uses NFSv3 WRITE / READ
   or NFSv4 READ / WRITE directly against each replica's data server.
   No CHUNK_WRITE, no CHUNK_READ, no per-chunk CRC.  See
   {{sec-encoding-passthrough}}.

-  Every other standards-track encoding (any FFV2_ENCODING_*
   value other than FFV2_ENCODING_PASSTHROUGH; see
   {{tbl-coding-types}}) uses the new operations defined here:
   in particular CHUNK_WRITE ({{sec-CHUNK_WRITE}}) and CHUNK_READ
   ({{sec-CHUNK_READ}}), which carry the per-chunk checksum this
   version of the layout type relies on for end-to-end integrity.
   The encoding type selects how chunks are produced from
   application data; the wire and the storage device are the
   same in every case.  See the individual encoding sections
   for the mathematical constructions of each encoding and for
   the wire-compatibility relationships among the Galois Field
   GF(2^8) family.

The 32-bit ffv2_encoding_type4 value space is partitioned by
intended scope -- Standards Track, Experimental, Vendor (open),
and Private / proprietary -- with different allocation policies
per range, so that vendors can assign encoding values without
consuming standards-track codepoints.  See
{{tbl-coding-ranges}} and the accompanying prose in
{{iana-considerations}} for the range assignments and allocation
policies.

### Heterogeneous Mirror Sets {#sec-heterogeneous-mirrors}

A single flexible file v2 layout's `ffv2l_mirrors` array MAY carry mirror
entries of different encoding types.  The protocol does not
require the entries to agree -- one mirror can be
FFV2_ENCODING_PASSTHROUGH, another can be
FFV2_ENCODING_RS_VANDERMONDE, both describing the same file's
data range.  This combination is the structural primitive for
three operations that motivate keeping PASSTHROUGH in the
layout type's vocabulary:

Assimilate:
:  A file that exists today as a plain copy on
   storage outside flexible file v2 layout -- no chunk envelope, no per-chunk
   CRC -- enters the namespace as a PASSTHROUGH mirror against
   the source bytes as they are.  The metadata server then
   adds one or more encoded mirrors (MIRRORED, RS, Mojette) to
   the same layout and synchronizes them from the PASSTHROUGH
   source.  Clients can read the file via the PASSTHROUGH
   mirror immediately; the encoded mirrors become available as
   they are populated.  No "rewrite before serve" step is
   required.

Copy / migrate between encodings:
:  Changing a file from
   one encoding to another is "add a mirror in the target
   encoding to the same layout, let it sync from any healthy
   source mirror, retire the source mirror."  PASSTHROUGH is
   the special case where one endpoint of that migration is
   "no encoding."

Repair across encodings:
:  When an encoded mirror has a
   chunk whose CRC fails and whose parity cannot reconstruct,
   a PASSTHROUGH mirror in the same layout is an authoritative
   source: CHUNK_READ a peer encoded mirror or read the
   PASSTHROUGH byte range, then CHUNK_WRITE the repaired
   chunk.  The reverse is also true: a byte range on the
   PASSTHROUGH copy whose contents the metadata server suspects
   has drifted can be repaired by reconstructing from the
   verified-CRC chunks of an encoded peer.  Two encodings of
   the same file are two independent recovery paths.

The metadata server is responsible for keeping the entries in
a heterogeneous mirror set in sync; the protocol does not
require client awareness of which encoding produced which
mirror beyond what the layout already states.

The wire-level coordination that makes a heterogeneous mirror
set safe to operate -- in particular, the rule that a client
arriving during a transition sees a single layout naming the
proxy server rather than two layouts naming the source and
destination encodings, and the rule that the metadata server's
commit of a transition is a single transaction -- is specified
in the proxy server draft
({{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}), in the
sections "Layout Shape During a Proxy Operation" and "Atomic
commit on PROXY_DONE".  This document specifies the per-mirror
encoding naming primitive; the proxy server document specifies
the transactional machinery that uses it.

The full description of each encoding type is deferred to its
own section.  The mapping between the enum values above and
those sections is:

| Value | Encoding type                        | Description                                              | Section                        |
|------:|--------------------------------------|----------------------------------------------------------|--------------------------------|
| 1     | FFV2_ENCODING_PASSTHROUGH            | On-ramp from the flexible file v1 layout; direct NFSv3/v4 I/O, no chunk envelope | {{sec-encoding-passthrough}}   |
| 2     | FFV2_ENCODING_MOJETTE_SYSTEMATIC     | Discrete Radon projections, systematic (data shards passed through) | {{sec-mojette-encoding}}       |
| 3     | FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC | Discrete Radon projections, non-systematic (all shards transformed) | {{sec-mojette-encoding}}       |
| 4     | FFV2_ENCODING_RS_VANDERMONDE         | Reed-Solomon Vandermonde over GF(2^8); arbitrary (k, m)  | {{sec-rs-encoding}}            |
| 5     | FFV2_ENCODING_MIRRORED               | Chunked replication; N-way redundancy at N x storage      | {{sec-encoding-mirrored}}      |
| 6     | FFV2_ENCODING_XOR_PARITY             | Single-parity RAID-5 shape; k+1, m=1, pure XOR            | {{sec-encoding-xor-parity}}    |
| 7     | FFV2_ENCODING_LINUX_MD_RAID          | Linux md/raid6 P+Q double-parity; k+2, m=2, GF(2^8)       | {{sec-encoding-linux-md-raid}} |
{: #tbl-encoding-type-sections title="Encoding type value to section mapping"}

### Encoding Type Interoperability {#encoding-type-interoperability}

The data servers do not interpret erasure-coded data -- they store and
return opaque chunks.  The NFS wire protocol likewise does not depend
on the encoding mathematics.  However, a client that writes data using
one encoding type MUST be able to read it back, and a different
client implementation MUST be able to read data written by the first
client if both claim to support the same encoding type.

This interoperability requirement means that each registered
encoding type MUST fully specify the encoding and decoding
mathematics such that two independent implementations produce
byte-identical encoded output for the same input.  The specification
of a new encoding type MUST include one of the following:

1. A complete mathematical specification of the encoding and decoding
   algorithms, including all parameters (e.g., field polynomial,
   matrix construction, element size) sufficient for an independent
   implementation to produce interoperable results.

2. A reference to a published patent or pending patent application
   that contains the algorithm specification.  Implementors can then
   evaluate the licensing terms and decide whether to support the
   encoding type.

3. A declaration that the encoding type is a proprietary
   implementation.  In this case, the encoding type name SHOULD
   include an organizational prefix (e.g.,
   FFV2_ENCODING_ACME_FOOBAR) to signal that interoperability is
   limited to implementations licensed by that organization.

Option 1 is RECOMMENDED for encoding types intended for broad
interoperability.  Options 2 and 3 allow vendors to register encoding
types for use within their own ecosystems while preserving the
encoding type namespace.

The rationale for this requirement is that erasure coding moves
computation from the server to the client.  If the client cannot
determine how data was encoded, it cannot decode it.  Unlike layout
types (where the server controls the storage format), encoding types
require client-side agreement on the mathematics.

##  ffv2_layout4 {#sec-ffv2_layout}

### ffv2_flags4 {#sec-ffv2_flags4}
~~~ xdr
   /// const FFV2_FLAGS_NO_LAYOUTCOMMIT  = FF_FLAGS_NO_LAYOUTCOMMIT;
   /// const FFV2_FLAGS_NO_IO_THRU_MDS   = FF_FLAGS_NO_IO_THRU_MDS;
   /// const FFV2_FLAGS_NO_READ_IO       = FF_FLAGS_NO_READ_IO;
   /// const FFV2_FLAGS_WRITE_ONE_MIRROR =
   ///     FF_FLAGS_WRITE_ONE_MIRROR;
   /// const FFV2_FLAGS_ONLY_ONE_WRITER  = 0x00000010;
   ///
   /// typedef uint32_t            ffv2_flags4;
~~~
{: #fig-ffv2_flags4 title="The ffv2_flags4" }

The ffv2_flags4 in {{fig-ffv2_flags4}}  is a bitmap that allows the
metadata server to inform the client of particular conditions that
may result from more or less tight coupling of the storage devices.

Each flag below describes both the semantics when set and the
normative requirement it places on the client.  When a flag is
not set, the client MUST follow the default behavior described
for its unset state.

FFV2_FLAGS_NO_LAYOUTCOMMIT:

:  When set, the client MAY omit the LAYOUTCOMMIT to the
metadata server.  When unset, the client MUST send LAYOUTCOMMIT
per {{RFC8881}} Section 18.42.

FFV2_FLAGS_NO_IO_THRU_MDS:

:  When set, the client MUST NOT proxy I/O operations through
the metadata server, even after detecting a network disconnect
to a storage device.  When unset, the client MAY retry failed
I/O via the metadata server.

FFV2_FLAGS_NO_READ_IO:

:  When set, the client MUST NOT issue READ against layouts of
iomode LAYOUTIOMODE4_RW, and MUST instead request a separate
layout of iomode LAYOUTIOMODE4_READ for any read I/O.  When
unset, the client MAY issue READ against either iomode.

FFV2_FLAGS_WRITE_ONE_MIRROR:

:  When set, the client MAY update only one mirror of each
layout segment (see {{sec-CSM}}) and rely on the metadata server
(or a proxy server acting on its behalf) or a peer data server
to propagate the update to the remaining mirrors.  When unset,
the client MUST update all mirrors.

   The metadata server MUST NOT set FFV2_FLAGS_WRITE_ONE_MIRROR
   on a layout whose ffv2l_mirrors carry more than one distinct
   ffv2m_coding_type_data value unless a propagation actor is
   available that speaks every encoding present in the layout.
   Cross-encoding propagation requires the actor to decode
   through the source mirror's encoding transform and re-encode
   for each target mirror's transform, which the metadata server
   itself cannot do for chunked encodings (it does not hold the
   encoded shards); a proxy server is the entity that performs
   cross-encoding translation.  On a
   mixed-encoding layout without a proxy server for the affected
   file, the metadata server MUST leave
   FFV2_FLAGS_WRITE_ONE_MIRROR unset and require the client to
   update all mirrors directly.

FFV2_FLAGS_ONLY_ONE_WRITER:

:  When set, the client is the exclusive writer for the layout
and MAY issue CHUNK_WRITE without setting cwa_guard, retaining
the ability to use CHUNK_ROLLBACK in the event of a write hole
caused by overwriting.  When unset, the client MUST set
cwa_guard on every CHUNK_WRITE so that chunk_guard4 CAS can
prevent collisions across concurrent writers.

## ffv2_file_info4

~~~ xdr
   /// struct ffv2_file_info4 {
   ///     stateid4                ffv2fi_stateid;
   ///     nfs_fh4                 ffv2fi_fh_vers;
   /// };
~~~
{: #fig-ffv2_file_info4 title="The ffv2_file_info4" }

The ffv2_file_info4 is a new structure that resolves the
stateid-vs-fh_vers pairing issue discussed in Section 5.1 of
{{RFC8435}}.  In {{RFC8435}}'s flexible file v1 layout, a
singleton ffv2ds_stateid was paired with an ffv2ds_fh_vers
array, forcing every fh_vers on a data server to share one
stateid.  In {{fig-ffv2_file_info4}} each fh_vers has its own
stateid alongside it.

The stateid value ffv2fi_stateid MUST carry depends on the
coupling mode advertised for the corresponding
(ffv2dv_version, ffv2dv_minorversion, ffv2dv_coupling) tuple
(see {{sec-ff_device_addr4}}):

- If ffv2dv_coupling for this entry equals
  FFV2_COUPLING_SYNTHETIC_UIDS (loose coupling), ffv2fi_stateid
  MUST be the anonymous stateid; the client authenticates to
  the data server via the synthetic ffv2ds_user / ffv2ds_group
  ({{sec-Fencing-Clients}}) rather than by presenting a
  meaningful stateid.
- If ffv2dv_coupling for this entry has the
  FFV2_COUPLING_TRUSTED_STATEID flag set, ffv2fi_stateid MUST
  be the layout stateid the metadata server issued in the
  LAYOUTGET that produced this layout.  The data server
  validates presented stateids against its per-file trust
  table populated by TRUST_STATEID
  ({{sec-tight-coupling-control}}).
- If ffv2dv_coupling for this entry has only
  FFV2_COUPLING_TIGHTLY_COUPLED set (a back-end control
  protocol other than trusted stateid, with no TRUST_STATEID
  support advertised), ffv2fi_stateid carries whatever
  stateid the deployment's back-end control protocol expects
  the client to present; this document does not further
  specify that value.

Because ffv2ds_file_info<> has one element per
(version, minorversion, coupling) tuple advertised on the
data server (parallel to ffv2da_versions<>), a single data
server that exposes both loose and tight combinations
carries multiple ffv2_file_info4 entries with different
stateid values.  The client selects one tuple to use for
I/O; it presents that tuple's stateid on subsequent CHUNK
operations.

## ffv2_ds_flags4 {#sec-ffv2_ds_flags4}

~~~ xdr
   /// const FFV2_DS_FLAGS_ACTIVE        = 0x00000001;
   /// const FFV2_DS_FLAGS_PARITY        = 0x00000004;
   /// const FFV2_DS_FLAGS_REPAIR        = 0x00000008;
   /// const FFV2_DS_FLAGS_PROXY         = 0x00000010;
   /// typedef uint32_t            ffv2_ds_flags4;
~~~
{: #fig-ffv2_ds_flags4 title="The ffv2_ds_flags4" }

The ffv2_ds_flags4 (in {{fig-ffv2_ds_flags4}}) flags detail the
state of the data servers.  With erasure coding algorithms,
there are both Systematic and Non-Systematic approaches.  In
the Systematic approach, the bits for integrity are placed
amongst the resulting transformed chunk.  Such an
implementation would typically see FFV2_DS_FLAGS_ACTIVE data
servers with FFV2_DS_FLAGS_REPAIR entries added by the
metadata server when a failed ACTIVE has been replaced.

With the Non-Systematic approach, the data and integrity live
on different data servers.  Such an implementation would
typically see FFV2_DS_FLAGS_ACTIVE and FFV2_DS_FLAGS_PARITY
data servers, again with FFV2_DS_FLAGS_REPAIR entries appearing
as needed.

The FFV2_DS_FLAGS_REPAIR flag informs the client that the
indicated data server is a replacement for a previously failed
ACTIVE data server, whose content has been (or is being)
reconstructed from the surviving shards of the mirror set.
Its payload was placed there by a repair actor executing the
flow in {{sec-repair-selection}} rather than directly by the
original writer.  The flag is the client's indication that
reads from this data server return erasure-decoded content
rather than content produced by the original write.

Clients that rely on write-provenance information (for example,
deployments that track which client wrote which generation)
SHOULD be aware of the REPAIR flag so they do not treat the
reconstructed payload as if it had been written directly by the
cg_client_id recorded in the chunk_guard4; the guard values
still match across the mirror set by construction, but the
physical write path differs.

Over the lifetime of a file, a single data server MAY transition
ACTIVE -> REPAIR (on replacement) or REPAIR -> ACTIVE (once the
metadata server has accepted the reconstructed content as
authoritative and the fail-over is complete); the metadata
server reflects the current flag set in the next layout it
returns.

The following paragraphs describe the mechanics of these
transitions.  The client is not the driver in either
direction; both are metadata-server-initiated changes that a
client observes only by refreshing its layout.

ACTIVE -> REPAIR:
:  Triggered when a client (or the metadata server itself,
   via scrub) reports a failure via LAYOUTERROR against a
   particular shard.  The metadata server picks a target for
   the reconstructed content -- either an existing
   FFV2_DS_FLAGS_REPAIR-flagged entry already in the layout,
   or a fresh data server drawn from an out-of-band
   deployment pool that the metadata server adds to the
   layout with FFV2_DS_FLAGS_REPAIR set -- and initiates the
   client-driven repair flow at {{sec-repair-selection}}.
   Once the reconstructed shard is written and the
   metadata server has accepted it (via CHUNK_REPAIRED),
   the metadata server updates the affected layout to
   remove the failed entry and mark the target entry as
   FFV2_DS_FLAGS_REPAIR.  The metadata server SHOULD then
   issue CB_LAYOUTRECALL against any client that holds an
   outstanding layout for the affected file, so those
   clients refresh via a subsequent LAYOUTGET and observe
   the updated flag set.  Clients that never issued
   LAYOUTGET during the incident window observe the new
   layout on first fetch.

REPAIR -> ACTIVE:
:  Triggered when the metadata server confirms the
   reconstructed content has been durably committed and
   the replaced data server is not returning.  This is a
   metadata-server-internal state change; no client-visible
   operations are required for the transition itself.  The
   flag update is reflected in the next layout the metadata
   server hands out (either the layout returned to the next
   LAYOUTGET, or the layout delivered after a CB_LAYOUTRECALL
   that the metadata server MAY issue to accelerate the
   transition).

Both transitions preserve the mirror set's array indexing:
the shard formerly held by the failed entry lives at the
same array position in the layout, under the REPAIR-flagged
entry.  A client reads by array position; the flag informs
the client of the read's provenance (originally written vs
reconstructed) but does not change the shard-index
addressing.  A client MUST NOT infer that a REPAIR-flagged
entry serves a different shard than the ACTIVE entry it
replaced.

If the same payload identifier appears at the same shard
position across an ACTIVE entry (about to be retired) and a
REPAIR entry (being promoted) during a transition window,
the two entries are guaranteed to carry identical chunk
contents (the reconstructed content matches the original by
the erasure-coding correctness invariant, and the checksum
verifies).  There is no client-driven failover to a passive
data server; a client that observes a CHUNK_WRITE failure
against an ACTIVE MUST report the failure via LAYOUTERROR
and rely on the metadata-server-initiated repair flow above
to promote a replacement.

The FFV2_DS_FLAGS_PROXY flag identifies a data-server entry
that names a proxy server rather than a real storage device.
A client whose local encoding capabilities cannot cover the
file's mirror set receives a layout in which one or more
mirror entries have FFV2_DS_FLAGS_PROXY set on their
ffv2_data_server4; the client directs I/O for that mirror
to the proxy, which translates on behalf of the client.  The
proxy server protocol itself is specified in the proxy server
draft; this document defines only the layout flag (this bit)
that lets the metadata server mark a data-server entry as
proxy-mediated.

## ffv2_data_server4

~~~ xdr
   /// struct ffv2_data_server4 {
   ///     deviceid4               ffv2ds_deviceid;
   ///     uint32_t                ffv2ds_efficiency;
   ///     ffv2_file_info4         ffv2ds_file_info<>;
   ///     fattr4_owner            ffv2ds_user;
   ///     fattr4_owner_group      ffv2ds_group;
   ///     ffv2_ds_flags4          ffv2ds_flags;
   /// };
~~~
{: #fig-ffv2_data_server4 title="The ffv2_data_server4" }

The ffv2_data_server4 (in {{fig-ffv2_data_server4}}) describes a data
file and how to access it via the different NFS protocols.

- ffv2ds_deviceid names the data server; see the flexible
  file v1 layout ({{RFC8435}}) for the deviceid model this
  layout inherits.
- ffv2ds_efficiency is the metadata-server-assigned mirror
  ranking used for read-mirror selection
  ({{sec-select-mirror}}).
- ffv2ds_file_info<> pairs a filehandle and a stateid for
  each (version, minorversion, coupling) tuple the layout
  advertises on this data server (see {{sec-ff_device_addr4}}
  and the discussion at ffv2_file_info4 above for the
  stateid-value rules per coupling mode).
- ffv2ds_user and ffv2ds_group are the synthetic uid/gid the
  client presents in the RPC credentials to the data server
  under loose coupling (see {{sec-Fencing-Clients}}).  They
  are present in every ffv2_data_server4 regardless of the
  coupling advertised on this data server, because the
  underlying file on the data server has a single uid/gid
  irrespective of which NFS protocol combination the client
  uses to reach it.  If ffv2dv_coupling for the tuple the
  client selects has any tight coupling flag set
  (FFV2_COUPLING_TIGHTLY_COUPLED or
  FFV2_COUPLING_TRUSTED_STATEID), the client MUST ignore
  ffv2ds_user and ffv2ds_group; the data server authorizes
  the write via the trusted stateid table or the back-end
  control protocol instead of via the synthetic uid.  If the
  client selects a tuple with ffv2dv_coupling =
  FFV2_COUPLING_SYNTHETIC_UIDS, the client MUST present
  ffv2ds_user and ffv2ds_group in the RPC credentials.
- ffv2ds_flags carries the ffv2_ds_flags4 state (ACTIVE,
  PARITY, REPAIR, PROXY; see {{sec-ffv2_ds_flags4}}).

## ffv2_data_protection4

~~~ xdr
   /// struct ffv2_data_protection4 {
   ///     uint32_t fdp_data;    /* data shards (k) */
   ///     uint32_t fdp_parity;  /* parity/redundancy shards (m) */
   /// };
~~~
{: #fig-ffv2_data_protection4 title="The ffv2_data_protection4" }

The ffv2_data_protection4 (in {{fig-ffv2_data_protection4}}) describes
the data protection geometry as a pair of counts: the number of data
shards (fdp_data, also known as k) and the number of parity or
redundancy shards (fdp_parity, also known as m).  This structure is
used in both layout hints and layout responses, and applies
uniformly to all encoding types:

| Protection Mode | fdp_data | fdp_parity | Total Data Servers | Description |
|---
| Mirroring (3-way) | 1 | 2 | 3 | 3 copies, no encoding |
| Striping (6-way) | 6 | 0 | 6 | Parallel I/O, no redundancy |
| RS Vandermonde 4+2 | 4 | 2 | 6 | Tolerates 2 data-server failures |
| Mojette-sys 8+2 | 8 | 2 | 10 | Tolerates 2 data-server failures |
{: #fig-protection-examples title="Example data protection configurations" }

By expressing all protection modes as (fdp_data, fdp_parity) pairs,
a single structure serves mirroring, striping, and all erasure
encoding types.  The encoding type ({{fig-ffv2_encoding_type4}}) determines
how the shards are encoded; the protection structure determines
how many shards there are.

The total number of data servers required is fdp_data + fdp_parity.
The storage overhead is fdp_parity / fdp_data (e.g., 50% for 4+2,
25% for 8+2).

## ffv2_coding_type_data4

~~~ xdr
   /// union ffv2_coding_type_data4 switch
   ///         (ffv2_encoding_type4 fctd_coding) {
   ///     case FFV2_ENCODING_PASSTHROUGH:
   ///         ffv2_data_protection4   fctd_protection;
   ///     case FFV2_ENCODING_MIRRORED:
   ///         ffv2_data_protection4   fctd_protection;
   ///     default:
   ///         ffv2_data_protection4   fctd_protection;
   /// };
~~~
{: #fig-ffv2_coding_type_data4 title="The ffv2_coding_type_data4" }

The ffv2_coding_type_data4 (in {{fig-ffv2_coding_type_data4}}) describes
the data protection geometry for the layout.  All encoding types carry an
ffv2_data_protection4 ({{fig-ffv2_data_protection4}}) specifying the
number of data and parity shards.  The encoding type enum determines how
the shards are encoded; the protection structure determines how many
shards there are.

Although every arm of the union currently carries the same
type, the union form is intentional.  Future revisions of this
specification may assign distinct arm types to specific coding
types; using a union now avoids an incompatible change to the
XDR at that time.

The (data, parity) tuple is interpreted per encoding type:

-  FFV2_ENCODING_PASSTHROUGH preserves the flexible file v1 layout-style notation
   for backward compatibility: fdp_data is 1 and fdp_parity is
   the number of additional copies (e.g., fdp_parity=2 for
   3-way mirroring).  The "1" data carrier is the file as
   stored; the fdp_parity additional copies are the flexible file v1 layout
   mirror replicas.

-  FFV2_ENCODING_MIRRORED uses the N+0 notation: fdp_data is
   the number of replicas (e.g., fdp_data=3 for 3-way
   mirroring) and fdp_parity MUST be 0.  Every replica is a
   full, independent data carrier; mirroring carries no
   parity reconstruction.

-  Erasure encoding types (FFV2_ENCODING_RS_VANDERMONDE,
   FFV2_ENCODING_MOJETTE_SYSTEMATIC,
   FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC, and any future types
   subsequently registered in the IANA registry established by
   this document) use fdp_data >= 2 and fdp_parity >= 1.

## ffv2_stripes4

~~~ xdr
   /// enum ffv2_striping4 {
   ///     FFV2_STRIPING_NONE = 0,
   ///     FFV2_STRIPING_SPARSE = 1,
   ///     FFV2_STRIPING_DENSE = 2
   /// };
   ///
   /// struct ffv2_stripes4 {
   ///         ffv2_data_server4       ffv2s_data_servers<>;
   /// };
~~~
{: #fig-ffv2_stripes4 title="The ffv2_stripes4 structure"}

Each stripe contains a set of data servers in ffv2s_data_servers.
If the stripe is part of a ffv2_coding_type_data4 of
FFV2_ENCODING_PASSTHROUGH or FFV2_ENCODING_MIRRORED, then the
length of ffv2s_data_servers MUST be 1: under both encoding
types each stripe's data lives on a single data server, with
replica multiplicity expressed in ffv2l_mirrors rather than in
ffv2s_data_servers.

ffv2_stripes4 has no direct counterpart in {{RFC8435}}.  In
the flexible file v1 layout, a mirror's data servers are
listed directly on the mirror (via ffm_data_servers<> on
ff_mirror4).  The flexible file v2 layout introduces this
intermediate stripes level so a single mirror MAY carry
multiple stripe groups, and pushes the striping-mode metadata
(ffv2m_striping, ffv2m_striping_unit_size) down onto the mirror
(see {{sec-ffv2-mirror4}}) rather than onto the layout as
{{RFC8435}} does with the layout-level ffl_stripe_unit.  The
ffv2_striping4 enum (FFV2_STRIPING_NONE / _SPARSE / _DENSE)
inherits its meaning from Section 13.3 of {{RFC8881}} and
Section 5.1 of {{RFC8435}}; the flexible file v2 layout
evolution is that the striping mode is a per-mirror decision
rather than a per-layout one.

## ffv2_mirror4 {#sec-ffv2-mirror4}

~~~ xdr
   /// struct ffv2_mirror4 {
   ///         ffv2_coding_type_data4  ffv2m_coding_type_data;
   ///         ffv2_striping4           ffv2m_striping;
   ///         uint32_t                ffv2m_striping_unit_size;
   ///         uint32_t                ffv2m_client_id;
   ///         checksum_algorithm4     ffv2m_checksum_algorithm;
   ///         ffv2_stripes4           ffv2m_stripes<>;
   /// };
~~~
{: #fig-ffv2_mirror4 title="The ffv2_mirror4" }

The ffv2_mirror4 (in {{fig-ffv2_mirror4}}) is the flexible
file v2 layout counterpart to ff_mirror4 in {{RFC8435}}.  The
flexible file v2 layout is a semantic superset of the flexible
file v1 layout: any ff_mirror4 can be re-expressed as an
ffv2_mirror4 by setting
ffv2m_coding_type_data = FFV2_ENCODING_PASSTHROUGH,
ffv2m_striping and ffv2m_striping_unit_size to the flexible
file v1 layout's layout-level values, ffv2m_checksum_algorithm
to CHECKSUM_ALG_NONE, and wrapping the flexible file v1
layout's ffm_data_servers<> in a single-element
ffv2m_stripes<>.  The reverse does not hold: ffv2_mirror4
instances whose ffv2m_coding_type_data is anything other than
FFV2_ENCODING_PASSTHROUGH have no ff_mirror4 representation.

Relative to ff_mirror4, ffv2_mirror4 adds the following
per-mirror fields:

- ffv2m_coding_type_data: per-mirror encoding type choice
  (see {{fig-ffv2_encoding_type4}}).  This enables a single
  layout to carry mirrors under different encodings
  (e.g., a PASSTHROUGH mirror alongside a Reed-Solomon
  mirror over the same file; see {{fig-example_mixing}}) --
  the transition-window and per-mirror-optimization patterns
  that motivated the flexible file v2 layout.
- ffv2m_striping and ffv2m_striping_unit_size: pull the
  striping-mode decision from the layout level down to the
  mirror level.  The flexible file v1 layout's
  ffl_stripe_unit is layout-wide; in the flexible file v2
  layout different mirrors of the same file MAY use different
  striping configurations.
- ffv2m_client_id: writer identity for chunk_guard4 CAS (see
  {{sec-chunk_guard4}}).  No flexible file v1 layout
  counterpart; introduced for the CHUNK operation set that
  the flexible file v2 layout adds.
- ffv2m_checksum_algorithm: per-mirror integrity-checksum
  algorithm.  No flexible file v1 layout counterpart;
  introduced for the per-chunk checksum integrity the
  flexible file v2 layout adds.
- ffv2m_stripes<>: replaces the flexible file v1 layout's
  flat ffm_data_servers<>
  with an array of ffv2_stripes4 (see {{fig-ffv2_stripes4}}),
  allowing a single mirror to carry multiple stripe groups.

The ffv2m_checksum_algorithm field names the checksum
algorithm the client MUST use when computing
cwa_checksums on CHUNK_WRITE and cwra_checksums on
CHUNK_WRITE_REPAIR, and the algorithm the client MUST
expect in cr_checksum on CHUNK_READ responses, for chunks
in this mirror.  The metadata server picks the algorithm
at LAYOUTGET time; the value is one of the registered
checksum_algorithm4 codes (see {{sec-checksum4}}).
Different mirrors of the same file MAY name different
checksum algorithms, supporting transition cases where one
mirror is being migrated to a stronger algorithm while
others retain the previous algorithm.

A client that does not implement the algorithm named in
ffv2m_checksum_algorithm MUST return the layout with
NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED; the metadata
server may then issue a new layout naming a different
algorithm the client supports, or deny the layout request.

The ffv2m_client_id is a 32-bit value, assigned by the metadata
server at layout-grant time, that the client MUST use as the
cg_client_id field of chunk_guard4 (see {{sec-chunk_guard4}}) in
every CHUNK_WRITE it issues against the mirror's data servers.
Its purpose is to satisfy the 32-bit-per-field budget of
chunk_guard4 while preserving the guarantee that concurrent
writers on the same file are distinguishable:

-  The NFSv4 clientid4 ({{RFC8881}}) is a 64-bit identifier;
   {{RFC8881}} does not constrain how a server populates its
   bits, and the bit-layout choices made by any particular
   metadata server implementation are not visible to the
   client and MUST NOT be assumed by the client.  Folding
   clientid4 to 32 bits locally at the client therefore risks
   colliding with another client's folded value, which would
   violate the uniqueness contract on chunk_guard4.

-  Only the metadata server has the information needed to avoid
   such collisions: it sees every layout it grants on a file and
   can assign a dense 32-bit ffv2m_client_id that is guaranteed
   distinct from the ffv2m_client_ids assigned to other clients
   holding concurrent write layouts on the same file.  The
   metadata server MUST assign ffv2m_client_id subject to this
   uniqueness rule.

-  Because cg_client_id participates in the deterministic
   tiebreaker for racing writers (see {{sec-chunk_guard4}}),
   having the metadata server assign it also lets the metadata
   server influence which client wins contention by choosing
   the numeric ordering of the values it hands out.  Specific
   ordering policies are implementation-defined and out of
   scope for this document, but the protocol mechanism is
   present.

An ffv2m_client_id is scoped to the file and layout for which it
was granted.  A client that holds layouts on two different files
may receive two different ffv2m_client_ids from the same metadata
server, and a client that relinquishes and later re-acquires a
layout on a given file MAY be assigned a different ffv2m_client_id.
ffv2m_client_id does NOT survive a metadata server restart: the
metadata server reassigns values as clients reclaim layouts
during the grace period.

The ffv2m_coding_type_data is which encoding type is used
by the mirror.

The ffv2m_striping selects the striping method used by the
mirror.  The three permissible values are FFV2_STRIPING_NONE
(the mirror is not striped), FFV2_STRIPING_SPARSE (stripe units
are mapped to the same physical offset on every data server,
leaving holes), and FFV2_STRIPING_DENSE (stripe units are
packed contiguously on each data server without holes).  See
{{sec-striping}} for the mapping math for each option.

The ffv2m_striping_unit_size is the stripe unit size used
by the mirror.  The minimum stripe unit size is 64 bytes.  If
the value of ffv2m_striping is FFV2_STRIPING_NONE, then the value
of ffv2m_striping_unit_size MUST be 1.

The ffv2m_stripes is the array of stripes for the mirror; the
length of the array is the stripe count.  If there is no
striping or the ffv2m_coding_type_data is FFV2_ENCODING_PASSTHROUGH,
then the length of ffv2m_stripes MUST be 1.  Under
FFV2_ENCODING_MIRRORED the file MAY be striped within each
replica; the constraint that ffv2s_data_servers length is 1
still applies, but ffv2m_stripes can carry multiple stripes.

## ffv2_layout4

~~~ xdr
   /// struct ffv2_layout4 {
   ///     ffv2_mirror4            ffv2l_mirrors<>;
   ///     ffv2_flags4             ffv2l_flags;
   ///     uint32_t                ffv2l_stats_collect_hint;
   /// };
~~~
{: #fig-ffv2_layout4 title="The ffv2_layout4" }

The ffv2_layout4 (in {{fig-ffv2_layout4}}) describes the Flexible
File Layout Version 2.

The ffv2l_mirrors field is the array of mirrored storage devices that
provide the storage for the current stripe; see {{fig-parallel-filesystem}}.

The ffv2l_stats_collect_hint field provides a hint to the client on
how often the server wants it to report LAYOUTSTATS for a file.
The time is in seconds.

~~~
                +-----------+
                |           |
                |           |
                |   File    |
                |           |
                |           |
                +-----+-----+
                      |
     +-------------+-----+----------------+
     |                   |                |
+----+-----+       +-----+----+       +---+----------+
| Mirror 1 |       | Mirror 2 |       | Mirror 3     |
| MIRRORED |       | MIRRORED |       | REED_SOLOMON |
+----+-----+       +-----+----+       +---+----------+
     |                   |                |
     |                   |                |
+-----------+      +-----------+      +-----------+
|+-----------+     | Stripe 1  |      |+-----------+
+| Stripe N  |     +-----------+      +| Stripe N  |
 +-----------+           |             +-----------+
     |                   |                |
     |                   |                |
+-----------+      +-----------+      +-----------+
| Storage   |      | Storage   |      |+-----------+
| Device    |      | Device    |      ||+-----------+
+-----------+      +-----------+      +||  Storage  |
                                       +|  Devices  |
                                        +-----------+
~~~
{: #fig-parallel-filesystem title="The Relationship between Metadata Server and Data Servers"}

As shown in {{fig-parallel-filesystem}} if the ffv2m_coding_type_data
is FFV2_ENCODING_PASSTHROUGH or FFV2_ENCODING_MIRRORED, then each
of the stripes MUST only have 1 storage device.  I.e., the length
of ffv2s_data_servers MUST be 1.  The erasure-coding encoding types
distribute shards across multiple storage devices and so carry
multiple entries in ffv2s_data_servers.

The abstraction here is that for FFV2_ENCODING_PASSTHROUGH and
FFV2_ENCODING_MIRRORED, each stripe describes exactly one data
server.  And for the erasure-coded encoding types, each of the
stripes describes a set of data servers to which the shards are
distributed.  Further, the payload length can be different per
stripe.

## ffv2_layouthint4 {#sec-ffv2-layouthint}

~~~ xdr
   /// struct ffv2_layouthint4 {
   ///     ffv2_encoding_type4       ffv2lh_supported_types<>;
   ///     ffv2_data_protection4   ffv2lh_preferred_protection;
   ///     uint32_t                ffv2lh_stripe_unit;
   ///     uint64_t                ffv2lh_expected_file_size;
   /// };
~~~
{: #fig-ffv2_layouthint4 title="The ffv2_layouthint4" }

The ffv2_layouthint4 (in {{fig-ffv2_layouthint4}}) describes the
layout_hint (see Section 5.12.4 of {{RFC8881}}) that the client can
provide to the metadata server.

The client provides four hints.  All four are advisory; the
metadata server MAY honor any subset and MAY override any of
them per administrative policy.

ffv2lh_supported_types

:  An ordered list of encoding types the client supports,
with the most preferred type first.  The server SHOULD select a type
from this list but MAY choose any type it supports.  If the server
does not support any of the listed types, it returns
NFS4ERR_CODING_NOT_SUPPORTED, and the client can retry
with a different list to discover the overlapping set.

ffv2lh_preferred_protection

:  The client's preferred data protection geometry as a
(fdp_data, fdp_parity) pair.  The server SHOULD honor this hint but
MAY override it based on server-side policy.  A server that manages
data protection via administrative policy (e.g., per-directory or
per-export objectives) will typically ignore this hint and return the
geometry dictated by policy.

ffv2lh_stripe_unit

:  The client's preferred stripe unit size in bytes.  A value of
zero means "no hint" -- the metadata server selects a stripe unit
from policy or from file history.  When the value is non-zero,
the metadata server SHOULD use it as the per-mirror stripe unit
when policy permits.  The metadata server MAY round to a
server-supported alignment.  The metadata server MAY return
NFS4ERR_INVAL when a non-zero value is below an
implementation-defined floor or above an implementation-defined
ceiling.  The hint SHOULD be a power of two.

ffv2lh_expected_file_size

:  The client's hint at the file's eventual size in bytes.  A
value of zero means "no hint."  When the value is non-zero, the
metadata server MAY use it to decide whether to issue a striped
layout (typically for files large enough that striping pays for
itself) versus a non-striped layout (typically for files
expected to remain small).  The hint applies to the layout
being requested and has no retroactive effect on layouts
already issued.  The hint is never required to be accurate; a
file is free to grow beyond its hint without protocol penalty,
and the metadata server is free to ignore the hint.

The stripe_unit and expected_file_size hints are most useful at
the LAYOUTGET that follows file creation, when the file is at
size zero and the metadata server has no usage history to drive
its own striping decision.  On a LAYOUTGET against an
already-grown file, the metadata server SHOULD ignore both
hints and use the file's actual size and access history.

For example, a client that prefers Mojette systematic with 8+2
protection, 1 MiB stripe units, and is creating a file expected
to grow to 16 GiB would send:

~~~
ffv2lh_supported_types = { FFV2_ENCODING_PASSTHROUGH,
                         FFV2_ENCODING_MIRRORED,
                         FFV2_ENCODING_MOJETTE_SYSTEMATIC,
                         FFV2_ENCODING_RS_VANDERMONDE }
ffv2lh_preferred_protection = { fdp_data = 8, fdp_parity = 2 }
ffv2lh_stripe_unit          = 1048576
ffv2lh_expected_file_size   = 17179869184
~~~

A server with a policy of RS 4+2 for this directory would ignore
both encoding hints and return a layout with
FFV2_ENCODING_RS_VANDERMONDE and (fdp_data=4, fdp_parity=2).  A
server without erasure coding might return FFV2_ENCODING_MIRRORED
with (fdp_data=3, fdp_parity=0) for 3-way mirroring with
per-chunk integrity, or FFV2_ENCODING_PASSTHROUGH with
(fdp_data=1, fdp_parity=2) for 3-way flexible file v1 layout-compatible
mirroring without per-chunk integrity.

A server may also use ffv2lh_expected_file_size as a striping
gate: a deployment that wants to avoid the runway and bookkeeping
overhead of striping small files (which dominate file-count even
when they do not dominate byte count) can use a single-mirror
non-striped layout for any LAYOUTGET whose hint is below a
configured threshold, and a striped layout above it.  Without
the hint the metadata server must either always stripe, never
stripe, or rely on observing the file's growth -- which is
exactly the friction the hint exists to remove.

### Encoding Negotiation {#sec-encoding-negotiation}

Because the encoding type registry is expected to grow over time
(new erasure encoding types are added, older ones fall out of favor,
vendors register private codes; see {{iana-considerations}}),
neither clients nor metadata servers are required to implement
every registered encoding.  The protocol negotiates encoding
capabilities via ffv2_layouthint4:

Client-side advertisement:
:  A client that wishes to influence encoding selection SHOULD
   send the set of encodings it actually implements in
   ffv2lh_supported_types.  A client MUST NOT claim support for
   an encoding it cannot encode or decode: a false advertisement
   produces silent data unavailability when the resulting layout
   is issued.

Metadata-server selection at file creation:
:  When the LAYOUTGET is against a newly-created file (the file
   has no committed data yet), the metadata server has real
   discretion.  It SHOULD select an encoding from the client's
   ffv2lh_supported_types list when the server's policy permits.
   The server MAY override the hint when its policy dictates a
   specific encoding (for example, per-export objectives); in that
   case the server issues a layout with the policy-dictated
   encoding and the client MUST either honor it or fail its I/O
   with NFS4ERR_CODING_NOT_SUPPORTED.

Metadata-server selection for an existing file:
:  When the LAYOUTGET is against a file that already has
   committed data on the data servers, the file's encoding is
   fixed by the bytes already written; the metadata server does
   not choose an encoding at layout-issue time.  Re-encoding an
   existing file is a separate operation (see the
   heterogeneous mirror set primitive in
   {{sec-heterogeneous-mirrors}} and the migration paths in the
   proxy server draft), not a consequence of a LAYOUTGET hint.  In this case
   ffv2lh_supported_types is not a selection input; it is an
   admissibility check.  The metadata server issues a layout
   with the file's actual encoding and evaluates whether the
   client can consume it:

   - If the file's encoding is in the client's
     ffv2lh_supported_types list, the metadata server issues
     the layout normally.
   - If it is not, the metadata server takes one of the
     fallback actions enumerated in "Fallback when no overlap
     exists" below (return NFS4ERR_CODING_NOT_SUPPORTED,
     route I/O through the metadata server, or route through
     a translating proxy server).

Fallback when no overlap exists:
:  If the server's policy cannot be satisfied by any encoding the
   client supports, the metadata server has three options:

   1.  Return NFS4ERR_CODING_NOT_SUPPORTED on the LAYOUTGET.
       The client MAY retry with a different (possibly empty)
       ffv2lh_supported_types list to learn the server's encoding
       repertoire through the errors returned.

   2.  Fall back to I/O via the metadata server itself, so the
       client's reads and writes are satisfied by the metadata server
       translating to the underlying data server encoding on the client's
       behalf (see {{sec-Fencing-Clients}} for the metadata-server I/O
       fallback).  This is correct but serializes all I/O for
       the encoding-ignorant client through a single actor.

   3.  Route the client through a translating proxy that
       understands both the file's native encoding and an encoding
       the client does support.  The metadata server issues a layout with
       the proxy's data-server entry carrying
       FFV2_DS_FLAGS_PROXY and a coding_type the client does
       support (typically FFV2_ENCODING_MIRRORED for a minimal
       NFSv4.2 client, or FFV2_ENCODING_PASSTHROUGH / a flat
       NFSv3 view for an NFSv3 client).  The proxy encodes
       and decodes on the fly
       against the real data servers.  This preserves parallel I/O
       for the encoding-ignorant client that the metadata-server I/O
       fallback loses.  The proxy registration, directive, and
       credential-forwarding rules are defined in the proxy server
       draft; this draft defines only the layout flag
       (FFV2_DS_FLAGS_PROXY in
       {{sec-ffv2_ds_flags4}}) that makes the proxy visible to
       the client.

   Options (1), (2), and (3) are not mutually exclusive: a
   given deployment MAY implement any combination.  A
   deployment that supports (3) covers all the clients that
   (1) and (2) would cover and additionally preserves parallel
   I/O for encoding-ignorant clients.

Runtime encoding change:
:  If a metadata server changes its encoding policy after layouts
   have been issued (for example, a deployment upgrade that
   retires an older encoding), the metadata server MUST recall the
   affected layouts via CB_LAYOUTRECALL and may re-issue new
   layouts with the new encoding.  Clients that do not support the
   new encoding LAYOUTRETURN with NFS4ERR_CODING_NOT_SUPPORTED,
   and the server either grants a layout using a mutually-supported encoding or the client falls back to I/O via the
   metadata server.

This mechanism deliberately avoids a separate capability-bit
handshake at EXCHANGE_ID.  ffv2_layouthint4 already provides
per-request negotiation; adding a session-level
capability set would duplicate it and would complicate encoding
upgrades without additional value, because a client that
genuinely upgrades its encoding set at runtime can simply update
the ffv2lh_supported_types on its next LAYOUTGET.

Note: In {{fig-ffv2_layout4}} ffv2_coding_type_data4 is an enumerated
union with the payload of each arm being defined by the protection
type. ffv2m_client_id tells the client which id to use when interacting
with the data servers.

The ffv2_layout4 structure (see {{fig-ffv2_layout4}}) specifies a layout
in that portion of the data file described in the current layout
segment.  It is either a single instance or a set of mirrored copies
of that portion of the data file.  When mirroring is in effect, it
protects against loss of data in layout segments.

While not explicitly shown in {{fig-ffv2_layout4}}, each layout4
element returned in the logr_layout array of LAYOUTGET4res (see
Section 18.43.2 of {{RFC8881}}) describes a layout segment.  Hence,
each ffv2_layout4 also describes a layout segment.  It is possible
that the file is concatenated from more than one layout segment.
Each layout segment MAY represent different striping parameters.

The ffv2m_striping_unit_size field (inside each ffv2_mirror4) is
the stripe unit size in use for that mirror.  The stripe width
W is given by the number of elements in ffv2s_data_servers
within each ffv2_stripes4 (the count of data servers over which
each stripe is spread).  If ffv2m_striping is FFV2_STRIPING_NONE
the mirror is unstriped and ffv2m_striping_unit_size MUST be 1
(matching the FFV2_STRIPING_NONE rule in {{sec-ffv2-mirror4}}
and {{sec-striping}}); when ffv2m_striping is
FFV2_STRIPING_SPARSE or FFV2_STRIPING_DENSE the field carries
the stripe unit size in bytes with a minimum of 64.  The
mapping scheme (sparse or dense) is selected per mirror by
ffv2m_striping and is detailed in {{sec-striping}}.

Stripe unit size and stripe count MAY differ between mirrors in
the same layout segment.  In particular, mirrors of different
encoding types (see {{sec-heterogeneous-mirrors}}) have stripe
counts determined by their respective (fdp_data, fdp_parity)
protection structures, and there is no requirement that those
structures match across mirrors.  Each mirror is self-consistent
internally; cross-mirror coherence is at the byte level (every
mirror represents the same file bytes), not at the stripe-geometry
level.

The ffv2l_mirrors field represents an array of state information for
each mirrored copy of the current layout segment.  Each element is
described by a ffv2_mirror4 type.

ffv2ds_deviceid provides the deviceid of the storage device holding
the data file.

ffv2ds_file_info is an array of ffv2_file_info4 structures, each
pairing a filehandle (ffv2fi_fh_vers) with a stateid (ffv2fi_stateid).
There MUST be exactly as many elements in ffv2ds_file_info as there
are in ffv2da_versions.  Each element of the array corresponds to a
particular combination of ffv2dv_version, ffv2dv_minorversion, and
ffv2dv_coupling provided for the device.  The array allows for
server implementations that have different filehandles and stateids
for different combinations of version, minor version, and coupling
strength.  See {{sec-version-errors}} for how to handle versioning
issues between the client and storage devices.

For tight coupling, ffv2fi_stateid provides the stateid to be used
by the client to access the file.  The metadata server registers
ffv2fi_stateid with each tight coupling capable storage device via
TRUST_STATEID (see {{sec-tight-coupling-control}}) before returning
the layout; the storage device validates subsequent CHUNK operations
against its trust table.

For loose coupling and an NFSv4 storage device (necessarily a
PASSTHROUGH mirror per {{sec-ff_device_addr4}}, since non-PASSTHROUGH
encodings require tight coupling), the client MUST
use the anonymous stateid to perform I/O on the storage device,
because the metadata server stateid has no meaning to a storage
device that is not participating in the control protocol.  In
this case the metadata server MUST set ffv2fi_stateid to the
anonymous stateid.

For an NFSv3 storage device (ffv2dv_version = 3), the tight coupling
model does not apply: {{sec-ff_device_addr4}} requires
ffv2dv_coupling to equal FFV2_COUPLING_SYNTHETIC_UIDS whenever
ffv2dv_version equals 3, because NFSv3 has no wire encoding for
stateids.  The corresponding
ffv2fi_stateid element in the ffv2ds_file_info array MUST therefore
be the anonymous stateid and is unused; an NFSv3 data server uses
the synthetic-uid fencing model (see {{sec-Fencing-Clients}})
rather than a stateid-based trust table.

This specification of the ffv2fi_stateid restricts both models for
NFSv4.x storage protocols:

loosely couple

:  the stateid has to be an anonymous stateid

tightly couple

:  the stateid has to be a global stateid

By pairing each ffv2fi_fh_vers with its own ffv2fi_stateid inside
ffv2_file_info4, the flexible file v2 layout addresses a limitation
in the flexible file v1 layout where a single stateid was shared
across all filehandles.

Whether the ffv2fi_stateid values across an ffv2_file_info4 array
are distinct depends on each entry's coupling mode per the rules
above.  Loose-coupling and NFSv3 entries MUST carry the anonymous
stateid; those entries are therefore byte-identical by mandate.
Tight-coupling entries carry stateids the metadata server assigned
and registered via TRUST_STATEID; the metadata server MAY assign
these distinctly per filehandle version or MAY reuse the same
stateid across entries.

The client MUST treat each (ffv2fi_fh_vers, ffv2fi_stateid) pair as
an opaque, independent authorization unit.  The client MUST NOT
compare ffv2fi_stateid values across entries in the array and MUST
NOT infer any relationship between two entries whose stateid values
are byte-identical.  When the client selects an entry to use for
I/O, it presents that entry's stateid with that entry's filehandle;
other entries in the array are unused for that I/O.

For loosely coupled storage devices, ffv2ds_user and ffv2ds_group
provide the synthetic user and group to be used in the RPC credentials
that the client presents to the storage device to access the data
files.  For tightly coupled storage devices, the user and group on
the storage device will be the same as on the metadata server; that
is, if ffv2dv_coupling has any tight coupling flag set (see
{{sec-ff_device_addr4}}), then the client MUST ignore both
ffv2ds_user and ffv2ds_group.

The allowed values for both ffv2ds_user and ffv2ds_group are specified
as owner and owner_group, respectively, in Section 5.9 of {{RFC8881}}.
For NFSv3 compatibility, user and group strings that consist of
decimal numeric values with no leading zeros can be given a special
interpretation by clients and servers that choose to provide such
support.  The receiver may treat such a user or group string as
representing the same user as would be represented by an NFSv3 uid
or gid having the corresponding numeric value.  Note that if using
Kerberos for security, the expectation is that these values will
be a name@domain string.

ffv2ds_efficiency describes the metadata server's evaluation as to
the effectiveness of each mirror.  Note that this is per layout and
not per device as the metric may change due to perceived load,
availability to the metadata server, etc.  Higher values denote
higher perceived utility.  The way the client can select the best
mirror to access is discussed in {{sec-select-mirror}}.

###  Error Codes from LAYOUTGET

{{RFC8881}} provides little guidance as to how the client is to
proceed with a LAYOUTGET that returns an error of either
NFS4ERR_LAYOUTTRYLATER, NFS4ERR_LAYOUTUNAVAILABLE, and NFS4ERR_DELAY.
Within the context of this document:

NFS4ERR_LAYOUTUNAVAILABLE:
:  there is no layout available and the I/O is to go to the metadata
server.  Note that it is possible to have had a layout before a
recall and not after.

NFS4ERR_LAYOUTTRYLATER:
:  there is some issue preventing the layout from being granted.
If the client already has an appropriate layout, it should continue
with I/O to the storage devices.

NFS4ERR_DELAY:
:  there is some issue preventing the layout from being granted.
If the client already has an appropriate layout, it should not
continue with I/O to the storage devices.

###  Client Interactions with FFV2_FLAGS_NO_IO_THRU_MDS

FFV2_FLAGS_NO_IO_THRU_MDS is normative: when the metadata
server sets FFV2_FLAGS_NO_IO_THRU_MDS on a layout, the client
MUST NOT proxy I/O for that layout through the metadata server,
even after detecting a network disconnect to a storage device
({{sec-ffv2_flags4}}).  A client that cannot reach a storage
device on which it holds a NO_IO_THRU_MDS layout MUST return
the layout via LAYOUTRETURN and reacquire (via LAYOUTGET), at
which point the metadata server chooses whether to grant a new
layout with the flag cleared, grant a layout naming a different
storage device, or fall back to metadata-server-terminated I/O
via the encoding-negotiation path
({{sec-encoding-negotiation}}) with the flag cleared.

The NO_IO_THRU_MDS flag is not advisory; it is an
instruction the client MUST honor.  When I/O through the
metadata server is required (for example, via the encoding-
negotiation fallback path in {{sec-encoding-negotiation}}),
the metadata server MUST clear NO_IO_THRU_MDS on the
fallback layout it issues.  A client MUST NOT interpret
a set NO_IO_THRU_MDS flag as advisory or bypass it.

##  LAYOUTCOMMIT

The flexible file v2 layout does not use lou_body inside the
loca_layoutupdate argument to LAYOUTCOMMIT.  If lou_type is
LAYOUT4_FLEX_FILES_V2, the lou_body field MUST have a zero length (see
Section 18.42.1 of {{RFC8881}}).

##  Interactions between Devices and Layouts

The file layout type is defined such that the relationship between
multipathing and filehandles can result in either 0, 1, or N
filehandles (see Section 13.3 of {{RFC8881}}).  Some rationales for
this are clustered servers that share the same filehandle or allow
for multiple read-only copies of the file on the same storage device.
In the flexible file v2 layout, while there is an array of
filehandles, they are independent of the multipathing being used.
If the metadata server wants to provide multiple read-only copies
of the same file on the same storage device, then it should provide
multiple mirrored instances, each with a different ffv2_device_addr4.
The client can then determine that, since each of the ffv2fi_fh_vers
values within ffv2ds_file_info are different, there are multiple
copies of the file for the current layout segment available.

##  Handling Version Errors {#sec-version-errors}

When the metadata server provides the ffv2da_versions array in the
ffv2_device_addr4 (see {{sec-ff_device_addr4}}), the client is
able to determine whether or not it can access a storage device
with any of the supplied combinations of ffv2dv_version,
ffv2dv_minorversion, and ffv2dv_coupling.  However, due to the limitations of
reporting errors in GETDEVICEINFO (see Section 18.40 in {{RFC8881}}),
the client is not able to specify which specific device it cannot
communicate with over one of the provided ffv2dv_version and
ffv2dv_minorversion combinations.  Using ffv2_ioerr4 ({{sec-ffv2_ioerr4}})
inside either the LAYOUTRETURN (see Section 18.44 of {{RFC8881}})
or the LAYOUTERROR (see Section 15.6 of {{RFC7862}} and {{sec-LAYOUTERROR}}
of this document), the client can isolate the problematic storage
device.

The error code to return for LAYOUTRETURN and/or LAYOUTERROR is
NFS4ERR_MINOR_VERS_MISMATCH.  It does not matter whether the mismatch
is a major version (e.g., client can use NFSv3 but not NFSv4) or
minor version (e.g., client can use NFSv4.1 but not NFSv4.2), the
error indicates that for all the supplied combinations for ffv2dv_version
and ffv2dv_minorversion, the client cannot communicate with the storage
device.  The client can retry the GETDEVICEINFO to see if the
metadata server can provide a different combination, or it can fall
back to doing the I/O through the metadata server.

#  Striping {#sec-striping}

The flexible file v2 layout inherits the dense and sparse striping
dispositions defined by the file layout type in Section 13.4 of
{{RFC8881}}.  The disposition for a given
mirror is selected by the ffv2m_striping field (see
{{sec-ffv2-mirror4}}) and applies to every data server in that
mirror's ffv2s_data_servers list.  Three values are permitted:

FFV2_STRIPING_NONE:
:  The mirror is not striped.  ffv2m_striping_unit_size MUST be 1
   and ffv2m_stripes MUST contain exactly one stripe.  The entire
   mirror lives on that stripe's single data server list, with
   no offset transformation.

FFV2_STRIPING_SPARSE:
:  Logical offsets within the file map to the same numeric
   offset on each data server.  A data server that does not own
   the stripe unit at a given logical offset presents a hole at
   that offset.  This is the simpler model and matches the
   mental picture of "the file is laid out end-to-end on each
   data server, but each data server stores only its stripe
   units".

FFV2_STRIPING_DENSE:
:  Stripe units owned by a given data server are packed
   contiguously on that data server, with no holes.  The
   logical offset is transformed into a compact physical offset
   on the target data server.  This matches pre-existing
   deployments that follow the dense layout convention of
   Section 13.4.4 of {{RFC8881}}.

The mapping math for sparse and dense is given in
{{fig-striping-math}}.  Common definitions apply to both.

~~~
L: logical offset within the file (bytes)
U: stripe-unit size in bytes  = ffv2m_striping_unit_size
W: stripe width               = length of ffv2s_data_servers
S: stripe size in bytes       = W * U
N: stripe number              = L / S
i: index (0-based) of the data server that owns L
                              = (L / U) mod W
R: byte offset within the stripe unit
                              = L mod U

FFV2_STRIPING_SPARSE:
  physical offset on data server i:
      P_sparse(L) = L
  other data servers see a hole at offset L.

FFV2_STRIPING_DENSE:
  physical offset on data server i:
      P_dense(L) = N * U + R
             = (L / S) * U + (L mod U)
  each data server stores only the stripe units it owns,
  packed contiguously.
~~~
{: #fig-striping-math title="Sparse and dense stripe mapping math"}

#  Recovering from Client I/O Errors

The pNFS client may encounter errors when directly accessing the
storage devices.  However, it is the responsibility of the metadata
server to recover from the I/O errors.  When the LAYOUT4_FLEX_FILES_V2
layout type is used, the client MUST report the I/O errors to the
server at LAYOUTRETURN time using the ffv2_ioerr4 structure (see
{{sec-ffv2_ioerr4}}).

The metadata server analyzes the error and determines the required
recovery operations such as recovering media failures or reconstructing
missing data files.

The metadata server MUST recall any outstanding layouts to allow
it exclusive write access to the stripes being recovered and to
prevent other clients from hitting the same error condition.  In
these cases, the server MUST complete recovery before handing out
any new layouts to the affected byte ranges.

The client's retry disposition depends on which encoding the
affected mirror uses.  The two subsections below split the
encoding types into two families: mirrored / PASSTHROUGH (where
the storage device holds the file's bytes directly, so retrying
the I/O through the metadata server is possible), and the
chunked encodings (where the storage device holds encoded
shards, so retrying the I/O through the metadata server is
meaningful only if a proxy server is available to translate).

## Retry policy for mirrored and PASSTHROUGH encodings {#sec-io-error-retry-mirrored}

For a mirror using FFV2_ENCODING_MIRRORED or
FFV2_ENCODING_PASSTHROUGH, the storage device holds the file's
bytes directly (no chunk envelope, no encoding transform), and
an ordinary NFS READ or WRITE on the metadata server accesses
the same bytes.

Although the client implementation has the option to propagate
a corresponding error to the application that initiated the I/O
operation and drop any unwritten data, the client should attempt
to retry the original I/O operation by either requesting a new
layout or sending the I/O via regular NFSv4.1+ READ or WRITE
operations to the metadata server.  The client SHOULD attempt to
retrieve a new layout and retry the I/O operation using the storage
device first and only retry the I/O operation via the metadata
server if the error persists.

## Retry policy for chunked (erasure-coded) encodings {#sec-io-error-retry-chunked}

For a mirror using any chunked encoding (any FFV2_ENCODING_*
value other than FFV2_ENCODING_PASSTHROUGH), the storage device
holds encoded shards inside chunk envelopes rather than the
file's bytes, and retrying the I/O through the metadata server
as a regular NFS READ or WRITE against the file is not an
equivalent fallback: the metadata server does not hold the
encoded shards, and the file's bytes are recoverable only by
decoding through the mirror's erasure transform.  The client's
retry disposition is correspondingly different.

For a CHUNK_READ error, the client SHOULD attempt local
reconstruction from surviving shards before returning the layout,
provided the encoding is a k+m code and the client holds
(directly or by fetching from unaffected data servers in the
same stripe) at least k surviving shards.  A successful local
reconstruction satisfies the read; the client MUST still record
the ioerr and report it at LAYOUTRETURN so the metadata server
can drive repair via CB_CHUNK_REPAIR
({{sec-CB_CHUNK_REPAIR}}) and the repair-actor flow
({{sec-repair-selection}}).

For a CHUNK_WRITE error, or when a CHUNK_READ error cannot be
satisfied by local reconstruction (fewer than k surviving
shards, or a non-recoverable chunk_guard4 CAS failure), the
client SHOULD return the layout with the ioerr recorded after
its own storage-device-directed retries (multipath, transient
error) have been exhausted.  The client MUST NOT retry the
same I/O through the metadata server as a regular NFSv4.1+
READ or WRITE against the file: the metadata server does not
hold the encoded shards, so an I/O through the metadata server
would either be rejected or would bypass the encoding transform
and corrupt the file.

Retrying the I/O through the metadata server is meaningful for
a chunked encoding only when a proxy server is available to
translate on the metadata server's behalf: the proxy server
admits the client's I/O, performs the encoding transform, and
issues the corresponding CHUNK operations to the data servers.
When no proxy server is available for the affected file, the
client's remaining option is to re-request a layout after the
metadata server has driven repair to completion.

#  Client-Side Protection Modes

##  Client-Side Mirroring {#sec-CSM}

The flexible file v2 layout has a simple model in place for the
mirroring of the file data constrained by a layout segment.  Each
mirror in ffv2l_mirrors is an independent representation of the
file's contents for that segment: the XDR (see {{fig-ffv2_mirror4}})
lets each mirror carry its own encoding
(ffv2m_coding_type_data), its own striping pattern
(ffv2m_striping and ffv2m_stripes), and its own set of data
servers.  A single layout MAY combine dissimilar mirrors -- for
example, one FFV2_ENCODING_MIRRORED mirror and one
FFV2_ENCODING_RS_VANDERMONDE mirror of the same file contents,
as sketched in {{fig-parallel-filesystem}} -- and there is no
cross-mirror constraint that striping patterns or encoding
choices match.

There is likewise no assumption that each copy of the mirror is
stored identically on the storage devices.  For example, one device
might employ compression or deduplication on the data.  What each
mirror MUST provide is the same reconstructed file contents on
read (after any decoding through the mirror's encoding
transform); the on-disk representation and the wire representation
per mirror are consequences of that mirror's independently
selected encoding.

The metadata server is responsible for determining the number of
mirrored copies and the location of each mirror.  While the client
may provide a hint to how many copies it wants (see {{sec-ffv2-layouthint}}),
the metadata server can ignore that hint; in any event, the client
has no means to dictate either the storage device (which also means
the coupling and/or protocol levels to access the layout segments)
or the location of said storage device.

The updating of mirrored layout segments is done via client-side
mirroring.  With this approach, the client is responsible for making
sure modifications are made on all copies of the layout segments
it is informed of via the layout.  If a layout segment is being
resilvered to a storage device, that mirrored copy will not be in
the layout.  Thus, the metadata server (or a proxy server acting
on its behalf, if one is available for the file) MUST update that
copy until the client is presented it in a layout.  If the
FFV2_FLAGS_WRITE_ONE_MIRROR is set in ffv2l_flags, the client
need only update one of the mirrors (see {{sec-write-mirrors}}).
If the client is writing to the layout segments via the metadata
server, then the metadata server (or a proxy server acting on its
behalf) MUST update all copies of the mirror; see the encoding
constraint on FFV2_FLAGS_WRITE_ONE_MIRROR in {{sec-ffv2_flags4}}
for the case where doing so requires the propagation actor to
translate across encodings.  As seen in {{sec-mds-resilvering}},
during the resilvering, the layout is recalled, and the client
has to make modifications through the metadata-server side.

###  Selecting a Mirror {#sec-select-mirror}

When the metadata server grants a layout to a client, it MAY let
the client know how fast it expects each mirror to be once the
request arrives at the storage devices via the ffv2ds_efficiency
member.  While the algorithms to calculate that value are left to
the metadata server implementations, factors that could contribute
to that calculation include speed of the storage device, physical
memory available to the device, operating system version, current
load, etc.

However, what should not be involved in that calculation is a
perceived network distance between the client and the storage device.
The client is better situated for making that determination based
on past interaction with the storage device over the different
available network interfaces between the two; that is, the metadata
server might not know about a transient outage between the client
and storage device because it has no presence on the given subnet.

As such, it is the client that decides which mirror to access for
reading the file.  The requirements for writing to mirrored layout
segments are presented below.

###  Writing to Mirrors {#sec-write-mirrors}

####  Single Storage Device Updates Mirrors

If the FFV2_FLAGS_WRITE_ONE_MIRROR flag in ffv2l_flags is set, the
client MAY update just one of the copies of the layout segment.
For this case, the storage device MUST ensure that all copies of
the mirror are updated when any one of the mirrors is updated.  If
the storage device gets an error when updating one of the mirrors,
then it MUST inform the client that the original WRITE had an error.
The client then MUST inform the metadata server (see {{sec-write-errors}}).
The client's responsibility with respect to COMMIT is explained in
{{sec-write-commits}}.  The client may choose any one of the mirrors
and may use ffv2ds_efficiency as described in {{sec-select-mirror}}
when making this choice.

####  Client Updates All Mirrors

If the FFV2_FLAGS_WRITE_ONE_MIRROR flag in ffv2l_flags is not set, the
client is responsible for updating all mirrored copies of the layout
segments that it is given in the layout.  A single failed update
is sufficient to fail the entire operation.  If all but one copy
is updated successfully and the last one provides an error, then
the client MUST inform the metadata server about the error.
The client can use either LAYOUTRETURN or LAYOUTERROR to inform the
metadata server that the update failed to that storage device.  If
the client is updating the mirrors serially, then it SHOULD stop
at the first error encountered and report that to the metadata
server.  If the client is updating the mirrors in parallel, then
it SHOULD wait until all storage devices respond so that it can
report all errors encountered during the update.

####  Handling Write Errors {#sec-write-errors}

When the client reports a write error to the metadata server, the
metadata server is responsible for determining if it wants to remove
the errant mirror from the layout, if the mirror has recovered from
some transient error, etc.  When the client tries to get a new
layout, the metadata server informs it of the decision by the
contents of the layout.  The client MUST NOT assume that the contents
of the previous layout will match those of the new one.  If it has
updates that were not committed to all mirrors, then it MUST resend
those updates to all mirrors.

There is no provision in the protocol for the metadata server to
directly determine that the client has or has not recovered from
an error.  For example, if a storage device was network partitioned
from the client and the client reported the error to the metadata
server, then the network partition would be repaired, and all of
the copies would be successfully updated.  There is no mechanism
for the client to report that fact, and the metadata server is
forced to repair the file across the mirror.

If the client supports NFSv4.2, it can use LAYOUTERROR and LAYOUTRETURN
to provide hints to the metadata server about the recovery efforts.
A LAYOUTERROR on a file is for a non-fatal error.  A subsequent
LAYOUTRETURN without a ffv2_ioerr4 indicates that the client successfully
replayed the I/O to all mirrors.  Any LAYOUTRETURN with a ffv2_ioerr4
is an error that the metadata server needs to repair.  The client
MUST be prepared for the LAYOUTERROR to trigger a CB_LAYOUTRECALL
if the metadata server determines it needs to start repairing the
file.

####  Handling Write COMMITs {#sec-write-commits}

When stable writes are done to the metadata server or to a single
replica (if allowed by the use of FFV2_FLAGS_WRITE_ONE_MIRROR), it
is the responsibility of the receiving node to propagate the written
data stably, before replying to the client.

In the corresponding cases in which unstable writes are done, the
receiving node does not have any such obligation, although it may
choose to asynchronously propagate the updates.  However, once a
COMMIT is replied to, all replicas MUST reflect the writes that
have been done, and this data MUST have been committed to stable
storage on all replicas.

In order to avoid situations in which stale data is read from
replicas to which writes have not been propagated:

-  A client that has outstanding unstable writes made to single
   node (metadata server or storage device) MUST do all reads from
   that same node.

-  When writes are flushed to the server (for example, to implement
   close-to-open semantics), a COMMIT must be done by the client
   to ensure that up-to-date written data will be available
   irrespective of the particular replica read.

###  Metadata Server Resilvering of the File {#sec-mds-resilvering}

The metadata server may elect to create a new mirror of the layout
segments at any time.  This might be to resilver a copy on a storage
device that was down for servicing, to provide a copy of the layout
segments on storage with different storage performance characteristics,
etc.  As the client will not be aware of the new mirror and the
metadata server will not be aware of updates that the client is
making to the layout segments, the metadata server MUST recall the
writable layout segment(s) that it is resilvering.  If the client
issues a LAYOUTGET for a writable layout segment that is in the
process of being resilvered, then the metadata server can deny that
request with an NFS4ERR_LAYOUTUNAVAILABLE.

The client's fallback while the layout is withheld follows the
per-encoding rules in
{{sec-io-error-retry-mirrored}} and {{sec-io-error-retry-chunked}}:
for a mirror whose I/O reduces to FFV2_ENCODING_MIRRORED or
FFV2_ENCODING_PASSTHROUGH the client MAY perform the I/O through
the metadata server as an ordinary NFSv4.1+ READ or WRITE; for a
mirror using any chunked encoding the metadata server itself
cannot service that I/O (it does not hold the encoded shards),
so the client's only fallback path is through a proxy server
if one is available for the file.  If no proxy server is available, the
client MUST wait for the metadata server to complete resilvering
and re-issue LAYOUTGET rather than attempt to route the I/O
through the metadata server.

## Client-Side Erasure Coding

Erasure coding takes a data block and transforms it to a payload
to send to the data servers (see {{fig-encoding-data-block}}).  It
generates a metadata header and transformed block per data server.
The header is metadata information for the transformed block.  From
now on, the metadata is simply referred to as the header and the
transformed block as the chunk.  The payload of a data block is the
set of generated headers and chunks for that data block.

The chunk header carries four conceptual fields, each stored
on the data server with the chunk and carried on the wire by
every op that reads or writes the chunk.  This document does
not define a single XDR struct for the chunk header; instead
each op names the four fields directly, and the fields
appear on the wire under an op-specific prefix.

Guard:
:  an XDR chunk_guard4 (cg_gen_id, cg_client_id) pair
   maintained by the data server to serialize concurrent
   writers (see {{sec-chunk_guard4}}).  Each accepted
   CHUNK_WRITE advances the target chunk's guard, and readers
   observe the accepted guard on the read path.

Owner:
:  an XDR chunk_owner4 (co_cohort_id, co_client_id, co_id)
   triple identifying the writer's cohort (see
   {{sec-chunk_owner4}}).  The owner is the identity that
   lifecycle operations (CHUNK_FINALIZE, CHUNK_COMMIT,
   CHUNK_ROLLBACK) address.

Payload identifier:
:  a writer-chosen uint32_t naming the chunk's position
   within the payload's shard array.  Unlike the guard and
   owner, the payload identifier is not a sub-struct with
   named fields; it is a bare scalar carried directly under
   an op-specific prefix on each op's wire arguments:
   cwa_payload_id on CHUNK_WRITE ({{sec-CHUNK_WRITE}}),
   cr_payload_id in the CHUNK_READ result
   ({{sec-CHUNK_READ}}), and cwra_payload_id on
   CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}).  The
   value the three carry names the same conceptual header
   field; only the wire prefix differs across ops.

Checksum:
:  a 32-bit CRC computed over the header and the chunk.
   Because the checksum field is itself part of the header,
   the computation treats the bytes of that field as zero so
   that the result is independent of the field's wire value;
   the writer then stores the computed CRC into the checksum
   field for transmission.  To validate on the read path, the
   receiver saves the received checksum, treats those bytes
   as zero, recomputes the CRC over the header and chunk, and
   compares against the saved value.  By combining the two
   parts of the payload in the CRC, integrity is ensured for
   both parts.

While the data block might have a length of 4kB, that does not
necessarily mean that the length of the chunk is 4kB.  That length
is determined by the erasure encoding type algorithm.  For example,
Reed Solomon might have 4kB chunks with the data integrity being
compromised by parity chunks.  Another example would be the Mojette
Transformation, which might have 1kB chunk lengths.

The payload contains redundancy which will allow the erasure
encoding type algorithm to repair chunks in the payload as it is
transformed back to a data block (see {{fig-decoding-db}}).

The protocol provides two levels of payload integrity, consumed at
different points in the read path:

Atomicity:
:  A payload is atomic when all of the chunks that belong
   to it carry the same chunk_guard4 value (see
   {{sec-chunk_guard4}}).  Atomicity alone does NOT imply the
   bytes are free of corruption; it means only that every chunk in
   the payload came from one write transaction.  A reader detects
   a non-atomic payload (a torn read across writes) when it
   assembles a payload and finds differing chunk_guard4 values
   across chunks.

Integrity:
:  A payload has integrity when it is atomic AND every
   contained chunk passes its checksum check.  Integrity is the
   precondition for returning the payload's data block to the
   application.

The separation matters because the two checks detect different
failure modes.  Atomicity detects protocol-level failures (racing
writers, partial writes, rollback windows); the checksum detects
byte-level corruption (network errors, media errors, software bugs
in the erasure transform).  Neither subsumes the other.

The two-level integrity model also reflects a deeper property of
distributed writes: last-writer-wins does not apply to a payload
spread across independent data servers.  The ordering of writes
arriving at one data server may differ from the ordering arriving
at another; the "last" write on one data server may well be the
"first" on another.  The chunk_guard4 CAS primitive (see
{{sec-chunk_guard4}}) resolves this by serializing concurrent
writers per chunk rather than by imposing a global order.

The erasure coding algorithm itself might not be sufficient to
detect all byte-level errors in the chunks.  The checksum checks
allow the data server to detect chunks with integrity issues; the
erasure decoding algorithm can then reconstruct the affected
chunks from the remaining integral chunks in the payload.

### Encoding a Data Block

~~~
                 +-------------+
                 | data block  |
                 +-------+-----+
                         |
                         |
   +---------------------+-------------------------------+
   |            Erasure Encoding (Transform Forward)     |
   +---+----------------------+---------------------+----+
       |                      |                     |
       |                      |                     |
   +-------------------+  +-------------------+  +-------------------+
   | HEADER            |..| HEADER            |..| HEADER            |
   +-------------------+  +-------------------+  +-------------------+
   | owner:            |..| owner:            |..| owner:            |
   |   co_cohort_id:42 |..|   co_cohort_id:42 |..|   co_cohort_id:42 |
   |   co_client_id: 6 |..|   co_client_id: 6 |..|   co_client_id: 6 |
   |   co_id       : 1 |..|   co_id       : 1 |..|   co_id       : 1 |
   | guard:            |..| guard:            |..| guard:            |
   |   cg_gen_id   : 3 |..|   cg_gen_id   : 3 |..|   cg_gen_id   : 3 |
   |   cg_client_id: 6 |..|   cg_client_id: 6 |..|   cg_client_id: 6 |
   | payload_id    : 0 |..| payload_id    : M |..| payload_id    : 5 |
   | checksum      :   |..| checksum      :   |..| checksum      :   |
   +-------------------+  +-------------------+  +-------------------+
   | CHUNK             |..| CHUNK             |..| CHUNK             |
   +-------------------+  +-------------------+  +-------------------+
   | data: ....        |..| data: ....        |..| data: ....        |
   +-------------------+  +-------------------+  +-------------------+
      Data Server 1          Data Server N          Data Server 6
~~~
{: #fig-encoding-data-block title="Encoding a Data Block" }

Each data block of the file resident in the client's cache of the
file will be encoded into N different payloads to be sent to the
data servers as shown in {{fig-encoding-data-block}}.  As CHUNK_WRITE
(see {{sec-CHUNK_WRITE}}) can encode multiple write_chunk4 into a
single transaction, a more accurate description of a CHUNK_WRITE
is in {{fig-example-chunk-write-args}}.

~~~ art
  +------------------------------------+
  | CHUNK_WRITEargs                    |
  +------------------------------------+
  | cwa_stateid: 0                     |
  | cwa_offset: 1                      |
  | cwa_stable: FILE_SYNC4             |
  | cwa_cohort_id: 0x000000000000002a  |
  | cwa_client_id: 6                   |
  | cwa_co_ids:                        |
  |         [0]:  1                    |
  |         [1]:  2                    |
  |         [2]:  3                    |
  | cwa_payload_id: 0                  |
  | cwa_chunk_size  :  1048            |
  | cwa_checksums:                     |
  |         [0]:  0x32ef89             |
  |         [1]:  0x56fa89             |
  |         [2]:  0x7693af             |
  | cwa_chunks  :  ......              |
  +------------------------------------+
~~~
{: #fig-example-chunk-write-args title="Example of CHUNK_WRITE_args" }

This describes a 3 block write of data from an offset of 1 block
in the file.  All three chunks share cwa_cohort_id and
cwa_client_id, so the cohort identity is presented once; each
chunk's writer-chosen opaque co_id appears in the co-indexed
cwa_co_ids array (here the client chose 1, 2, 3, but any
distinct-per-cohort uint32_t values would be equally valid per
{{sec-chunk_owner4}}).  The data server can construct the cohort
record for the i'th chunk from cwa_chunks using cwa_payload_id,
cwa_cohort_id + cwa_client_id + `cwa_co_ids[i]`, and the i'th
checksum from cwa_checksums.  The cwa_chunks are sent together
as a byte stream to increase performance.

Assuming that there were no issues, {{fig-example-chunk-write-res}}
illustrates the results.  The payload sequence id is implicit in
the CHUNK_WRITEargs.

~~~ art
  +-------------------------------+
  | CHUNK_WRITEresok              |
  +-------------------------------+
  | cwr_count: 3                  |
  | cwr_committed: FILE_SYNC4     |
  | cwr_writeverf: 0xf1234abc     |
  | cwr_owners[0]:                |
  |        co_cohort_id: 0x2a     |
  |        co_client_id: 6        |
  |        co_id: 1               |
  | cwr_owners[1]:                |
  |        co_cohort_id: 0x2a     |
  |        co_client_id: 6        |
  |        co_id: 2               |
  | cwr_owners[2]:                |
  |        co_cohort_id: 0x2a     |
  |        co_client_id: 6        |
  |        co_id: 3               |
  +-------------------------------+
~~~
{: #fig-example-chunk-write-res title="Example of CHUNK_WRITE_res" }

#### Worked Example: Calculating the CRC32

The examples in this section and in
{{sec-checking-crc32}} illustrate checksum computation
and verification using CHECKSUM_ALG_CRC32 as the worked
algorithm.  The other registered checksum algorithms (see
{{sec-checksum4}}) follow the same pattern -- the algorithm
names a function over the header and chunk bytes, the writer
fills cs_value with the computed output, and the reader
recomputes and compares.  Only the algorithm and the
cs_value length differ.

~~~
  +--------------------+
  | HEADER             |
  +--------------------+
  | guard:             |
  |   gen_id   : 7     |
  |   client_id: 6     |
  | payload_id : 0     |
  | crc32   : 0        |
  +--------------------+
  | CHUNK              |
  +--------------------+
  | data:  ....        |
  +--------------------+
        Data Server 1
~~~
{: #fig-calc-before title="CRC32 Before Calculation" }

Assuming the header and payload as in {{fig-calc-before}}, the crc32
needs to be calculated in order to fill in the cwa_checksums entry field.  In
this case, the crc32 is calculated over the 4 fields as shown in
the header and the cw_chunk.  In this example, it is calculated to
be 0x21de8.  The resulting CHUNK_WRITE is shown in {{fig-calc-crc-after}}.

~~~ art
  +------------------------------------+
  | CHUNK_WRITEargs                    |
  +------------------------------------+
  | cwa_stateid: 0                     |
  | cwa_offset: 1                      |
  | cwa_stable: FILE_SYNC4             |
  | cwa_cohort_id: 0x000000000000002b  |
  | cwa_client_id: 6                   |
  | cwa_co_ids:                        |
  |         [0]:  1                    |
  | cwa_payload_id: 0                  |
  | cwa_chunk_size  :  1048            |
  | cwa_checksums:                     |
  |         [0]:  0x21de8              |
  | cwa_chunks  :  ......              |
  +------------------------------------+
~~~
{: #fig-calc-crc-after title="CRC32 After Calculation" }

### Decoding a Data Block

~~~
    Data Server 1          Data Server N          Data Server 6
  +----------------+     +----------------+     +----------------+
  | HEADER         | ... | HEADER         | ... | HEADER         |
  +----------------+     +----------------+     +----------------+
  | guard:         | ... | guard:         | ... | guard:         |
  |   gen_id   : 3 | ... |   gen_id   : 3 | ... |   gen_id   : 3 |
  |   client_id: 6 | ... |   client_id: 6 | ... |   client_id: 6 |
  | payload_id : 0 | ... | payload_id : M | ... | payload_id : 5 |
  | crc32   :      | ... | crc32   :      | ... | crc32   :      |
  +----------------+     +----------------+     +----------------+
  | CHUNK          | ... | CHUNK          | ... | CHUNK          |
  +----------------+     +----------------+     +----------------+
  | data: ....     | ... | data: ....     | ... | data: ....     |
  +---+------------+     +--+-------------+     +-+--------------+
      |                     |                     |
      |                     |                     |
  +---+---------------------+---------------------+-----+
  |            Erasure Decoding (Transform Reverse)     |
  +---------------------+-------------------------------+
                        |
                        |
                +-------+-----+
                | data block  |
                +-------------+
~~~
{: #fig-decoding-db title="Decoding a Data Block" }

When reading chunks via a CHUNK_READ operation, the client will
decode them into data blocks as shown in {{fig-decoding-db}}.

At this time, the client could detect issues in the integrity of
the data.  The handling and repair are out of the scope of this
document and MUST be addressed in the document describing each
erasure encoding type.

#### Worked Example: Checking the CRC32 {#sec-checking-crc32}

~~~ art
  +------------------------------------+
  | CHUNK_READresok                    |
  +------------------------------------+
  | crr_eof: false                     |
  | crr_chunks[0]:                     |
  |        cr_checksum: 0x21de8        |
  |        cr_owner:                   |
  |            co_cohort_id: 0x2b      |
  |            co_client_id: 6         |
  |            co_id       : 1         |
  |        cr_chunk  :  ......         |
  +------------------------------------+
~~~
{: #fig-example-chunk-read-crc title="CRC32 on the Wire" }

Assuming the CHUNK_READ results as in {{fig-example-chunk-read-crc}},
the crc32 needs to be checked in order to detect accidental
corruption.  Conceptually, a header and payload can be built as
shown in {{fig-example-crc-checked}}.  The crc32 is calculated
over the 4 fields as shown in the header and the cr_chunk.  In
this example, it is calculated to be 0x21de8; because the
calculated value matches the received cr_checksum, no
accidental corruption was detected on this payload.  (Content
authentication -- protection against adversarial modification --
requires a keyed MAC or signature; see
{{sec-security-checksum-scope}}.)

~~~
  +--------------------+
  | HEADER             |
  +--------------------+
  | guard:             |
  |   gen_id   : 7     |
  |   client_id: 6     |
  | payload_id  : 0    |
  | crc32    : 0       |
  +--------------------+
  | CHUNK              |
  +--------------------+
  | data:  ....        |
  +--------------------+
       Data Server 1
~~~
{: #fig-example-crc-checked title="CRC32 Being Checked" }

### Write Modes

There are three writing modes for erasure coding, aligned with
the three workload classes in {{sec-use-cases}}.  The mode is
selected by the metadata server using FFV2_FLAGS_ONLY_ONE_WRITER
in the ffv2l_flags in the ffv2_layout4 (see {{fig-ffv2_layout4}})
to inform the client whether it is the only writer to the file
or not, and by the client's own understanding of its workload
class when the flag is unset.

Single writer:
:  When FFV2_FLAGS_ONLY_ONE_WRITER is set, the client is the
only writer to the file.  CHUNK_WRITE with cwa_guard not set
can be used to write chunks.  There is no write contention,
but write holes can occur as the client overwrites old data.
The client does not need guarded writes, but it does need the
ability to rollback writes.  This mode corresponds to Use
Case 1 (single writer, multiple readers) in {{sec-use-cases}}.

Concurrent writers with occasional contention:
:  When FFV2_FLAGS_ONLY_ONE_WRITER is not set, the client is
one of several possible concurrent writers.  CHUNK_WRITE
with cwa_guard set MUST be used to write chunks.  Write holes
can be caused by multiple clients writing to the same chunk,
so the client needs guarded writes to prevent overwrites and
also needs the ability to rollback writes.  Racing writers
that lose the chunk_guard4 CAS receive NFS4ERR_CHUNK_GUARDED
and retry with a refreshed guard.  This mode corresponds to
Use Case 2 (multiple writers without sustained contention) in
{{sec-use-cases}}.

Concurrent writers on disjoint regions:
:  A specialization of the concurrent-writers mode above,
targeting Use Case 3 (multiple writers, disjoint regions --
the HPC checkpoint pattern) in {{sec-use-cases}}.  The wire
primitives are the same as the concurrent-writers mode
(cwa_guard set, chunk_guard4 CAS), but the deployment relies
on block alignment to keep per-chunk contention rare despite a
high overall writer count.  Contention that does occur is
resolved via the deterministic tiebreaker rule defined in
{{sec-chunk_guard4}}, so racing writers get a stable winner
across the mirror set without additional round trips.
Deployments that use an XOR-based erasure encoding and
expect frequent small edits from this workload class MAY
additionally use the delta-write protocol defined in
{{I-D.haynes-nfsv4-flexfiles-v2-delta-writes}}, which lets
the client forward per-projection XOR deltas directly to
each data server, avoiding client-side read-modify-write of
the full stripe on the small-edit path.

In both modes, clients MUST NOT overwrite payloads which already
contain non-atomicity.  This directly follows from {{sec-reading-chunks}}
and MUST be handled as discussed there.  Once atomicity in the
payload has been detected, the client can use those chunks as a
basis for read/modify/update.

CHUNK_WRITE is a two-pass operation in cooperation with
CHUNK_FINALIZE ({{sec-CHUNK_FINALIZE}}) and CHUNK_ROLLBACK
({{sec-CHUNK_ROLLBACK}}).  It writes new bytes into the chunk
and transitions the chunk to the PENDING state; the data
server is responsible for retaining the prior COMMITTED
content until the chunk reaches its next stable state.  While
a chunk is in PENDING or FINALIZED, a subsequent CHUNK_READ
does NOT observe the new content (visibility rules of
{{sec-system-model}} apply: PENDING and FINALIZED chunks are
not globally visible; CHUNK_READ returns only COMMITTED
content).

Concurrent CHUNK_WRITE against a PENDING or FINALIZED chunk is
regulated by chunk_guard4 ({{sec-chunk_guard4}}), not by an
implicit lock.  A racing writer whose guard check fails
receives NFS4ERR_CHUNK_GUARDED; an explicit CHUNK_LOCK
({{sec-CHUNK_LOCK}}) holder is signaled by NFS4ERR_CHUNK_LOCKED.
No implicit chunk-write lock is acquired by CHUNK_WRITE.
A client that requires exclusive access to a chunk MUST
invoke CHUNK_LOCK explicitly ({{sec-CHUNK_LOCK}}).

If the CHUNK_WRITE results in a atomic data block, then the
client will send a CHUNK_FINALIZE in a subsequent compound to inform
the data server that the chunk is finalized and can be overwritten
by another CHUNK_WRITE.

If the CHUNK_WRITE results in an non-atomic data block, or if the
data server returns NFS4ERR_CHUNK_LOCKED, the client reports the
condition to the metadata server via LAYOUTERROR with an error code
of NFS4ERR_PAYLOAD_NOT_ATOMIC.

### Selecting the Repair Actor {#sec-repair-selection}

The repair topology involves three actors communicating along
distinct paths, as shown in {{fig-repair-topology}}.

~~~
     +-------------+      (1)         +-----------------+
     |  Reporting  | ---------------> |                 |
     |  client     |   LAYOUTERROR    | Metadata Server |
     |  (detects   |                  |                 |
     |  error)     |                  |                 |
     +-------------+                  +--------+--------+
                                               |
                                               | (2b)
                                               | CB_CHUNK_REPAIR
                                               | (RACE or SCRUB)
                                               v
     +-------------+      (4)         +-----------------+
     |  Repair     | ---------------> |  Data Servers   |
     |  actor      |   CHUNK ops      |  (mirror set    |
     |  (selected  |                  |  for affected   |
     |  per (2a),  |                  |  ranges)        |
     |  adopts     |                  |                 |
     |  lock (3))  |                  |                 |
     +-------------+                  +-----------------+

     (1)   Reporting client LAYOUTERRORs the metadata server.
     (2a)  Metadata server selects a repair actor (may be a
           client -- possibly the reporting client -- a data
           server under tight coupling, or a proxy server).
     (2b)  Metadata server escrows the chunk lock and issues
           CB_CHUNK_REPAIR to the selected repair actor.
     (3)   Repair actor adopts the lock and drives the repair.
     (4)   Repair actor issues CHUNK_LOCK_ADOPT, CHUNK_WRITE_REPAIR,
           CHUNK_FINALIZE, CHUNK_COMMIT, and CHUNK_REPAIRED against
           the mirror set.
~~~
{: #fig-repair-topology title="Repair topology"}

The metadata server is the authority that selects the repair
actor for a non-atomic payload.  The candidate set is any
client, any data server (in a tightly coupled deployment), or
the proxy server (in a proxy server deployment); the selection
is analogous to the way the metadata server assigns per-mirror
priority via ffv2ds_efficiency (see {{sec-select-mirror}}): the
protocol does not prescribe the selection algorithm, and each
deployment MAY tune its policy.

Implementations MAY consider factors such as:

- Whether a client holds an active write layout on the affected
  payload (the client most likely to hold surviving shards in
  cache).
- Whether a client has previously reported atomic shards to
  the metadata server via LAYOUTSTATS or a prior LAYOUTERROR.
- Whether the layout exposes a data server carrying
  FFV2_DS_FLAGS_REPAIR as a target for reconstructed shards.
- Network proximity, observed latency, or recent client load --
  the same class of information that informs ffv2ds_efficiency.

The selection algorithm is not normative.  What is normative is
that every client MUST be prepared to:

1.  Receive a repair request for a payload that the client does
    not have an outstanding write layout on, and did not write;
    and

2.  Continue its own workload after reporting
    NFS4ERR_PAYLOAD_NOT_ATOMIC without itself being selected
    to repair the payload it reported.

The metadata server signals the selected client via the
CB_CHUNK_REPAIR callback ({{sec-CB_CHUNK_REPAIR}}), which
identifies the file, the affected ranges (each with its own
triggering nfsstat4), and a wall-clock deadline.  A client that
receives CB_CHUNK_REPAIR for a file for which it does not
already hold a layout MUST acquire a layout via LAYOUTGET before
attempting the repair.

Operational expectations for CB_CHUNK_REPAIR:
CB_CHUNK_REPAIR is an exceptional path, triggered only by
concurrent writer races or data-server failures.  It is not a
steady-state operation and its frequency is a function of
racing-writer and data-server-failure rates in the deployment
rather than of normal client workload.  Implementations SHOULD
treat the CB_CHUNK_REPAIR handler as rare-path code and avoid
over-optimising it.  Implementations SHOULD, however, provision
enough client-side compute to handle a repair transaction
without stalling their foreground I/O, because foreground
throughput during repair is the externally observable cost of
this callback.

### Repair Protocol: Normative vs. Informative

The selection algorithm is non-normative and deployment-tunable.
The externally-observable state transitions of the repair flow
are normative.  The line between the two is drawn at what
another party on the wire -- the metadata server, another
client, a reader -- can observe.  What no other party can see
(client-internal ordering, retry policy, whether to CHUNK_READ
first to confirm the failure) is left to implementations.

The following requirements are normative.  An implementation
that violates any of these can leak inconsistency or write-holes
into the cluster:

Final state flat:
:  Every shard in every range identified
   in a CB_CHUNK_REPAIR MUST reach either the COMMITTED state
   (repaired) or the EMPTY state (rolled back).  No shard is
   left in PENDING or FINALIZED indefinitely.

Lock before write:
:  The repair actor MUST adopt the
   lock on every affected range via CHUNK_LOCK with
   CHUNK_LOCK_FLAGS_ADOPT ({{sec-CHUNK_LOCK}}) before issuing
   any CHUNK_WRITE_REPAIR, CHUNK_ROLLBACK, or CHUNK_WRITE on a
   chunk in that range.  The lock on the affected chunks is
   held continuously from the failure that triggered
   CB_CHUNK_REPAIR through the adoption; at no point is the
   range unlocked.

Clear the errored state:
:  On the reconstruction path,
   the repair actor MUST issue CHUNK_REPAIRED
   ({{sec-CHUNK_REPAIRED}}) after CHUNK_COMMIT.  Without it,
   readers continue to see holes regardless of on-disk state.

Release locks explicitly:
:  CHUNK_ROLLBACK does not
   release chunk locks.  On the rollback path the client MUST
   issue CHUNK_UNLOCK ({{sec-CHUNK_UNLOCK}}) on each affected
   chunk.  A client that walks away without either completing
   CHUNK_REPAIRED or issuing CHUNK_UNLOCK holds the locks
   until lease expiry, blocking progress for other writers.

Deadline honored:
:  The client MUST drive every range to
   its final flat state before ccra_deadline, or MUST respond
   to the CB_CHUNK_REPAIR with NFS4ERR_DELAY (requesting an
   extension), NFS4ERR_CODING_NOT_SUPPORTED (declining), or
   NFS4ERR_PAYLOAD_LOST (declaring the data unrecoverable).
   A deadline that elapses without any of these leaves the
   metadata server free to re-select; the client MUST NOT
   continue repair-related CHUNK operations after the
   deadline without first re-verifying its layout and the
   chunk lock state.

Terminal return codes:
:  NFS4ERR_CODING_NOT_SUPPORTED
   MUST mean "decline; select another client."
   NFS4ERR_PAYLOAD_LOST MUST mean "the data is not
   recoverable; do not retry."  The metadata server relies on
   these to decide whether to re-issue.

The following aspects are informative / implementation-defined:

- Choice between the reconstruction path (CHUNK_WRITE_REPAIR)
  and the rollback path (CHUNK_ROLLBACK) on a given range.  The
  protocol MUST support both; the client MAY use either based
  on its local state and whether reconstruction is feasible
  from surviving shards.
- Ordering among multiple affected ranges in a single
  CB_CHUNK_REPAIR (parallel or serial).
- Whether to issue CHUNK_READ to confirm the failure mode
  before reconstructing.
- Retry policy on transient CHUNK_WRITE_REPAIR errors below the
  deadline cutoff.
- How the repair status is surfaced to local filesystem API
  callers.

### Carrying Out the Repair

With the normative framing above, the reconstruction path is:

1.  CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT on each affected
    range ({{sec-CHUNK_LOCK}}).

2.  CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}) with the
    reconstructed data for each non-atomic shard.  The
    client's chunk_owner4 on this and all subsequent operations
    is the one it presented in the CHUNK_LOCK ADOPT above;
    prior owners' generation ids are now historical.

3.  CHUNK_FINALIZE ({{sec-CHUNK_FINALIZE}}) and CHUNK_COMMIT
    ({{sec-CHUNK_COMMIT}}) to persist the repaired shards.

4.  CHUNK_REPAIRED ({{sec-CHUNK_REPAIRED}}) to clear the
    errored state.

The rollback path, when reconstruction is not possible:

1.  CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT on each affected
    range.

2.  CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}}) on each affected
    shard to restore the previously committed content.

3.  CHUNK_UNLOCK ({{sec-CHUNK_UNLOCK}}) on each shard.

In both paths, the repair actor SHOULD target reconstructed
shards according to the following fallback order: first, any
data server in the layout carrying FFV2_DS_FLAGS_REPAIR; then
the data server that reported the failure (the one carrying the
failing shard at the range identified by ccr_offset and ccr_count
in the CB_CHUNK_REPAIR argument).  If neither is available, the
client MUST return NFS4ERR_PAYLOAD_LOST on the CB_CHUNK_REPAIR
response; the metadata server is then responsible for adding a
new REPAIR-flagged data server to the layout (drawn from its
out-of-band pool) and re-driving the repair.

#### Single Writer Mode

In single writer mode, the metadata server sets FFV2_FLAGS_ONLY_ONE_WRITER
in ffv2l_flags, indicating that no other client holds a write layout for
the file.  The client sends CHUNK_WRITE with cwa_guard.cwg_check set to
FALSE, omitting the guard value.  Because only one writer is active,
there is no risk of two clients overwriting the same chunk concurrently.

The single writer write sequence is:

1. The client issues CHUNK_WRITE (cwa_guard.cwg_check = FALSE) for each
   shard.  The data server places the written block in the PENDING state
   and retains a copy of the previous block for rollback.

2. The client issues CHUNK_FINALIZE to advance the blocks from PENDING
   to FINALIZED, validating the per-block checksum.

3. The client issues CHUNK_COMMIT to advance the blocks from FINALIZED
   to COMMITTED, persisting the block metadata to stable storage.

If the client detects an error after CHUNK_WRITE but before CHUNK_FINALIZE
(e.g., a CRC mismatch on a subsequent CHUNK_READ), it issues CHUNK_ROLLBACK
to restore the previous block content.  CHUNK_ROLLBACK does not lock the
chunk; the next CHUNK_WRITE is permitted immediately.

#### Repairing Single Writer Payloads

In single writer mode, non-atomic blocks arise from a client or data
server failure during a CHUNK_WRITE / CHUNK_FINALIZE sequence.  Because
no other writer is active, the original writer is the typical choice
for repair, but the metadata server MAY designate any client according
to the rules in {{sec-repair-selection}}.  A designated client that
did not originate the writes MUST follow the rollback path of that
section if it cannot reconstruct the payload from surviving shards.

The repair sequence when the selected client is the original writer is:

1. The repair actor issues CHUNK_READ to identify which blocks are in a
   failed state (PENDING with a CRC mismatch, or in the errored state
   set by a prior CHUNK_ERROR).

2. For each errored chunk, the repair actor reconstructs the correct
   data using the erasure coding algorithm from the surviving atomic
   chunks (treating each chunk's payload as a shard of the stripe).

3. The repair actor issues CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}})
   to write the reconstructed data.  CHUNK_WRITE_REPAIR bypasses the guard
   check and applies different data server policies (e.g., allowing writes
   to blocks in the errored state).

4. The repair actor issues CHUNK_FINALIZE and CHUNK_COMMIT to persist the
   repaired blocks.

5. The repair actor issues CHUNK_REPAIRED ({{sec-CHUNK_REPAIRED}}) to
   clear the errored state and make the blocks available for normal reads.

#### Transitioning from Single Writer Mode to Multiple Writer Mode {#sec-swm-to-mwm}

When a second writer requests a write layout for a file currently
covered by a single writer layout (FFV2_FLAGS_ONLY_ONE_WRITER set),
the metadata server recalls the existing layout before granting
the new request.  The sequence is:

1. The metadata server issues CB_LAYOUTRECALL to the single writer
   client.

2. The single writer client drains its outstanding I/O issued
   under the single writer assumption (CHUNK_WRITE with
   cwa_guard.cwg_check = FALSE).  Operations already underway
   complete under the layout that authorized them: CHUNK_FINALIZE
   and CHUNK_COMMIT proceed normally for blocks already written.

3. Once drained, the single writer client issues LAYOUTRETURN.

4. The metadata server grants the new writer a layout without
   FFV2_FLAGS_ONLY_ONE_WRITER set.  When the original writer next
   issues LAYOUTGET, it also receives a layout without the flag.
   Both clients then operate in multiple writer mode
   ({{sec-multi-writer}}), supplying cwa_guard.cwg_check = TRUE
   and a chunk_guard4 on every CHUNK_WRITE.

The transition uses standard NFSv4.1 layout recall semantics
(Section 12.5.5 of {{RFC8881}}).  Drained single writer I/O does
not need to be re-issued under multiple writer rules; it
completed under the layout that authorized it.  If the
single writer client fails to return the layout within the
recall window, the metadata server escalates to layout
revocation (Section 12.5.5.2.1 of {{RFC8881}}); any single writer
writes that did not complete before revocation are repaired via
the multiple-writer repair path on subsequent access.

#### Multiple Writer Mode {#sec-multi-writer}

In multiple writer mode, the metadata server does not set
FFV2_FLAGS_ONLY_ONE_WRITER, indicating that concurrent writers may hold
write layouts for the file.  The client sends CHUNK_WRITE with
cwa_guard.cwg_check set to TRUE, supplying the expected prior
chunk_guard4 in cwa_guard.cwg_guard so the data server can perform
per-chunk CAS.  The client obtains the expected prior chunk_guard4
by observing the chunk's current guard first: either cr_guard from
CHUNK_READ ({{sec-CHUNK_READ}}) when the payload is also required,
or the corresponding chrr_guards entry from CHUNK_HEADER_READ
({{sec-CHUNK_HEADER_READ}}) when only the guard is needed.  The
write transaction is separately identified by the cohort pair
`(cwa_cohort_id, cwa_client_id)` supplied on the same CHUNK_WRITE.

The multiple writer write sequence is:

1. The client selects a unique cohort pair `(cwa_cohort_id,
   cwa_client_id)` for this transaction.  cwa_client_id is the client's
   layout-granted ffv2m_client_id (see {{sec-ffv2-mirror4}}); the
   cwa_cohort_id is a per-writer opaque identifier the client picks
   distinct per transaction.

2. The client issues CHUNK_WRITE (cwa_guard.cwg_check = TRUE) for each
   chunk.  The data server checks that no other client's chunk is in the
   PENDING state at this offset.  If another client's chunk is already
   pending, the data server returns NFS4ERR_CHUNK_LOCKED with the
   clr_owner field identifying the lock holder.

3. On NFS4ERR_CHUNK_LOCKED, the client MUST back off.  It issues
   CHUNK_ROLLBACK for any chunks it has already written in this
   transaction, then retries after a delay.

4. If all CHUNK_WRITEs succeed, the client issues CHUNK_FINALIZE and
   CHUNK_COMMIT as in single writer mode.

The cohort pair ensures that the chunks carrying the shards of an
atomic erasure-coded stripe all carry the same
`(co_cohort_id, co_client_id)`.  A reader that encounters chunks with
different cohort pairs knows the stripe is not yet atomic and MUST
either retry or report NFS4ERR_PAYLOAD_NOT_ATOMIC.

#### Repairing Multiple Writer Payloads {#sec-repair-multi-writer}

In multiple writer mode, non-atomic chunks can arise from two sources:
a client failure leaving some chunks in PENDING state, or two clients
writing different data to the same chunk before one has committed.

The metadata server coordinates repair by designating a repair
client according to the rules in {{sec-repair-selection}}.  The
FFV2_DS_FLAGS_REPAIR flag, when present on a data server in the
layout, identifies the target data server into which reconstructed
shards should be written; it does not by itself identify the
repair actor.  The repair sequence is:

1. The repair actor issues CHUNK_LOCK ({{sec-CHUNK_LOCK}}) on the
   affected block range of each data server.  If any lock attempt returns
   NFS4ERR_CHUNK_LOCKED, the repair actor records the existing lock
   holder's chunk_owner4 and proceeds; the lock holder's data is a
   candidate for the winning payload.

2. The repair actor issues CHUNK_READ on all data servers to retrieve
   the current payload.  It examines the chunk_owner4 of each shard to
   identify which transaction (if any) produced a atomic set across
   all k data shards.

3. If a atomic set is found (all k data shards carry the same
   chunk_guard4), that payload is the winner.  The repair actor issues
   CHUNK_WRITE_REPAIR to copy the winner's data to any data servers whose
   shard is non-atomic, followed by CHUNK_FINALIZE and CHUNK_COMMIT.

4. If no atomic set exists (all available payloads are partial), the
   repair actor selects one transaction's payload as authoritative
   (typically the one with the most complete set of shards, or the most
   recent cg_gen_id) and proceeds as above.

5. After all data servers carry atomic, finalized, committed data, the
   repair actor issues CHUNK_REPAIRED to clear the errored state and
   CHUNK_UNLOCK to release the locks acquired in step 1.

6. The repair actor reports success to the metadata server via
   LAYOUTRETURN.

#### Transitioning from Multiple Writer Mode to Single Writer Mode {#sec-mwm-to-swm}

The reverse transition is optional.  When the metadata server
determines that only one writer holds a write layout for a file
(for example, because other writers' layouts have been returned or
their leases have expired), it MAY recall the remaining writer's
layout and grant a fresh layout with FFV2_FLAGS_ONLY_ONE_WRITER
set, restoring the single writer optimization.  The metadata
server MAY also leave the writer in multiple writer mode
indefinitely; single writer mode is an optimization, not a
correctness requirement.

The metadata server's choice of when to grant
FFV2_FLAGS_ONLY_ONE_WRITER is policy and is implementation-defined.
A metadata server that aggressively grants single writer mode and
then must recall it each time a second writer appears can produce
recall churn under workloads with irregular concurrent access:
each single writer to multiple writer transition costs a
CB_LAYOUTRECALL round trip and drain time for in-flight I/O.
Strategies to limit churn include withholding
FFV2_FLAGS_ONLY_ONE_WRITER until sustained single writer behavior
is observed, deferring the single writer grant after a recent
recall, or never granting single writer mode for files with a
history of concurrent access.

### Reading Chunks {#sec-reading-chunks}

The client reads chunks from the data file via CHUNK_READ.  The
number of chunks in the payload that need to be atomic depend
on both the Erasure Encoding Type and the level of protection selected.
If the client has enough atomic chunks in the payload, then it
can proceed to use them to build a data block.  If it does not have
enough atomic chunks in the payload, then it can either decide
to return a LAYOUTERROR of NFS4ERR_PAYLOAD_NOT_ATOMIC to the
metadata server or it can retry the CHUNK_READ until there are
enough atomic chunks in the payload.

As another client might be writing to the chunks as they are being
read, it is entirely possible to read the chunks while they are not
atomic.  As such, it might even be the non-atomic chunks
which contain the new data and a better action than building the
data block is to retry the CHUNK_READ to see if new chunks are
overwritten.

### Whole File Repair

Whole-file repair is the case in which too many data servers have
failed, or too many chunks have been lost, for the per-range repair
flow defined in {{sec-repair-selection}} to reconstruct the file in
place.  In this case the metadata server MUST either:

1.  Construct a new layout backed by replacement data servers and
    drive the reconstruction via the proxy server mechanism (a
    designated data server acts as the source of truth for client
    I/O during the transition, pushing reconstructed content to the
    replacement data servers in the background).  The proxy server mechanism also covers the non-repair cases where a file's layout
    must change while remaining available to clients -- policy-driven layout transitions, data server maintenance evacuation,
    administrative ingest, TLS coverage transition, and
    filehandle-backend migration.

2.  If the metadata server has no proxy server capable data server
    available, or the surviving shards are insufficient to
    reconstruct any portion of the file, terminate the affected
    byte ranges with NFS4ERR_PAYLOAD_LOST (see
    {{sec-NFS4ERR_PAYLOAD_LOST}}).

Implementations that do not support the proxy server mechanism can
still perform recovery for cases where per-range repair suffices,
using CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}) and the repair
client selection rules in {{sec-repair-selection}}.  Such
implementations will surface NFS4ERR_PAYLOAD_LOST on any failure
that exceeds per-range repair's reach, including the multi-data-server failure scenarios the proxy server mechanism is intended to
handle.

## Mixing of Encoding Types

Multiple encoding types can be present in a Flexible File Version 2
Layout Type layout.  The ffv2_layout4 has an array of ffv2_mirror4,
each of which has a ffv2_encoding_type4.  Mixing encoding types in a single file's mirror set addresses
several use cases:

Assimilation and export:

: assimilation of a non-erasure-coded file into an
  erasure-coded representation, or export of an erasure-coded
  file to a non-erasure-coded representation.

Online migration between encodings:

: for example, from a Reed-Solomon Vandermonde encoding to a
  Mojette systematic encoding when a read-access-pattern change
  makes the new encoding a better fit.  Both representations
  remain addressable through the layout throughout the
  transition.

Cross-encoding recovery:

: when one encoding loses data to a correlated failure mode
  (an encoding implementation bug, a memory-corruption pattern
  that affects parity shards identically), a second mirror in
  a different encoding provides an independent recovery
  path.

Client-capability routing:

: a proxy server sees the full mirror set and chooses between
  encodings on behalf of clients that do not implement every
  encoding the file is represented in.

Consider a layout that exposes a file in two encodings
simultaneously: a PASSTHROUGH mirror over the original byte
stream and a Reed-Solomon Vandermonde
(FFV2_ENCODING_RS_VANDERMONDE) mirror with 4 active data shards
plus 2 parity data servers.  A layout for such a
file might appear as in {{fig-example_mixing}}.  Both
representations are active and addressable through the layout
simultaneously.  This is the transition-window pattern: a file
may transiently span encodings while it is being assimilated
from a non-flexible-file-v2 source or migrated between
encodings.  Steady
state is homogeneous; the multi-encoding window is what the
protocol must accommodate.

The active mirrors serve different access patterns concurrently:

- A client that speaks only the file-layout READ path issues
  READ (Section 18.22 of {{RFC8881}}) calls to index 0 (the
  PASSTHROUGH mirror).

- A client that speaks the chunked path issues CHUNK_READ
  ({{sec-CHUNK_READ}}) calls to index 1 (the RS_VANDERMONDE
  mirror).

- A proxy server fronting legacy clients chooses between the two
  encodings on the client's behalf.

All three patterns coexist during the transition.

~~~ art
 +-----------------------------------------------------+
 | ffv2_layout4:                                       |
 +-----------------------------------------------------+
 |     ffv2l_mirrors[0]:                               |
 |         ffv2s_data_servers:                         |
 |             ffv2_data_server4[0]                    |
 |                 ffv2ds_flags: 0                     |
 |         ffv2m_coding: FFV2_ENCODING_PASSTHROUGH     |
 +-----------------------------------------------------+
 |     ffv2l_mirrors[1]:                               |
 |         ffv2s_data_servers:                         |
 |             ffv2_data_server4[0]                    |
 |                 ffv2ds_flags: FFV2_DS_FLAGS_ACTIVE  |
 |             ffv2_data_server4[1]                    |
 |                 ffv2ds_flags: FFV2_DS_FLAGS_ACTIVE  |
 |             ffv2_data_server4[2]                    |
 |                 ffv2ds_flags: FFV2_DS_FLAGS_ACTIVE  |
 |             ffv2_data_server4[3]                    |
 |                 ffv2ds_flags: FFV2_DS_FLAGS_ACTIVE  |
 |             ffv2_data_server4[4]                    |
 |                 ffv2ds_flags: FFV2_DS_FLAGS_PARITY  |
 |             ffv2_data_server4[5]                    |
 |                 ffv2ds_flags: FFV2_DS_FLAGS_PARITY  |
 |     ffv2m_coding: FFV2_ENCODING_RS_VANDERMONDE      |
 +-----------------------------------------------------+
~~~
{: #fig-example_mixing title="Example of Mixed Encoding Types in a Layout" }

When performing I/O via a FFV2_ENCODING_PASSTHROUGH encoding type,
the non-transformed data will be used; whereas with any of the
chunked encoding types (any FFV2_ENCODING_* value other than
FFV2_ENCODING_PASSTHROUGH; see {{tbl-coding-types}}), a metadata
header and transformed block will be sent.  Further, when reading data from the
instance files, the client MUST be prepared to have one of the
encoding types supply data and the other type not to supply data.
I.e., the CHUNK_READ call to the data servers in mirror 1 might
return rlr_eof set to true (see {{fig-read_chunk4}}), which
indicates that there is no data, where the READ call to the
data server in mirror 0 might return eof to be false, which
indicates that there is data.  The client MUST determine that
there is in fact data.  An example use case is the active
assimilation of a file to ensure integrity.  As the client is
helping to translate the file to the new coding scheme, it is
actively modifying the file.  As such, it might be sequentially
reading the file in order to translate.  The READ calls to
mirror 0 would be returning data and the CHUNK_READ calls to
mirror 1 would not be returning data.  As the client overwrites
the file, the WRITE call and CHUNK_WRITE call would have data
sent to all of the data servers.  Finally, if the client reads
back a section which had been modified earlier, both the READ
and CHUNK_READ calls would return data.

The two-mirror layout shown in {{fig-example_mixing}} is the
file's full mirror set as known to the metadata server.  A
client that arrives during the assimilation or migration window
above does not necessarily receive that layout; per the
proxy server draft, the client gets a single layout naming the
proxy server as a single endpoint, and the proxy server selects
which of the file's
mirrors to read from or write to on the client's behalf.  The
two-mirror view in this section describes the metadata server's
bookkeeping during the transition; the client directs its I/O
to a single endpoint.

### Steady-state heterogeneous mirrors {#sec-steady-state-heterogeneous}

The transition-window patterns above (assimilation, migration,
repair) are the most visible motivations for heterogeneous
mirror sets, but they are not the only ones.  A file's mirror
set MAY be heterogeneous in steady state -- where no transition
is in progress and no transition is planned -- when the
deployment's storage pools have different encoding capabilities
and the file is too large to fit in any single pool.

Consider an operator with three 100-TB storage pools.  Pool A
is a set of NFSv3-only data servers, which is a hard capability
constraint: the chunked encodings require NFSv4.2's CHUNK
operations, so an NFSv3-only pool can hold data only under an
FFV2_ENCODING_PASSTHROUGH mirror.  Pools B and C are NFSv4.2
data servers, which are encoding-agnostic at the wire level
(CHUNK_READ and CHUNK_WRITE just move opaque chunk payloads;
the encoding transform is client-side).  The operator, however,
has chosen to write Pool B under FFV2_ENCODING_RS_VANDERMONDE
and Pool C under FFV2_ENCODING_MOJETTE_SYSTEMATIC -- a policy
decision motivated by durability diversity (hedging against a
correlated failure in any single encoder implementation) and by
per-workload fit (each encoding's reconstruction cost and
failure-tolerance profile suits a different tenant on that pool).

A 250-TB file cannot fit in any single pool.  Striping the file
across all three pools is forced by capacity arithmetic: 250 >
100.  Because bytes in each pool were written under the pool's
chosen encoding, the layout for this file MUST name the actual
per-mirror `ffv2_encoding_type4` so that clients decode each
segment correctly: PASSTHROUGH for the Pool A segment,
RS_VANDERMONDE for the Pool B segment, MOJETTE_SYSTEMATIC for
the Pool C segment.  The heterogeneity is not a transition
window; it is the permanent consequence of striping across
pools whose bytes were written under different operator-chosen
encodings.

In this steady-state case, no proxy server mediated transition
machinery is involved.  The client receives a layout
enumerating the mirrors at different `ffv2m_coding` values and
routes chunk operations to the appropriate data server per
segment (or, if the client cannot speak one of the encodings,
requests proxy mediation per the proxy server draft's section
"Encoding Translation for Encoding-Ignorant Clients"
({{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}})).  The layout
machinery that supports this case is exactly the per-mirror
encoding naming primitive described above; no additional protocol
elements are required to express it.

The transient case (one file moving between encodings) and the
steady-state case (one file permanently striped across
heterogeneous pools) share a single wire primitive: an
`ffv2l_mirrors` array that admits mixed `ffv2_encoding_type4`
values.  Removing that primitive would foreclose both cases
and would force one of three workarounds: (a) split the
250-TB file into three independently-named files (loses
single-namespace semantics), (b) require every pool to
implement every encoding (forces a single-vendor or
single-implementation procurement story), or (c) require an
always-on transcoding proxy in front of every read and write
(re-introduces the centralized data-plane that the
proxy server role is scoped to avoid in steady state).  None
of these alternatives address the steady-state case while
preserving the transition-window flexibility this document
specifies.

## FFV2_ENCODING_PASSTHROUGH {#sec-encoding-passthrough}

FFV2_ENCODING_PASSTHROUGH is the on-ramp from the flexible file v1 layout ({{RFC8435}})
into the flexible file v2 layout.  A PASSTHROUGH mirror points at the
file's bytes as they exist on the data server, without the
chunk envelope, checksum header, or chunk_guard4 fields that the
encoded types use.  Client I/O against a PASSTHROUGH mirror
uses NFSv3 WRITE / READ ({{RFC1813}}) or NFSv4 READ / WRITE
({{RFC8881}}) directly -- not CHUNK_WRITE / CHUNK_READ.

PASSTHROUGH provides:

-  Replication of data across N data servers, exactly as flexible file v1 layout
   does.  Clients write to every replica; clients read from any
   one.  N-way redundancy tolerates up to N-1 replica losses.
-  Zero encoding compute at the client and zero chunk-metadata
   overhead at the server.  The on-disk format is the file
   itself.
-  Compatibility with files that already exist outside flexible file v2 layout.
   A PASSTHROUGH mirror can be created over an existing
   file without rewriting it.

PASSTHROUGH does NOT provide:

-  Per-chunk integrity.  There is no checksum on the data path.
   Silent corruption is undetectable without out-of-band
   tooling (e.g., comparing checksums across replicas).
-  Chunk-grained repair.  The repair unit is the whole file:
   resilvering picks a trusted replica and replicates it end
   to end to the affected replica(s).
-  The concurrent writer disambiguation that chunk_guard4
   provides for encoded types.

PASSTHROUGH is RECOMMENDED for the assimilation, migration, and
heterogeneous-mirror use cases described in
{{sec-heterogeneous-mirrors}}.  New deployments that do not
need a flexible file v1 layout on-ramp SHOULD use FFV2_ENCODING_MIRRORED for
the integrity guarantees described in
{{sec-encoding-mirrored}}.

## FFV2_ENCODING_MIRRORED {#sec-encoding-mirrored}

FFV2_ENCODING_MIRRORED is the chunked-with-integrity peer of
PASSTHROUGH.  The chunk produced for each replica is the
application data verbatim -- no transform, no parity shards --
but it travels on the wire and is stored on the data server
through CHUNK_WRITE / CHUNK_READ and so carries every integrity
property the encoded encoding types carry.

What FFV2_ENCODING_MIRRORED keeps from the mirror model:

-  Zero encoding compute at the client.  Each replica's chunk is
   the input bytes; there is no transform to apply on write and
   nothing to decode on read.
-  Storage cost of N x payload, where N is the replica count.
   Mirroring trades storage for redundancy without the
   reconstruction machinery that erasure coding requires.
-  Reading any one intact replica is sufficient.  If a replica
   fails to verify (see below), the client tries another.

What FFV2_ENCODING_MIRRORED adds beyond PASSTHROUGH, by virtue
of using CHUNK_WRITE and CHUNK_READ:

-  Per-chunk checksum on write and on read.  The CRC is computed
   by the client over the chunk header and chunk payload with
   the checksum field itself treated as zero
   ({{sec-checksum4}}), sent on the wire with the chunk,
   recomputed by the data server before storing, and
   recomputed again from disk by the data server on every
   CHUNK_READ.  Wire-level bit flips are caught before the
   chunk is stored; on-disk bit rot is caught the next time
   the chunk is read.
-  Per-chunk repair granularity.  When one replica's CRC fails
   to verify and another replica's verifies, the repair unit
   is the chunk, not the file: CHUNK_READ the good replica,
   CHUNK_WRITE to the bad replica, done.  No whole-file
   resilvering is required.
-  Per-chunk concurrent writer disambiguation.  Mirrored
   writes carry the same chunk_guard4 ({{sec-chunk_guard4}})
   the erasure encoding types do.  Two clients racing to write
   the same offset of the same file fan out to every replica
   with a guard pair (generation, owning-client short-id) per
   chunk; the CHUNK_FINALIZE step resolves which writer's
   chunk wins and the other writer observes a deterministic
   loss instead of an unresolved split-mirror.

What FFV2_ENCODING_MIRRORED is for: files where the deployment
wants integrity and replication without the storage savings or
the reconstruction story of erasure coding.  Small files that
do not exceed a single stripe, files whose access pattern is
read-mostly and where the N x storage cost is acceptable, and
files where the operator prefers the simplicity of "any one
replica is the file" over "k of (k+m) shards reconstruct the
file."  The coding choice is per-file; a deployment can mix
mirrored and erasure-coded files in the same namespace and
pick whichever fits each file's profile.

What FFV2_ENCODING_MIRRORED is not: a substitute for erasure
coding when storage efficiency or multi-replica fault tolerance
matters.  An N-way mirror tolerates up to N-1 replica losses
but costs N x the payload; a (k, m) erasure coding tolerates m
losses at (k+m)/k x the payload.  Both have per-chunk
integrity under this document; the choice is the
cost-vs-tolerance one.

## FFV2_ENCODING_XOR_PARITY {#sec-encoding-xor-parity}

### Overview

FFV2_ENCODING_XOR_PARITY is a single-parity, systematic,
RAID-5-shape encoding: k data shards accompanied by one parity
shard computed as the bytewise XOR of every data shard.
Parameters: k in the range 1 to 254, m fixed at 1.

Unlike Reed-Solomon and Linux md/raid6, XOR_PARITY requires no
finite-field arithmetic.  The "encoding" is a plain XOR
reduction across k shards, so the implementation footprint is
trivial and the compute cost scales at memory bandwidth.  This
makes XOR_PARITY the simplest candidate encoding: any
conformant implementation can support it without a GF(2^8)
library.

### Encoding

Given k data shards, each of shard_len bytes, encoding produces
a single parity shard of shard_len bytes:

~~~
For each byte position j in [0, shard_len):
  parity[j] = data[0][j] XOR data[1][j] XOR ... XOR data[k-1][j]
~~~

All shards (data and parity) are the same size.  No table
lookups, no multiplications; a straight bitwise XOR reduction.

### Recovery

XOR_PARITY tolerates the loss of exactly one shard (any one
data shard or the parity shard).

- Missing data shard `data[i]`: reconstruct by XOR-ing all
  surviving shards (k-1 data shards plus the parity shard):
  `data[i][j] = parity[j] XOR data[0][j] XOR ... (skip i) ... XOR data[k-1][j]`.
- Missing parity shard: recompute from the k intact data
  shards using the encoding step above.

Reconstruction cost is a single XOR reduction over shard_len
bytes; memory bandwidth dominates.  No matrix inversion is
required.

Loss of two or more shards is unrecoverable under XOR_PARITY.
Deployments requiring tolerance of two or more concurrent
losses SHOULD use FFV2_ENCODING_LINUX_MD_RAID (m=2) or
FFV2_ENCODING_RS_VANDERMONDE (configurable m).

### Interoperability

XOR_PARITY produces a parity shard byte-identical to the P
(first) parity row of Reed-Solomon Vandermonde encoding at m=1
and to the P row of Linux md/raid6 at any m >= 1.  This
follows from using the same primitive coefficients:

- RS Vandermonde at m=1 uses parity row `[1, 1, ..., 1]` in
  GF(2^8), which reduces to bitwise XOR (see
  {{sec-rs-encoding}}).
- LINUX_MD_RAID's P row is defined as the bitwise XOR of every
  data shard, identical to XOR_PARITY's parity by
  construction.

A receiver capable of FFV2_ENCODING_RS_VANDERMONDE at m=1 or
FFV2_ENCODING_LINUX_MD_RAID at m >= 1 therefore consumes an
XOR_PARITY-encoded chunk without re-encoding, provided the k
matches.  Conversely, an XOR_PARITY receiver consumes the P
row of any GF(2^8) family encoding at m >= 1 unchanged.

### XOR_PARITY Interoperability Test Vectors

Concrete byte-level test vector with `k = 3`, `m = 1`,
`shard_len = 1`:

| `data[0]` | `data[1]` | `data[2]` | parity | Notes |
|---|---|---|---|---|
| `0x00`  | `0x00`  | `0x00`  | `0x00` | zero input                    |
| `0x01`  | `0x00`  | `0x00`  | `0x01` | single non-zero data shard    |
| `0x01`  | `0x02`  | `0x04`  | `0x07` | 0x01 XOR 0x02 XOR 0x04 = 0x07 |
| `0x37`  | `0x91`  | `0xac`  | `0x0a` | matches P from {{tbl-rs-test-vector-k3m2}} |
| `0xff`  | `0xff`  | `0x00`  | `0x00` | 0xff XOR 0xff XOR 0x00 = 0x00 |
{: #tbl-xor-parity-test-vector title="XOR_PARITY test vector: k=3, m=1"}

The fourth row is byte-identical to the P entry of the same
input in {{tbl-rs-test-vector-k3m2}} -- the wire-compat
property in action.

### XOR_PARITY Shard Sizes

All XOR_PARITY shards (data and parity) are exactly shard_len
bytes.  chunk_size equals shard_len for every mirror in the
layout.  Total storage overhead is `1/k` of payload.

| Configuration | File Size | Shard Size | Total Storage | Overhead |
|---|---|---|---|---|
| 3+1 | 3 KB | 1 KB   | 4 KB    | 33% |
| 3+1 | 1 MB | ~342 KB | ~1.33 MB | 33% |
| 7+1 | 7 KB | 1 KB   | 8 KB    | 14% |
| 7+1 | 1 MB | ~147 KB | ~1.14 MB | 14% |
{: #tbl-xor-parity-shards title="XOR_PARITY shard sizes for common configurations"}

## FFV2_ENCODING_LINUX_MD_RAID {#sec-encoding-linux-md-raid}

### Overview

FFV2_ENCODING_LINUX_MD_RAID is the Linux kernel md/raid6 P+Q
double-parity encoding, evaluated in GF(2^8) with primitive
polynomial `x^8 + x^4 + x^3 + x^2 + 1` (encoded as `0x1d` when
the implicit degree-8 term is dropped, `0x11d` when it is
kept).  Parameters: k in the range 2 to 253, m fixed at 2.

The encoding produces two parity shards.  P is the bitwise XOR
of every data shard (identical to FFV2_ENCODING_XOR_PARITY's
parity, see {{sec-encoding-xor-parity}}).  Q is a weighted sum
`sum(g^i * data_i)` in GF(2^8) with `g = 2`.  The construction
is bit-for-bit compatible with Linux kernel `lib/raid6`
{{LINUX-RAID6}} and with FFV2_ENCODING_RS_VANDERMONDE at m<=2
(see {{sec-rs-encoding}}).

The k=1 case (a single data shard with P and Q) is degenerate
and MUST NOT be used with FFV2_ENCODING_LINUX_MD_RAID.  Callers
who need triple-mirror semantics MUST use
FFV2_ENCODING_MIRRORED with N=3 instead.

### LINUX_MD_RAID Galois Field Arithmetic

All LINUX_MD_RAID operations are performed over GF(2^8), the
Galois field with 256 elements.  Each element is represented
as a byte.

Irreducible Polynomial:
:  The field is constructed using `x^8 + x^4 + x^3 + x^2 + 1`,
encoded as `0x1d` when the implicit x^8 term is dropped (Linux
md convention), or `0x11d` when it is kept (RS Vandermonde
convention in {{sec-rs-encoding}}).  Both encodings refer to
the same field; only the notation differs.

Primitive Element:
:  `g = 2`.  Powers of `g` cycle through GF(2^8) \ {0} with
period 255.

Addition:
:  Bitwise XOR.

Multiplication:
:  Via log/antilog tables in the reference implementation, or
SIMD vector multiply in modern kernels.  See the Linux kernel
`lib/raid6/{int.uc, sse2.c, altivec.uc, ...}` sources
{{LINUX-RAID6}} for the canonical implementation.

### LINUX_MD_RAID Encoding

Given k data shards, each of shard_len bytes, encoding
produces two parity shards P and Q, each shard_len bytes:

~~~
For each byte position j in [0, shard_len):
  P[j] = data[0][j] XOR data[1][j] XOR ... XOR data[k-1][j]
  Q[j] =         1 * data[0][j]
           XOR   g * data[1][j]
           XOR g^2 * data[2][j]
           XOR ...
           XOR g^(k-1) * data[k-1][j]
~~~

where multiplication is in GF(2^8) and `g = 2`.  All shards
(data, P, and Q) are the same size.

The P row is identical to FFV2_ENCODING_XOR_PARITY's parity by
construction; the two encodings share the P computation.  The
Q row is the m=2 P+Q construction from {{sec-rs-encoding}},
and produces byte-identical output to
FFV2_ENCODING_RS_VANDERMONDE at m=2.

### LINUX_MD_RAID Recovery

LINUX_MD_RAID tolerates up to two concurrent shard losses (any
two of the k+2 shards).

Single-shard failure:
:  If only P or only Q is missing, recompute from the k intact
data shards using the encoding step above.
:  If exactly one data shard `data[i]` is missing but both P
and Q are intact, prefer the P-only recovery (cheaper): XOR
all surviving shards (k-1 data plus P) to recover `data[i]`.

Dual-shard failure:
:  If two data shards are missing, use both P and Q to solve a
2x2 linear system in GF(2^8) per byte position.  See the Linux
kernel `lib/raid6/recov.c` for the canonical solver.
:  If one data shard and one parity shard are missing, first
recover the data shard using the intact parity row (as in the
single-shard case), then recompute the missing parity from the
reconstructed data.

Loss of three or more shards is unrecoverable under
LINUX_MD_RAID.  Deployments requiring m >= 3 fault tolerance
MUST use FFV2_ENCODING_RS_VANDERMONDE.

### LINUX_MD_RAID Interoperability

FFV2_ENCODING_LINUX_MD_RAID is wire-compatible with
FFV2_ENCODING_RS_VANDERMONDE at m <= 2 by construction: both
encoders emit byte-identical P and Q for the same (k, data)
input at m <= 2.

- At m = 1, LINUX_MD_RAID's P row equals RS_VANDERMONDE's m=1
  parity and equals XOR_PARITY's parity (see
  {{sec-encoding-xor-parity}}).
- At m = 2, LINUX_MD_RAID's P+Q equals RS_VANDERMONDE's m=2
  P+Q rows byte-for-byte.

RS_VANDERMONDE joined the m <= 2 wire-compat set as a
wire format revision in this document: its m <= 2 parity rows
are the hand-crafted P/Q construction rather than the
normalized-Vandermonde bottom rows RS uses at m >= 3.  See
{{sec-rs-encoding}} for the RS construction and its
interoperability parameters.

A client implementing either LINUX_MD_RAID or RS_VANDERMONDE
at m <= 2 can consume the other without re-encoding, provided
the (k, m) geometry matches.

### LINUX_MD_RAID Interoperability Test Vectors

Concrete byte-level test vector with `k = 3`, `m = 2`,
`shard_len = 1`:

| `data[0]` | `data[1]` | `data[2]` | P     | Q     | Notes |
|---|---|---|---|---|---|
| `0x00`  | `0x00`  | `0x00`  | `0x00` | `0x00` | zero input                     |
| `0x01`  | `0x02`  | `0x03`  | `0x00` | `0x09` | 1 XOR (2*2) XOR (4*3) = 1 XOR 4 XOR 12 = 9 |
| `0x80`  | `0x00`  | `0x00`  | `0x80` | `0x80` | Q = 1 * 0x80 = 0x80            |
| `0x00`  | `0x80`  | `0x00`  | `0x80` | `0x1d` | Q = 2 * 0x80 = 0x100 -> reduce by 0x11d -> 0x1d |
| `0x00`  | `0x00`  | `0x80`  | `0x80` | `0x3a` | Q = 4 * 0x80 = 2 * 0x1d = 0x3a |
| `0x37`  | `0x91`  | `0xac`  | `0x0a` | `0x82` | general non-degenerate case    |
{: #tbl-linux-md-test-vector title="LINUX_MD_RAID test vector: k=3, m=2"}

Every row above is byte-identical to the k=3, m=2 test vector
for FFV2_ENCODING_RS_VANDERMONDE ({{tbl-rs-test-vector-k3m2}})
at the same input.  This is the wire-compat property in
action: an implementation whose LINUX_MD_RAID output matches
these bytes is producing the same wire encoding as
RS_VANDERMONDE at m=2.

### LINUX_MD_RAID Shard Sizes

All LINUX_MD_RAID shards (data, P, Q) are exactly shard_len
bytes.  chunk_size equals shard_len for every mirror in the
layout.  Total storage overhead is `2/k` of payload.

| Configuration | File Size | Shard Size | Total Storage | Overhead |
|---|---|---|---|---|
| 4+2 | 4 KB | 1 KB   | 6 KB    | 50% |
| 4+2 | 1 MB | 256 KB | 1.5 MB  | 50% |
| 8+2 | 4 KB | 512 B  | 5 KB    | 25% |
| 8+2 | 1 MB | 128 KB | 1.25 MB | 25% |
{: #tbl-linux-md-shards title="LINUX_MD_RAID shard sizes for common configurations"}

## Reed-Solomon Vandermonde Encoding (FFV2_ENCODING_RS_VANDERMONDE) {#sec-rs-encoding}

### Overview

Reed-Solomon (RS) codes are Maximum Distance Separable codes:
for a (k+m, k) code, any k of the k+m encoded shards suffice to
recover the original data.  The code tolerates the simultaneous loss
of up to m shards.  {{Plank97}} is a tutorial treatment of RS
coding in RAID-like systems and is the recommended background
reading for implementers unfamiliar with the construction used
here.

### Galois Field Arithmetic

All RS operations are performed over GF(2^8), the Galois field with
256 elements.  Each element is represented as a byte.

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

### Encoding Matrix

The systematic encoding matrix E has (k + m) rows and k columns.
The top k rows are always the k x k identity, so data shards pass
through unchanged.  The bottom m parity rows are chosen as
follows.

#### At m = 1: single parity row

The single parity row is `[1, 1, ..., 1]`:

~~~
E[k][j] = 1    for j = 0, 1, ..., k-1
~~~

Encoded parity is the bitwise XOR of every data shard.  This
matches the P row of Linux md's RAID6 construction and the sole
parity row of FFV2_ENCODING_XOR_PARITY byte-for-byte; a receiver
that speaks either of those consumes RS_VANDERMONDE at m=1
without re-encoding.

#### At m = 2: P + Q parity rows

The two parity rows are:

~~~
E[k][j]     = 1              for j = 0, 1, ..., k-1   (P row)
E[k+1][j]   = g^j            for j = 0, 1, ..., k-1   (Q row)
~~~

where g = 2 is the primitive element of GF(2^8) with polynomial
0x11d.  These are exactly the coefficients Linux md RAID6 uses
for its P and Q shards.  A receiver that speaks
FFV2_ENCODING_LINUX_MD_RAID at m <= 2 also consumes
RS_VANDERMONDE at m <= 2 byte-for-byte (and vice versa).

#### At m >= 3: normalized Vandermonde bottom rows

The parity rows are the bottom m rows of a normalized
Vandermonde encoding matrix, constructed as follows.

1. Assign each of the k+m shards a distinct non-zero evaluation
   point in GF(2^8): shard i (for i = 0, 1, ..., k+m-1) is assigned
   the point alpha_i = i + 1.  This gives evaluation points
   1, 2, ..., k+m, all non-zero and distinct.  The value k+m MUST
   NOT exceed 255 so that all points fit in GF(2^8) \ {0}.

2. Construct a (k+m) x k Vandermonde matrix V where the row for
   shard i is the geometric progression of alpha_i:

   ~~~
   V[i][j] = alpha_i^j = (i+1)^j    for j = 0, 1, ..., k-1
   ~~~

   Row i is (1, alpha_i, alpha_i^2, ..., alpha_i^(k-1)).  The
   exponent zero is defined as `x^0 = 1` for all `x` in GF(2^8),
   including x = 0 (this is the standard combinatorial
   convention; here `alpha_i` is never zero by step 1's
   construction, but the convention makes the `V[0][0]` cell
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

### Encoding

Given k data shards, each of shard_len bytes, encoding produces m
parity shards, each also shard_len bytes:

~~~
For each byte position j in [0, shard_len):
  For each parity shard i in [0, m):
    parity[i][j] = sum over s in [0, k) of P[i][s] * data[s][j]
~~~

where the sum and product are in GF(2^8).  All shards (data and
parity) are the same size.

### Decoding

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

### RS Interoperability Requirements

For two implementations of FFV2_ENCODING_RS_VANDERMONDE to
interoperate, they MUST agree on all of the following parameters.
Any deviation produces a different encoding matrix and renders
data unrecoverable by a different implementation.

Irreducible polynomial:

: `x^8 + x^4 + x^3 + x^2 + 1` (`0x11d`).

Primitive element:

: `g = 2`.

Evaluation points:

: shard `i` (`i = 0, 1, ..., k+m-1`) uses
  `alpha_i = i + 1` in GF(2^8) (values 1 through `k+m`, all
  non-zero and distinct).

Vandermonde entries:

: `V[i][j] = alpha_i^j = (i+1)^j` in GF(2^8) for
  `i = 0..k+m-1`, `j = 0..k-1`.

Matrix normalization:

: `E = V * T^(-1)` where `T` is the top `k x k` sub-matrix
  (rows for shards `0..k-1`).

Parameter bound:

: `k + m` MUST NOT exceed 255.

These parameters fully determine the encoding matrix for any
(k, m) configuration in the permitted range.

### RS Interoperability Test Vectors

The following worked examples pin the encoding matrix and
end-to-end encodings for two representative geometries: k=2 m=1
(exercises the m=1 all-ones parity row) and k=3 m=2 (exercises
the m=2 P + Q parity rows).  An implementation whose encoded
output matches these tables is using the same GF(2^8)
representation and the same parity-row construction as required
by the interoperability parameters above.

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

| `data[0]` | `data[1]` | parity  | Notes |
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

~~~
P[j] = data[0][j] XOR data[1][j] XOR data[2][j]
Q[j] = 1 * data[0][j] XOR 2 * data[1][j] XOR 4 * data[2][j]
~~~

where the multiplication is in GF(2^8) with polynomial `0x11d`.

Concrete byte-level test vector with `shard_len = 1`:

| `data[0]` | `data[1]` | `data[2]` | P     | Q     | Notes                          |
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
interoperate.  m >= 3 test vectors are not included here because
the normalized-Vandermonde parity rows are not easily
hand-computed; implementations that need m >= 3 verification
SHOULD cross-check against a reference implementation.

### RS Shard Sizes

All RS shards (data and parity) are exactly shard_len bytes.  This
simplifies the CHUNK operation protocol: chunk_size is exactly the
shard size for all mirrors.

| Configuration | File Size | Shard Size | Total Storage | Overhead |
|---
| 4+2 | 4 KB | 1 KB | 6 KB | 50% |
| 4+2 | 1 MB | 256 KB | 1.5 MB | 50% |
| 8+2 | 4 KB | 512 B | 5 KB | 25% |
| 8+2 | 1 MB | 128 KB | 1.25 MB | 25% |
{: #tbl-rs-shards title="RS shard sizes for common configurations"}

## Mojette Transform Encoding (FFV2_ENCODING_MOJETTE_SYSTEMATIC, FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC) {#sec-mojette-encoding}

### Overview

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
point it becomes a wire-visible parameter.  Fixing W in this
revision prevents an interoperability hazard: the same shard
input XOR'd at W = 4 versus W = 8 produces different bin values
that appear "close but wrong" to a mismatched decoder.

### Grid Structure

Data is arranged as a P x Q grid of unsigned integer elements,
where P is the number of columns and Q is the number of rows.
For k data shards of S bytes each with W-byte elements:

~~~
P = S / W       (columns per row)
Q = k           (rows = data shards)
~~~

### Directions

A direction is a pair of coprime integers (p_i, q_i).  This
specification pins all directions to q_i = 1 for both Mojette
encoding types (systematic and non-systematic) in this
revision.  Non-unity q_i values may be introduced by a future
distinct registered encoding type.

For n = k + m total shards (Mojette non-systematic) or m parity
shards (Mojette systematic), the direction set is determined by
the following mandatory rule on the shard count N (N = n for
non-systematic, N = m for systematic).

For N even (N = 2t):
:  `directions = { (p, 1) : p in {-t, -t+1, ..., -1, 1, 2, ..., t} }`
   -- symmetric around zero, giving `|directions| = 2t = N`.

For N odd (N = 2t + 1):
:  `directions = { (p, 1) : p in {-t, -t+1, ..., -1, 1, 2, ..., t, t+1} }`
   -- asymmetric by including one additional positive magnitude
   so that `|directions| = 2t + 1 = N`.

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

### Forward Transform (Encoding)

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

### Katz Reconstruction Criterion

Reconstruction from a set of `n` projections is possible if and
only if the Katz criterion {{KATZ}} holds over those `n`
projections:

~~~
SUM(i=1..n) |q_i| >= Q    OR    SUM(i=1..n) |p_i| >= P
~~~

With q_i = 1 pinned for every direction (see the Directions
subsection above), the q-sum simplifies to n >= Q.

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
`r + s <= m`; the systematic form therefore achieves
Maximum-Distance-Separable-like recovery up to `m` combined
data-row and parity-projection losses.

### Inverse Transform (Decoding)

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

### Systematic Mojette

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

### Non-Systematic Mojette

In the non-systematic form (FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC),
all k + m shards are projections.  Every read requires the full
inverse transform.  This provides constant performance regardless of
failure count, but at higher baseline read cost than systematic.

### Mojette Shard Sizes and Layout

Slot-to-direction mapping:

: The canonical shard layout for Mojette is:

  Systematic (FFV2_ENCODING_MOJETTE_SYSTEMATIC):

  : shard slots `0..k-1` carry the k data rows (row r in slot
    r); shard slots `k..k+m-1` carry the m parity projections
    in the canonical direction order defined in the Directions
    subsection above (direction slot i occupies shard slot
    `k + i`).

  Non-systematic (FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC):

  : shard slots `0..k+m-1` carry the n = k + m parity
    projections in the canonical direction order (direction
    slot i occupies shard slot i).

Bin ordering within a projection:

: Within a projection shard the bins are serialized in
  ascending bin-index order (bin 0 first, bin B-1 last), with
  no gap or header.  Each bin value is `W = 8` bytes wide; the
  W-byte element is serialized in big-endian byte order (the
  same order the data-row shards present their W-byte grid
  elements in).

Projection sizes:

: Unlike Reed-Solomon, Mojette parity shard sizes vary by
  direction:

| Direction (p, q) | Bins (B) for P=512, Q=4 | Size (bytes, W=8) |
|---
| (-3, 1) | 521 | 4168 |
| (-2, 1) | 518 | 4144 |
| (-1, 1) | 515 | 4120 |
| (1, 1) | 515 | 4120 |
| (2, 1) | 518 | 4144 |
| (3, 1) | 521 | 4168 |
{: #tbl-mojette-proj-sizes title="Mojette projection sizes for 4+2, 4KB shards, W=8"}

Chunk sizing for variable-length projections:

: When a projection shard is written via `CHUNK_WRITE` /
  `CHUNK_FINALIZE` / `CHUNK_COMMIT`, the shard is divided into
  chunks by the following mapping.  Let `shard_bytes = B * W`
  be the projection shard's total byte size (where B is the
  number of bins per the B formula above
  ({{tbl-mojette-proj-sizes}} uses it) applied to the shard's
  direction (p, q) and the grid dimensions (P, Q)):

  - `num_chunks = ceil(shard_bytes / chunk_size)`
  - Chunk `j` (for j = 0..num_chunks-1) covers the shard byte
    range `[j * chunk_size, min((j+1) * chunk_size,
    shard_bytes))`.
  - The final chunk (chunk `num_chunks - 1`) MAY be shorter
    than `chunk_size` if `shard_bytes` is not a multiple of
    `chunk_size`; all other chunks are exactly `chunk_size`
    bytes.

The `chunk_size` value is a per-mirror parameter and does not
vary across the parity projections of a single file, even
though the shard sizes vary.  For a file with parity
projections of sizes `S_i = B_i * W`, the number of chunks per
shard is `ceil(S_i / chunk_size)` per shard; a reader that
requests chunk offset `>= S_i` on shard i receives
`NFS4ERR_PAYLOAD_LOST` (per {{sec-NFS4ERR_PAYLOAD_LOST}}) with a
short read reporting the shard's true byte length.

## Comparison of Encoding Types

| Property | Reed-Solomon | Mojette Systematic | Mojette Non-Systematic |
|---
| Maximum Distance Separable guarantee | Yes | Yes (Katz) | Yes (Katz) |
| Shard sizes | Uniform | Variable | Variable |
| Reconstruction cost | O(k^3) shard ops<br>(matrix inversion) | O(m*k*P*Q) grid ops (peeling) | O(m*k*P*Q) grid ops (peeling) |
| Healthy read cost | Zero | Zero | Full decode |
| GF operations | Yes (GF(2^8)) | No | No |
{: #tbl-encoding-comparison title="Comparison of erasure encoding types"}

Reed-Solomon uses uniform shard sizes and GF(2^8) operations.
Mojette systematic provides zero-cost healthy reads with variable
parity shard sizes; reconstruction cost scales as O(m * k) rather
than O(k^3).  Mojette non-systematic encodes all k + m shards as
projections, providing constant decode cost regardless of failure
count at a higher baseline read cost than systematic.  The choice
among these is a deployment decision driven by workload
characteristics and operational priorities.

## Handling write holes

A write hole occurs when a client begins writing a stripe but does not
successfully write all k+m shards before a failure.  Some data servers
will hold new data while others still hold old data, producing an
non-atomic payload.

The CHUNK_WRITE / CHUNK_ROLLBACK mechanism addresses this.  When a client
issues CHUNK_WRITE, the data server retains a copy of the previous shard
and places the new data in the PENDING state.  If any shard write fails,
the client issues CHUNK_ROLLBACK to each data server that received a
CHUNK_WRITE, restoring the previous content.  The payload remains
atomic from the reader's perspective throughout, because PENDING
blocks carry the new chunk_guard4 value and CHUNK_READ returns the last
COMMITTED or FINALIZED block when a PENDING block exists.

A single-shard CHUNK_WRITE failure MAY alternatively be
handled by reporting the failure to the metadata server via
LAYOUTERROR and letting the metadata server initiate the
repair flow at {{sec-repair-selection}}.  The metadata server
adds a REPAIR-flagged replacement data server to the layout
(from its out-of-band pool) and drives reconstruction of the
missing shard.

In the multiple writer model, a write hole can also arise when two clients
are racing.  The chunk_guard4 value on each chunk identifies which
transaction wrote it.  A reader that finds chunks with different guard
values detects the non-atomicity and either retries (if a concurrent write
is still in progress) or reports NFS4ERR_PAYLOAD_NOT_ATOMIC to the
metadata server to trigger repair.

When CHUNK_ROLLBACK and repair are both unavailable, and the
payload cannot be reconstructed because too many shards have
been lost (for example, a catastrophic multi-data server failure
with no reachable replacement data servers), the repair flow
ultimately terminates with NFS4ERR_PAYLOAD_LOST; see
{{sec-NFS4ERR_PAYLOAD_LOST}}.

#  System Model and Correctness {#sec-system-model}

The design decisions in this document -- centralized coordination
through the metadata server, CAS semantics via chunk_guard4,
pessimistic lock escrow during repair, and erasure-coded reads
from any sufficient subset -- depart visibly from a classical
distributed-consensus protocol such as Paxos or Raft.  This
section states the system model those decisions rest on, the
consistency and progress guarantees the protocol provides under
that model, and how the protocol relates to (and when it relies
on) classical consensus.  It is intended as the correctness
framing for implementers and reviewers; the normative wire
behavior is defined in the preceding sections.

##  Wire Semantics vs Implementation {#sec-system-model-wire}

The protocol defines wire semantics, not data-server
implementation.  The operations introduced in
{{sec-new-ops}} (CHUNK_WRITE, CHUNK_FINALIZE, CHUNK_COMMIT,
CHUNK_ROLLBACK, CHUNK_LOCK / CHUNK_UNLOCK, CHUNK_READ,
CHUNK_REPAIRED, CHUNK_ERROR, CHUNK_HEADER_READ,
CHUNK_WRITE_REPAIR) together with the per-chunk state machine
({{sec-system-model-chunk-state}}) and the chunk_guard4 CAS
({{sec-chunk_guard4}}) are everything a peer observes.
The data server's internal representation of persistent state is
not exposed on the wire, and two data-server implementations
that satisfy the same wire semantics MAY differ arbitrarily in
their internal structure.

In particular, the protocol does NOT exchange:

-  which on-disk layout (log-structured, append-only,
   in-place-overwrite, external object store, key-value store,
   or any other) a data server uses to persist chunks;
-  whether a data server holds PENDING and FINALIZED chunks in
   a single blob or in distinct regions;
-  how a data server represents the CHUNK_LOCK table, the guard
   epoch, or the escrow owner;
-  whether a data server's chunk retention beyond COMMIT is
   implemented via shadow blocks, journals, reference counts,
   or copy-on-write.

This decoupling is deliberate.  It lets the protocol accommodate
future smart-data server designs -- including designs that integrate more
closely with storage back-ends that already provide atomic
replace, multi-version concurrency, or internal erasure coding --
without protocol revisions, provided the wire semantics are
preserved.  Conversely, a data server implementer is free to
pick the representation that best fits the underlying storage
stack without fear that some less common implementation choice
is disallowed.

The counterpart of this rule is that the wire is the entire
contract.  Any behavior a client relies on MUST be observable
via the operations listed above; any behavior that is not
observable (cache state, background scrubbing cadence,
internal retry ordering, on-disk layout) is implementation
detail and MUST NOT be depended upon.

##  Chunks Are Not Blocks {#sec-system-model-chunk-not-block}

The chunk is a protocol-level primitive distinct from a block.
Throughout this document, "block" refers to a byte range in the
file's address space (the application's view); "chunk" refers to
the addressable unit carried by the CHUNK operations, which
has an envelope that blocks do not.

A chunk carries five properties that a block does not:

Atomicity:

: the chunk_guard4 compare-and-swap guard ({{sec-chunk_guard4}})
  sequences concurrent writers and rejects torn-write attempts.
  Block I/O has no comparable primitive; concurrent block
  writes either serialize at the storage layer or interleave
  unpredictably.

Integrity:

: the checksum in each chunk header is computed over the header
  and payload and verified end-to-end on the read path
  ({{sec-CHUNK_READ}}).  Block I/O carries no integrity tag;
  data-corruption detection is delegated to the underlying
  storage medium or is absent.

Provenance:

: the chunk_owner4 ({{sec-chunk_owner4}}) records which
  transaction produced the chunk.  Block I/O carries no
  per-write provenance; a block's bytes have no
  protocol-visible producer.

Lifecycle state:

: a chunk progresses through PENDING -> FINALIZED -> COMMITTED
  via CHUNK_FINALIZE / CHUNK_COMMIT
  ({{sec-system-model-chunk-state}}).  Block I/O has no
  lifecycle states; a block is either present or absent.

Lock continuity across revocation:

: the chunk's lock ({{sec-CHUNK_LOCK}}) is transferred to the
  metadata server in escrow when a holder's stateid is revoked,
  and adopted by a repair actor via CHUNK_LOCK_FLAGS_ADOPT.
  Block I/O has no per-block locking and no continuity
  mechanism; client failure leaves any external lock
  indeterminate.

Each of these properties is load-bearing for some part of the
flexible file v2 layout's consistency story: the chunk_guard4
CAS underlies multi-writer correctness; the checksum underlies
end-to-end integrity; lock escrow underlies repair coordination
across stateid revocation; the state machine underlies the
PENDING / FINALIZED / COMMITTED distinction that enables
rollback and repair.  Removing any one of them would change
what the protocol can guarantee.

A protocol that exchanges file data as byte ranges with no
envelope -- whether described as "block I/O" or as "generic
data movement" -- is not interoperable with this specification's
CHUNK operations.  The CHUNK operations are not a byte-range
I/O protocol with optional integrity bolted on; they are a
chunk protocol in which the envelope is the primitive.

##  Actors and Roles {#sec-system-model-roles}

Three actors participate on behalf of any given file:

pNFS client:
:  Issues CHUNK operations to data servers over the data path;
   issues LAYOUTGET, LAYOUTRETURN, LAYOUTERROR, and SEQUENCE to
   the metadata server on the control path.  Authenticates to the
   metadata server via AUTH_SYS, RPCSEC_GSS, or TLS.  MAY be
   selected as a repair actor via CB_CHUNK_REPAIR.

Metadata server:
:  Is the sole coordinator for the file.  Grants, renews, and
   revokes layouts; issues TRUST_STATEID / REVOKE_STATEID /
   BULK_REVOKE_STATEID to each tight-coupled data server; selects
   the repair actor under the rules in
   {{sec-repair-selection}}; owns the reserved
   CHUNK_GUARD_CLIENT_ID_MDS escrow identity for in-flight repair.

Data server:
:  Persists chunks and enforces the per-file trust table, the
   per-chunk guard CAS (chunk_guard4), the per-chunk lock state
   (including the metadata-server escrow owner), and the chunk state machine
   (EMPTY / PENDING / FINALIZED / COMMITTED).  Has no
   coordinator role.  Has no knowledge of the erasure encoding type
   in use for any file: the erasure transform is performed
   entirely at the client, and the data server stores the
   resulting chunks without interpreting their contents.

An entity MAY simultaneously hold more than one of these roles
with respect to a given data server, with each role bound to a
distinct session.  A metadata server that opens a control
session to a data server (presenting EXCHGID4_FLAG_USE_PNFS_MDS
at EXCHANGE_ID; see {{sec-tight-coupling-control-session}})
issues TRUST_STATEID, REVOKE_STATEID, and BULK_REVOKE_STATEID on
that session; on a separate client-side session (presenting
EXCHGID4_FLAG_USE_NON_PNFS), the same metadata server MAY also
issue CHUNK operations as a data-path client.  A data server
MUST NOT assume that the metadata server is not also one of its
clients; it distinguishes metadata-server-only operations from client-side
operations by the EXCHANGE_ID flags of the session that carries
the operation, not by the requester's IP address or principal.

A data server MAY likewise act as a client of another data
server -- for example, when selected as the repair actor by an
metadata-server-directed CB_CHUNK_REPAIR.  Independent of the actor role,
any entity may operate as encoding-aware (issuing CHUNK
operations directly against data servers) or encoding-unaware
(operating through the proxy server mediated READ / WRITE path
described in the proxy server draft).  Proxy-server registration
carries the encoding capability
explicitly; direct pNFS clients reveal their encoding posture
implicitly through the operations they issue.

The protocol does NOT mandate how a data server implements the
chunk state machine or stores PENDING chunks.  An implementation
MAY use per-client staging files, a single append-only instance
file with an index, a separate metadata-header file paired with
a blocks file, a log-structured store, or any other
representation that preserves the normative semantics (the
EMPTY / PENDING / FINALIZED / COMMITTED transitions, the
chunk_guard4 CAS, lock continuity across revocation, and the
integrity checks).  The choice is a data-server implementation
concern and is transparent to clients and the metadata server.

##  Failure Model {#sec-system-model-failures}

The protocol assumes:

Crash-stop:
:  Clients, metadata servers, and data servers fail by stopping.
   A restarted component rejoins the protocol with a fresh epoch
   and participates in the grace / reclaim path already defined
   in {{RFC8881}}.  Correct components do not exhibit arbitrary
   (Byzantine) behavior.

Fail-silent data servers:
:  Data servers report honestly about the state of the data they
   hold.  The protocol detects on-disk bit rot via checksum
   (see {{sec-CHUNK_WRITE}}) but does not defend against a data
   server that deliberately lies about whether a chunk is
   COMMITTED or what its contents are.  Byzantine data servers
   are explicitly outside the trust model; see
   {{sec-system-model-nongoals}}.

Authenticated writers and their own data:
:  An authenticated client may write arbitrary (even
   semantically-invalid) bytes into chunks it owns.  The checksum
   check detects transport corruption, not adversarial content.
   This matches the existing NFSv4 authorization model: once
   you have write access, you may write anything.

Network partitions:
:  The protocol is partition-tolerant at the cost of availability
   during the partition window.  A client partitioned from a
   data server recovers via LAYOUTERROR and may be issued a new
   layout (with a REPAIR-flagged replacement data server
   added by the metadata server; see
   {{sec-repair-selection}}).  A metadata server partitioned from a data
   server eventually renews trust entries on reconnection; in
   the interim, the data server returns NFS4ERR_DELAY for
   affected stateids (see {{sec-tight-coupling-mds-crash}}).
   Message loss is bounded by RPC retransmit; eventual delivery
   is assumed once the partition heals.

   Split-brain scenarios (in which a partitioned minority of
   the data servers in a mirror set attempts to make progress
   independently of the majority) cannot drive non-atomic
   writes to COMMITTED state.  The chunk_guard4 CAS on each
   write requires the guard value from a successor chunk to
   strictly advance the guard value of its predecessor; on
   partition heal, any writes attempted on the minority side
   are detected by the majority because their guard values do
   not satisfy the CAS precondition, and those writes are
   discarded.  When reconciliation is impossible -- for example,
   the erasure coding has lost too many shards across both sides
   of the partition to reconstruct any single atomic
   generation -- the repair flow terminates with
   NFS4ERR_PAYLOAD_LOST (see {{sec-NFS4ERR_PAYLOAD_LOST}}),
   which is terminal for the affected ranges.

Lease bound:
:  All state held by a data server on behalf of a metadata server
   is bounded by the TRUST_STATEID expiry (see
   {{sec-tight-coupling-lease}}).  An orphaned entry will
   eventually expire even if the metadata server never returns.

##  Chunk State Machine {#sec-system-model-chunk-state}

Each chunk on a data server occupies exactly one of four states.
The transitions below are the complete set; any implementation
of the data server's chunk state table MUST admit these
transitions and no others.

~~~
                            CHUNK_WRITE
                         (fresh cg_gen_id)
        +---------+ -------------------> +-------------+
        |  EMPTY  |                      |   PENDING   |
        +---------+ <------------------- +-------------+
             ^         CHUNK_ROLLBACK            |
             |        (discard PENDING)          |
             |                                   | CHUNK_FINALIZE
             |                                   |  (writer stops
             |                                   |   further writes)
             |                                   v
             |                            +-------------+
             |       CHUNK_ROLLBACK       |  FINALIZED  |
             |      (discard FINALIZED)   +-------------+
             |                                   |
             |                                   | CHUNK_COMMIT
             |                                   |  (make durable
             |                                   |   and globally
             |                                   |   visible)
             |                                   v
             |                            +-------------+
             +--------------------------> |  COMMITTED  |
                   CHUNK_ROLLBACK         +-------------+
                (only via repair;                 |
                 replaces with a newer            | CHUNK_WRITE with
                 COMMITTED generation             | a higher cg_gen_id
                 or discards per the              | begins a new
                 rollback invariant)              | PENDING successor;
                                                  | the prior COMMITTED
                                                  | is retained until
                                                  | its successor is
                                                  | COMMITTED (see the
                                                  v  rollback invariant
                                            (next PENDING
                                             against same chunk)
~~~
{: #fig-chunk-state-machine title="Chunk lifecycle on the data server"}

CHUNK_WRITE against a chunk already in PENDING from the same
writer with the same cg_gen_id is a self-transition on PENDING:
the data server replaces the PENDING payload in place and the
state does not change.  This case is not drawn in
{{fig-chunk-state-machine}} for clarity.

States:

EMPTY:
:  The chunk has no payload.  CHUNK_READ returns a zero-filled
   result; CHUNK_WRITE against an EMPTY chunk is the first write.

PENDING:
:  The chunk has payload accepted by CHUNK_WRITE but not yet
   finalized.  Not visible to CHUNK_READ (see
   {{sec-system-model-consistency}}).  Further CHUNK_WRITEs from
   the same writer MAY replace the payload in place (same
   cg_gen_id).

FINALIZED:
:  The writer has signalled via CHUNK_FINALIZE that it will send
   no more CHUNK_WRITEs for this generation.  Still not visible
   to CHUNK_READ, but a candidate for CHUNK_COMMIT.

COMMITTED:
:  The chunk is durable and globally visible.  Subsequent
   CHUNK_READs return this content until a newer COMMITTED
   generation replaces it.  A higher-generation PENDING successor
   MAY exist concurrently; the rollback invariant in
   {{sec-system-model-consistency}} requires the data server to
   retain the COMMITTED content while that successor exists.

Transitions are driven by the operations named on the arrows.
CHUNK_ROLLBACK against a COMMITTED chunk is used only on the
repair path (see {{sec-CHUNK_ROLLBACK}}) and replaces the chunk
with a newer COMMITTED generation chosen by the repair actor,
rather than returning the chunk to EMPTY.

{{fig-chunk-state-machine}} covers the lifecycle of a chunk's
payload but not the lock that may be held on it.  The lock has
its own state machine, shown in {{fig-chunk-lock-machine}}.

~~~
                          CHUNK_LOCK
                       (writer acquires)
        +----------+ ----------------> +-------------------+
        | UNLOCKED |                   | LOCKED by writer  |
        +----------+ <---------------- +-------------------+
             ^           CHUNK_UNLOCK            |
             |          (writer releases)        |
             |                                   | REVOKE_STATEID
             |                                   |  (metadata server
             |                                   |   invalidates writer
             |                                   |   stateid; lock
             |                                   |   transfers to
             |                                   |   metadata-server
             |                                   |   escrow)
             |                                   v
             |        CHUNK_UNLOCK     +-------------------+
             |       or CHUNK_REPAIRED |     LOCKED by     |
             |      (repair actor     |  metadata-server  |
             |       releases after    |      escrow       |
             |       repair completes) +-------------------+
             |                                   |
             |                                   | CHUNK_LOCK with
             |                                   | CHUNK_LOCK_FLAGS_ADOPT
             |                                   |  (repair actor
             |                                   |   adopts metadata-
             |                                   |   server escrow
             |                                   |   ownership per
             |                                   |   CB_CHUNK_REPAIR)
             |                                   v
             |                         +-------------------+
             +------------------------ | LOCKED by repair  |
                                       +-------------------+
~~~
{: #fig-chunk-lock-machine title="Chunk lock ownership on the data server"}

The lock state machine is orthogonal to the chunk lifecycle in
{{fig-chunk-state-machine}}: a chunk in any of EMPTY, PENDING,
FINALIZED, or COMMITTED MAY simultaneously be in any of the
four lock states.  The errored bit (set by CHUNK_ERROR, cleared
by CHUNK_REPAIRED) is a third orthogonal axis and is not drawn;
CHUNK_ERROR may set the bit in any state, and CHUNK_REPAIRED
clears it as part of completing a repair sequence.  A CHUNK_LOCK
that arrives while the chunk is already LOCKED by a different
owner returns NFS4ERR_CHUNK_LOCKED with the existing owner's
chunk_owner4 in clr_owner ({{sec-CHUNK_LOCK}}).

##  Read-Time Generation Status {#sec-system-model-read-time-status}

Independent of the chunk lifecycle state
({{fig-chunk-state-machine}}) and the lock state
({{sec-CHUNK_LOCK}}), a data server distinguishes three
read-time statuses for any generation the caller names or
observes at a chunk index.  These are the higher-level
categories the CHUNK_READ ({{sec-CHUNK_READ}}) per-chunk
status codes and the CHUNK_HEADER_READ
({{sec-CHUNK_HEADER_READ}}) discovery response classify
into:

AVAILABLE:
:  the generation's payload is held by the data server and
   its integrity check succeeds at read time.  A
   CHUNK_READ returns the payload with NFS4_OK.  A
   CHUNK_HEADER_READ that observes an AVAILABLE
   predecessor is the input the caller uses to decide
   whether CHUNK_ROLLBACK's restore case
   ({{sec-CHUNK_ROLLBACK}} "Rollback of COMMITTED
   Chunks") can succeed under the caller's own retention
   scope ({{sec-system-model-retention-scope}}).

ERRORED:
:  the owner-to-index association is still recorded but
   the payload is not readable -- the persisted checksum
   or guard check fails at read time
   ({{sec-NFS4ERR_PAYLOAD_NOT_ATOMIC}}), the underlying
   storage is unreachable, or the chunk carries the
   errored bit set by an earlier CHUNK_ERROR
   ({{sec-CHUNK_ERROR}}).  A CHUNK_READ returns
   NFS4ERR_PAYLOAD_NOT_ATOMIC (or another per-chunk
   status appropriate to the failure); the client
   reports the fault via LAYOUTERROR and the metadata
   server arranges repair.  An ERRORED generation is
   observable -- its owner triple can be discovered -- but
   not consumable.

ABSENT:
:  the data server holds no generation at the requested
   chunk index (the chunk is EMPTY) or holds no
   generation matching the requested owner triple.  A
   CHUNK_READ returns the synthetic-hole response
   ({{sec-CHUNK_READ}}) or per-chunk NFS4ERR_NOENT.  A
   CHUNK_HEADER_READ that names a predecessor and finds
   ABSENT returns the absence in its per-chunk response
   fields; a CHUNK_ROLLBACK that names such a
   predecessor returns NFS4ERR_NO_PREDECESSOR
   ({{sec-NFS4ERR_NO_PREDECESSOR}}) or NFS4ERR_INVAL per
   the rules under "Deletion Atomicity and Invalidated
   Triples" ({{sec-CHUNK_ROLLBACK}}).

The three statuses are exhaustive at read time: any
generation the caller might reference is exactly one of
AVAILABLE, ERRORED, or ABSENT.  A generation can
transition from AVAILABLE to ERRORED (via CHUNK_ERROR
or a checksum failure) and from ERRORED back to
AVAILABLE (via a successful repair sequence).  The
transition from AVAILABLE or ERRORED to ABSENT is a
release under the retention scope rule
({{sec-system-model-retention-scope}}) coupled with the
payload/association biconditional
({{sec-system-model-payload-association-biconditional}}):
the payload and its owner-to-index association are
released together and the generation vanishes from the
observable set.  There is no transition from ABSENT
back to any observable status for the same owner
triple: the invalidated-triple rule ("Deletion
Atomicity and Invalidated Triples" under
{{sec-CHUNK_ROLLBACK}}) forbids resurrection.

##  Consistency Guarantees {#sec-system-model-consistency}

The protocol provides per-chunk linearizability on COMMITTED
state:

1.  Once CHUNK_COMMIT returns success to a writer for a given
    chunk, every subsequent CHUNK_READ whose stateid postdates
    the COMMIT observes either that writer's data or the data of
    a later committed write.  A reader MUST NOT observe a
    rolled-back write as if it had committed.

2.  Concurrent writers on the same chunk in multi-writer mode
    serialize via chunk_guard4.  On guard conflict one writer
    succeeds; the other receives NFS4ERR_CHUNK_GUARDED and MUST
    either abandon the write or re-read and retry.  At most one
    generation becomes COMMITTED per serialized decision.

3.  During repair, the chunk's lock is held continuously -- first
    by the original writer, then transferred to the metadata-server escrow
    owner on REVOKE_STATEID, and finally adopted by the repair
    client via CHUNK_LOCK_FLAGS_ADOPT.  No writer that did not
    hold the lock may observe or mutate the chunk.  The
    invariant "a chunk with a live lock has exactly one logical
    owner at any instant" is preserved across revocation.

Across multiple chunks the protocol makes **no multi-chunk
atomicity or ordering guarantee**.  A reader that reads chunk A
at one offset and chunk B at another MAY observe A's new value
and B's old value simultaneously.  Applications that require
multi-chunk atomicity MUST layer it above this protocol -- for
example, via file-level checksums, application-level generation
fields, or external transaction managers.

The chunk is the unit of atomicity:

: Two properties follow.

1.  Chunk-aligned writes do not interfere.  Two concurrent
    writers whose writes cover disjoint chunks -- even writes
    that cover adjacent chunks -- never race.  Each write
    terminates independently at COMMITTED per the per-chunk
    linearizability rule above.

2.  Sub-chunk overlapping writes from different writers
    produce chunk-resolution-granularity contention.  When two
    concurrent writers target overlapping byte ranges within a
    single chunk, chunk_guard4 resolves them: one writer's
    entire chunk-generation wins and becomes COMMITTED; the
    other writer sees NFS4ERR_CHUNK_GUARDED and is expected to
    re-read and retry if it wishes to apply its change on top
    of the winning generation (see
    {{sec-NFS4ERR_CHUNK_GUARDED}}).  The protocol does NOT
    produce byte-level merges of overlapping sub-chunk writes:
    the losing writer's bytes are not preserved as a partial
    update within the winning generation.

Applications that require byte-level write merging or sub-chunk
ordering guarantees MUST serialize such writes externally, for
example via NFSv4 byte range locks ({{RFC8881}}, Section 12).
The chunk size that bounds the atomicity unit for a given file
is the product of ffv2m_striping_unit_size and the stripe width
W in {{fig-striping-math}}; applications can query
fattr4_coding_block_size (see {{sec-fattr4_coding_block_size}})
to learn the effective chunk size and align their writes
accordingly.

This choice -- chunk-boundary atomicity rather than stripe- or
block-boundary atomicity -- is load-bearing for the rest of the
consistency story: the chunk_guard4 CAS evaluates at the chunk
level, the PENDING / FINALIZED / COMMITTED state machine is per
chunk, CHUNK_LOCK is per chunk, and repair via CB_CHUNK_REPAIR
operates on chunks.  A different atomicity boundary would
require redefining those primitives.

Erasure-coded reads:
:  A reader of an erasure-coded file reconstructs the plaintext
   from any sufficient subset of k shards of the (k+m)-shard
   stripe; the guard values on those shards MUST agree.  Shards
   with stale guards are ignored.  This is not a quorum read in
   the Paxos sense -- there is no voting on a value; there is
   only reconstruction of the single value identified by the
   current guard.

Rollback invariant:
:  The data server MUST retain the prior FINALIZED or COMMITTED
   content of a chunk while any successor PENDING or FINALIZED
   chunk exists.
   A corollary of this rule is the **lowest-guard-recoverable**
   property: as long as at least k data servers in the mirror
   set retain the chunk at some generation G or lower, the
   payload that was COMMITTED at generation G (or earlier) can
   be reconstructed.  This is the correctness basis for
   CHUNK_ROLLBACK (see {{sec-CHUNK_ROLLBACK}}): rollback does not
   synthesize data, it simply selects the lowest-generation
   chunks whose guards agree across the mirror set and discards
   the higher-generation PENDING or FINALIZED chunks that
   triggered the rollback.  The protocol never relies on locating
   or reconstructing data from outside the mirror set.

Visibility of non-committed state:
:  PENDING and FINALIZED chunks MUST NOT be globally visible.
   CHUNK_READ returns only COMMITTED content; a CHUNK_READ whose
   target chunk is currently PENDING or FINALIZED sees the
   predecessor COMMITTED content (or an EMPTY chunk if none
   exists), not the in-progress successor.  A writer observing
   its own PENDING or FINALIZED chunk MAY receive the in-progress
   content on the same stateid that produced it, but no other
   stateid -- on the same or a different client -- sees it.
   The retention window that makes the prior COMMITTED content
   available to CHUNK_READ and to CHUNK_ROLLBACK is itself
   bounded; see {{sec-system-model-retention-scope}} for the
   normative scoping rule.

##  Ownership and Scope of Retained Prior Content {#sec-system-model-retention-scope}

The rollback invariant in {{sec-system-model-consistency}}
requires a data server to retain the prior FINALIZED or
COMMITTED content of a chunk while any successor PENDING or
FINALIZED chunk exists.  That retained content -- sometimes informally called
the "safe buffer" -- is not global state.  It is scoped to the
stateid that wrote the PENDING successor, and its retention and
visibility are governed by that owning stateid's lease.

Owner:
:  The data server MUST record, alongside each PENDING chunk,
   the owning stateid (the stateid presented on the CHUNK_WRITE
   that produced the PENDING).  This is the owning writer's
   stateid; it identifies the client and openowner/lockowner
   that the data server will release the PENDING to on
   CHUNK_FINALIZE or CHUNK_COMMIT, and that the metadata server will treat
   as the authoritative owner for purposes of
   {{sec-system-model-progress}}.

Visibility:
:  Before transition to COMMITTED, the PENDING content is
   visible only on the owning stateid.  A CHUNK_READ presenting
   any other stateid (from the same client or a different
   client) MUST observe the predecessor COMMITTED or EMPTY
   state, not the PENDING successor.  This is the normative
   form of the "non-committed data MUST NOT be globally visible"
   rule stated in the "Visibility of non-committed state"
   bullet of {{sec-system-model-consistency}}.

Retention window:
:  The data server MUST retain the predecessor COMMITTED (or
   FINALIZED) content that the PENDING is superseding for as
   long as the owning stateid's lease is valid.  If the owning
   stateid's lease expires without the PENDING reaching
   COMMITTED, the retention obligation for that PENDING ends
   (see {{sec-system-model-progress}} for the scavenger rule
   that drives demotion).  If the PENDING does reach COMMITTED,
   the new COMMITTED generation supersedes the prior one under
   the standard rollback invariant and its own retention is
   governed by any newer PENDING successor.

The practical effect is that the "safe buffer" for a chunk is
not an unbounded chunk-global state but a per-writer window
bounded by that writer's lease.  The data server always has a
rule for discarding retained prior content -- it is the
owning stateid's lease expiry -- so a chunk cannot accumulate
indefinitely many retained generations even in the presence of
dropped or partitioned writers.

##  Owner-to-Index Persistence Coupling {#sec-system-model-owner-persistence}

The wire lifecycle operations (CHUNK_COMMIT
({{sec-CHUNK_COMMIT}}), CHUNK_FINALIZE
({{sec-CHUNK_FINALIZE}}), CHUNK_ROLLBACK
({{sec-CHUNK_ROLLBACK}})) name generations by full
(co_cohort_id, co_client_id, co_id) owner triples
({{sec-chunk_owner4}}) and require the data server to
locate the chunk-index each triple was written at.  For
that lookup to succeed after a data server restart, the
data server MUST persist the owner-to-index association
with a durability floor that matches the payload's:
without the association the payload can never again be
addressed by a lifecycle operation.

Uniqueness invariant (normative):

: An accepted (co_cohort_id, co_client_id, co_id) triple is
UNIQUE across the live generations the data server holds
for a given file: at any instant there is at most one
live generation on any chunk of the file that matches
that full triple.  Two writers with distinct co_client_id
values cannot collide.  A single writer that reuses a
co_cohort_id + co_id pair within the same co_client_id
across two distinct chunk indices MUST NOT do so while
the earlier generation remains live; the data server MAY
reject a CHUNK_WRITE that attempts to create such a
collision with NFS4ERR_INVAL in the corresponding
cwr_block_status slot.  The predecessor-retention rule
({{sec-system-model-consistency}}) is compatible: a
retained predecessor and its successor on the same
chunk index MUST carry distinct triples (typically
distinct co_cohort_id under a shared co_client_id) so that
CHUNK_ROLLBACK can name each unambiguously.

Durability floor (normative, per CHUNK_WRITE {{sec-CHUNK_WRITE}} "Stability and Activation"):

: The durability requirement varies by the CHUNK_WRITE
  stability level:

  FILE_SYNC4:

  : both the chunk payload AND its owner-to-index
    association MUST survive a data server restart.

  DATA_SYNC4:

  : both the chunk payload AND its owner-to-index
    association MUST survive a data server restart.
    (The association is retrieval metadata for the
    payload; it shares the payload's durability floor.
    An implementation MAY treat DATA_SYNC4 identically
    to FILE_SYNC4.)

  UNSTABLE4:

  : the association MAY be lost on restart, but ONLY if
    the payload is also lost.  A data server MUST NOT
    retain payload without its associated owner triple;
    a payload whose association was lost is
    unaddressable by every lifecycle operation and MUST
    be treated as destroyed.  cwr_writeverf changes on
    any restart that loses UNSTABLE4 state, allowing the
    client to detect the loss.

A data server that cannot honor the durability floor
for a given stability level MUST reject the CHUNK_WRITE
with NFS4ERR_IO rather than accepting the payload without
its association.

The retention scope rule ({{sec-system-model-retention-scope}})
governs WHEN a predecessor generation's payload +
association may be released; the payload/association
biconditional in the next subsection governs the
INVARIANT that whenever the payload survives, the
association survives with it, and vice versa.

##  Payload and Association Biconditional {#sec-system-model-payload-association-biconditional}

For every generation the data server holds -- PENDING,
FINALIZED, or COMMITTED, including any predecessor
retained under the rollback invariant
({{sec-system-model-retention-scope}}) -- the chunk
payload and its owner-to-index association
({{sec-system-model-owner-persistence}}) MUST share a
lifetime.  A conforming data server MUST NOT release
one while retaining the other:

MUST NOT retain payload without association:

: A chunk payload whose owner-to-index association has
  been released is unaddressable by every lifecycle
  operation (CHUNK_COMMIT ({{sec-CHUNK_COMMIT}}),
  CHUNK_FINALIZE ({{sec-CHUNK_FINALIZE}}),
  CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}})) because
  those operations name generations by full owner
  triple ({{sec-chunk_owner4}}).  A data server that
  cannot locate the recorded chunk index for a
  presented triple returns the appropriate per-entry
  error under the release-scope split at
  {{sec-NFS4ERR_NO_PREDECESSOR}}: NFS4ERR_INVAL when
  the data server holds a concrete invalidation
  context that identifies the triple (structurally
  invalid, or released by an explicit CHUNK_ROLLBACK
  delete case within the session slot's replay-cache
  window), NFS4ERR_NO_PREDECESSOR otherwise.
  Retaining the payload while making it unaddressable
  serves no purpose and is prohibited.  The payload MUST be released
  atomically with the association.

MUST NOT release association while retaining payload:

: A recorded owner-to-index association refers to a specific
  chunk payload; the data server MUST NOT retain the
  association after releasing that payload.  A subsequent
  CHUNK_READ or lifecycle operation whose recorded index still
  points to a released payload would return data whose
  provenance the client cannot verify against its own writer
  history; forbidding this releases the client from having to
  detect such stale associations.

The biconditional is symmetric: released together,
retained together.  This coupling is what makes
CHUNK_ROLLBACK's delete case ({{sec-CHUNK_ROLLBACK}})
atomic -- invalidating a generation drops BOTH the
association and the payload in one step -- and what
makes CHUNK_ROLLBACK's restore case rely on the
predecessor's association surviving with its payload
as a single unit.  Data servers implementing an
on-disk chunk store SHOULD treat the association and
payload as the crash-consistent atomic unit at the
storage layer.

The retention scope rule
({{sec-system-model-retention-scope}}) governs WHEN the
pair may be released (bounded by the owning stateid's
lease and any successor's presence); this
biconditional governs the INVARIANT that whenever the
release happens, the two go together.

##  Progress and Termination {#sec-system-model-progress}

Under the failure model above, the protocol guarantees the
following progress properties:

Data-path progress:
:  If all mirrors are reachable and none are failed, a
   CHUNK_WRITE followed by CHUNK_FINALIZE followed by
   CHUNK_COMMIT completes in O(1) round trips independent of
   cluster size.  In particular, there is no consensus round,
   no leader election, and no quorum voting on the write
   itself.  The three operations MAY be amortized across
   compounds: a steady-state writer sending a series of
   CHUNK_WRITEs can piggyback the CHUNK_FINALIZE of the previous
   write on the compound that carries the next write (for
   example, `SEQUENCE + PUTFH + CHUNK_FINALIZE + CHUNK_WRITE`),
   reducing the data-path happy case to a single round trip per
   CHUNK_WRITE rather than three.  The CHUNK_COMMIT for the
   final write in a sequence MAY similarly ride on the CLOSE
   compound.  These compound-packing optimizations are
   permitted by the normal NFSv4.2 compound rules and require
   no protocol extensions.

Repair termination:
:  Every CB_CHUNK_REPAIR completes in bounded time.  The client
   selected as the repair actor either:

   1.  returns NFS4_OK for every range in ccra_ranges (repair
       succeeded), or

   2.  returns NFS4ERR_PAYLOAD_LOST for one or more ranges (the
       erasure coding lost too many shards to reconstruct; the
       data is permanently unrecoverable), or

   3.  fails to respond within the ccra_deadline, in which case
       the metadata server MUST re-select under the rules in
       {{sec-repair-selection}} or MUST declare the ranges lost.

   NFS4ERR_PAYLOAD_LOST is terminal for the affected ranges.
   The protocol makes no further attempt to recover them.

Eventual trust-table convergence:
:  After a metadata server restart, each data server's trust
   table converges to the metadata server's view within one
   metadata-server lease period.  Entries that the metadata
   server does not re-issue expire naturally via tsa_expire;
   entries that the metadata server does re-issue transition
   from pending-revalidation back to active on the next
   TRUST_STATEID (see {{sec-tight-coupling-mds-crash}}).

Orphaned PENDING scavenger:
:  A PENDING chunk whose owning stateid (see
   {{sec-system-model-retention-scope}}) has expired without
   transition to FINALIZED or COMMITTED is an orphan.  The
   metadata server MUST drive demotion of orphaned PENDINGs so
   that no chunk remains in a non-terminal state indefinitely:

   1.  When an owning stateid's lease expires, the metadata
       server identifies every PENDING chunk owned by that
       stateid (either from its own bookkeeping or by query
       against the data server) and issues the control-plane
       operations needed to demote each PENDING.

   2.  Demotion replaces the PENDING with the predecessor
       COMMITTED (or EMPTY) content that the data server has
       been retaining under
       {{sec-system-model-retention-scope}}.  The data server
       MUST NOT wait for a separate client action before
       performing the demotion.

   3.  Any CHUNK_LOCK held in escrow on behalf of the expired
       stateid (see {{sec-chunk_guard_mds}}) is released after
       a metadata-server-defined grace period.  The grace period exists to
       let a recovering client reclaim its lock via the grace /
       reclaim path defined in {{RFC8881}}; on expiry of the
       grace period without reclaim, the lock becomes available
       for new CHUNK_LOCK_FLAGS_ADOPT acquirers.

   The scavenger timeout (the delay between lease expiry and
   demotion) is implementation-defined but SHOULD be tied to
   the metadata server lease period so that it composes
   naturally with existing NFSv4 grace / reclaim semantics.  A
   scavenger timeout shorter than the lease risks racing an
   in-progress client reclaim; a timeout substantially longer
   than the lease extends the retention budget without a
   commensurate benefit.

   A late-arriving client op against a demoted PENDING sees
   NFS4ERR_BAD_STATEID under trusted-stateid tight coupling
   ({{sec-REVOKE_STATEID}}) or NFS4ERR_NO_PREDECESSOR under
   loose coupling ({{sec-NFS4ERR_NO_PREDECESSOR}}); a
   CHUNK_LOCK reclaim after the grace period fails per the
   RFC 8881 grace-reclaim semantics.

The protocol does NOT guarantee progress if the metadata server
is unavailable for longer than its lease period -- this is the
standard NFSv4 lease assumption and is inherited unchanged.

##  Relation to Classical Consensus {#sec-system-model-consensus}

Classical consensus protocols (Paxos, Raft, Viewstamped
Replication) solve the problem of reaching agreement among
mutually-distrusting replicas in the absence of a trusted
coordinator.  They typically cost two or three round trips per
decision, require a majority of replicas to be live and
reachable for progress, and impose the overhead of leader
election and log replication.

This protocol is not a consensus protocol and does not attempt
to be.  Its approach instead is:

Designated coordinator:
:  The metadata server is the
   coordinator for a file.  Clients accept the metadata server's authority
   for layout grants, stateid registration, repair actor
   selection, and revocation.  This assumption is the same one
   made by {{RFC8434}} and all pNFS layout types to date.

Per-chunk CAS, not per-chunk voting:
:  Concurrent writes
   on the same chunk serialize via chunk_guard4 as a CAS
   primitive (see {{sec-chunk_guard4}}).  No replica vote is
   required; the data server that owns the chunk evaluates the
   guard locally and rejects stale writes with
   NFS4ERR_CHUNK_GUARDED.

Pessimistic locks off the critical path:
:  CHUNK_LOCK is
   used only during repair, never on the normal write path.
   Lock escrow (see {{sec-chunk_guard_mds}}) preserves the
   "exactly one owner" invariant across stateid revocation
   without requiring a consensus round to elect the next owner.

Erasure-coded reads replace quorum reads:
:  A reader
   reconstructs from any k of k+m shards with matching guards.
   No voting is needed because there is no disagreement to
   resolve: the guard identifies the single generation that was
   committed.

The result is a data path with O(1) round-trip cost independent
of the number of replicas, and a repair path whose cost is
bounded by the number of affected chunks rather than by the
cluster size.

Metadata-server high availability is orthogonal.  Deployments
that require a highly-available metadata server MAY replicate
metadata-server state across multiple metadata server instances
using classical consensus (Raft, Paxos, or equivalent).  Such
replication is implementation-defined; from a pNFS client's
perspective a highly-available metadata server looks like a
single metadata server that occasionally resets its session and
triggers grace-period reclaim, and the client's behavior is
already specified by {{RFC8881}}.  This protocol neither
requires nor precludes such an implementation.

##  Non-Goals {#sec-system-model-nongoals}

For clarity, the protocol explicitly does not provide:

Byzantine fault tolerance:
:  A data server that
   deliberately misreports its state, or a client that
   bypasses its own authentication, is outside the trust model.
   Deployments requiring Byzantine tolerance MUST add it in a
   layer above or below this protocol.

Metadata server high availability:
:  Single-metadata-server-per-file is the protocol model.  Metadata server
   high availability, if deployed, is implemented below the wire
   protocol and transparent to clients.

Cross-file atomicity:
:  Writes to multiple files are not
   atomic at the protocol level.  File-system-level transactions
   are not defined.

Multi-chunk atomicity within a single file:
:  COMMITs on
   distinct chunks are independent.  A reader may observe a
   partial write across chunks; applications must layer their
   own consistency if they need otherwise.

Global linearizability across unrelated files:
:  Each
   file's COMMITTED state is linearizable in isolation; no
   total order is defined across files.

Authenticated malicious client protection:
:  An
   authenticated client may write garbage into its own chunks
   with a correctly computed checksum; see
   {{sec-security-checksum-scope}}.  A bit-flip-class checksum
   is a transport-integrity check, not an adversarial-integrity
   check; cryptographic-class checksums detect adversarial
   modification by anyone other than the authenticated writer.

# NFSv4.2 Operations Allowed to Data Files

In the Flexible File Version 1 Layout Type ({{RFC8435}}), the data path
between client and data server was NFSv3 ({{RFC1813}}); the
operations a client sent to a data file were limited to READ,
WRITE, and COMMIT, and the operations the metadata server sent on
its control plane to the data server were limited to GETATTR,
SETATTR, CREATE, and REMOVE.  An NFSv4.2 data server, as used by
the Flexible File Version 2 Layout Type, exposes a much larger
operation set.  This section defines which operations a client MAY
send to a data file, which operations the metadata server MAY
send, and which operations a data server MUST reject.

The restrictions below apply only to operations directed at a data
file on a data server.  Clients retain the full NFSv4.2 operation
set for files visible through the metadata server, including the
operations prohibited below (RENAME, LINK, CLONE, COPY, ACL-scoped
SETATTR, and so on).  The metadata server MAY internally use
operations on data files that clients MUST NOT send, as part of
its control-plane duties for the file (see
{{sec-system-model-roles}}).

##  Control Plane: Metadata Server to Data Server {#sec-ops-mds}

When the metadata server acts as a client to a data server, it is
managing the data file on behalf of the metadata file's namespace.
A data server MUST support the following operations on data files
when issued by the metadata server:

-  SEQUENCE, PUTFH, PUTROOTFH, GETFH ({{RFC8881}} Sections 18.46,
   18.19, 18.21, 18.8): session and filehandle plumbing.
-  LOOKUP ({{RFC8881}} Section 18.15): directory traversal
   the metadata server issues when locating data files it has
   allocated for its use.
-  GETATTR ({{RFC8881}} Section 18.7): the metadata server issues
   GETATTR against the data file after a write layout is returned,
   to pull the post-write size, mtime, and other attributes back
   and reconcile its cached view.  Any other attribute queries
   the metadata server needs for the same purpose use the same
   operation.
-  SETATTR ({{RFC8881}} Section 18.30): data file truncate for
   metadata-server-level SETATTR(size) fan-out, synthetic uid/gid rotation
   for fencing, and mode-bit initialization when the metadata
   server binds a data file to a new metadata-level file.
-  CREATE ({{RFC8881}} Section 18.4): the metadata server's own
   allocation of data files on the data server.
-  REMOVE ({{RFC8881}} Section 18.25): cleanup on metadata server file
   unlink.
-  OPEN, CLOSE ({{RFC8881}} Sections 18.16, 18.2): used by the
   metadata server when it acts as a client to the data server
   for I/O routed through the metadata server or through a
   proxy server on the metadata server's behalf.
-  EXCHANGE_ID, CREATE_SESSION, DESTROY_SESSION,
   BIND_CONN_TO_SESSION, DESTROY_CLIENTID ({{RFC8881}} Sections
   18.35, 18.36, 18.37, 18.34, 18.50): control-session
   management.  The metadata server sets
   EXCHGID4_FLAG_USE_PNFS_MDS in its EXCHANGE_ID.  A data
   server that supports the tight coupling control protocol
   (see {{sec-tight-coupling-control-session}}) identifies the
   metadata server's session by EXCHGID4_FLAG_USE_PNFS_MDS and
   accepts TRUST_STATEID, REVOKE_STATEID, and
   BULK_REVOKE_STATEID on that session.
-  TRUST_STATEID ({{sec-TRUST_STATEID}}), REVOKE_STATEID
   ({{sec-REVOKE_STATEID}}), BULK_REVOKE_STATEID
   ({{sec-BULK_REVOKE_STATEID}}): the metadata-server-to-data-server tight coupling
   trust-table control operations.

The metadata server MAY also use other NFSv4.2 operations on data
files as implementation-defined control-plane actions (for
example, COPY or CLONE to migrate a data file between data
servers during a proxy server operation).  The list above is the
minimum set a flexible file v2 layout data server MUST support for the
metadata server's use.

##  Data Path: Client to Data Server {#sec-ops-client}

A pNFS client with an active flexible file v2 layout MUST restrict
the operations it issues against data files to the operations
defined below.  A data server that has identified the file as a
chunked data file (see {{sec-data-file-identification}}) MUST
reject any other operation on that file with NFS4ERR_NOTSUPP.

### Data-File Identification on the Data Server {#sec-data-file-identification}

The "MUST reject" rules in this section apply on the data server
side only to files the data server has identified as chunked data
files.  A data server identifies a file by any of the following
means, in decreasing order of authority:

fattr4_ffv2_chunked_data_file = TRUE:

: The metadata server has set this attribute
  ({{sec-fattr4_ffv2_chunked_data_file}}) when it allocated the
  file as a chunked data file.  This is the authoritative
  per-file identification and is required for a data server that
  supports the attribute.

Live TRUST_STATEID entry for the file:

: Under trusted-stateid tight coupling
  ({{sec-tight-coupling-control}}), a live trust entry for the
  file registered via TRUST_STATEID ({{sec-TRUST_STATEID}})
  identifies the file as under FFv2 management.  This is a
  fallback for data servers that do not yet support
  fattr4_ffv2_chunked_data_file, and it is per-client rather
  than per-file, but it is sufficient to trigger the "MUST
  reject" rules for that client's operations against the file.

Deployment namespace convention:

: Deployments SHOULD export chunked data files in a namespace
  scope not shared with client-accessible file access, as one
  means of preventing a misconfigured or malicious client from
  reaching data files through a normal NFS mount.  A data server
  MAY apply the "MUST reject" rules to every file in a
  namespace configured for FFv2 data-file service, without
  per-file classification.  Note that a separate NFS export
  does not close direct filesystem access on the data server
  host itself; that is outside the scope of this specification.

If none of the above identifies the file, the data server cannot
reliably classify it and the client-side "MUST NOT" rules in this
section remain the primary defense.  Client-side compliance is
mandatory in all deployment modes regardless of what the data
server can enforce.

### Session and Identity Plumbing

Required for all protection modes:

-  SEQUENCE, PUTFH, GETFH, PUTROOTFH ({{RFC8881}} Sections 18.46,
   18.19, 18.8, 18.21).
-  EXCHANGE_ID, CREATE_SESSION, DESTROY_SESSION,
   BIND_CONN_TO_SESSION, DESTROY_CLIENTID ({{RFC8881}} Sections
   18.35, 18.36, 18.37, 18.34, 18.50).
-  RECLAIM_COMPLETE ({{RFC8881}} Section 18.51).
-  SECINFO, SECINFO_NO_NAME ({{RFC8881}} Sections 18.29, 18.45):
   discovery of acceptable security flavours on the data
   server.

These operations are baseline NFSv4.2 session plumbing and are
supported on data files as on any NFSv4.2 file.

### Stateid Model on the Data Server {#sec-ds-stateid-model}

The stateid presented on a CHUNK operation is a **layout
stateid** returned by a prior LAYOUTGET against the metadata
server (see Section 18.43 of {{RFC8881}}), NOT an open
stateid, byte range lock stateid, or delegation stateid.  A
pNFS client does NOT issue OPEN against the data server.
This is a meaningful departure from the stateid model in
Section 18.32 of {{RFC8881}} (which states that the WRITE
stateid "represents a value returned from a previous
byte range LOCK or OPEN request or the stateid associated
with a delegation"), and clients implementing
Flexible File Version 2 MUST NOT carry over those
expectations to the data path.

The three roles the RFC 8881 stateid plays on a regular
NFSv4 server split apart in the Flexible File Version 2
data-server model:

Open and share-mode tracking:
:  Lives at the metadata server, established by OPEN
   ({{RFC8881}} Section 18.16) on the metadata-server
   filehandle.  The metadata server's open stateid is NOT
   exposed to data servers; share-mode conflicts are
   resolved at the metadata server before LAYOUTGET grants
   a layout.

Byte-range lock tracking:
:  Does not apply at the data server.  Locking on the data
   path is chunk-range rather than byte range, expressed
   via CHUNK_LOCK ({{sec-CHUNK_LOCK}}), and the lock holder
   is identified by chunk_owner4 (the (co_cohort_id,
   co_client_id, co_id) triple) rather than by a lock stateid.  A
   client wanting byte range locks on a file MUST acquire
   them on the metadata-server filehandle, where standard
   {{RFC8881}} Section 12 byte range locking applies.

I/O authorization on the data server:
:  The layout stateid carried on CHUNK operations.
   encodings that use CHUNK operations require tight coupling
   ({{sec-ff_device_addr4}}); the metadata server registers
   each issued layout stateid with the data server via
   TRUST_STATEID ({{sec-TRUST_STATEID}}) together with the
   ffv2m_client_id assigned to the writer, and the data
   server validates subsequent CHUNK operation stateids against
   the trust table and the presented cwa_client_id
   against the trust-table's tsa_client_id.  Loose coupling
   applies only to PASSTHROUGH mirrors, which use regular
   READ/WRITE authorized by the synthetic uid/gid the layout
   carries (see {{sec-Fencing-Clients}}).

Because the layout stateid does authorization but does not
identify a per-open or per-lock owner, a single client may
present the same layout stateid on many CHUNK operations
across many parallel writers within the client, without any
of the open-owner ordering constraints {{RFC8881}}
Section 8.2.2 imposes on regular NFSv4 stateids.  Chunk-level
write ordering and contention are resolved by the
per-chunk chunk_guard4 CAS ({{sec-chunk_guard4}}) and the
chunk-range CHUNK_LOCK, not by stateid-owner sequencing.

### GETATTR on a Data File

GETATTR MAY be issued by a client against a data file.  The
primary use case is repair: a repair actor selected by
CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}) may need to query the
per-server file size or allocation state when reconstructing a
payload, and the proxy server described informally in
{{sec-system-model-roles}} similarly benefits from attribute
queries on surviving mirrors.  Diagnostic use is also permitted.

Clients MUST NOT treat GETATTR values returned by a data server as
authoritative for any file attribute (size, timestamps, owner,
mode, ACL, and so on).  The metadata server is the sole authority
for file attributes.  Values returned by a data server reflect the
per-server data file instance only and MAY diverge from the
metadata server's view, particularly during a write layout's
lifetime or during a proxy server transition.  A client that uses a
data-server GETATTR result to determine the file's visible size
will observe inconsistencies.

### SETATTR on a Data File {#sec-setattr-on-data-file}

Clients MUST NOT issue SETATTR against a data file.  A data server
that has identified the file as a chunked data file (see
{{sec-data-file-identification}}) MUST reject a client SETATTR
with NFS4ERR_NOTSUPP.

Attribute changes on data files MUST be reconciled with the
metadata server's view and cannot be applied unilaterally by a
client.  A client that wants to truncate, change the mode, change
ownership, or otherwise modify attributes on a file MUST issue
SETATTR to the metadata server for the file's metadata server handle; the
metadata server fans the change out to the data files as a
control-plane operation.

This rule explicitly covers truncate (SETATTR with size in the
bitmap): a client MUST NOT truncate a data file directly.  See
{{sec-mds-truncate-ec}} for how the metadata server handles
truncate on chunked files.  Similarly, a client MUST NOT
issue DEALLOCATE against a data file; see the next subsection.

### Metadata-Server-Driven Truncate on Chunked Files {#sec-mds-truncate-ec}

A client that wants to truncate a chunked file MUST
issue SETATTR(FATTR4_SIZE) to the metadata-server filehandle
(see {{sec-setattr-on-data-file}}).  The metadata server
translates the logical truncate into per-shard size changes
across the data servers in each mirror.  For
FFV2_ENCODING_MIRRORED, per-shard size equals the logical
truncate size; for erasure-coded encodings the per-shard sizes
are derived from the geometry parameters below.

Stripe-aligned truncate:
:  When the new size lies on a stripe boundary (including
   zero), no chunk re-encoding is required.  The metadata
   server computes per-shard sizes from the encoding geometry it
   issued in the layout (k, m, and the projection parameters
   for Mojette; see {{sec-mojette-encoding}}) and issues
   per-data-server SETATTR(FATTR4_SIZE) with the computed
   per-shard size.  Geometry parameters are sufficient
   arithmetic; no encoding implementation is required at the
   metadata server.

Non-stripe-aligned truncate:
:  When the new size falls within a stripe, the data shards
   covering the partial stripe must be truncated and the
   parity shards re-encoded from the truncated data.  Because
   re-encoding requires running the erasure transform, the
   metadata server MUST delegate this case to an encoding-aware
   actor: either a proxy server for proxy-mediated truncate, or
   an encoding-aware client selected per {{sec-repair-selection}}
   via CB_CHUNK_REPAIR with the
   affected partial-stripe chunks as the repair target.  If
   neither path is available, the metadata server MUST return
   NFS4ERR_NOTSUPP to the originating SETATTR.

The metadata server knows encoding geometry from the layout but
is not required to include an encoding implementation.  The
delegation rule above accommodates a metadata server that has
geometry knowledge only.

### PASSTHROUGH Data Files (FFV2_ENCODING_PASSTHROUGH)

For a mirror whose ffv2m_coding_type_data is
FFV2_ENCODING_PASSTHROUGH (see {{sec-encoding-passthrough}}),
client operations on the data file follow the same pattern as
the File Layout Type in {{RFC8881}} Section 13.6 and the
Flexible File Version 1 Layout Type in {{RFC8435}}:

Required:

-  READ ({{RFC8881}} Section 18.22).
-  WRITE ({{RFC8881}} Section 18.32).
-  COMMIT ({{RFC8881}} Section 18.3).

Optional (the client MAY send, and the data server MAY support):

-  READ_PLUS ({{RFC7862}} Section 15.10): hole-aware reads.
-  SEEK ({{RFC7862}} Section 15.11): hole and data detection.
-  ALLOCATE ({{RFC7862}} Section 15.1): space reservation hint.

The client MUST NOT send:

-  DEALLOCATE ({{RFC7862}} Section 15.4): hole punching is a
   metadata-server responsibility; the client issues DEALLOCATE
   on the metadata-server filehandle, and the metadata server
   fans out to the data servers as a control-plane operation.

### Chunked Data Files

For a mirror whose ffv2m_coding_type_data is any of the chunked
encoding types defined in this document -- i.e., every
FFV2_ENCODING_* value except FFV2_ENCODING_PASSTHROUGH (see
{{sec-encoding-passthrough}}) -- client operations use the
CHUNK operations rather than READ / WRITE / COMMIT.  This
includes FFV2_ENCODING_MIRRORED despite its name: the "mirrored"
refers to the encoding's verbatim payload replication, not to
the wire dispatch (see {{tbl-ops-allowed}} legend).

Required for all chunked clients:

-  CHUNK_WRITE ({{sec-CHUNK_WRITE}}).
-  CHUNK_READ ({{sec-CHUNK_READ}}).
-  CHUNK_FINALIZE ({{sec-CHUNK_FINALIZE}}).
-  CHUNK_COMMIT ({{sec-CHUNK_COMMIT}}).
-  CHUNK_HEADER_READ ({{sec-CHUNK_HEADER_READ}}).
-  CHUNK_LOCK ({{sec-CHUNK_LOCK}}) and CHUNK_UNLOCK
   ({{sec-CHUNK_UNLOCK}}).
-  CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}}).

Required for clients that participate in repair:

-  CHUNK_ERROR ({{sec-CHUNK_ERROR}}).
-  CHUNK_REPAIRED ({{sec-CHUNK_REPAIRED}}).
-  CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}).

Clients MUST NOT send:

-  READ, WRITE, COMMIT against a chunked data file.  A
   data server MUST reject these with NFS4ERR_NOTSUPP and MAY
   log the client for operator attention; this case is almost
   always a client bug in which the client did not inspect the
   mirror's ffv2m_coding_type_data before issuing I/O.
-  READ_PLUS, SEEK, ALLOCATE, DEALLOCATE against a chunked
   data file.  Chunk-level allocation is a metadata-server
   responsibility.
-  SETATTR against a chunked data file (the general
   prohibition in {{sec-setattr-on-data-file}} applies to all
   data files; truncate in particular is handled by the
   metadata server per {{sec-mds-truncate-ec}}).

### Operations That MUST NOT Be Sent to a Data File

Clients MUST NOT send the following operations to a data server
on a data file, regardless of protection mode.  A data server
that has identified the file as a chunked data file (see
{{sec-data-file-identification}}) MUST return NFS4ERR_NOTSUPP:

-  OPEN, CLOSE, OPEN_DOWNGRADE, OPEN_CONFIRM ({{RFC8881}}
   Sections 18.16, 18.2, 18.18, 18.20).  Opens occur on the
   metadata server; the stateid obtained there is used on the
   data path.
-  LOCK, LOCKU, LOCKT, RELEASE_LOCKOWNER ({{RFC8881}} Sections
   18.10, 18.11, 18.13, 18.24).  Byte-range locks on data files
   are not supported; chunked files use CHUNK_LOCK, and
   PASSTHROUGH files rely on metadata-server coordination.
-  DELEGPURGE, DELEGRETURN, WANT_DELEGATION ({{RFC8881}} Sections
   18.5, 18.6 and {{RFC7862}} Section 15.3).  Delegations are
   issued by the metadata server.
-  Any operation whose purpose is to manipulate the file's
   namespace: RENAME, LINK, SYMLINK, CREATE (at the client's
   file-creation use, not the metadata server's own
   allocation of data files on the data server described
   above), REMOVE.  Namespace
   operations belong on the metadata server.
-  Any ACL-scoped SETATTR or GETATTR bit (FATTR4_ACL,
   FATTR4_DACL, FATTR4_SACL).  Access control on data files is
   delegated to the metadata server.
-  CLONE, COPY, COPY_NOTIFY, OFFLOAD_CANCEL, OFFLOAD_STATUS
   ({{RFC7862}} Sections 15.13, 15.2, 15.3, 15.8, 15.9).
   File-level data migration is a metadata-server responsibility.
-  LAYOUTGET, LAYOUTCOMMIT, LAYOUTRETURN, LAYOUTSTATS,
   LAYOUTERROR, GETDEVICEINFO, GETDEVICELIST ({{RFC8881}}
   Sections 18.43, 18.42, 18.44, {{RFC7862}} Sections 15.7,
   15.6, {{RFC8881}} Sections 18.40, 18.41).  Layout operations
   belong on the metadata server.
-  TRUST_STATEID, REVOKE_STATEID, BULK_REVOKE_STATEID
   ({{sec-TRUST_STATEID}}, {{sec-REVOKE_STATEID}},
   {{sec-BULK_REVOKE_STATEID}}).  These are metadata-server-to-data-server
   control-plane operations; a data server rejects them with
   NFS4ERR_PERM when received on a client session (see
   {{sec-tight-coupling-control-session}}).

##  Callback Path: Data Server to Client

A data server does not call back directly to pNFS clients.
Recall notifications and repair coordination flow through the
metadata server's backchannel session with the client.  The
callbacks a client will observe that affect its data files are:

-  CB_LAYOUTRECALL ({{RFC8881}} Section 20.3).
-  CB_NOTIFY_DEVICEID ({{RFC8881}} Section 20.12).
-  CB_RECALL_ANY ({{RFC8881}} Section 20.6).
-  CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}).

A data server influences these callbacks only indirectly, via
LAYOUTERROR reports the client issues to the metadata server or
by returning error codes that prompt the client to report.  A
data server MUST NOT attempt to send CB_* operations to clients
directly.

##  Summary Table

The classification below adapts the operation taxonomy of
{{RFC8881}} Section 17 (REQUIRED / RECOMMENDED / OPTIONAL /
MUST NOT IMPLEMENT) to the two-direction per-operation view a
Flexible File Version 2 data server requires.  Two of the four
labels in the table below match {{RFC8881}} usage; the other
two are extensions specific to this document.

REQUIRED:
:  The data server MUST support the operation on this path.
   Matches {{RFC8881}} Section 17 REQ.

OPTIONAL:
:  The data server MAY support the operation; if it does, the
   actor in this column MUST tolerate the absence of support.
   Matches {{RFC8881}} Section 17 OPT.

MUST NOT:
:  The actor in this column MUST NOT send the operation, and
   the data server MUST reject it with NFS4ERR_NOTSUPP.  This
   per-direction prohibition extends {{RFC8881}} Section 17's
   single-axis MUST NOT IMPLEMENT classification: an operation
   may be forbidden on one path (client to data server) while
   required on another (metadata server to data server).
   SETATTR is the canonical example.

MAY:
:  The metadata server MAY use the operation as an
   implementation-defined control-plane action.  Not in
   {{RFC8881}} Section 17; specific to the metadata-server-to-data-server
   path in this document.

 | Operation                        | Client -> data server                | metadata server -> data server          |
 | ---
 | SEQUENCE, PUTFH, GETFH, PUTROOTFH | REQUIRED                   | REQUIRED           |
 | EXCHANGE_ID, CREATE_SESSION, DESTROY_SESSION, BIND_CONN_TO_SESSION, DESTROY_CLIENTID | REQUIRED | REQUIRED  |
 | RECLAIM_COMPLETE                  | REQUIRED                   | REQUIRED           |
 | SECINFO, SECINFO_NO_NAME          | REQUIRED                   | MAY                |
 | GETATTR                           | OPTIONAL (non-authoritative) | REQUIRED         |
 | SETATTR                           | MUST NOT                   | REQUIRED           |
 | LOOKUP, CREATE, REMOVE            | MUST NOT                   | REQUIRED           |
 | READ, WRITE, COMMIT               | REQUIRED (PASSTHROUGH); MUST NOT (chunked) | MAY |
 | READ_PLUS, SEEK, ALLOCATE         | OPTIONAL (PASSTHROUGH); MUST NOT (chunked) | MAY |
 | DEALLOCATE                        | MUST NOT                   | MAY                |
 | CHUNK_WRITE, CHUNK_READ, CHUNK_FINALIZE, CHUNK_COMMIT, CHUNK_HEADER_READ, CHUNK_LOCK, CHUNK_UNLOCK, CHUNK_ROLLBACK | REQUIRED (chunked); MUST NOT (PASSTHROUGH) | not used |
 | CHUNK_ERROR, CHUNK_REPAIRED, CHUNK_WRITE_REPAIR | REQUIRED (chunked repair actors); MUST NOT (PASSTHROUGH) | not used |
 | OPEN, CLOSE, OPEN_DOWNGRADE, OPEN_CONFIRM | MUST NOT           | OPTIONAL (proxy I/O) |
 | LOCK, LOCKU, LOCKT, RELEASE_LOCKOWNER | MUST NOT               | MUST NOT           |
 | DELEGPURGE, DELEGRETURN, WANT_DELEGATION | MUST NOT            | MUST NOT           |
 | RENAME, LINK, SYMLINK             | MUST NOT                   | MUST NOT           |
 | CLONE, COPY, COPY_NOTIFY, OFFLOAD_CANCEL, OFFLOAD_STATUS | MUST NOT | MAY (data migration) |
 | LAYOUTGET, LAYOUTCOMMIT, LAYOUTRETURN, LAYOUTSTATS, LAYOUTERROR, GETDEVICEINFO, GETDEVICELIST | MUST NOT | MUST NOT |
 | ACL-scoped GETATTR/SETATTR bits   | MUST NOT                   | MAY                |
 | TRUST_STATEID, REVOKE_STATEID, BULK_REVOKE_STATEID | MUST NOT  | REQUIRED (tight coupling) |
 | CHUNK_ESCROW_INSTALL, CHUNK_ESCROW_RELEASE, CHUNK_ESCROW_ENUMERATE, CHUNK_ESCROW_TAKEOVER | MUST NOT | REQUIRED |
{: #tbl-ops-allowed title="NFSv4.2 operations allowed on data files"}

The (PASSTHROUGH) and (chunked) qualifiers in the client-to-data-server
column select by the mirror's ffv2m_coding_type_data value.
FFV2_ENCODING_PASSTHROUGH ({{sec-encoding-passthrough}}) uses
NFSv3 WRITE / READ or NFSv4 READ / WRITE directly and does not
use the CHUNK operations.  Every other standards-track encoding
(any FFV2_ENCODING_* value other than FFV2_ENCODING_PASSTHROUGH;
see {{tbl-coding-types}}) is (chunked): it uses CHUNK_WRITE
({{sec-CHUNK_WRITE}}) and CHUNK_READ ({{sec-CHUNK_READ}}) and
MUST NOT use the RFC 8881 READ / WRITE / COMMIT operations
against the data server.  FFV2_ENCODING_MIRRORED is (chunked)
despite its name -- the "mirrored" refers to the encoding's
verbatim replication of the payload, not to the wire dispatch;
it uses the CHUNK operations for the per-chunk checksum this
version of the layout type relies on for end-to-end integrity
({{sec-encoding-mirrored}}).


#  Flexible File Version 2 Layout Type Return {#sec-layouthint}

layoutreturn_file4 is used in the LAYOUTRETURN operation to convey
layout type specific information to the server.  It is defined in
Section 18.44.1 of {{RFC8881}} (also shown in {{fig-LAYOUTRETURN}}).

~~~ xdr
      /* Constants used for LAYOUTRETURN and CB_LAYOUTRECALL */
      const LAYOUT4_RET_REC_FILE      = 1;
      const LAYOUT4_RET_REC_FSID      = 2;
      const LAYOUT4_RET_REC_ALL       = 3;

      enum layoutreturn_type4 {
              LAYOUTRETURN4_FILE = LAYOUT4_RET_REC_FILE,
              LAYOUTRETURN4_FSID = LAYOUT4_RET_REC_FSID,
              LAYOUTRETURN4_ALL  = LAYOUT4_RET_REC_ALL
      };

   struct layoutreturn_file4 {
           offset4         lrf_offset;
           length4         lrf_length;
           stateid4        lrf_stateid;
           /* layouttype4 specific data */
           opaque          lrf_body<>;
   };

   union layoutreturn4 switch(layoutreturn_type4 lr_returntype) {
           case LAYOUTRETURN4_FILE:
                   layoutreturn_file4      lr_layout;
           default:
                   void;
   };

   struct LAYOUTRETURN4args {
           /* CURRENT_FH: file */
           bool                    lora_reclaim;
           layouttype4             lora_layout_type;
           layoutiomode4           lora_iomode;
           layoutreturn4           lora_layoutreturn;
   };
~~~
{: #fig-LAYOUTRETURN title="Layout Return XDR"}

If the lora_layout_type layout type is LAYOUT4_FLEX_FILES_V2 and the
lr_returntype is LAYOUTRETURN4_FILE, then the lrf_body opaque value
is defined by ffv2_layoutreturn4 (see {{sec-ffv2_layoutreturn4}}).  This
allows the client to report I/O error information or layout usage
statistics back to the metadata server as defined below.  Note that
while the data structures are built on concepts introduced in
NFSv4.2, the effective discriminated union (lora_layout_type combined
with ffv2_layoutreturn4) allows for an NFSv4.1 metadata server to
utilize the data.

##  I/O Error Reporting {#sec-io-error}

###  ffv2_ioerr4 {#sec-ffv2_ioerr4}

~~~ xdr
   /// struct ffv2_ioerr4 {
   ///         offset4        ffv2ie_offset;
   ///         length4        ffv2ie_length;
   ///         stateid4       ffv2ie_stateid;
   ///         device_error4  ffv2ie_errors<>;
   /// };
   ///
~~~
{: #fig-ffv2_ioerr4 title="ffv2_ioerr4"}

Recall that {{RFC7862}} defines device_error4 as in {{fig-device_error4}}:

~~~ xdr
   struct device_error4 {
           deviceid4       de_deviceid;
           nfsstat4        de_status;
           nfs_opnum4      de_opnum;
   };
~~~
{: #fig-device_error4 title="device_error4"}

The ffv2_ioerr4 structure is used to return error indications for
data files that generated errors during data transfers.  These are
hints to the metadata server that there are problems with that file.
For each error, ffv2ie_errors.de_deviceid, ffv2ie_offset, and ffv2ie_length
represent the storage device and byte range within the file in which
the error occurred; ffv2ie_errors represents the operation and type
of error.  The use of device_error4 is described in Section 15.6
of {{RFC7862}}.

Even though the storage device might be accessed via NFSv3 and
reports back NFSv3 errors to the client, the client is responsible
for mapping these to appropriate NFSv4 status codes as de_status.
Likewise, the NFSv3 operations need to be mapped to equivalent NFSv4
operations.

##  Layout Usage Statistics {#sec-layout-stats}

###  ff_io_latency4

~~~ xdr
   /// struct ffv2_io_latency4 {
   ///         uint64_t       ffv2il_ops_requested;
   ///         uint64_t       ffv2il_bytes_requested;
   ///         uint64_t       ffv2il_ops_completed;
   ///         uint64_t       ffv2il_bytes_completed;
   ///         uint64_t       ffv2il_bytes_not_delivered;
   ///         nfstime4       ffv2il_total_busy_time;
   ///         nfstime4       ffv2il_aggregate_completion_time;
   /// };
   ///
~~~
{: #fig-ff_io_latency4 title="ff_io_latency4"}

Both operation counts and bytes transferred are kept in the
ff_io_latency4 (see {{fig-ff_io_latency4}}).  As seen in ff_layoutupdate4
(see {{sec-ff_layoutupdate4}}), READ and WRITE operations are
aggregated separately.  READ operations are used for the ff_io_latency4
ffv2l_read.  Both WRITE and COMMIT operations are used for the
ff_io_latency4 ffv2l_write.  "Requested" counters track what the
client is attempting to do, and "completed" counters track what was
done.  There is no requirement that the client only report completed
results that have matching requested results from the reported
period.

ffv2il_bytes_not_delivered is used to track the aggregate number of
bytes requested but not fulfilled due to error conditions.
ffv2il_total_busy_time is the aggregate time spent with outstanding
RPC calls. ffv2il_aggregate_completion_time is the sum of all round-trip
times for completed RPC calls.

In Section 3.3.1 of {{RFC8881}}, the nfstime4 is defined as the
number of seconds and nanoseconds since midnight or zero hour January
1, 1970 Coordinated Universal Time (UTC).  The use of nfstime4 in
ff_io_latency4 is to store time since the start of the first I/O
from the client after receiving the layout.  In other words, these
are to be decoded as duration and not as a date and time.

Note that LAYOUTSTATS are cumulative, i.e., not reset each time the
operation is sent.  If two LAYOUTSTATS operations for the same file
and layout stateid originate from the same NFS client and are
processed at the same time by the metadata server, then the one
containing the larger values contains the most recent time series
data.

###  ff_layoutupdate4 {#sec-ff_layoutupdate4}

~~~ xdr
   /// struct ffv2_layoutupdate4 {
   ///         netaddr4         ffv2l_addr;
   ///         nfs_fh4          ffv2l_fhandle;
   ///         ffv2_io_latency4 ffv2l_read;
   ///         ffv2_io_latency4 ffv2l_write;
   ///         nfstime4         ffv2l_duration;
   ///         bool             ffv2l_local;
   /// };
   ///
~~~
{: #fig-ff_layoutupdate4 title="ff_layoutupdate4"}

ffv2l_addr differentiates which network address the client is connected
to on the storage device.  In the case of multipathing, ffv2l_fhandle
indicates which read-only copy was selected. ffv2l_read and ffv2l_write
convey the latencies for both READ and WRITE operations, respectively.
ffv2l_duration is used to indicate the time period over which the
statistics were collected.  If true, ffv2l_local indicates that the
I/O was serviced by the client's cache.  This flag allows the client
to inform the metadata server about "hot" access to a file it would
not normally be allowed to report on.

###  ff_iostats4

~~~ xdr
   /// struct ffv2_iostats4 {
   ///         offset4            ffv2is_offset;
   ///         length4            ffv2is_length;
   ///         stateid4           ffv2is_stateid;
   ///         io_info4           ffv2is_read;
   ///         io_info4           ffv2is_write;
   ///         deviceid4          ffv2is_deviceid;
   ///         ffv2_layoutupdate4 ffv2is_layoutupdate;
   /// };
   ///
~~~
{: #fig-ff_iostats4 title="ff_iostats4"}

{{RFC7862}} defines io_info4 as in {{fig-ff_iostats4}}.

~~~ xdr
   struct io_info4 {
           uint64_t        ii_count;
           uint64_t        ii_bytes;
   };
~~~
{: #fig-io_info4 title="io_info4"}

With pNFS, data transfers are performed directly between the pNFS
client and the storage devices.  Therefore, the metadata server has
no direct knowledge of the I/O operations being done and thus cannot
create on its own statistical information about client I/O to
optimize the data storage location.  ff_iostats4 MAY be used by the
client to report I/O statistics back to the metadata server upon
returning the layout.

Since it is not feasible for the client to report every I/O that
used the layout, the client MAY identify "hot" byte ranges for which
to report I/O statistics.  The definition and/or configuration
mechanism of what is considered "hot" and the size of the reported
byte range are out of the scope of this document.  For client
implementation, providing reasonable default values and an optional
run-time management interface to control these parameters is
suggested.  For example, a client can define the default byte range
resolution to be 1 MB in size and the thresholds for reporting to
be 1 MB/second or 10 I/O operations per second.

For each byte range, ffv2is_offset and ffv2is_length represent the
starting offset of the range and the range length in bytes.
ffv2is_read.ii_count, ffv2is_read.ii_bytes, ffv2is_write.ii_count, and
ffv2is_write.ii_bytes represent the number of contiguous READ and
WRITE I/Os and the respective aggregate number of bytes transferred
within the reported byte range.

The combination of ffv2is_deviceid and ffv2l_addr uniquely identifies
both the storage path and the network route to it.  Finally,
ffv2l_fhandle allows the metadata server to differentiate between
multiple read-only copies of the file on the same storage device.

##  ffv2_layoutreturn4 {#sec-ffv2_layoutreturn4}

~~~ xdr
   /// struct ffv2_layoutreturn4 {
   ///         ffv2_ioerr4     ffv2lr_ioerr_report<>;
   ///         ffv2_iostats4   ffv2lr_iostats_report<>;
   /// };
   ///
~~~
{: #fig-ffv2_layoutreturn4 title="ffv2_layoutreturn4"}

When data file I/O operations fail, ffv2lr_ioerr_report<> is used to
report these errors to the metadata server as an array of elements
of type ffv2_ioerr4.  Each element in the array represents an error
that occurred on the data file identified by ffv2ie_errors.de_deviceid.
If no errors are to be reported, the size of the ffv2lr_ioerr_report<>
array is set to zero.  The client MAY also use ffv2lr_iostats_report<>
to report a list of I/O statistics as an array of elements of type
ff_iostats4.  Each element in the array represents statistics for
a particular byte range.  Byte ranges are not guaranteed to be
disjoint and MAY repeat or intersect.

#  Flexible File Version 2 Layout Type LAYOUTERROR {#sec-LAYOUTERROR}

If the client is using NFSv4.2 to communicate with the metadata
server, then instead of waiting for a LAYOUTRETURN to send error
information to the metadata server (see {{sec-io-error}}), it MAY
use LAYOUTERROR (see Section 15.6 of {{RFC7862}}) to communicate
that information.  For the flexible file v2 layout, this means
that LAYOUTERROR4args is treated the same as ffv2_ioerr4.

#  Flexible File Version 2 Layout Type LAYOUTSTATS

If the client is using NFSv4.2 to communicate with the metadata
server, then instead of waiting for a LAYOUTRETURN to send I/O
statistics to the metadata server (see {{sec-layout-stats}}), it
MAY use LAYOUTSTATS (see Section 15.7 of {{RFC7862}}) to communicate
that information.  For the flexible file v2 layout, this means
that LAYOUTSTATS4args.lsa_layoutupdate is overloaded with the same
contents as in ffv2is_layoutupdate.

#  Flexible File Version 2 Layout Type Creation Hint

The layouthint4 type is defined in the {{RFC8881}} as in
{{fig-layouthint4-v1}}.

~~~ xdr
   struct layouthint4 {
       layouttype4        loh_type;
       opaque             loh_body<>;
   };
~~~
{: #fig-layouthint4-v1 title="layouthint4 v1"}

                              {{fig-layouthint4-v1}}

The layouthint4 structure is used by the client to pass a hint about
the type of layout it would like created for a particular file.  If
the loh_type layout type is LAYOUT4_FLEX_FILES, then the loh_body
opaque value is defined by the ff_layouthint4 type (v1
compatibility).  If the loh_type layout type is
LAYOUT4_FLEX_FILES_V2, then the loh_body opaque value is defined
by the ffv2_layouthint4 type (see {{sec-ffv2-layouthint}}).

#  ff_layouthint4

~~~ xdr
   union ff_mirrors_hint switch (bool ffmc_valid) {
       case TRUE:
           uint32_t    ffmc_mirrors;
       case FALSE:
           void;
   };

   struct ff_layouthint4 {
       ff_mirrors_hint    fflh_mirrors_hint;
   };
~~~
{: #fig-ff_layouthint4-v2 title="ff_layouthint4 (v1 compatibility)"}

The ff_layouthint4 is retained for backwards compatibility with
flexible file v1 layouts.  For flexible file v2 layouts, clients
SHOULD use ffv2_layouthint4 ({{fig-ffv2_layouthint4}}) instead,
which provides encoding type selection and data protection geometry
hints via ffv2_data_protection4 ({{fig-ffv2_data_protection4}}).

#  Recalling a Layout

While Section 12.5.5 of {{RFC8881}} discusses reasons independent
of layout type for recalling a layout, the flexible file v2 layout
type metadata server should recall outstanding layouts in the
following cases:

-  When the file's security policy changes, i.e., ACLs or permission
   mode bits are set.

-  When the file's layout changes, rendering outstanding layouts
   invalid.

-  When existing layouts are inconsistent with the need to enforce
   locking constraints.

-  When existing layouts are inconsistent with the requirements
   regarding resilvering as described in {{sec-mds-resilvering}}.

##  CB_RECALL_ANY

The metadata server can use the CB_RECALL_ANY callback operation
to notify the client to return some or all of its layouts.  Section
22.3 of {{RFC8881}} defines the allowed types of the "NFSv4 Recallable
Object Types Registry".

~~~ xdr
   /// const RCA4_TYPE_MASK_FF2_LAYOUT_MIN     = 20;
   /// const RCA4_TYPE_MASK_FF2_LAYOUT_MAX     = 21;
   ///
~~~
{: #fig-new-rca4 title="RCA4 masks for v2"}

~~~ xdr
   struct  CB_RECALL_ANY4args      {
       uint32_t        craa_layouts_to_keep;
       bitmap4         craa_type_mask;
   };
~~~
{: #fig-CB_RECALL_ANY4args title="CB_RECALL_ANY4args XDR"}

Typically, CB_RECALL_ANY will be used to recall client state when
the server needs to reclaim resources.  The craa_type_mask bitmap
specifies the type of resources that are recalled, and the
craa_layouts_to_keep value specifies how many of the recalled
flexible file v2 layouts the client is allowed to keep.  The mask flags
for the flexible file v2 layout are defined as in {{fig-mask-flags}}.

~~~ xdr
   /// enum ffv2_cb_recall_any_mask {
   ///     PNFS_FF_RCA4_TYPE_MASK_READ = 20,
   ///     PNFS_FF_RCA4_TYPE_MASK_RW   = 21
   /// };
   ///
~~~
{: #fig-mask-flags title="Recall Mask Flags for v2"}

The flags represent the iomode of the recalled layouts.  In response,
the client SHOULD return layouts of the recalled iomode that it
needs the least, keeping at most craa_layouts_to_keep flexible file
layouts.

The PNFS_FF_RCA4_TYPE_MASK_READ flag notifies the client to return
layouts of iomode LAYOUTIOMODE4_READ.  Similarly, the
PNFS_FF_RCA4_TYPE_MASK_RW flag notifies the client to return layouts
of iomode LAYOUTIOMODE4_RW.  When both mask flags are set, the
client is notified to return layouts of either iomode.

#  Layout Revocation and Fencing

In cases where clients are uncommunicative and their lease has
expired, or when clients fail to return recalled layouts within
a lease period, the metadata server MAY revoke client layouts
and reassign these resources to other clients (see Section
12.5.5 of {{RFC8881}}).  To avoid data corruption from a
revoked client continuing to issue I/O, the metadata server
MUST fence the revoked client from the affected data files.
The mechanism varies by coupling model and by whether the
client's layout stateid has been registered with the data
servers via TRUST_STATEID:

Loosely coupled, untrusted stateid:
:  The metadata server rotates the synthetic uid/gid on the
   affected data files per {{sec-Fencing-Clients}}.  The
   revoked client presents stale RPC credentials and receives
   NFS4ERR_ACCESS from the data server.  This is the
   flexible-file-v1-layout-style fencing mechanism; it operates
   per data file and
   does not distinguish between clients that hold layouts on
   the same file.

Tightly coupled, trusted stateid:
:  When the metadata server has registered a client's layout
   stateid with the data servers via TRUST_STATEID
   ({{sec-TRUST_STATEID}}), it can revoke per-client access
   without rotating credentials by issuing REVOKE_STATEID
   ({{sec-REVOKE_STATEID}}) to each affected data server, or
   BULK_REVOKE_STATEID ({{sec-BULK_REVOKE_STATEID}}) when
   revoking all stateids belonging to a single clientid4
   across a data server.  Subsequent I/O from the revoked
   client carrying the revoked stateid receives
   NFS4ERR_BAD_STATEID.  This is the preferred mechanism for
   chunked layouts because it is per-client and avoids the
   flexible file v1 layout's limitation of fencing all clients
   on a data file when only one needs to be revoked.

Mixed:
:  A metadata server MAY combine the two mechanisms when a
   file's layout includes both PASSTHROUGH mirrors (where
   stateid registration is not in play) and chunked mirrors
   with trusted stateids.  The metadata server rotates
   synthetic ids for the PASSTHROUGH mirror's data file and
   issues REVOKE_STATEID for the chunked mirror's data
   servers.

#  New NFSv4.2 Error Values

~~~ xdr
   ///
   /// /* Erasure Coding error constants; added to nfsstat4 enum */
   ///
   /// const NFS4ERR_CODING_NOT_SUPPORTED         = 10097;
   /// const NFS4ERR_PAYLOAD_NOT_ATOMIC           = 10098;
   /// const NFS4ERR_CHUNK_LOCKED                 = 10099;
   /// const NFS4ERR_CHUNK_GUARDED                = 10100;
   /// const NFS4ERR_PAYLOAD_LOST                 = 10101;
   /// const NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED = 10102;
   /// const NFS4ERR_NO_PREDECESSOR               = 10103;
   /// const NFS4ERR_NO_ADOPTABLE_LOCK            = 10104;
   /// const NFS4ERR_STALE_ESCROW                 = 10105;
   /// const NFS4ERR_STALE_MDS_EPOCH              = 10106;
   /// /* NFS4ERR_PARTIAL numeric TBD at draft-edit time
   ///    (collision scan against the current nfsstat4
   ///    range required before publication). */
   /// const NFS4ERR_PARTIAL                      = 10107;
   ///
~~~
{: #fig-errors-xdr title="Errors XDR" }

The new error codes are shown in {{fig-errors-xdr}}.

## Error Definitions

 | Error                          | Number | Description   |
 |---
 | NFS4ERR_CODING_NOT_SUPPORTED   | 10097  | {{sec-NFS4ERR_CODING_NOT_SUPPORTED}} |
 | NFS4ERR_PAYLOAD_NOT_ATOMIC | 10098  | {{sec-NFS4ERR_PAYLOAD_NOT_ATOMIC}} |
 | NFS4ERR_CHUNK_LOCKED | 10099  | {{sec-NFS4ERR_CHUNK_LOCKED}} |
 | NFS4ERR_CHUNK_GUARDED | 10100  | {{sec-NFS4ERR_CHUNK_GUARDED}} |
 | NFS4ERR_PAYLOAD_LOST | 10101  | {{sec-NFS4ERR_PAYLOAD_LOST}} |
 | NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED | 10102 | {{sec-NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED}} |
 | NFS4ERR_NO_PREDECESSOR | 10103 | {{sec-NFS4ERR_NO_PREDECESSOR}} |
 | NFS4ERR_NO_ADOPTABLE_LOCK | 10104 | {{sec-NFS4ERR_NO_ADOPTABLE_LOCK}} |
 | NFS4ERR_STALE_ESCROW | 10105 | {{sec-NFS4ERR_STALE_ESCROW}} |
 | NFS4ERR_STALE_MDS_EPOCH | 10106 | {{sec-NFS4ERR_STALE_MDS_EPOCH}} |
 | NFS4ERR_PARTIAL | 10107 | {{sec-NFS4ERR_PARTIAL}} |
{: #tbl-protocol-errors title="Error Definitions"}

### NFS4ERR_CODING_NOT_SUPPORTED (Error Code 10097) {#sec-NFS4ERR_CODING_NOT_SUPPORTED}

The client requested a ffv2_encoding_type4 which the metadata server
does not support.  I.e., if the client sends a layout_hint requesting
an erasure encoding type that the metadata server does not support,
this error code can be returned.  The client might have to send the
layout_hint several times to determine the overlapping set of
supported erasure encoding types.

### NFS4ERR_PAYLOAD_NOT_ATOMIC (Error Code 10098) {#sec-NFS4ERR_PAYLOAD_NOT_ATOMIC}

The client encountered a payload in which the blocks were non-atomic
and stay non-atomic.  As the client can not tell if another
client is actively writing, it informs the metadata server of this
error via LAYOUTERROR.  The metadata server can then arrange for
repair of the file.

### NFS4ERR_CHUNK_LOCKED (Error Code 10099) {#sec-NFS4ERR_CHUNK_LOCKED}

The client tried an operation on a chunk which resulted in the data
server reporting that the chunk was locked. The client will then
inform the metadata server of this error via LAYOUTERROR.  The
metadata server can then arrange for repair of the file.

### NFS4ERR_CHUNK_GUARDED (Error Code 10100) {#sec-NFS4ERR_CHUNK_GUARDED}

The client tried a guarded CHUNK_WRITE on a chunk which did not match
the guard on the chunk in the data file. As such, the CHUNK_WRITE was
rejected and the client should refresh the chunk it has cached.

### NFS4ERR_PAYLOAD_LOST (Error Code 10101) {#sec-NFS4ERR_PAYLOAD_LOST}

Returned by a repair actor on the CB_CHUNK_REPAIR response
(ccrr_status) to indicate that the identified ranges cannot be
repaired and the underlying data is no longer recoverable.
Causes include: too few surviving shards to meet the
reconstruction threshold (Katz criterion for Mojette, any
k-of-(k+m) subset for Reed-Solomon Vandermonde), inability to
roll back to a previously committed payload because that payload
is also lost, or exhaustion of all FFV2_DS_FLAGS_REPAIR data
servers available in the layout with no additional replacement
reachable from the metadata server's out-of-band pool.

On receipt, the metadata server MUST NOT retry the repair by
selecting a different client -- the payload is damaged and the
metadata server transitions the affected file or byte range into
an implementation-defined damaged state.  Operator notification
and restore-from-snapshot are out of scope for this specification.

NFS4ERR_PAYLOAD_LOST is distinct from NFS4ERR_DELAY (transient;
metadata server MAY extend the deadline or re-select) and from
NFS4ERR_IO (per-operation failure; metadata server MAY retry or
re-select).  Only NFS4ERR_PAYLOAD_LOST is terminal.

### NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED (Error Code 10102) {#sec-NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED}

Returned by the client on LAYOUTRETURN to indicate that the
layout's ffv2m_checksum_algorithm
({{sec-ffv2-mirror4}}) names a checksum_algorithm4
({{sec-checksum4}}) that the client does not implement.
The client returns the layout with this error code rather
than attempting CHUNK operations it cannot validate.

On receipt, the metadata server MAY:

-  issue a new layout for the same file naming a different
   checksum_algorithm4 that the client supports (if the
   file's policy permits any of the algorithms the client
   does support); or

-  deny the layout request, in which case the client MUST
   either fall back to metadata-server-mediated I/O or report an I/O
   error to the application.

NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED is distinct from
NFS4ERR_BADLAYOUT (generic "this layout shape is unusable"):
the explicit per-checksum-algorithm signal lets the metadata
server discriminate "client can't read this layout because
of the checksum algorithm" from "client can't read this
layout for some other reason" and respond accordingly.

### NFS4ERR_NO_PREDECESSOR (Error Code 10103) {#sec-NFS4ERR_NO_PREDECESSOR}

Returned on a CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}})
against a COMMITTED chunk when the caller names a
predecessor generation whose owner-to-index association
is no longer recorded by the data server, and no other
per-entry error covers the situation.  This is the "no
restorable predecessor" outcome of the restore case
described under "Rollback of COMMITTED Chunks": the
predecessor's payload+association pair was released some
time earlier under the retention scope rule
({{sec-system-model-retention-scope}}) -- by lease expiry,
by an earlier CHUNK_ROLLBACK delete case, or by any
other terminal transition -- and the data server cannot
restore what it no longer holds.

NFS4ERR_NO_PREDECESSOR is a per-entry status (a caller
that names several generations in a single
CHUNK_ROLLBACK MAY receive NFS4ERR_NO_PREDECESSOR on
some slots and NFS4_OK or other per-entry errors on
others).  It is a data-plane result, NOT a
control-plane failure: the caller reached the data
server successfully, was authorized, and the operation
evaluated normally -- the named predecessor simply
does not exist to restore.

NFS4ERR_NO_PREDECESSOR is distinct from NFS4ERR_INVAL
(the triple was invalidated by an explicit delete case
and cannot be resurrected -- see "Deletion Atomicity and
Invalidated Triples") and from NFS4ERR_PAYLOAD_LOST
(terminal payload loss reported on CB_CHUNK_REPAIR).
The data server distinguishes NFS4ERR_NO_PREDECESSOR
from NFS4ERR_INVAL on the basis of what the data server
can concretely observe about the presented triple, NOT
on historical knowledge the data server may no longer
retain:

NFS4ERR_INVAL:

: returned in exactly the cases where the data server can
  concretely recognize the presented triple as invalid:
  (a) **structurally invalid**: the triple is
      malformed or truncated, or names a different
      file or a different data server; or
  (b) **within-window release**: a prior explicit
      CHUNK_ROLLBACK delete case released the
      association and the current request falls
      within the same session slot's replay-cache
      window of that CHUNK_ROLLBACK, so the data
      server still holds the concrete invalidation
      context that identifies this triple as
      released-by-delete-case.

NFS4ERR_NO_PREDECESSOR:

: covers every other case in which the data server holds no
  association for the presented triple, including:
  (a) release under the retention scope rule (lease
      expiry, storage-pressure release);
  (b) the eventual release of a triple invalidated
      by an earlier delete case whose replay-cache
      window has since elapsed; and
  (c) a well-formed triple for this file and this
      data server for which the data server holds no
      surviving record and no concrete invalidation
      context.

An implementation following the no-tombstone model
cannot distinguish "the data server never recorded
this triple" from "the data server recorded and later
released this triple" outside a live invalidation
context, and this specification does not require it
to: both cases resolve to NFS4ERR_NO_PREDECESSOR under
(c) above.  The two errors are
not interchangeable: NFS4ERR_INVAL is a caller-side
signal that the client MUST NOT retry the same
identity, while NFS4ERR_NO_PREDECESSOR is a data-plane
signal that the caller MAY fall back to
best-effort reconstruction via CHUNK_WRITE_REPAIR
({{sec-CHUNK_WRITE_REPAIR}}).

A client that receives NFS4ERR_NO_PREDECESSOR MAY fall
back to reconstructing authoritative bytes from
surviving shards and writing them via
CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}) under a
new owner triple; that fallback is best-effort and
MAY itself terminate at NFS4ERR_PAYLOAD_LOST if no
authoritative source exists.  A client that requires
the restored generation to retain the predecessor's
original owner triple in cases where the retention
scope ({{sec-system-model-retention-scope}}) would
otherwise permit release MUST use the metadata-server escrow
control plane ({{sec-CHUNK_ESCROW_INSTALL}}
through {{sec-CHUNK_ESCROW_TAKEOVER}}), which pins
the predecessor's payload and its owner-to-index
association jointly against that release rule for as
long as the escrow-lock or a client-owned lock
adopted from it remains in continuous custody (see
{{sec-composed-rollback}}).

### NFS4ERR_NO_ADOPTABLE_LOCK (Error Code 10104) {#sec-NFS4ERR_NO_ADOPTABLE_LOCK}

Returned by CHUNK_LOCK ({{sec-CHUNK_LOCK}}) when a
repair actor attempts to adopt a metadata-server escrow lock
({{sec-chunk_guard_mds}}) and no such adoption is
possible on the data server for the requested range.
There are four state-level causes:

- no metadata-server escrow lock is installed on the data server
  for the requested range;
- a metadata-server escrow lock is installed but its
  escrow_id4 ({{sec-escrow_id4}}) does not match
  the identity the repair actor presents;
- the range's escrow lock is currently under a
  reconciliation hold following a metadata-server
  incarnation change (see
  {{sec-CHUNK_ESCROW_TAKEOVER}}) and cannot be
  adopted until the hold clears; or
- the escrow was already adopted by a different
  repair actor whose adoption remains active.

Authorization-level failures -- the caller is not
the metadata-server-designated repair actor for
this escrow, or the caller lacks credentials for
the escrow's scope -- surface as NFS4ERR_ACCESS
rather than NFS4ERR_NO_ADOPTABLE_LOCK, so that no
data-plane information about the current adopter is
leaked to an unauthorized caller.

On receipt of NFS4ERR_NO_ADOPTABLE_LOCK, the repair
client MUST report the outcome to the metadata
server via CB_CHUNK_REPAIR's per-range status array
({{sec-CB_CHUNK_REPAIR}}) and MUST NOT
unilaterally acquire a fresh CHUNK_LOCK, retry the
adoption, or invoke the discovery/fallback path of
NFS4ERR_NO_PREDECESSOR
({{sec-NFS4ERR_NO_PREDECESSOR}}) -- the four causes
above are all control-plane conditions the metadata
server is best placed to resolve (by reissuing the
escrow, waiting for the reconciliation hold to
clear, or abandoning the repair).

### NFS4ERR_STALE_ESCROW (Error Code 10105) {#sec-NFS4ERR_STALE_ESCROW}

Returned by CHUNK_ESCROW_RELEASE
({{sec-CHUNK_ESCROW_RELEASE}}) when the escrow_id4
the metadata server presents does not match any
escrow currently installed on the data server for
the referenced range.  Two causes lead to the same
wire outcome:

- no escrow covers the referenced range at the
  data server (whether never installed, released
  earlier, or consumed by a repair adoption); or
- an escrow covers the range but its recorded
  escrow_id4 differs from the one presented (the
  presented identity is a stale reference to an
  earlier installation).

The data server MUST NOT alter any current lock or
escrow state as a side effect of returning
NFS4ERR_STALE_ESCROW: the response reports "the
identity you presented is not what I hold" without
changing what is held.  In particular, if the range
carries a metadata-server escrow lock whose escrow_id4 differs
from the presented identity, that lock survives the
call unchanged; and if the range carries a
client-owned lock that was previously adopted from
an escrow whose identity matches, that adopted
lock is not affected by a release of the presented
(now-stale) identity.

### NFS4ERR_STALE_MDS_EPOCH (Error Code 10106) {#sec-NFS4ERR_STALE_MDS_EPOCH}

Returned by any of the CHUNK_ESCROW operations
({{sec-CHUNK_ESCROW_INSTALL}},
{{sec-CHUNK_ESCROW_RELEASE}},
{{sec-CHUNK_ESCROW_ENUMERATE}}) when the requesting
metadata server presents an epoch value the data
server no longer accepts because a newer metadata-server
incarnation has completed a
CHUNK_ESCROW_TAKEOVER ({{sec-CHUNK_ESCROW_TAKEOVER}}).
The metadata server that receives NFS4ERR_STALE_MDS_EPOCH
has been fenced from continued escrow operations on
this data server; it MUST NOT retry the operation
under the same epoch and MUST obtain a fresh
incarnation-lease token and reissue via
CHUNK_ESCROW_TAKEOVER before resuming.  CHUNK_ESCROW_TAKEOVER itself is
not subject to this rejection -- it is the recovery
path out of an expired epoch and carries its own
compare-and-advance semantics per
{{sec-CHUNK_ESCROW_TAKEOVER}}.

NFS4ERR_STALE_MDS_EPOCH is distinct from
NFS4ERR_ACCESS (credential-level failure) and from
NFS4ERR_STALE_ESCROW (identity mismatch on a
specific escrow): the stale-epoch response fences
the presenter's entire escrow-control session, not
a single per-escrow operation.

### NFS4ERR_PARTIAL (Error Code 10107) {#sec-NFS4ERR_PARTIAL}

Returned as the top-level status of a
CB_CHUNK_REPAIR response ({{sec-CB_CHUNK_REPAIR}})
when the repair actor evaluated every named range
but at least one range's per-range status is not
NFS4_OK.  The per-range status array
(ccrr_range_status) is authoritative for the
outcome of each range; NFS4ERR_PARTIAL is the
top-level signal that the metadata server MUST
consume the per-range array rather than treating
the response as uniformly successful or uniformly
failed.

NFS4ERR_PARTIAL is distinct from operation-wide
errors (decode failures, authorization failures,
session state failures) that fail every range at
once: those return the operation-wide error at the
top level with an EMPTY per-range array.
NFS4ERR_PARTIAL requires a co-indexed array with
one entry per named range and MAY carry any mix
of NFS4_OK and per-range failure codes.

The numeric value 10107 is provisional; a final
draft-edit-time collision scan against the
current nfsstat4 range in {{RFC8881}} may adjust
the assignment.

## Operations and Their Valid Errors

The operations and their valid errors are presented in
{{tbl-ops-and-errors}}.  All error codes not defined in this document
are defined in Section 15 of {{RFC8881}} and Section 11 of {{RFC7862}}.

 | Operation          | Errors |
 | ---
 | CHUNK_COMMIT       | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_ERROR        | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_FINALIZE     | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_HEADER_READ  | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_REP_TOO_BIG, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_LOCK         | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_CHUNK_LOCKED, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_NO_ADOPTABLE_LOCK, NFS4ERR_SERVERFAULT |
 | CHUNK_READ         | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_PAYLOAD_NOT_ATOMIC, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_REPAIRED     | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_ROLLBACK     | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_NO_PREDECESSOR, NFS4ERR_SERVERFAULT |
 | CHUNK_UNLOCK       | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_WRITE        | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_CHUNK_GUARDED, NFS4ERR_CHUNK_LOCKED, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOSPC, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_WRITE_REPAIR | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOSPC, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | TRUST_STATEID      | NFS4_OK, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_INVAL, NFS4ERR_NOFILEHANDLE, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT |
 | REVOKE_STATEID     | NFS4_OK, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_INVAL, NFS4ERR_NOFILEHANDLE, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT |
 | BULK_REVOKE_STATEID| NFS4_OK, NFS4ERR_BADXDR, NFS4ERR_DELAY, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT |
 | CHUNK_ESCROW_INSTALL   | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_CHUNK_LOCKED, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT, NFS4ERR_STALE_MDS_EPOCH |
 | CHUNK_ESCROW_RELEASE   | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT, NFS4ERR_STALE_ESCROW, NFS4ERR_STALE_MDS_EPOCH |
 | CHUNK_ESCROW_ENUMERATE | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT, NFS4ERR_STALE_MDS_EPOCH |
 | CHUNK_ESCROW_TAKEOVER  | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM, NFS4ERR_SERVERFAULT, NFS4ERR_STALE_MDS_EPOCH |
{: #tbl-ops-and-errors title="Operations and Their Valid Errors"}

## Callback Operations and Their Valid Errors

The callback operations and their valid errors are presented in
{{tbl-cb-ops-and-errors}}.  All error codes not defined in this document
are defined in Section 15 of {{RFC8881}} and Section 11 of {{RFC7862}}.

 | Callback Operation| Errors                                       |
 | ---
 | CB_CHUNK_REPAIR | NFS4_OK, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DEADSESSION, NFS4ERR_DELAY, NFS4ERR_CODING_NOT_SUPPORTED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_ISDIR, NFS4ERR_LOCKED, NFS4ERR_NOTSUPP, NFS4ERR_OLD_STATEID, NFS4ERR_PARTIAL, NFS4ERR_PAYLOAD_LOST, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
{: #tbl-cb-ops-and-errors title="Callback Operations and Their Valid Errors"}

## Errors and the Operations That Use Them

The operations and their valid errors are presented in
{{tbl-errors-and-ops}}.  All operations not defined in this document
are defined in Section 18 of {{RFC8881}} and Section 15 of {{RFC7862}}.

 | Error                            | Operations                  |
 | ---
 | NFS4ERR_CODING_NOT_SUPPORTED     | CB_CHUNK_REPAIR, LAYOUTGET  |
 | NFS4ERR_PAYLOAD_NOT_ATOMIC       | CHUNK_READ                  |
 | NFS4ERR_CHUNK_LOCKED             | CHUNK_LOCK, CHUNK_WRITE, CHUNK_ESCROW_INSTALL |
 | NFS4ERR_CHUNK_GUARDED            | CHUNK_WRITE                 |
 | NFS4ERR_PAYLOAD_LOST             | CB_CHUNK_REPAIR             |
 | NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED | LAYOUTGET              |
 | NFS4ERR_NO_PREDECESSOR           | CHUNK_ROLLBACK              |
 | NFS4ERR_NO_ADOPTABLE_LOCK        | CHUNK_LOCK                  |
 | NFS4ERR_STALE_ESCROW             | CHUNK_ESCROW_RELEASE        |
 | NFS4ERR_STALE_MDS_EPOCH          | CHUNK_ESCROW_INSTALL, CHUNK_ESCROW_RELEASE, CHUNK_ESCROW_ENUMERATE, CHUNK_ESCROW_TAKEOVER |
 | NFS4ERR_PARTIAL                  | CB_CHUNK_REPAIR             |
{: #tbl-errors-and-ops title="Errors and the Operations That Use Them"}

# EXCHGID4_FLAG_USE_ERASURE_DS

~~~ xdr
   /// const EXCHGID4_FLAG_USE_ERASURE_DS      = 0x00100000;
~~~
{: #fig-EXCHGID4_FLAG_USE_ERASURE_DS title="The EXCHGID4_FLAG_USE_ERASURE_DS" }

When a data server connects to a metadata server it can via
EXCHANGE_ID (see Section 18.35 of {{RFC8881}}) state its pNFS role.
The data server can use EXCHGID4_FLAG_USE_ERASURE_DS (see
{{fig-EXCHGID4_FLAG_USE_ERASURE_DS}}) to indicate that it supports the
new NFSv4.2 operations introduced in this document.  Section 13.1
of {{RFC8881}} describes the interaction of the various pNFS roles
masked by EXCHGID4_FLAG_MASK_PNFS.  However, that does not mask out
EXCHGID4_FLAG_USE_ERASURE_DS.  I.e., EXCHGID4_FLAG_USE_ERASURE_DS can
be used in combination with all of the pNFS flags.

If the data server sets EXCHGID4_FLAG_USE_ERASURE_DS during the
EXCHANGE_ID operation, then it MUST support all of the operations
in {{tbl-protocol-ops}}.  Further, this support is orthogonal to the
Erasure Encoding Type selected.  The data server is unaware of which type
is driving the I/O.

# New NFSv4.2 Attributes

## Attribute 89: fattr4_coding_block_size {#sec-fattr4_coding_block_size}

~~~ xdr
   /// typedef uint64_t                  fattr4_coding_block_size;
   ///
   /// const FATTR4_CODING_BLOCK_SIZE  = 89;
   ///
~~~
{: #fig-fattr4_coding_block_size title="XDR for fattr4_coding_block_size" }

The new attribute fattr4_coding_block_size (see
{{fig-fattr4_coding_block_size}}) is an OPTIONAL to NFSv4.2 attribute
which MUST be supported if the metadata server supports the Flexible
File Version 2 Layout Type.  By querying it, the client can determine
the data block size it is to use when coding the data blocks to
chunks.

## Attribute 90: fattr4_ffv2_chunked_data_file {#sec-fattr4_ffv2_chunked_data_file}

~~~ xdr
   /// typedef bool                      fattr4_ffv2_chunked_data_file;
   ///
   /// const FATTR4_FFV2_CHUNKED_DATA_FILE  = 90;
   ///
~~~
{: #fig-fattr4_ffv2_chunked_data_file title="XDR for fattr4_ffv2_chunked_data_file" }

The new attribute fattr4_ffv2_chunked_data_file (see
{{fig-fattr4_ffv2_chunked_data_file}}) is an OPTIONAL to NFSv4.2
attribute a data server uses to classify a data file as a
chunked-encoding data file for the purpose of enforcing the client
restrictions in {{sec-ops-client}}.  When set to TRUE, the file is
under FFv2 chunked-encoding management by a metadata server; the
data server MUST apply the "MUST reject" rules on client operations
against such files (see {{sec-data-file-identification}}).  When
FALSE or absent, no such enforcement is triggered by this attribute
alone.

Only the metadata server sets this attribute; the metadata server
sets it as part of allocating a chunked-encoding data file on the
data server and does not change it during the file's lifetime.
Clients MUST NOT SETATTR this attribute; a data server MUST reject
a client SETATTR of FATTR4_FFV2_CHUNKED_DATA_FILE with
NFS4ERR_INVAL.  A data server that does not support this attribute
falls back to the other identification methods described in
{{sec-data-file-identification}}.

# New NFSv4.2 Common Data Structures

## chunk_guard4 {#sec-chunk_guard4}

~~~ xdr
   /// const CHUNK_GUARD_CLIENT_ID_NONE = 0x00000000;
   /// const CHUNK_GUARD_CLIENT_ID_MDS  = 0xFFFFFFFF;
   ///
   /// typedef uint64_t   chunk_cohort_id4;
   ///
   /// struct chunk_guard4 {
   ///     uint32_t   cg_gen_id;
   ///     uint32_t   cg_client_id;
   /// };
~~~
{: #fig-chunk_guard4 title="XDR for chunk_guard4 and chunk_cohort_id4" }

The chunk_cohort_id4 is a 64-bit writer-chosen opaque identifier
that names a single write transaction (a "cohort" of chunks written
together in one CHUNK_WRITE batch, or across several CHUNK_WRITEs
that a single writer chooses to associate as one logical
transaction).  Under the shared-cohort model
({{sec-CHUNK_WRITE}}), every chunk in a batch carries the same
chunk_cohort_id4 so that lifecycle operations (CHUNK_FINALIZE,
CHUNK_COMMIT, CHUNK_ROLLBACK) can name the transaction as a
whole.  The data server treats chunk_cohort_id4 opaquely: it does
NOT interpret the value beyond equality comparison, and it is NOT
required to be monotonic, dense, or ordered in any way.  Writers
MUST choose a new chunk_cohort_id4 per distinct write transaction
so that transactions can be distinguished on the data server; the
uniqueness scope required is per-(writer, file), not global.  A
writer with sufficient state MAY generate chunk_cohort_id4 values
from a counter, a random 64-bit source, a hashed transaction
identifier, or any other locally convenient scheme, subject to
the per-writer uniqueness rule.

On the wire, a single CHUNK_WRITE carries a 12-byte cohort
header (chunk_cohort_id4 + writer's cg_client_id) once for
the batch, followed by, per chunk in the batch, the tagged
checksum4 and the opaque chunk payload, as shown in
{{fig-chunk-wire-layout}}.  The payload length is carried
separately in the CHUNK_WRITE4args cwa_chunks<> slot; the
diagram shows the header once and the per-chunk framing
that repeats.

~~~
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    cwa_cohort_id (hi 32)                      |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    cwa_cohort_id (lo 32)                      |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                       cwa_client_id                           |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                       cs_algorithm                            |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                        cs_value_len                           |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    cs_value ... (variable)                    |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    opaque payload ...                         |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

   Bytes 0-7:    cwa_cohort_id   (chunk_cohort_id4; 64-bit opaque
                                  writer-chosen cohort identifier;
                                  once per CHUNK_WRITE)
   Bytes 8-11:   cwa_client_id   (writer's layout-granted 32-bit
                                  client id; once per CHUNK_WRITE)
   Bytes 12-15:  cs_algorithm    (checksum_algorithm4; per chunk)
   Bytes 16-19:  cs_value_len    (XDR opaque length prefix; per chunk)
   Bytes 20-N:   cs_value        (checksum bytes; length per
                                  cs_algorithm's registered output;
                                  per chunk)
   Bytes N+1-M:  opaque payload  (encoded shard; variable length;
                                  per chunk)

   The checksum block (cs_algorithm + cs_value_len + cs_value)
   is the XDR encoding of one checksum4 ({{fig-checksum4}}).
   For CHECKSUM_ALG_NONE the cs_value_len is zero and the
   payload follows immediately after byte 19.  The per-chunk
   framing (bytes 12 onward) repeats for each chunk in the
   batch; the cohort header (bytes 0-11) appears once per
   CHUNK_WRITE.  The per-chunk co_id values live in
   CHUNK_WRITE4args cwa_co_ids<> and are not part of this
   framing.
~~~
{: #fig-chunk-wire-layout title="CHUNK_WRITE wire framing: cohort header + per-chunk chunks"}

The chunk_guard4 (see {{fig-chunk_guard4}}) is the per-chunk
compare-and-swap (CAS) state used by CHUNK_WRITE
({{sec-CHUNK_WRITE}}) to detect concurrent updates.  It is state
that the data server MAINTAINS per chunk; the writer transaction
identity (the "cohort") is carried separately by
chunk_cohort_id4 and is NOT part of chunk_guard4.  chunk_guard4
has two fields:

cg_gen_id:
:  A per-chunk monotonic generation counter, tracked by the data
   server.  Each chunk's gen_id starts at 0 when the chunk is
   first written and is incremented on each successful CHUNK_WRITE
   by any client.  cg_gen_id is NOT a timestamp -- the protocol
   does not rely on a global clock, and no interpretation of
   cg_gen_id as a wall-clock value is supported.  cg_gen_id
   values are NOT comparable across distinct chunks; a given
   cg_gen_id is only meaningful within the scope of a single
   chunk on a single file.  cg_gen_id is NOT a transaction
   identifier and MUST NOT be interpreted as naming or ordering
   write transactions: transaction identity is chunk_cohort_id4
   (see above).

cg_client_id:
:  A 32-bit value established by the metadata server at the time
   the client's layout is granted (see {{sec-ffv2-mirror4}} and
   ffv2m_client_id).  The metadata server MUST assign distinct
   cg_client_id values to distinct clients that hold concurrent
   write layouts on the same file.  cg_client_id is opaque with
   respect to client identity -- a data server MUST NOT
   interpret its bits as naming or ordering clients in any
   external sense.  The value supports two operations only:
   equality comparison (to detect whether the current writer is
   the client that last wrote a chunk) and numeric comparison
   (to implement the tiebreaker rule below).  The same
   cg_client_id value appears in the cohort record
   ({{sec-chunk_owner4}}) as co_client_id; the two are
   redundant carriers of the same layout-granted writer identity
   so that both CAS state and cohort records remain
   self-contained.

Uniqueness contract:
:  The chunk_guard4 pair (cg_gen_id, cg_client_id) identifies the
   MOST RECENT successful writer of a chunk plus that chunk's
   generation counter; it does NOT identify a specific write
   transaction (that role is filled by chunk_cohort_id4).
   Neither field alone is globally unique; two clients MAY
   observe the same cg_gen_id on distinct chunks (each chunk's
   counter is independent), and the cg_client_id is what makes
   concurrent writers distinguishable at the CAS layer.

Observability:
:  The data server exposes the chunk's current chunk_guard4 on
   the read path so that a client preparing a CAS update in
   multiple writer mode ({{sec-multi-writer}}) can obtain the
   expected prior value without racing.  Two operations return
   it: CHUNK_READ carries cr_guard in each read_chunk4
   ({{sec-CHUNK_READ}}), and CHUNK_HEADER_READ returns a
   chrr_guards<> array co-indexed with the other per-chunk
   arrays ({{sec-CHUNK_HEADER_READ}}).  A client places the
   observed pair into cwa_guard.cwg_guard and sets
   cwa_guard.cwg_check = TRUE on the subsequent CHUNK_WRITE
   ({{sec-CHUNK_WRITE}}); the data server compares against its
   currently-held chunk_guard4 and returns NFS4ERR_CHUNK_GUARDED
   on mismatch.

Deterministic contention resolution for concurrent writers:
:  When two or more clients race on the same chunk in the
   multi-writer mode, the losing writer -- the one whose CAS
   fails at any affected data server -- MUST roll back the
   chunks it already wrote for the affected transaction and
   retry under a fresh cohort id.  Convergence is achieved
   by making losing writers back off, not by having the data
   server pick a winner from the losing writer's state.

    - **At CHUNK_WRITE** (per data server, arrival-order): the
      data server accepts the first CHUNK_WRITE whose
      chunk_guard4 CAS check succeeds against the chunk's
      current chunk_guard4 value.  Later writers whose CAS
      fails receive NFS4ERR_CHUNK_GUARDED for that chunk.
      Because arrival order can differ between data servers,
      different subsets of the mirror set MAY initially
      accept different clients' writes for different chunks;
      that is transient divergence, resolved by the
      client-driven rollback below.

    - **At NFS4ERR_CHUNK_GUARDED** (client-driven rollback and
      retry): a client that observes NFS4ERR_CHUNK_GUARDED
      on any chunk of an in-flight transaction MUST treat the
      entire transaction as lost.  It MUST issue
      CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}}) against every
      data server that accepted a CHUNK_WRITE under this
      transaction's cohort pair, so that the data server can
      release the PENDING state and revert cg_gen_id to the
      value it held before the losing writer's CAS
      succeeded.  The client then re-reads the chunks with
      CHUNK_READ, applies its intended change to the
      as-observed data, chooses a fresh cwa_cohort_id, and
      re-issues CHUNK_WRITE with cwa_guard.cwg_check = TRUE
      supplying the refreshed prior chunk_guard4.

    - **At CHUNK_FINALIZE** (single winner already
      established): by the time the mirror set converges,
      only one writer's cohort remains as the PENDING state
      for each affected chunk (all others have rolled
      back).  CHUNK_FINALIZE against that PENDING state
      succeeds; there is no tiebreaker comparison against
      the caller's co_client_id at FINALIZE.  A caller that
      attempts CHUNK_FINALIZE against a chunk whose current
      PENDING state carries a cohort pair not matching the
      caller's transaction MUST receive
      NFS4ERR_CHUNK_GUARDED and MUST proceed with the
      rollback-and-retry flow above.  A caller whose own
      PENDING state was overwritten by a different writer
      SHOULD also receive NFS4ERR_CHUNK_GUARDED (the caller
      no longer has a PENDING chunk to finalize).

   A client that has rolled back and retried but continues
   to observe NFS4ERR_CHUNK_GUARDED without forward
   progress after a bounded number of retries MUST
   escalate via LAYOUTERROR and the repair coordination
   flow in {{sec-repair-selection}}.  Bounded retry is a
   client-implementation matter; the protocol does not
   mandate a specific count, only that unbounded retry is
   forbidden so that a contentious workload cannot livelock
   without surfacing the contention to the metadata server.

   Client cg_client_id ordering is NOT used to pick a
   winner: the numeric ordering of cg_client_id values is
   arbitrary with respect to clients' external identities
   and MUST NOT be interpreted as a preference ordering
   over the clients themselves.  The arrival-order
   arbitration at each data server, combined with mandatory
   client rollback on CAS failure, is what makes the mirror
   set converge; the metadata server MAY still arrange
   cg_client_id assignment to influence diagnosis but MUST
   NOT rely on numeric ordering for correctness.

### Metadata-Server Assignment Rules for cg_client_id

To uphold the uniqueness contract, the metadata server MUST
follow these rules when assigning cg_client_id (that is, when
populating ffv2m_client_id at layout-grant time):

-  Two clients holding concurrent write layouts on the same
   file MUST receive distinct cg_client_id values.  A client
   that holds only a read layout need not be assigned a
   distinct value.

-  The reserved sentinel CHUNK_GUARD_CLIENT_ID_NONE (0x00000000)
   MUST NOT be assigned to any client.  Reserving 0 prevents an
   uninitialized cg_client_id field from passing as a real
   client and ensures the deterministic tiebreaker (numerically
   lowest wins) does not encode an implicit priority via
   assignment of 0.

-  The reserved sentinel CHUNK_GUARD_CLIENT_ID_MDS (0xFFFFFFFF)
   MUST NOT be assigned to any client.

-  A cg_client_id MAY be reused by the metadata server after
   the prior holder's layout has been fully returned (via
   LAYOUTRETURN or revocation).  The metadata server SHOULD
   avoid reusing a cg_client_id within a single lease period
   to simplify diagnosis of stale writes.

-  cg_client_id values do not persist across metadata-server
   restart.  Clients reclaiming layouts during the grace period
   receive freshly assigned values; the protocol does not rely
   on any pre-restart assignment surviving.

### Data-Server Collision Handling

A (cg_gen_id, cg_client_id) pair that the uniqueness contract
would otherwise render unique can nonetheless collide if a
client and the metadata server disagree about which
cg_client_id the client currently holds, or if a client
presents a spoofed cg_client_id.  The data server enforces the
contract locally:

-  If the data server receives a CHUNK_WRITE whose
   chunk_guard4 has the same (cg_gen_id, cg_client_id) as a
   chunk already in PENDING, FINALIZED, or COMMITTED state
   AND the presented payload differs from the retained
   payload, the data server MUST reject the write with
   NFS4ERR_CHUNK_GUARDED and SHOULD report the collision to
   the metadata server via LAYOUTERROR.  This situation is a
   protocol violation on one side of the conversation; the
   metadata server resolves it by revoking the offending
   client's layout and selecting a repair actor under
   {{sec-repair-selection}}.

-  If a client presents CHUNK_GUARD_CLIENT_ID_MDS as
   cg_client_id in any client-originated operation, the data
   server MUST reject the operation with NFS4ERR_INVAL (see
   {{sec-chunk_guard_mds}}).

-  A cg_client_id that does not match the tsa_client_id
   recorded for the layout stateid under which the
   CAS operation is issued MUST be rejected with
   NFS4ERR_BAD_STATEID.  This (stateid, client_id) binding is
   registered by the metadata server via TRUST_STATEID
   ({{sec-TRUST_STATEID}}); an unmatched cg_client_id is
   treated as a stale-layout condition, see
   {{sec-tight-coupling-control}}.

### Reserved cg_client_id Value: CHUNK_GUARD_CLIENT_ID_NONE {#sec-chunk_guard_none}

The value `CHUNK_GUARD_CLIENT_ID_NONE` (0x00000000) is reserved.
It does not denote any client.  Reserving 0 prevents an
uninitialized cg_client_id field from passing as a real client
and ensures the deterministic tiebreaker (numerically lowest
wins, see {{sec-chunk_guard4}}) does not encode an implicit
priority via assignment of 0.

Clients MUST NOT present CHUNK_GUARD_CLIENT_ID_NONE as the
cg_client_id of any client-originated chunk_guard4 or
chunk_owner4.  A data server that receives such a value from
a client MUST reject the operation with NFS4ERR_INVAL.

### Reserved cg_client_id Value: CHUNK_GUARD_CLIENT_ID_MDS {#sec-chunk_guard_mds}

The value `CHUNK_GUARD_CLIENT_ID_MDS` (0xFFFFFFFF) is reserved.
It denotes that the chunk lock is held by the metadata server
itself, in escrow during a repair coordination sequence (see
{{sec-repair-selection}}).  The data server produces a
chunk_guard4 with this cg_client_id when the metadata server
revokes the prior holder's stateid while that holder still holds
chunk locks; the locks MUST NOT be dropped and are transferred to
the metadata-server escrow owner instead.

The metadata server does not originate CHUNK_LOCK or CHUNK_WRITE
traffic on its own session.  Clients MUST NOT present
CHUNK_GUARD_CLIENT_ID_MDS as the cg_client_id of any
client-originated chunk_guard4 or chunk_owner4.  A data server
that receives such a value from a client MUST reject the
operation with NFS4ERR_INVAL.

The metadata-server escrow owner is released only by a CHUNK_LOCK from the
client selected via CB_CHUNK_REPAIR, carrying
CHUNK_LOCK_FLAGS_ADOPT.  See {{sec-CHUNK_LOCK}}.

Each metadata-server escrow lock carries an escrow_id4
({{sec-escrow_id4}}) the metadata server chose at
CHUNK_ESCROW_INSTALL ({{sec-CHUNK_ESCROW_INSTALL}}) time
and presents on every subsequent operation that refers
to that lock (CHUNK_ESCROW_RELEASE, CB_CHUNK_REPAIR,
CHUNK_LOCK adoption via cla_adopt).  When a repair
client adopts the metadata-server escrow lock (CHUNK_LOCK with
CHUNK_LOCK_FLAGS_ADOPT), the data server MUST retain
the adopted escrow_id4 as durable custody metadata on
the resulting client-owned lock, for as long as a
subsequent revocation-transfer can occur that would
convert the client-owned lock back to a metadata-server escrow
lock (for example, when the client's lease later
expires while the lock is still held).  If such a
revocation-transfer occurs, the resulting new
metadata-server escrow lock MUST be installed with the SAME
escrow_id4 that was preserved as custody metadata,
not a fresh identity: this preserves the full durable
key `(file, escrow_id, data-server set)` across the entire
custody chain so that a metadata server's tuple
records can re-associate with the reappeared escrow
across an incarnation change (see
{{sec-CHUNK_ESCROW_ENUMERATE}} discovery).

## chunk_owner4 {#sec-chunk_owner4}

~~~ xdr
   /// struct chunk_owner4 {
   ///     chunk_cohort_id4  co_cohort_id;
   ///     uint32_t          co_client_id;
   ///     uint32_t          co_id;
   /// };
~~~
{: #fig-chunk_owner4 title="XDR for chunk_owner4" }

The chunk_owner4 (see {{fig-chunk_owner4}}) is the "cohort
record" for a chunk: it identifies the write transaction that
produced the chunk and which of that transaction's chunks the
record refers to.  It is separate from chunk_guard4
({{sec-chunk_guard4}}), which is the per-chunk CAS state.  The
three fields together form the full owner triple.

co_cohort_id is the chunk_cohort_id4 shared by every chunk
written together in a single logical transaction (see
{{sec-CHUNK_WRITE}} and the discussion of chunk_cohort_id4
above).  Two chunks are members of the same write transaction
iff their (co_cohort_id, co_client_id) pairs are equal.
Lifecycle operations (CHUNK_FINALIZE, CHUNK_COMMIT,
CHUNK_ROLLBACK) name transactions by co_cohort_id + co_client_id.

co_client_id is the writer's layout-granted 32-bit identity, the
same value that appears as cg_client_id in the chunk_guard4 CAS
state (see {{sec-chunk_guard4}}).  It supports equality
comparison (matching cohort records to lifecycle operations) and
numeric comparison (implementing the multi-writer tiebreaker
described in {{sec-chunk_guard4}}).

co_id is a writer-supplied opaque per-chunk identifier the client
chooses at CHUNK_WRITE time (see {{sec-CHUNK_WRITE}}).  It is
NOT required to equal the chunk's file index; the client MAY
choose any uint32_t value, subject only to the uniqueness
constraint that within a single (co_cohort_id, co_client_id) all
co_id values MUST be distinct so that a subsequent lifecycle
operation can name individual chunks unambiguously.  The data
server treats co_id opaquely; it does NOT interpret the value
beyond equality comparison against the co_id values it previously
accepted from the client for this cohort.  Writers that would
otherwise choose file-index values MAY do so, but the wire
semantics do not privilege that choice.

Each distinct chunk-write transaction from a given client MUST
carry a unique co_cohort_id, so lifecycle operations can be
correlated with the transactions that produced them across all
data files.  The uniqueness scope required is per-(co_client_id,
file); different clients MAY independently pick colliding
co_cohort_id values because co_client_id disambiguates them.

## escrow_id4 {#sec-escrow_id4}

~~~ xdr
   /// typedef opaque   escrow_id4[16];
~~~
{: #fig-escrow_id4 title="XDR for escrow_id4" }

The escrow_id4 is a 128-bit opaque identifier the
metadata server chooses for each metadata-server escrow lock
({{sec-chunk_guard_mds}}) it installs on a data
server.  It is distinct from the chunk_owner4 owner
triple ({{sec-chunk_owner4}}) that identifies a chunk
generation: the escrow identity refers to the
custody of a repair-scope lock, while the owner
triple refers to a specific generation's bytes.  The
two namespaces do not overlap and are compared only
within their own contexts (an escrow_id4 is never
matched against a chunk_owner4 field).

The escrow identity is threaded through the
metadata-server operations that manage escrow
custody: it appears in each escrow-family operation
this specification defines (CHUNK_ESCROW_INSTALL /
CHUNK_ESCROW_RELEASE / CHUNK_ESCROW_ENUMERATE /
CHUNK_ESCROW_TAKEOVER), in the callback that carries
the repair instruction (CB_CHUNK_REPAIR), and in the
CHUNK_LOCK argument variant that adopts an escrow
lock (see {{sec-CHUNK_LOCK}}).  A conforming
metadata server MUST choose escrow_id4 values that
are unique across every escrow it has ever installed
on any data server that might still recognize a
prior installation -- sufficient uniqueness is
provided by a 128-bit identifier drawn from a
metadata-server-incarnation prefix and a
per-incarnation monotonic counter, or by any
mechanism whose collision probability is negligible
across the lifetime of the deployment.  The metadata
server MUST NOT reuse an escrow_id4 whose lifecycle
is not provably complete.

The data server treats escrow_id4 opaquely: it
compares two escrow_id4 values for equality when
matching a CHUNK_LOCK adoption against an
installed escrow, or when reconciling an escrow
tuple against a discovery response, and does not
interpret the internal structure.

## Incarnation-Lease Proof {#sec-proof-profile}

CHUNK_ESCROW_TAKEOVER
({{sec-CHUNK_ESCROW_TAKEOVER}}) accepts a bounded
opaque proof payload identified by a proof profile
identifier.  The proof is not the metadata server's
own machine credential (which would only prove the
role, not the current exclusive incarnation): it is
an assertion issued by a single writer authority
external to the metadata server (a high-availability
manager, a cluster-consensus service, or an
operator-mediated recovery workflow) that only one
metadata-server instance currently holds the
incarnation lease.  The data server verifies the
proof before it will compare-and-advance its
recorded metadata-server epoch to the value the
takeover names.

~~~ xdr
   /// /* Registered proof profile identifier.  Values
   ///  * are allocated from the flexible file v2 layout
   ///  * proof-profile registry (see IANA Considerations,
   ///  * "Proof-Profile Registry"). */
   /// typedef uint32_t   proof_profile_id4;
   ///
   /// /* Reserved sentinel; MUST NOT appear on the wire. */
   /// const PROOF_PROFILE_UNSPECIFIED           = 0;
   ///
   /// /* Mandatory-to-implement profile:
   ///  * HA-authority-signed COSE_Sign1 lease token
   ///  * (see "Mandatory-to-Implement Profile" below). */
   /// const PROOF_PROFILE_HA_AUTHORITY_ED25519  = 1;
   ///
   /// /* Upper bound (in bytes) on the proof payload
   ///  * a metadata server MAY present. */
   /// const CETA_INCARNATION_PROOF_MAX4         = 4096;
~~~
{: #fig-proof-profile-typedef title="XDR for proof_profile_id4" }

### Mandatory-to-Implement Profile

A conforming implementation MUST support at least
one proof profile so that two independent
implementations can verify each other's takeover
proofs at the wire level without prior out-of-band
negotiation.  This specification designates the
following profile as mandatory-to-implement.

The mandatory profile carries a signed token whose
signer is the incarnation-lease authority (NOT the
metadata server itself).  The envelope is a
COSE_Sign1 structure (Section 4.2 of {{!RFC9052}})
over a deterministic CBOR payload (Section 4.2 of
{{!RFC8949}}) with the following normative choices:

Signature algorithm (mandatory-to-implement):

: Ed25519 (algorithm identifier -8 per {{!RFC9053}}).  A
  conforming signer MUST use
  Ed25519; a conforming verifier MUST accept
  Ed25519.  Other signature algorithms (e.g.,
  ECDSA-P256 with identifier -7, RSASSA-PSS-SHA256
  with identifier -37) MAY be registered as
  additional profiles per the IANA Considerations.
- **kid header parameter**: OPTIONAL.  A deployment
  with a single trust anchor MAY omit it; a
  deployment supporting key rotation or multiple
  trust anchors SHOULD include it so a data server
  can select the correct verification key.  Absent
  kid, the data server attempts verification
  against each configured trust anchor and accepts
  on the first match.
Payload map fields:

: the signed CBOR payload is a map with integer-keyed fields
  (per {{!RFC9053}} convention for compact wire size).
  The mandatory-profile keys are:
   - 1 = principal (CBOR text string): the
     metadata-server principal that holds this
     incarnation.  Comparison is byte-for-byte
     against the RPCSEC_GSS authenticated name of
     the presenter (Section 5 of {{!RFC7861}}),
     with no Unicode normalization or case
     folding; a deployment MUST provision the
     authority to sign tokens whose principal
     field is exactly the RPC-authenticated name
     the data server will observe.
   - 2 = epoch (CBOR uint): the metadata-server
     epoch value being claimed.  On presentation in
     CHUNK_ESCROW_TAKEOVER
     ({{sec-CHUNK_ESCROW_TAKEOVER}}) the data server
     MUST verify that this field equals
     ceta_new_epoch in the operation arguments; any
     mismatch is a signature-and-payload check
     failure at step 4 of "Presentation and
     Verification" below and returns NFS4ERR_ACCESS.
   - 3 = scope (CBOR text string): identifier of
     the data server or data-server set the token
     is valid for.  Comparison is byte-for-byte
     against the data-server-side value the
     deployment provisions at trust-anchor setup
     (see "Trust Anchor Provisioning" below); a
     data server accepts a token whose scope
     field exactly matches any scope identifier
     it has been provisioned to serve, and
     rejects any other value.  The scope
     namespace is deployment-local -- this
     specification neither defines a format nor
     constrains the character set beyond
     requiring UTF-8 CBOR text.
   - 4 = issued_at (CBOR tag-1 epoch-based
     date/time per {{!RFC8949}} Section 3.4.2):
     the instant the authority signed the token.
     A conforming issuer MUST encode this as a
     CBOR unsigned integer number of seconds
     since the POSIX epoch; a verifier MUST
     reject a token whose issued_at is not an
     unsigned integer under tag 1 (fractional or
     negative values are rejected).
   - 5 = expires_at (CBOR tag-1 epoch-based
     date/time per {{!RFC8949}} Section 3.4.2):
     the instant the token ceases to be
     admissible.  Same encoding constraints as
     issued_at.
   - 6 = token_id (CBOR byte string, 16 bytes):
     a nonce for replay detection.

### Presentation and Verification

The metadata server presents the profile identifier
and the proof bytes together in the takeover
arguments (see {{sec-CHUNK_ESCROW_TAKEOVER}}).  The
data server MUST evaluate the takeover in a fixed
order so that no failure discloses state that a
prior check would have denied:

1. session replay-cache lookup: retransmission of a
   prior request in the current session slot
   returns the cached response;
2. presenter authorization: RPCSEC_GSS presenter
   authentication and credential check
   (NFS4ERR_ACCESS if the caller lacks metadata-server
   role);
3. profile support: unknown proof_profile_id4
   returns NFS4ERR_NOTSUPP;
4. proof verification: the profile's signature and
   payload checks are applied (NFS4ERR_ACCESS on
   any failure -- bad signature, mismatched
   principal, mismatched epoch, mismatched scope,
   token past expires_at, or token_id already in
   the data server's replay cache);
5. epoch compare-and-advance: NFS4ERR_STALE_MDS_EPOCH
   on mismatch, otherwise the epoch and
   epoch_expires_at are advanced atomically per
   {{sec-CHUNK_ESCROW_TAKEOVER}}.

The strict ordering ensures an unauthenticated
caller learns nothing about which profiles the data
server supports or which epoch it currently holds.

Replay-cache scoping (both layers): the NFSv4.1
session replay cache in step 1 is scoped to the
session slot and its lifetime is bounded by session
liveness.  The token_id replay cache in step 4 is
scoped to the (proof_profile_id4, verified issuer)
pair and MUST be sized and expired coherently with
the token's own expires_at, so that a valid token
cannot be replayed after its natural expiry and a
recently-observed token cannot be inadvertently
retired while still admissible.  A data server MAY
persist the token_id replay cache across restart.
Loss of a cache entry (eviction, non-persisted
restart) does not permanently defeat lost-response
recovery: the byte-identical uncertain-completion
recovery path in
{{sec-CHUNK_ESCROW_TAKEOVER-uncertain-completion}}
covers the cache-miss form and returns the same
postcondition-equivalent NFS4_OK when the operation
had already completed.

### Uncertain-Completion Recovery for TAKEOVER {#sec-CHUNK_ESCROW_TAKEOVER-uncertain-completion}

CHUNK_ESCROW_TAKEOVER
({{sec-CHUNK_ESCROW_TAKEOVER}}) is the recovery
path a metadata server uses after an incarnation
change; the compare-and-advance semantics make the
successful case observable to the data server, but
the metadata server MAY lose the response to a
successful TAKEOVER (network drop, RPC
retransmission timeout, session loss).  The bare
strict-ordering rules above would rebuff a
byte-identical reissue: either the token_id
replay-cache check at step 4 rejects with
NFS4ERR_ACCESS (the cache still holds the entry) or
the epoch compare-and-advance at step 5 rejects
with NFS4ERR_STALE_MDS_EPOCH (the ordinary path,
because the reissue's ceta_expected_prior_epoch
names the pre-advance epoch that the earlier
successful TAKEOVER has already moved past).  In
either case the metadata server has no way to
distinguish "the prior TAKEOVER succeeded and the
response was lost" from "the proof is invalid."

To close that recovery gap, a data server MUST
accept a byte-identical CHUNK_ESCROW_TAKEOVER
reissue as postcondition-equivalent success when
step 4's signature and payload checks succeed
(signature verifies against the deployment-provisioned
trust anchor; the signed principal,
scope, and epoch match; the token is within its
expires_at window; all per {{sec-proof-profile}}
"Payload map fields"), with the ordinary step-4
"token_id already in the replay cache" rejection
overridden as stated below, and both of the
following hold:

- the reissue's ceta_new_epoch equals the data
  server's currently-recorded metadata-server
  epoch (the takeover the token authorized has
  already completed); and
- the reissue's ceta_expected_prior_epoch is
  strictly less than the reissue's ceta_new_epoch
  (the token names a genuine advance, not a
  no-op).

The recovery rule takes two forms distinguished by
the state of the token_id replay cache at the data
server:

Cache-hit form (ordinary lost-response case):

: the token_id is present in the token_id replay cache.  The
  data server recognizes the
  cached byte-identical decision and returns the
  cached NFS4_OK result; step 5 is not re-executed.
Cache-miss form (applies after eviction or non-persisted restart):

: the token_id is not present in the replay cache.  The data
  server
  treats the presentation as a fresh byte-identical
  proof under the two epoch predicates
  above and does NOT execute step 5 (the epoch is
  already at the post-advance state).

Under these predicates the data server returns
NFS4_OK without side effect: the epoch and
epoch_expires_at are already at the post-advance
state, no state changes, and the second observation
is idempotent.  The rule is safe against a fresh
presentation of an already-used token by a
different party -- a different party would not
present the same proof bytes without stealing the
signer's key material, the token was issued to a
specific principal matched by step 4's principal
check, expiry admissibility windows for successor
principals do not overlap ({{sec-proof-profile}}
"Time-Related Bounds"), and a subsequent
successful TAKEOVER by any party advances the
current epoch past ceta_new_epoch and
disqualifies the reissue on the first predicate
above.

When any predicate fails the data server returns
NFS4ERR_ACCESS or NFS4ERR_STALE_MDS_EPOCH per the
ordinary strict-ordering rule and the metadata
server MUST obtain a fresh incarnation-lease token
from the authority.  A fresh token has a new
token_id and does not collide with the replay
cache; the fresh takeover uses the ordinary
advance form.

### Trust Anchor Provisioning

The verification trust anchor (the public key or
key set the authority's signatures verify against)
is provisioned at each data server at deployment
time.  Key distribution mechanisms (X.509 chain,
JWK set fetch, raw public key push) are deployment
concerns outside the scope of this specification;
rotation is likewise deployment-local.  The wire
format is fully specified so that two independent
implementations sharing the same trust anchor can
interoperate; the trust-anchor bootstrap itself is
not a wire-negotiated step.

### Time-Related Bounds

The token's issued_at MUST NOT be more than
`skew_tolerance` in the future when the data server
evaluates it (deployment-configured; recommend
NTP-consistent, roughly 10 s).  The token's
expires_at is compared strictly: the token becomes
inadmissible at the first instant `now >=
expires_at`.  No skew tolerance is added to the
right edge; the incarnation-lease authority MUST
NOT issue a successor token to a different
metadata-server principal until at least
`prior.expires_at + max_ds_skew_tolerance`, where
max_ds_skew_tolerance is a deployment-configured
bound that MUST equal or exceed the largest
skew_tolerance any data server in the scope is
allowed to use.  This ordering ensures that no
data server admits the prior holder at any instant
after the successor's token becomes admissible.

## checksum4 {#sec-checksum4}

~~~ xdr
   /// typedef uint32_t   checksum_algorithm4;
   ///
   /// const CHECKSUM_ALG_NONE      = 0;
   /// const CHECKSUM_ALG_CRC32     = 1;
   /// const CHECKSUM_ALG_CRC32C    = 2;
   /// const CHECKSUM_ALG_FLETCHER4 = 3;
   /// const CHECKSUM_ALG_SHA256    = 4;
   /// const CHECKSUM_ALG_SHA512    = 5;
   /// const CHECKSUM_ALG_BLAKE3    = 6;
   /// /* Additional values registered with IANA;
   ///    see Section "Checksum Algorithm Registry" in
   ///    the IANA Considerations. */
   ///
   /// struct checksum4 {
   ///     checksum_algorithm4   cs_algorithm;
   ///     opaque                cs_value<64>;
   /// };
~~~
{: #fig-checksum4 title="XDR for checksum4" }

The checksum4 (see {{fig-checksum4}}) is a tagged
checksum value used to detect transport corruption and
on-disk bit rot of chunk payloads.  Every chunk on the
wire and at rest carries a checksum4 alongside its
chunk_owner4.

cs_algorithm:
:  identifies the checksum algorithm.  The values
   listed above are registered by this document; additional
   values are managed by the IANA registry (see
   "Checksum Algorithm Registry" in the IANA
   Considerations section).  CHECKSUM_ALG_NONE indicates
   the deployment relies on transport-layer (TLS, IPsec)
   or storage-layer integrity instead of a protocol-level
   per-chunk checksum.

cs_value:
:  the checksum bytes.  The length is fixed per registered
   algorithm:

   *  CHECKSUM_ALG_NONE: 0 bytes.

   *  CHECKSUM_ALG_CRC32: 4 bytes.

   *  CHECKSUM_ALG_CRC32C: 4 bytes.

   *  CHECKSUM_ALG_FLETCHER4: 32 bytes (four 64-bit
      accumulators, matching the ZFS Fletcher4 layout).

   *  CHECKSUM_ALG_SHA256: 32 bytes.

   *  CHECKSUM_ALG_SHA512: 64 bytes.

   *  CHECKSUM_ALG_BLAKE3: 32 bytes (BLAKE3 standard
      output length).

   A checksum4 whose cs_value length does not match the
   registered length for cs_algorithm MUST be rejected
   with NFS4ERR_INVAL.

Coverage:
:  Every registered algorithm covers the same input
   bytes: the chunk's header immediately followed by the
   chunk payload, in wire-transmission order, with the
   bytes of the header's own checksum field (`cs_value`)
   treated as zero for the duration of the computation.
   After computing, the writer stores the resulting bytes
   into `cs_value` for transmission and at-rest storage;
   the reader saves the received `cs_value`, treats those
   bytes as zero, recomputes over the same input, and
   compares against the saved value.  Including the header
   in coverage protects the per-chunk metadata
   (`payload_id`, guard, owner, length fields) as well as
   the payload; treating the checksum field as zero makes
   the computation independent of the field's wire value
   so the same input produces the same output on both
   ends.  This coverage rule applies uniformly to every
   registered `cs_algorithm`; individual registry entries
   name the function and any function-specific parameters,
   but do not restate the covered-bytes rule.

The checksum algorithm for a given file is selected by
the metadata server at LAYOUTGET time and carried in
the layout (see {{sec-ffv2-mirror4}}).  A client that
does not implement the algorithm a layout names returns
the layout with NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED
({{sec-NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED}}); the
metadata server may then offer a layout with a
different algorithm.

# New NFSv4.2 Operations {#sec-new-ops}

~~~ xdr
   ///
   /// /* New operations for Erasure Coding start here */
   ///
   ///  OP_CHUNK_COMMIT        = 78,
   ///  OP_CHUNK_ERROR         = 79,
   ///  OP_CHUNK_FINALIZE      = 80,
   ///  OP_CHUNK_HEADER_READ   = 81,
   ///  OP_CHUNK_LOCK          = 82,
   ///  OP_CHUNK_READ          = 83,
   ///  OP_CHUNK_REPAIRED      = 84,
   ///  OP_CHUNK_ROLLBACK      = 85,
   ///  OP_CHUNK_UNLOCK        = 86,
   ///  OP_CHUNK_WRITE         = 87,
   ///  OP_CHUNK_WRITE_REPAIR  = 88,
   ///
   /// /* metadata-server-to-data-server control-plane operations for tight coupling */
   ///
   ///  OP_TRUST_STATEID       = 89,
   ///  OP_REVOKE_STATEID      = 90,
   ///  OP_BULK_REVOKE_STATEID = 91,
   ///
   /// /* metadata-server-side escrow control-plane operations */
   ///
   ///  OP_CHUNK_ESCROW_INSTALL   = 92,
   ///  OP_CHUNK_ESCROW_RELEASE   = 93,
   ///  OP_CHUNK_ESCROW_ENUMERATE = 94,
   ///  OP_CHUNK_ESCROW_TAKEOVER  = 95,
   ///
~~~
{: #fig-ops-xdr title="Operations XDR" }

The following amendment blocks extend the nfs_argop4 and
nfs_resop4 dispatch unions defined in {{RFC7863}} with arms for
each of the new operations defined in this document.  A consumer
that combines this document's extracted XDR with the RFC 7863
XDR applies these amendments at the union's extension point.

~~~ xdr
   /// /* nfs_argop4 amendment block */
   ///
   /// case OP_CHUNK_COMMIT: CHUNK_COMMIT4args opchunkcommit;
   /// case OP_CHUNK_ERROR: CHUNK_ERROR4args opchunkerror;
   /// case OP_CHUNK_FINALIZE: CHUNK_FINALIZE4args opchunkfinalize;
   /// case OP_CHUNK_HEADER_READ:
   ///     CHUNK_HEADER_READ4args opchunkheaderread;
   /// case OP_CHUNK_LOCK: CHUNK_LOCK4args opchunklock;
   /// case OP_CHUNK_READ: CHUNK_READ4args opchunkread;
   /// case OP_CHUNK_REPAIRED: CHUNK_REPAIRED4args opchunkrepaired;
   /// case OP_CHUNK_ROLLBACK: CHUNK_ROLLBACK4args opchunkrollback;
   /// case OP_CHUNK_UNLOCK: CHUNK_UNLOCK4args opchunkunlock;
   /// case OP_CHUNK_WRITE: CHUNK_WRITE4args opchunkwrite;
   /// case OP_CHUNK_WRITE_REPAIR:
   ///     CHUNK_WRITE_REPAIR4args opchunkwriterepair;
   /// case OP_TRUST_STATEID: TRUST_STATEID4args optruststateid;
   /// case OP_REVOKE_STATEID: REVOKE_STATEID4args oprevokestateid;
   /// case OP_BULK_REVOKE_STATEID:
   ///     BULK_REVOKE_STATEID4args opbulkrevokestateid;
   /// case OP_CHUNK_ESCROW_INSTALL:
   ///     CHUNK_ESCROW_INSTALL4args opchunkescrowinstall;
   /// case OP_CHUNK_ESCROW_RELEASE:
   ///     CHUNK_ESCROW_RELEASE4args opchunkescrowrelease;
   /// case OP_CHUNK_ESCROW_ENUMERATE:
   ///     CHUNK_ESCROW_ENUMERATE4args opchunkescrowenumerate;
   /// case OP_CHUNK_ESCROW_TAKEOVER:
   ///     CHUNK_ESCROW_TAKEOVER4args opchunkescrowtakeover;
~~~
{: #fig-nfs_argop4-amend title="nfs_argop4 amendment block"}

~~~ xdr
   /// /* nfs_resop4 amendment block */
   ///
   /// case OP_CHUNK_COMMIT: CHUNK_COMMIT4res opchunkcommit;
   /// case OP_CHUNK_ERROR: CHUNK_ERROR4res opchunkerror;
   /// case OP_CHUNK_FINALIZE: CHUNK_FINALIZE4res opchunkfinalize;
   /// case OP_CHUNK_HEADER_READ:
   ///     CHUNK_HEADER_READ4res opchunkheaderread;
   /// case OP_CHUNK_LOCK: CHUNK_LOCK4res opchunklock;
   /// case OP_CHUNK_READ: CHUNK_READ4res opchunkread;
   /// case OP_CHUNK_REPAIRED: CHUNK_REPAIRED4res opchunkrepaired;
   /// case OP_CHUNK_ROLLBACK: CHUNK_ROLLBACK4res opchunkrollback;
   /// case OP_CHUNK_UNLOCK: CHUNK_UNLOCK4res opchunkunlock;
   /// case OP_CHUNK_WRITE: CHUNK_WRITE4res opchunkwrite;
   /// case OP_CHUNK_WRITE_REPAIR:
   ///     CHUNK_WRITE_REPAIR4res opchunkwriterepair;
   /// case OP_TRUST_STATEID: TRUST_STATEID4res optruststateid;
   /// case OP_REVOKE_STATEID: REVOKE_STATEID4res oprevokestateid;
   /// case OP_BULK_REVOKE_STATEID:
   ///     BULK_REVOKE_STATEID4res opbulkrevokestateid;
   /// case OP_CHUNK_ESCROW_INSTALL:
   ///     CHUNK_ESCROW_INSTALL4res opchunkescrowinstall;
   /// case OP_CHUNK_ESCROW_RELEASE:
   ///     CHUNK_ESCROW_RELEASE4res opchunkescrowrelease;
   /// case OP_CHUNK_ESCROW_ENUMERATE:
   ///     CHUNK_ESCROW_ENUMERATE4res opchunkescrowenumerate;
   /// case OP_CHUNK_ESCROW_TAKEOVER:
   ///     CHUNK_ESCROW_TAKEOVER4res opchunkescrowtakeover;
~~~
{: #fig-nfs_resop4-amend title="nfs_resop4 amendment block"}

Operations 78 through 88 (the CHUNK operations) are sent by
clients to storage devices on the data path.  Operations 89
through 91 (TRUST_STATEID, REVOKE_STATEID, BULK_REVOKE_STATEID)
and operations 92 through 95 (CHUNK_ESCROW_INSTALL,
CHUNK_ESCROW_RELEASE, CHUNK_ESCROW_ENUMERATE,
CHUNK_ESCROW_TAKEOVER) are sent by the metadata server to
storage devices on the metadata-server-to-data-server control session (see
{{sec-tight-coupling-control-session}}); they MUST NOT be sent by
pNFS clients.  The escrow control-plane operations (92 through
95) are available on the metadata-server-to-data-server control session under either
loose- or tight coupling deployment; the tight coupling section
is cited for its description of the session itself, not to
restrict availability to the tight coupling profile.

All CHUNK operations MUST be issued under an active flexible
file v2 layout obtained via LAYOUTGET against the metadata
server.  Because encodings that use CHUNK operations require tight coupling (see
the three constraints in {{sec-ff_device_addr4}}), the presented
stateid is the tight coupling registered layout stateid, and the
data server MUST validate it against its per-file trust table:
a stateid not present in the trust table MUST be rejected with
NFS4ERR_BAD_STATEID per {{sec-TRUST_STATEID}}.  The anonymous
stateid is reserved for PASSTHROUGH mirrors under loose coupling
({{sec-encoding-negotiation}}) and MUST NOT appear on a CHUNK
operation; a data server receiving a CHUNK operation with the
anonymous stateid MUST reject it with NFS4ERR_BAD_STATEID.

The chunk envelope's safety properties (atomicity via
chunk_guard4 CAS, integrity via checksum, lock continuity across
revocation) depend on metadata-server coordination of layout
grants, guard generation, and lock escrow.  A client that issues
CHUNK operations outside an active layout is operating outside
this specification; the data server's behavior in that case is
undefined.  See {{sec-system-model-chunk-not-block}} for the
distinction between the CHUNK operations and a generic block I/O
interface.

   | Operation              | Number | Target Server     | Description |
   | ---
   | CHUNK_COMMIT           | 78     | data server (client)       | {{sec-CHUNK_COMMIT}} |
   | CHUNK_ERROR            | 79     | data server (client)       | {{sec-CHUNK_ERROR}} |
   | CHUNK_FINALIZE         | 80     | data server (client)       | {{sec-CHUNK_FINALIZE}} |
   | CHUNK_HEADER_READ      | 81     | data server (client)       | {{sec-CHUNK_HEADER_READ}} |
   | CHUNK_LOCK             | 82     | data server (client)       | {{sec-CHUNK_LOCK}} |
   | CHUNK_READ             | 83     | data server (client)       | {{sec-CHUNK_READ}} |
   | CHUNK_REPAIRED         | 84     | data server (client)       | {{sec-CHUNK_REPAIRED}} |
   | CHUNK_ROLLBACK         | 85     | data server (client)       | {{sec-CHUNK_ROLLBACK}} |
   | CHUNK_UNLOCK           | 86     | data server (client)       | {{sec-CHUNK_UNLOCK}} |
   | CHUNK_WRITE            | 87     | data server (client)       | {{sec-CHUNK_WRITE}} |
   | CHUNK_WRITE_REPAIR     | 88     | data server (client)       | {{sec-CHUNK_WRITE_REPAIR}} |
   | TRUST_STATEID          | 89     | data server (metadata server control)  | {{sec-TRUST_STATEID}} |
   | REVOKE_STATEID         | 90     | data server (metadata server control)  | {{sec-REVOKE_STATEID}} |
   | BULK_REVOKE_STATEID    | 91     | data server (metadata server control)  | {{sec-BULK_REVOKE_STATEID}} |
   | CHUNK_ESCROW_INSTALL   | 92     | data server (metadata server control)  | {{sec-CHUNK_ESCROW_INSTALL}} |
   | CHUNK_ESCROW_RELEASE   | 93     | data server (metadata server control)  | {{sec-CHUNK_ESCROW_RELEASE}} |
   | CHUNK_ESCROW_ENUMERATE | 94     | data server (metadata server control)  | {{sec-CHUNK_ESCROW_ENUMERATE}} |
   | CHUNK_ESCROW_TAKEOVER  | 95     | data server (metadata server control)  | {{sec-CHUNK_ESCROW_TAKEOVER}} |
{: #tbl-protocol-ops title="Protocol OPs"}

## Bounds on Chunk-Operation Arrays {#sec-chunk-op-bounds}

The chunk-lifecycle operations (CHUNK_WRITE, CHUNK_WRITE_REPAIR,
CHUNK_READ, CHUNK_FINALIZE, CHUNK_COMMIT, CHUNK_ROLLBACK,
CHUNK_LOCK, CHUNK_UNLOCK, CHUNK_ERROR, CHUNK_REPAIRED,
CHUNK_HEADER_READ) carry variable-length arrays of chunks,
owners, status codes, checksums, and payloads.  To bound
allocation and to guarantee that a valid request always has an
encodable response, this document defines the following
protocol maxima:

~~~ xdr
   ///
   /// const CHUNK_MAX_CHUNKS_PER_OP     = 4096;
   /// const CHUNK_MAX_PAYLOAD_BYTES     = 4194304;
   /// const CHUNK_MAX_CHECKSUMS_PER_OP  = 4096;
   /// const CHUNK_MAX_OWNERS_PER_OP     = 4096;
   /// const CHUNK_MAX_STATUS_PER_OP     = 4096;
   ///
~~~
{: #fig-chunk-op-bounds title="Chunk-operation array maxima" }

`CHUNK_MAX_CHUNKS_PER_OP` is the maximum number of chunks
addressed by a single CHUNK_WRITE, CHUNK_WRITE_REPAIR,
CHUNK_READ, CHUNK_FINALIZE, CHUNK_COMMIT, CHUNK_ROLLBACK, or
CHUNK_LOCK request; it bounds cwa_co_ids, cra_ranges, cca_chunks,
cfa_chunks, cra_chunks (CHUNK_ROLLBACK), and the equivalent
arrays in the other operations.  `CHUNK_MAX_PAYLOAD_BYTES`
bounds the aggregate opaque payload (cwa_chunks, cwra_chunks,
and the concatenated cr_chunk bytes returned in
CHUNK_READ4resok).  `CHUNK_MAX_CHECKSUMS_PER_OP`,
`CHUNK_MAX_OWNERS_PER_OP`, and `CHUNK_MAX_STATUS_PER_OP` bound
the co-indexed result and argument arrays with matching
cardinality; each MUST equal the request's chunk count on
success, and MUST be present with the requested cardinality on
failures for positional correlation.

A data server MUST reject a request whose array length exceeds
any of these maxima with NFS4ERR_INVAL before performing any
mutation.  A data server MUST also verify, before performing
any mutation, that the response it will construct fits within
the session's negotiated `ca_maxresponsesize` (Section 18.36 of
{{RFC8881}}); if the mandatory response arrays (per-chunk
status, per-chunk owner, per-chunk checksum, and payload where
applicable) would exceed `ca_maxresponsesize`, the data server
MUST reject with NFS4ERR_TOOSMALL and MUST NOT partially
process the request.  The client is expected to split the
request across multiple compounds when either bound is reached.

Short processing (a data server returning fewer chunks than
requested at its discretion) is NOT permitted for the
lifecycle operations because the co-indexed result arrays would
lose positional correlation.  A data server that cannot process
all requested chunks MUST reject the entire request; the client
retries with a smaller batch.

## Operation 78: CHUNK_COMMIT - Activate Cached Chunk Data {#sec-CHUNK_COMMIT}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_COMMIT4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cca_stateid;
   ///     offset4         cca_offset;
   ///     count4          cca_count;
   ///     chunk_owner4    cca_chunks<>;
   /// };
~~~
{: #fig-CHUNK_COMMIT4args title="XDR for CHUNK_COMMIT4args" }

### RESULTS

~~~ xdr
   /// struct CHUNK_COMMIT4resok {
   ///     verifier4       ccr_writeverf;
   ///     nfsstat4        ccr_status<>;
   /// };
~~~
{: #fig-CHUNK_COMMIT4resok title="XDR for CHUNK_COMMIT4resok" }

~~~ xdr
   /// union CHUNK_COMMIT4res switch (nfsstat4 ccr_status) {
   ///     case NFS4_OK:
   ///         CHUNK_COMMIT4resok   ccr_resok4;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_COMMIT4res title="XDR for CHUNK_COMMIT4res" }

### DESCRIPTION

The CHUNK_COMMIT operation is based upon the NFSv4.1 COMMIT
operation (see Section 18.3 of {{RFC8881}}) and similarly
commits previously written data to stable storage on the
regular file identified by the current filehandle, with the
difference that CHUNK_COMMIT operates on the chunk
coordinate system used by Flexible File Version 2 layouts
rather than on the byte coordinate system, and that
CHUNK_COMMIT advances each named chunk through the chunk
state machine from FINALIZED to COMMITTED
({{fig-chunk-state-machine}}) rather than acting on a byte
range without a state-machine context.

The client provides cca_offset and cca_count to bound the
chunk range, and cca_chunks to name the specific
(chunk_owner4) generations within that range to commit:

cca_offset:
:  starting chunk index in the file (not a byte offset).

cca_count:
:  number of chunks the range covers, starting at
   cca_offset.  When cca_count is zero, the client MUST
   also supply an empty cca_chunks array, and the data
   server returns NFS4_OK with an empty ccr_status array.
   A cca_offset beyond the data server's highest chunk
   with a non-zero cca_count is not itself an error at the
   operation level: the data server evaluates each
   cca_chunks entry per its normal per-entry rules and
   returns the co-indexed ccr_status.

cca_chunks:
:  an array of chunk_owner4 entries
   ({{fig-chunk_owner4}}) naming the specific
   (co_cohort_id, co_client_id, co_id) generations to
   commit.  For each entry the data server looks up the
   chunk index it associated with the complete
   (co_cohort_id, co_client_id, co_id) triple when the
   client wrote it via CHUNK_WRITE or
   CHUNK_WRITE_REPAIR.  That recorded chunk index MUST
   lie in [cca_offset, cca_offset + cca_count); if the
   triple does not match any recorded owner association
   on this data server for this file, or the recorded
   chunk index lies outside the requested range, the
   entry is rejected with NFS4ERR_INVAL in the
   corresponding ccr_status slot.  The co_id itself is
   opaque per {{sec-chunk_owner4}} and is NOT compared
   numerically with cca_offset or cca_count.  The
   reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   co_client_id of any cca_chunks entry; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.

cca_offset and cca_count are NOT redundant with
cca_chunks: the owner triples in cca_chunks name specific
generations (which the data server correlates via its
recorded owner-to-index association), while cca_offset
and cca_count bound the intended chunk-index scope of the
operation.  A chunk index MAY have multiple persisted
generations at the moment CHUNK_COMMIT arrives -- an
older COMMITTED generation retained for the rollback
invariant ({{sec-system-model-consistency}}) alongside a
newer FINALIZED successor.  cca_chunks selects which
(co_cohort_id, co_client_id, co_id) triple to advance to
COMMITTED at each affected index; cca_offset and
cca_count let the data server reject malformed requests
that name generations whose recorded chunk index lies
outside the intended commit window.

The CHUNK_COMMIT result reports the outcome per chunk in
the same order as cca_chunks:

ccr_writeverf:
:  a verifier identifying the data server's incarnation
   at the time the commit completed.  A client compares
   ccr_writeverf to the cwr_writeverf returned by the
   prior CHUNK_WRITE ({{sec-CHUNK_WRITE}}) to detect a
   data server restart that lost UNSTABLE4 writes
   between the write and the commit; on a mismatch the
   client MUST re-issue the CHUNK_WRITE before any
   committed bytes are considered durable.
   ccr_writeverf changes on every data server restart
   that loses uncommitted state.

ccr_status:
:  per-chunk commit status, one entry per cca_chunks
   entry, co-indexed.  NFS4_OK indicates that the named
   chunk is COMMITTED on return.  Other per-entry
   failure codes are described in
   "Interaction with CHUNK_FINALIZE" and "Interaction
   with a Locked Chunk" below.  The top-level
   CHUNK_COMMIT status is NFS4_OK as long as the data
   server could evaluate each cca_chunks entry;
   per-chunk failures are reported in ccr_status rather
   than by failing the whole operation.  The top-level
   status returns a non-OK code only when the request
   could not be evaluated at all (for example,
   NFS4ERR_BADXDR, NFS4ERR_SERVERFAULT).

Like CHUNK_READ ({{sec-CHUNK_READ}}) and CHUNK_WRITE
({{sec-CHUNK_WRITE}}), CHUNK_COMMIT carries an explicit
layout stateid in cca_stateid.  The data server authorizes
CHUNK_COMMIT by validating cca_stateid against the file
identified by the current filehandle: cca_stateid MUST be
the layout stateid the metadata server issued to the
caller for the current filehandle, or the special anonymous
stateid (see below).  Under trusted stateid tight coupling
({{sec-TRUST_STATEID}}), the data server rejects
CHUNK_COMMIT with NFS4ERR_BAD_STATEID unless cca_stateid
is present in the data server's trust table for the
current filehandle.  The explicit field ensures that a
CHUNK_COMMIT in its own standalone compound (typical for
recovery and pipelined lifecycle operations) carries the
authorization the data server needs without depending on
any prior operation's implicit state.  Passing the special
anonymous stateid is permitted only when the underlying
security regime authorizes an unattributed writer (that is,
when tight coupling is not in force and the deployment's
access-control policy permits it).

If the current filehandle is not an ordinary file, an
error MUST be returned.  If the current filehandle
represents an object of type NF4DIR, NFS4ERR_ISDIR is
returned.  If the current filehandle designates a
symbolic link, NFS4ERR_SYMLINK is returned.  In all
other cases of non-regular-file filehandles,
NFS4ERR_WRONG_TYPE is returned.

#### Interaction with CHUNK_FINALIZE

CHUNK_COMMIT transitions a chunk from FINALIZED to COMMITTED
(see {{sec-system-model-chunk-state}}).  A chunk MUST have
previously been transitioned from PENDING to FINALIZED via
CHUNK_FINALIZE before CHUNK_COMMIT is accepted:

-  If the target chunk is PENDING (i.e., the writer never
   issued CHUNK_FINALIZE), the data server MUST reject the
   CHUNK_COMMIT entry for that chunk with
   NFS4ERR_PAYLOAD_NOT_ATOMIC in the corresponding
   ccr_status slot.  The writer is expected to either issue
   CHUNK_FINALIZE to advance the state or CHUNK_ROLLBACK to
   abandon the PENDING generation.

-  If the target chunk is EMPTY (no generation to commit), the
   data server MUST reject with NFS4ERR_PAYLOAD_NOT_ATOMIC
   for that chunk.

-  If the target chunk is already COMMITTED at the generation
   identified by the cca_chunks entry's owner triple
   (co_cohort_id, co_client_id, co_id), the
   CHUNK_COMMIT is idempotent and MUST succeed.  Idempotence
   preserves the NFSv4 COMMIT contract for duplicate-request
   retransmission.

-  If the target chunk is FINALIZED at a different generation
   than the one named in the cca_chunks entry, the data server
   MUST reject with NFS4ERR_CHUNK_GUARDED.  A client that sees
   this has lost a race and SHOULD re-read the chunk (see
   {{sec-chunk_guard4}}).

#### Pipelining Considerations

The three-step CHUNK_WRITE -> CHUNK_FINALIZE -> CHUNK_COMMIT
sequence MAY be pipelined within a single NFSv4.2 compound
(see Section 12.8 of {{RFC8881}}) in single writer mode, where
no other writer can race the client's per-chunk transitions
and the CHUNK_WRITE per-block status array reports only
local-failure cases (NFS4ERR_NOSPC, NFS4ERR_IO, and so on).

Same-compound pipelining is NOT RECOMMENDED in multiple-writer
mode.  CHUNK_WRITE reports per-block outcomes in cwr_block_status
({{sec-CHUNK_WRITE}}); a partial-success outcome (some chunks
accepted, others rejected with NFS4ERR_CHUNK_GUARDED on a lost
race) leaves the client without an opportunity to react before
a same-compound CHUNK_FINALIZE / CHUNK_COMMIT proceeds against
whichever chunks happen to be PENDING.  The compound-level
status is NFS4_OK in this case because per-block failures are
reported in the per-op status array rather than as a compound-level
error, so NFSv4 compound short-circuit (Section 2.10.6.4
of {{RFC8881}}) does not stop the trailing ops.  A client that
wants atomic-or-none semantics across multiple chunks MUST
examine the per-block status returned by each CHUNK_WRITE
before issuing the corresponding CHUNK_FINALIZE.

For multi-chunk pipelines in multiple-writer mode, the
recommended pattern is to stagger the three steps across
compounds so each trailing operation acts only on chunks whose
preceding operation's status the client has already inspected:

~~~
Compound A:  SEQUENCE PUTFH CHUNK_WRITE(a)
Compound B:  SEQUENCE PUTFH CHUNK_WRITE(b) CHUNK_FINALIZE(a)
Compound C:  SEQUENCE PUTFH CHUNK_WRITE(c) CHUNK_FINALIZE(b)
                              CHUNK_COMMIT(a)
Compound D:  SEQUENCE PUTFH CHUNK_WRITE(d) CHUNK_FINALIZE(c)
                              CHUNK_COMMIT(b)
...
~~~
{: #fig-staggered-chunk-pipeline title="Staggered three-stage chunk pipeline (multiple-writer mode)"}

In each compound, the CHUNK_WRITE acts on the trailing chunk
the client wants to enqueue next; the CHUNK_FINALIZE operates
on a chunk whose CHUNK_WRITE the client has already inspected
in a previous compound; the CHUNK_COMMIT operates on a chunk
whose CHUNK_FINALIZE the client has already inspected.  If
any per-block status in compound N reports a guard loss or
other failure, the client abandons the affected chunk (via
CHUNK_ROLLBACK in compound N+1 or later) without ever issuing
the trailing FINALIZE / COMMIT for it.

This pattern adds two compounds of latency between a chunk's
write and its commit (one for the FINALIZE wait, one for the
COMMIT wait), but provides the client with the per-step
inspection point required for atomic-or-none multi-chunk
writes under contention.

#### Interaction with a Locked Chunk

When a chunk is locked via CHUNK_LOCK (see {{sec-CHUNK_LOCK}}),
CHUNK_COMMIT is permitted only when the submitter owns the
lock -- that is, when the stateid carried on the compound
matches the lock holder's stateid (or is an
CHUNK_LOCK_FLAGS_ADOPT-transferred continuation):

-  The owning writer MAY issue CHUNK_COMMIT; the chunk
   transitions from FINALIZED to COMMITTED normally.

-  A non-owning client MUST receive NFS4ERR_CHUNK_LOCKED in
   the corresponding ccr_status slot.  The chunk's state is
   not changed.

-  During repair, the metadata-server escrow owner
   (CHUNK_GUARD_CLIENT_ID_MDS, see {{sec-chunk_guard_mds}})
   holds the lock while the repair actor adopts it via
   CHUNK_LOCK_FLAGS_ADOPT.  CHUNK_COMMIT during the escrow
   window is permitted only to the holder of the adopted
   lock.

This rule is what {{sec-system-model-consistency}} calls
"lock continuity across revocation": the COMMIT privilege
follows the lock without gaps in which a non-owner could race.

### RESPONSE CODES

NFS4_OK:
:  every named chunk transitioned to COMMITTED.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to commit on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_FHEXPIRED:
:  the current filehandle has expired.

NFS4ERR_INVAL:
:  arguments named chunks outside the file's mirror
   set or in a non-atomic state.

NFS4ERR_IO:
:  an I/O error occurred while persisting the commit.

NFS4ERR_NOTSUPP:
:  the data server does not implement CHUNK_COMMIT.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

NFS4ERR_STALE:
:  the current filehandle no longer identifies a
   valid file.

## Operation 79: CHUNK_ERROR - Report Error on Cached Chunk Data {#sec-CHUNK_ERROR}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_ERROR4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cea_stateid;
   ///     offset4         cea_offset;
   ///     count4          cea_count;
   ///     nfsstat4        cea_error;
   ///     chunk_owner4    cea_owner;
   /// };
~~~
{: #fig-CHUNK_ERROR4args title="XDR for CHUNK_ERROR4args" }

### RESULTS

~~~ xdr
   /// struct CHUNK_ERROR4res {
   ///     nfsstat4        cer_status;
   /// };
~~~
{: #fig-CHUNK_ERROR4res title="XDR for CHUNK_ERROR4res" }

### DESCRIPTION

CHUNK_ERROR allows a client that has detected corruption or
inconsistency in a chunk to report the condition to the data
server, so that the data server can mark the affected chunks
as errored.  Errored chunks are excluded from subsequent
CHUNK_READ responses until they are repaired via
CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}) and the
repair is confirmed via CHUNK_REPAIRED ({{sec-CHUNK_REPAIRED}}).

CHUNK_ERROR has no direct analog in {{RFC8881}}.  The closest
parallel is LAYOUTERROR ({{RFC7862}} Section 15.6), which
reports layout-level errors to the metadata server.
CHUNK_ERROR is the data-path counterpart: it reports a
chunk-level integrity finding directly to the data server so
that the corrupted chunks are quarantined before the
metadata server has had time to coordinate repair.  A client
SHOULD issue CHUNK_ERROR to the data server holding the bad
chunks before issuing LAYOUTERROR to the metadata server.

The client provides:

cea_stateid:
:  the layout stateid the metadata server granted for
   this file.  Under trusted stateid tight coupling
   ({{sec-TRUST_STATEID}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cea_offset:
:  starting chunk index of the affected range (not a byte
   offset).

cea_count:
:  number of chunks the affected range covers, starting at
   cea_offset.

cea_error:
:  the nfsstat4 error code that describes the integrity
   finding.  Typical values include
   NFS4ERR_PAYLOAD_NOT_ATOMIC (the chunk's persisted checksum
   or guard did not match the value the client expected),
   NFS4ERR_IO (the client's CHUNK_READ returned an I/O
   error from this data server), and NFS4ERR_INVAL (the
   chunk's chunk_owner4 did not match the expected
   generation across mirrors).  The data server MAY record
   the supplied error code in operator logs but does not
   otherwise interpret it; the chunk-level effect (mark
   errored) is the same for any cea_error value.

cea_owner:
:  the chunk_owner4 ({{fig-chunk_owner4}}) the client read
   when it observed the error, so the data server can
   record which (co_cohort_id, co_client_id, co_id) generation was
   reported as corrupted.  The reserved sentinels
   CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear in
   cea_owner; see {{sec-chunk_guard_none}} and
   {{sec-chunk_guard_mds}}.

CHUNK_ERROR returns a single top-level status in cer_status;
there is no per-chunk status array because the data server
either accepts the report for the whole range or returns a
top-level error.  Once a CHUNK_ERROR has been accepted, the
affected chunks transition into the errored state described
in {{sec-system-model-chunk-state}}; subsequent CHUNK_READ
operations against those chunks return
NFS4ERR_PAYLOAD_NOT_ATOMIC in the per-chunk cr_status slot
until a successful CHUNK_REPAIRED sequence clears the
errored flag.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the client's chunk error report has been recorded.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to report errors on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_INVAL:
:  the reported chunk range or error code was not
   recognized.

NFS4ERR_NOTSUPP:
:  the data server does not implement CHUNK_ERROR.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 80: CHUNK_FINALIZE - Transition Chunks from Pending to Finalized {#sec-CHUNK_FINALIZE}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_FINALIZE4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cfa_stateid;
   ///     offset4         cfa_offset;
   ///     count4          cfa_count;
   ///     chunk_owner4    cfa_chunks<>;
   /// };
~~~
{: #fig-CHUNK_FINALIZE4args title="XDR for CHUNK_FINALIZE4args" }

### RESULTS

~~~ xdr
   /// struct CHUNK_FINALIZE4resok {
   ///     verifier4       cfr_writeverf;
   ///     nfsstat4        cfr_status<>;
   /// };
~~~
{: #fig-CHUNK_FINALIZE4resok title="XDR for CHUNK_FINALIZE4resok" }

~~~ xdr
   /// union CHUNK_FINALIZE4res switch (nfsstat4 cfr_status) {
   ///     case NFS4_OK:
   ///         CHUNK_FINALIZE4resok   cfr_resok4;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_FINALIZE4res title="XDR for CHUNK_FINALIZE4res" }

### DESCRIPTION

CHUNK_FINALIZE transitions chunks from the PENDING state (set
by CHUNK_WRITE, see {{sec-CHUNK_WRITE}}) to the FINALIZED
state in the chunk state machine ({{fig-chunk-state-machine}}).
A FINALIZED chunk is visible on the owning stateid for reads
({{sec-system-model-consistency}}) and is eligible for
CHUNK_COMMIT ({{sec-CHUNK_COMMIT}}); the FINALIZED transition
is the writer's signal that it will issue no further
CHUNK_WRITEs for the named (co_cohort_id, co_client_id, co_id)
generation of each chunk.

CHUNK_FINALIZE has no direct analog in {{RFC8881}}: the COMMIT
operation in {{RFC8881}} Section 18.3 combines the "no more
writes" signal and the "make durable and globally visible"
step into one operation; the Flexible File Version 2 chunk
lifecycle separates them so a writer in multiple-writer mode
can validate the per-chunk acceptance status reported by
CHUNK_WRITE before committing any chunk to durable storage
(see "Pipelining Considerations" in
{{sec-CHUNK_COMMIT}}).

The client provides cfa_offset and cfa_count to bound the
chunk range, and cfa_chunks to name the specific
(chunk_owner4) generations within that range to finalize:

cfa_offset:
:  starting chunk index in the file (not a byte offset).

cfa_count:
:  number of chunks the range covers, starting at
   cfa_offset.  When cfa_count is zero, the client MUST
   also supply an empty cfa_chunks array, and the data
   server returns NFS4_OK with an empty cfr_status array.
   A cfa_offset beyond the data server's highest chunk
   with a non-zero cfa_count is not itself an error at the
   operation level: the data server evaluates each
   cfa_chunks entry per its normal per-entry rules and
   returns the co-indexed cfr_status.

cfa_chunks:
:  an array of chunk_owner4 entries
   ({{fig-chunk_owner4}}) naming the specific
   (co_cohort_id, co_client_id, co_id) generations to
   finalize.  For each entry the data server looks up
   the chunk index it associated with the complete
   (co_cohort_id, co_client_id, co_id) triple when the
   client wrote it via CHUNK_WRITE or
   CHUNK_WRITE_REPAIR.  That recorded chunk index MUST
   lie in [cfa_offset, cfa_offset + cfa_count); if the
   triple does not match any recorded owner association
   on this data server for this file, or the recorded
   chunk index lies outside the requested range, the
   entry is rejected with NFS4ERR_INVAL in the
   corresponding cfr_status slot.  The co_id itself is
   opaque per {{sec-chunk_owner4}} and is NOT compared
   numerically with cfa_offset or cfa_count.  The
   reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   co_client_id of any cfa_chunks entry; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.

The CHUNK_FINALIZE result reports the outcome per chunk in
the same order as cfa_chunks:

cfr_writeverf:
:  a verifier identifying the data server's incarnation
   at the time the finalization completed.  Semantics
   match cwr_writeverf in CHUNK_WRITE
   ({{sec-CHUNK_WRITE}}): a client that observes a
   different writeverf on a subsequent CHUNK_COMMIT MUST
   re-issue the CHUNK_WRITE before treating any of the
   finalized chunks as durable.

cfr_status:
:  per-chunk finalization status, one entry per
   cfa_chunks entry, co-indexed.  NFS4_OK indicates that
   the named chunk is FINALIZED on return.  Other
   per-entry failure cases:

   *  NFS4ERR_INVAL -- the named generation is not in the
      PENDING state at its recorded chunk index (the
      chunk is EMPTY, FINALIZED at a different generation,
      or COMMITTED), or the triple does not match any
      recorded owner association, or the recorded chunk
      index lies outside [cfa_offset, cfa_offset +
      cfa_count).

   *  NFS4ERR_CHUNK_GUARDED -- the chunk is PENDING but
      the current PENDING owner is a different
      (co_cohort_id, co_client_id) than the one named in
      the cfa_chunks entry.  A client that sees this has
      lost a race with another writer; see
      {{sec-chunk_guard4}}.

   *  NFS4ERR_CHUNK_LOCKED -- the chunk is locked by a
      CHUNK_LOCK ({{sec-CHUNK_LOCK}}) held by a different
      stateid; the finalize is rejected.

   The top-level CHUNK_FINALIZE status is NFS4_OK as long
   as the data server could evaluate each cfa_chunks
   entry; per-chunk failures are reported in cfr_status
   rather than by failing the whole operation.  The
   top-level status returns a non-OK code only when the
   request could not be evaluated at all (for example,
   NFS4ERR_BADXDR, NFS4ERR_SERVERFAULT).

CHUNK_FINALIZE serves as the CRC validation checkpoint for
the chunk lifecycle.  The data server SHOULD have validated
each chunk's checksum against the value supplied in cwa_checksums
at CHUNK_WRITE time; the FINALIZE transition persists the
chunk metadata (CRC, owner, state) to stable storage so it
survives a data server restart.  An implementation MAY
defer some metadata persistence to CHUNK_COMMIT instead of
CHUNK_FINALIZE; in that case the FINALIZED state is
recovered by replay of the data server's local journal on
restart.

A chunk that has been FINALIZED but not yet COMMITTED MAY
be rolled back via CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}}),
which returns the chunk to the EMPTY state (or to the
prior COMMITTED generation, if one exists).

Like CHUNK_COMMIT ({{sec-CHUNK_COMMIT}}), CHUNK_FINALIZE
carries an explicit layout stateid in cfa_stateid.  The
data server authorizes CHUNK_FINALIZE by validating
cfa_stateid against the file identified by the current
filehandle: cfa_stateid MUST be the layout stateid the
metadata server issued to the caller for the current
filehandle, or the special anonymous stateid (see below).
Under trusted stateid tight coupling
({{sec-TRUST_STATEID}}), the data server rejects
CHUNK_FINALIZE with NFS4ERR_BAD_STATEID unless
cfa_stateid is present in the data server's trust table
for the current filehandle.  The explicit field ensures
that a CHUNK_FINALIZE in its own standalone compound
(typical for pipelined and recovery cases) carries the
authorization the data server needs.  Passing the
special anonymous stateid is permitted only when the
underlying security regime authorizes an unattributed
writer.

If the current filehandle is not an ordinary file, an
error MUST be returned.  If the current filehandle
represents an object of type NF4DIR, NFS4ERR_ISDIR is
returned.  If the current filehandle designates a
symbolic link, NFS4ERR_SYMLINK is returned.  In all
other cases of non-regular-file filehandles,
NFS4ERR_WRONG_TYPE is returned.

### RESPONSE CODES

NFS4_OK:
:  every named chunk transitioned from PENDING to
   FINALIZED.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to finalize on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_FHEXPIRED:
:  the current filehandle has expired.

NFS4ERR_INVAL:
:  arguments named chunks not in PENDING or outside
   the file's mirror set.

NFS4ERR_IO:
:  an I/O error occurred while persisting the
   transition.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   CHUNK_FINALIZE.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

NFS4ERR_STALE:
:  the current filehandle no longer identifies a
   valid file.

## Operation 81: CHUNK_HEADER_READ - Read Chunk Header from File {#sec-CHUNK_HEADER_READ}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_HEADER_READ4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4    chra_stateid;
   ///     offset4     chra_offset;
   ///     count4      chra_count;
   /// };
~~~
{: #fig-CHUNK_HEADER_READ4args title="XDR for CHUNK_HEADER_READ4args" }

### RESULTS

~~~ xdr
   /// /* Upper bound on both chra_count and each of the
   ///  * four co-indexed response arrays.  Bounds argument
   ///  * range width and response-array width together so
   ///  * that a caller cannot request an unbounded scan
   ///  * and a data server cannot construct an unbounded
   ///  * response. */
   /// const CHUNK_HEADER_READ_MAX4 = 1024;
   ///
   /// struct retained_predecessor4 {
   ///     chunk_owner4  rp_owner;
   /// };
   ///
   /// enum retained_generation_disposition4 {
   ///     RETAINED_GENERATION_DISPOSITION_ABSENT   = 0,
   ///     RETAINED_GENERATION_DISPOSITION_PRESENT  = 1,
   ///     RETAINED_GENERATION_DISPOSITION_ERRORED  = 2
   /// };
   ///
   /// union optional_retained4
   ///     switch (retained_generation_disposition4
   ///             disposition) {
   /// case RETAINED_GENERATION_DISPOSITION_ABSENT:
   ///     void;
   /// case RETAINED_GENERATION_DISPOSITION_PRESENT:
   ///     retained_predecessor4  restorable;
   /// case RETAINED_GENERATION_DISPOSITION_ERRORED:
   ///     retained_predecessor4  errored;
   /// };
   ///
   /// struct CHUNK_HEADER_READ4resok {
   ///     bool                chrr_eof;
   ///     nfsstat4
   ///         chrr_status<CHUNK_HEADER_READ_MAX4>;
   ///     bool
   ///         chrr_locked<CHUNK_HEADER_READ_MAX4>;
   ///     chunk_owner4
   ///         chrr_chunks<CHUNK_HEADER_READ_MAX4>;
   ///     chunk_guard4
   ///         chrr_guards<CHUNK_HEADER_READ_MAX4>;
   ///     optional_retained4
   ///         chrr_predecessors<CHUNK_HEADER_READ_MAX4>;
   /// };
~~~
{: #fig-CHUNK_HEADER_READ4resok title="XDR for CHUNK_HEADER_READ4resok" }

~~~ xdr
   /// union CHUNK_HEADER_READ4res switch (nfsstat4 chrr_status) {
   ///     case NFS4_OK:
   ///         CHUNK_HEADER_READ4resok     chrr_resok4;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_HEADER_READ4res title="XDR for CHUNK_HEADER_READ4res" }

### DESCRIPTION

CHUNK_HEADER_READ returns the per-chunk metadata
(chunk_owner4, chunk_guard4, lock state, and per-chunk
status) for a range of chunks in the target data file
without returning the chunk payloads.  The operation enables clients and
repair coordinators to inspect chunk lifecycle and
ownership cheaply, without the data-transfer cost of
CHUNK_READ ({{sec-CHUNK_READ}}).  CHUNK_HEADER_READ has
no direct analog in {{RFC8881}}; it is the chunk-protocol
counterpart of a stat-like fast probe and exists because
chunks are first-class state-bearing objects whose
ownership, lock state, and lifecycle status are not
recoverable from a byte-offset query.

The client provides:

chra_stateid:
:  the layout stateid the metadata server granted for
   this file.  Under trusted stateid tight coupling
   ({{sec-TRUST_STATEID}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

chra_offset:
:  starting chunk index of the range to inspect (not a
   byte offset).

chra_count:
:  number of chunks the inspection range covers,
   starting at chra_offset.  chra_count MUST NOT
   exceed CHUNK_HEADER_READ_MAX4; a request that
   exceeds the bound is rejected with NFS4ERR_INVAL.
   The bound protects the data server against
   arbitrarily large response construction.

The CHUNK_HEADER_READ result returns five co-indexed
arrays, one entry per chunk in the requested range in
chunk-offset order from chra_offset:

chrr_eof:
:  TRUE if the requested range extended at or past the
   data server's last chunk for this file.  Same
   per-data-server semantics as crr_eof in CHUNK_READ
   ({{sec-CHUNK_READ}}).

chrr_status:
:  per-chunk lifecycle state encoded as an nfsstat4
   (see "Per-Chunk Status Encoding" below).

chrr_locked:
:  per-chunk boolean.  TRUE if the chunk currently has a
   CHUNK_LOCK ({{sec-CHUNK_LOCK}}) held by some
   chunk_owner4; FALSE otherwise.  Lock state is
   reported orthogonally to chrr_status so that a locked
   chunk still surfaces its lifecycle state and
   chunk_owner4 to the inspector.

chrr_chunks:
:  per-chunk chunk_owner4 ({{fig-chunk_owner4}}).  For a
   chunk whose chrr_status is NFS4_OK the field is the
   COMMITTED generation's owner.  For
   NFS4ERR_PAYLOAD_NOT_ATOMIC the field is the writer of
   the in-progress (PENDING or FINALIZED) generation.
   For NFS4ERR_NOENT (EMPTY chunk) the chunk_owner4 is
   unspecified.

chrr_guards:
:  per-chunk chunk_guard4 ({{fig-chunk_guard4}}) -- the
   (cg_gen_id, cg_client_id) pair the data server holds
   as the chunk's current guard at CHUNK_HEADER_READ
   time.  A caller that intends to update the chunk in
   multiple writer mode uses the corresponding chrr_guards
   entry as the expected prior value for the guard CAS
   ({{sec-multi-writer}}), avoiding the payload cost of
   CHUNK_READ.  For a chunk whose chrr_status is
   NFS4ERR_NOENT (EMPTY) the chunk_guard4 is the
   all-zeros pair (cg_gen_id = 0 and cg_client_id =
   CHUNK_GUARD_CLIENT_ID_NONE, see
   {{sec-chunk_guard_none}}).  chrr_guards is a read-time
   observation; a concurrent writer MAY advance the
   guard between the CHUNK_HEADER_READ response and the
   subsequent CHUNK_WRITE, in which case the CAS returns
   NFS4ERR_CHUNK_GUARDED and the caller re-observes the
   guard per the rollback-and-retry flow in
   {{sec-chunk_guard4}}.

chrr_predecessors:
:  per-chunk immediate-predecessor disposition, one
   optional_retained4 entry per chunk in the returned
   range, co-indexed with chrr_status, chrr_locked, and
   chrr_chunks.  Each entry names the read-time state
   of the single most recent retained predecessor of
   the current generation the data server holds for
   that chunk index under the retention scope rule
   ({{sec-system-model-retention-scope}}); the entry's
   discriminant is exactly one of:

   - **RETAINED_GENERATION_DISPOSITION_ABSENT**: the
     data server holds no retained predecessor at
     that index (either the current chrr_chunks
     generation is the only one, or the chunk is
     EMPTY).  The arm carries no owner triple.
   - **RETAINED_GENERATION_DISPOSITION_PRESENT**: the
     data server retains an immediate predecessor
     whose owner triple is carried in the restorable
     arm and whose payload is in the AVAILABLE
     read-time state
     ({{sec-system-model-read-time-status}}).  A
     CHUNK_ROLLBACK naming this owner triple
     satisfies "Rollback of COMMITTED Chunks" case
     (a) ({{sec-CHUNK_ROLLBACK}}).
   - **RETAINED_GENERATION_DISPOSITION_ERRORED**: the
     data server retains the immediate predecessor's
     owner triple (in the errored arm) but its
     payload is in the ERRORED read-time state and
     cannot be restored by CHUNK_ROLLBACK.  A
     CHUNK_ROLLBACK naming this owner triple MUST
     return NFS4ERR_NO_PREDECESSOR
     ({{sec-NFS4ERR_NO_PREDECESSOR}}); the client
     falls back to best-effort reconstruction via
     CHUNK_WRITE_REPAIR
     ({{sec-CHUNK_WRITE_REPAIR}}) with an
     authoritative source of its own choosing.
     The owner triple is disclosed so a caller can
     coordinate reconstruction from surviving
     shards.

   The list is informational and MAY change between
   successive CHUNK_HEADER_READ calls -- the data
   server MAY release a predecessor between calls
   under the retention scope rule.  A caller that
   observes a PRESENT disposition and issues
   CHUNK_ROLLBACK before that release remains
   guaranteed by the composed rollback guarantee
   ({{sec-composed-rollback}}) when it holds a
   qualifying lock or escrow; without such a lock,
   the retention scope MAY release the predecessor
   at any time and a subsequent CHUNK_ROLLBACK MAY
   return NFS4ERR_NO_PREDECESSOR even though a
   previous CHUNK_HEADER_READ observed PRESENT.

Cardinality and short responses:

: All five response arrays are the same length; the data
  server MUST NOT sparsify or truncate one array independently
  of the others.

  The response array length N MAY be smaller than chra_count
  when the requested range extends past the data server's last
  chunk (chrr_eof = TRUE, N = the number of chunks the data
  server holds within the requested range) or when the
  fully-populated response would exceed the session-negotiated
  ca_maxresponsesize (Section 18.36.3 of {{RFC8881}}).  In the
  response-size case the data server returns a short response
  with chrr_eof = FALSE containing as many entries N as fit
  under ca_maxresponsesize minus COMPOUND/RPC overhead; the
  client resumes at chra_offset + N.  If even the minimum
  useful response (a single entry) will not fit, the data
  server returns NFS4ERR_REP_TOO_BIG per {{RFC8881}}; the
  client MUST NOT retry with a smaller chra_count (there is no
  positive integer below 1) and instead uses a session or
  COMPOUND with more available response budget.

The operation has several uses:

Whole-file repair scan:
:  A repair actor selected via CB_CHUNK_REPAIR
   ({{sec-CB_CHUNK_REPAIR}}) walks the affected chunk
   range and uses the per-chunk chunk_owner4 returned by
   each mirror's data server to identify which chunks
   carry an atomic stripe (all k data shards share the
   same chunk_guard4) and which require reconstruction.
   CHUNK_HEADER_READ is the discovery primitive that
   drives the per-chunk decisions described in
   {{sec-repair-multi-writer}}; without it, a repair
   client would have to issue CHUNK_READ to retrieve the
   full payload of every chunk merely to inspect its
   guard.

Client-side recovery from partial writes:
:  After a network disruption or client restart, a writer
   that holds the file's layout MAY issue
   CHUNK_HEADER_READ to learn which of its prior
   CHUNK_WRITEs reached the data server.  Chunks whose
   chunk_owner4 reports the writer's own (co_cohort_id,
   co_client_id) pair are PENDING or FINALIZED and
   recoverable; chunks absent from the response or
   carrying another writer's owner are not.  The writer
   can then re-issue CHUNK_WRITE for the missing chunks
   or CHUNK_ROLLBACK for the abandoned ones without
   reading payloads it has already committed locally.

Read-side atomicity check:
:  Before issuing a multi-chunk CHUNK_READ in
   multiple-writer mode, a client MAY issue
   CHUNK_HEADER_READ to verify that the chunks in the
   target range share a common `(co_cohort_id,
   co_client_id)` pair in chrr_chunks (the cohort-atomicity
   property in
   {{sec-system-model-consistency}}) and MAY additionally
   inspect chrr_guards as a cheaper generation-level
   corroboration.  If the cohort pairs diverge, the
   client knows the read will not be atomic and can
   wait for a writer to commit, retry, or report
   NFS4ERR_PAYLOAD_NOT_ATOMIC via LAYOUTERROR.  This is
   a hint rather than a guarantee: a concurrent writer
   MAY advance a chunk's state between the
   CHUNK_HEADER_READ response and the subsequent
   CHUNK_READ.

Predecessor-guided rollback discovery:
:  A caller preparing a CHUNK_ROLLBACK against a
   COMMITTED chunk inspects the corresponding
   chrr_predecessors entry to decide whether
   CHUNK_ROLLBACK will succeed:
   - **PRESENT**: name the disclosed owner triple
     in the cra_chunks entry of the subsequent
     CHUNK_ROLLBACK.  "Rollback of COMMITTED
     Chunks" case (a) will succeed subject to the
     composed rollback guarantee's continuous-custody
     condition
     ({{sec-composed-rollback}}).
   - **ERRORED**: do NOT issue CHUNK_ROLLBACK
     against the disclosed owner triple.  The
     data server MUST return NFS4ERR_NO_PREDECESSOR
     for that owner; use CHUNK_WRITE_REPAIR
     ({{sec-CHUNK_WRITE_REPAIR}}) directly with a
     reconstructed authoritative source.
     The disclosed owner triple lets the caller
     coordinate reconstruction from other sources.
   - **ABSENT**: no restorable predecessor exists.
     Skip CHUNK_ROLLBACK; use CHUNK_WRITE_REPAIR
     ({{sec-CHUNK_WRITE_REPAIR}}) if reconstruction
     is possible, or defer to a guaranteed-pinning
     mechanism when the caller requires the
     original owner triple be preserved.
   As with the atomicity check, a subsequent
   lifecycle event MAY change a chunk's disposition
   between the CHUNK_HEADER_READ response and the
   CHUNK_ROLLBACK (a PRESENT observation MAY
   become ABSENT if the retention scope releases
   the predecessor and the caller does not hold a
   qualifying lock or escrow).

Lock probe before write:
:  A client MAY issue CHUNK_HEADER_READ and inspect the
   chrr_locked array to discover whether any chunk in
   the target range is currently held by a CHUNK_LOCK
   ({{sec-CHUNK_LOCK}}) before attempting CHUNK_WRITE,
   avoiding the round-trip cost of receiving
   NFS4ERR_CHUNK_LOCKED.  As above, this is a hint; a
   lock MAY be acquired between the header read and the
   write.

CHUNK_HEADER_READ does not change any chunk state.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

#### Per-Chunk Status Encoding

The per-chunk chrr_status field reports the chunk's
lifecycle state encoded as an nfsstat4:

NFS4_OK:
:  the chunk is COMMITTED and the chunk_owner4 in the
   corresponding chrr_chunks slot is the COMMITTED
   generation's owner.

NFS4ERR_PAYLOAD_NOT_ATOMIC:
:  the chunk is PENDING or FINALIZED (a non-globally-visible
   generation is in progress).  The
   chunk_owner4 in the corresponding chrr_chunks slot
   names the writer of that in-progress generation.

NFS4ERR_NOENT:
:  the chunk is EMPTY (no COMMITTED generation has been
   written at this offset).  The chunk_owner4 in the
   corresponding chrr_chunks slot is unspecified.

CHUNK_HEADER_READ never returns NFS4ERR_CHUNK_LOCKED in
chrr_status; lock state is reported orthogonally via
chrr_locked so that locked chunks still surface their
chunk_owner4 to the inspector.

### RESPONSE CODES

NFS4_OK:
:  the chunk headers have been returned.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to read chunk headers on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_FHEXPIRED:
:  the current filehandle has expired.

NFS4ERR_IO:
:  an I/O error occurred while reading chunk headers.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   CHUNK_HEADER_READ.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

NFS4ERR_STALE:
:  the current filehandle no longer identifies a
   valid file.

## Operation 82: CHUNK_LOCK - Lock Cached Chunk Data {#sec-CHUNK_LOCK}

### ARGUMENTS

~~~ xdr
   /// const CHUNK_LOCK_FLAGS_ADOPT    = 0x00000001;
   /// const CHUNK_LOCK_FLAGS_TAKEOVER = 0x00000002;
   ///
   /// union chunk_lock_adopt4 switch (bool cla_adopt) {
   ///     case TRUE:
   ///         escrow_id4      cla_escrow_id;
   ///     case FALSE:
   ///         void;
   /// };
   ///
   /// struct CHUNK_LOCK4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4            cla_stateid;
   ///     offset4             cla_offset;
   ///     count4              cla_count;
   ///     uint32_t            cla_flags;
   ///     chunk_owner4        cla_owner;
   ///     chunk_lock_adopt4   cla_adopt;
   /// };
~~~
{: #fig-CHUNK_LOCK4args title="XDR for CHUNK_LOCK4args" }

### RESULTS

~~~ xdr
   /// union CHUNK_LOCK4res switch (nfsstat4 clr_status) {
   ///     case NFS4_OK:
   ///         void;
   ///     case NFS4ERR_CHUNK_LOCKED:
   ///         chunk_owner4    clr_owner;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_LOCK4res title="XDR for CHUNK_LOCK4res" }

### DESCRIPTION

CHUNK_LOCK acquires an exclusive chunk-range lock on the
range specified by cla_offset and cla_count.  While the
lock is held, CHUNK_WRITE, CHUNK_WRITE_REPAIR,
CHUNK_FINALIZE, CHUNK_COMMIT, CHUNK_ROLLBACK, and
CHUNK_UNLOCK ({{sec-CHUNK_UNLOCK}}) operations on any of
the locked chunks from any other chunk_owner4 receive
NFS4ERR_CHUNK_LOCKED in the corresponding per-chunk
status slot.  The lock is associated with the
chunk_owner4 in cla_owner.

CHUNK_LOCK is loosely analogous to LOCK ({{RFC8881}}
Section 18.10) in that it acquires an exclusive
guard against concurrent modification, but the two
operate on different coordinate systems and use
different naming: LOCK is byte range and stateid-based;
CHUNK_LOCK is chunk-range and chunk_owner4-based.
CHUNK_LOCK is used in multiple-writer mode
({{sec-multi-writer}}) to serialize racing writers on a
common chunk range, and in the repair flow
({{sec-repair-selection}}) to transfer lock ownership
to a repair actor via CHUNK_LOCK_FLAGS_ADOPT.

The client provides:

cla_stateid:
:  the layout stateid the metadata server granted for
   this file.  Under trusted stateid tight coupling
   ({{sec-TRUST_STATEID}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cla_offset:
:  starting chunk index of the lock range (not a byte
   offset).

cla_count:
:  number of chunks the lock range covers, starting at
   cla_offset.

cla_flags:
:  bitmask of CHUNK_LOCK_FLAGS_* values.  Defined:
   CHUNK_LOCK_FLAGS_ADOPT (adopt a metadata-server escrow lock;
   see "Lock Transfer via CHUNK_LOCK_FLAGS_ADOPT" below);
   CHUNK_LOCK_FLAGS_TAKEOVER (transfer ownership of a
   live client-held lock, distinct from adoption; see
   "Live-Client Lock Takeover via
   CHUNK_LOCK_FLAGS_TAKEOVER" below).  The two flags
   are mutually exclusive; a request with both bits set
   MUST be rejected with NFS4ERR_INVAL.  Unknown bits
   MUST be rejected with NFS4ERR_INVAL.

cla_owner:
:  the chunk_owner4 ({{fig-chunk_owner4}}) that will hold
   the lock on success.  The reserved sentinel values
   CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   co_client_id of cla_owner; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.
   (A client requesting CHUNK_LOCK_FLAGS_ADOPT MUST use
   its own co_client_id, not the metadata-server escrow sentinel,
   even when adopting from a metadata-server escrow holder.)

cla_adopt:
:  a discriminated union carrying the escrow_id4
   ({{sec-escrow_id4}}) that identifies the specific
   metadata-server escrow lock the caller is adopting.  When
   cla_flags carries CHUNK_LOCK_FLAGS_ADOPT, cla_adopt
   MUST be the TRUE arm and cla_escrow_id MUST match
   the escrow_id4 the metadata server installed on
   this data server for the requested range (identity
   mismatch is one of the state-level causes of
   NFS4ERR_NO_ADOPTABLE_LOCK per
   {{sec-NFS4ERR_NO_ADOPTABLE_LOCK}}).  When cla_flags
   does not carry CHUNK_LOCK_FLAGS_ADOPT, cla_adopt
   MUST be the FALSE arm.  The two conditions
   (bit-flag value and discriminant value) MUST agree;
   a mismatch is rejected with NFS4ERR_INVAL.

The CHUNK_LOCK result returns:

clr_status:
:  NFS4_OK if the lock was acquired (or transferred via
   ADOPT).  NFS4ERR_CHUNK_LOCKED if one or more chunks
   in the range are already locked and the request does
   not carry CHUNK_LOCK_FLAGS_ADOPT.

clr_owner (NFS4ERR_CHUNK_LOCKED case only):
:  the chunk_owner4 of the current lock holder, so the
   caller can identify the blocking writer.

The lock is released by CHUNK_UNLOCK
({{sec-CHUNK_UNLOCK}}) or implicitly when the holder's
lease expires; on lease expiry without explicit
release, the data server transitions the lock to the
metadata-server escrow owner if the metadata server has revoked
the holder's stateid via REVOKE_STATEID
({{sec-REVOKE_STATEID}}), per the lock-continuity-across-revocation
invariant in
{{sec-system-model-consistency}}.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

#### Lock Transfer via CHUNK_LOCK_FLAGS_ADOPT

The CHUNK_LOCK_FLAGS_ADOPT flag in cla_flags requests an atomic
transfer of lock ownership to cla_owner for every chunk in
[cla_offset, cla_offset+cla_count).  The data server MUST perform
the transfer as a single atomic step per chunk: there is no window
in which the chunk is unlocked.  After a successful ADOPT, subsequent
CHUNK_WRITE, CHUNK_WRITE_REPAIR, CHUNK_ROLLBACK, and CHUNK_UNLOCK
operations MUST present cla_owner as their chunk_owner4.

CHUNK_LOCK_FLAGS_ADOPT is the sole mechanism by which a chunk lock
can change hands without first being released.  The lock ordering
invariant -- that every chunk in a payload transitioning through
repair is held by exactly one owner continuously from failure
detection to repair completion -- depends on it.

CHUNK_LOCK_FLAGS_ADOPT is valid only when the caller has been
selected as the repair actor for the range by the metadata server,
typically via CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}).  A data
server that receives CHUNK_LOCK with the ADOPT flag from a client
that has not been so designated MAY reject the operation with
NFS4ERR_ACCESS.  Because CHUNK_LOCK is a CHUNK operation and
encodings that use CHUNK operations require tight coupling
({{sec-ff_device_addr4}}), the metadata server notifies the data
server of the ADOPT designation via the control protocol (e.g.,
TRUST_STATEID with the new client's stateid or a similar
facility); no loose coupling ADOPT path exists.

The current lock holder at the moment of ADOPT MAY be:

1. Another client whose stateid remains valid (for example, a
   client that has stopped making progress but has not yet lost
   its lease).  The prior owner's PENDING or FINALIZED shards
   remain on disk until the new owner issues CHUNK_WRITE_REPAIR,
   CHUNK_ROLLBACK, or CHUNK_COMMIT.

2. The metadata server itself, acting through the
   CHUNK_GUARD_CLIENT_ID_MDS escrow owner
   ({{sec-chunk_guard_mds}}).  This occurs when the metadata
   server has revoked the prior holder's stateid in a tightly
   coupled deployment.

In either case, ADOPT's effect from the repair actor's
perspective is the same: after the successful return the caller
holds the lock and may drive the range to consistency.

The data server MUST reject CHUNK_LOCK with
CHUNK_LOCK_FLAGS_ADOPT if cla_owner's co_client_id equals
CHUNK_GUARD_CLIENT_ID_MDS -- that value is reserved for server
production and MUST NOT be presented by a client.  The operation
returns NFS4ERR_INVAL in that case.

#### Live-Client Lock Takeover via CHUNK_LOCK_FLAGS_TAKEOVER

The CHUNK_LOCK_FLAGS_TAKEOVER flag in cla_flags requests
an atomic transfer of lock ownership from a currently
live client-held lock to cla_owner, distinct from
CHUNK_LOCK_FLAGS_ADOPT which transfers from an
metadata-server escrow lock.  The two flags are mutually exclusive:
ADOPT names the metadata server's escrow identity via
cla_adopt, while TAKEOVER names another client's
already-held lock and is used only when the metadata
server has designated cla_owner as the successor to a
displaced live client (for example, when a repair
sequence must proceed while the prior writer's session
remains valid).

Under CHUNK_LOCK_FLAGS_TAKEOVER, cla_adopt MUST be the
FALSE arm (there is no escrow identity being adopted);
the metadata server's designation is what authorizes
the transfer, and the data server verifies the
designation by the same coupling-model-dependent
mechanism used for ADOPT above.  A data server that
receives TAKEOVER from a client not designated as
successor MAY reject with NFS4ERR_ACCESS.  As with
ADOPT, TAKEOVER is atomic: no window exists in which
the chunk is unlocked, and after a successful
TAKEOVER subsequent operations on the range MUST
present cla_owner as their chunk_owner4.

### RESPONSE CODES

NFS4_OK:
:  the requested chunk range has been locked.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to lock chunks on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_CHUNK_LOCKED:
:  one or more chunks in the requested
   range are already locked by another writer.

NFS4ERR_INVAL:
:  the requested range was malformed or outside
   the file's mirror set.

NFS4ERR_NOTSUPP:
:  the data server does not implement CHUNK_LOCK.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 83: CHUNK_READ - Read Chunks from File {#sec-CHUNK_READ}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_READ4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4    cra_stateid;
   ///     offset4     cra_offset;
   ///     count4      cra_count;
   /// };
~~~
{: #fig-CHUNK_READ4args title="XDR for CHUNK_READ4args" }

### RESULTS

~~~ xdr
   /// struct read_chunk4 {
   ///     checksum4       cr_checksum;
   ///     uint32_t        cr_effective_len;
   ///     chunk_owner4    cr_owner;
   ///     chunk_guard4    cr_guard;
   ///     uint32_t        cr_payload_id;
   ///     bool            cr_locked;
   ///     nfsstat4        cr_status;
   ///     opaque          cr_chunk<>;
   /// };
~~~
{: #fig-read_chunk4 title="XDR for read_chunk4" }

~~~ xdr
   /// struct CHUNK_READ4resok {
   ///     bool        crr_eof;
   ///     read_chunk4 crr_chunks<>;
   /// };
~~~
{: #fig-CHUNK_READ4resok title="XDR for CHUNK_READ4resok" }

~~~ xdr
   /// union CHUNK_READ4res switch (nfsstat4 crr_status) {
   ///     case NFS4_OK:
   ///          CHUNK_READ4resok     crr_resok4;
   ///     default:
   ///          void;
   /// };
~~~
{: #fig-CHUNK_READ4res title="XDR for CHUNK_READ4res" }

### DESCRIPTION

The CHUNK_READ operation is based upon the NFSv4.1 READ
operation (see Section 18.22 of {{RFC8881}}) and similarly
reads data from the regular file identified by the current
filehandle, with the difference that CHUNK_READ operates on
the chunk coordinate system used by Flexible File Version 2
layouts rather than on the byte coordinate system.

The client provides a cra_offset of where the CHUNK_READ is
to start and a cra_count of how many chunks are to be read.
cra_offset is the starting chunk index in the file (not a
byte offset); the chunk at index N occupies the bytes
[N * chunk_size, (N + 1) * chunk_size) for encodings with a
uniform chunk size, where chunk_size is taken from
ffv2m_striping_unit_size in the file's layout
({{sec-ffv2-mirror4}}).  For encodings whose parity shards
have variable sizes (the Mojette family), the parity-shard
chunks on a given data server may use a smaller per-shard
chunk size; see {{sec-mojette-encoding}}.  cra_count is a
count of chunks to read and not bytes to read.

A cra_offset of zero starts reading at the first chunk of
the file.  If cra_offset is greater than or equal to the
number of chunks the data server holds for this file, the
status NFS4_OK is returned with crr_chunks empty and
crr_eof set to TRUE.

If cra_count is zero, the CHUNK_READ succeeds and returns
zero chunks.  In all situations the data server MAY choose
to return fewer chunks than the client requested; the
client must be prepared to handle a short read and reissue
CHUNK_READ for the remaining chunks.

The CHUNK_READ result is comprised of an array of
read_chunk4, each describing the metadata and payload of
one chunk.  The array entries are in chunk-index order
starting from cra_offset.  Within each read_chunk4
({{fig-read_chunk4}}):

cr_checksum:
:  the checksum4 ({{sec-checksum4}}) the data server
   recomputed over the chunk header and cr_chunk (with the
   checksum field's bytes treated as zero, per the uniform
   coverage rule in {{sec-checksum4}}) at CHUNK_READ time,
   from the persisted value it recorded at CHUNK_FINALIZE
   or CHUNK_COMMIT time.  The cs_algorithm field matches
   the layout's ffv2m_checksum_algorithm
   ({{sec-ffv2-mirror4}}); the cs_value carries the
   computed bytes at the length registered for that
   algorithm.  The client uses cr_checksum to detect
   transport corruption between the data server and the
   client; see {{sec-security-checksum-scope}} for the
   scope and limits of checksum protection per algorithm
   class.

cr_effective_len:
:  the byte length of cr_chunk.  This may be smaller than
   the layout's chunk_size when the chunk is the final
   chunk of a file whose size is not chunk-aligned, or
   when the chunk belongs to a variable-size Mojette
   parity shard.

cr_owner:
:  the full (co_cohort_id, co_client_id, co_id) owner triple
   of the COMMITTED generation being returned (see
   {{sec-chunk_owner4}}); co_id is the opaque writer-supplied
   per-chunk identifier the client provided at
   CHUNK_WRITE or CHUNK_WRITE_REPAIR time, not a chunk
   index.  A client reading from multiple data servers in
   an erasure-coded layout MUST compare the pair
   `(cr_owner.co_cohort_id, cr_owner.co_client_id)` across
   data servers; agreement of the cohort pair across the k
   data shards is the atomicity invariant on which
   reconstruction depends.  See
   {{sec-system-model-consistency}}.

cr_guard:
:  the (cg_gen_id, cg_client_id) pair the data server holds
   as the chunk's current chunk_guard4 ({{sec-chunk_guard4}})
   at CHUNK_READ time.  A client that intends to update this
   chunk in multiple writer mode uses cr_guard as the
   expected prior value for the guard CAS: it supplies
   cwa_guard.cwg_check = TRUE with cwa_guard.cwg_guard set
   to the observed cr_guard on the subsequent CHUNK_WRITE
   ({{sec-CHUNK_WRITE}}, {{sec-multi-writer}}).  A client
   reading from multiple data servers in an erasure-coded
   layout MAY also compare cr_guard values across shards as
   an auxiliary check on payload atomicity; the cr_owner
   cohort-pair comparison (see the bullet above and
   {{sec-system-model-consistency}}) is the normative
   atomicity invariant and cr_guard adds a cheaper
   generation-level check.  For the
   NFS4ERR_NOENT synthetic zero-filled chunk the cr_guard is
   set to the all-zeros pair (cg_client_id =
   CHUNK_GUARD_CLIENT_ID_NONE, see {{sec-chunk_guard_none}}).

cr_payload_id:
:  the payload-id the writer associated with the chunk at
   CHUNK_WRITE time, used by repair coordinators to
   correlate chunks across mirrors.

cr_locked:
:  TRUE if the chunk currently has a CHUNK_LOCK
   ({{sec-CHUNK_LOCK}}) held against it; FALSE otherwise.
   Lock state does not block the read.

cr_status:
:  per-chunk status.  NFS4_OK indicates that cr_chunk is
   the COMMITTED payload.  NFS4ERR_PAYLOAD_NOT_ATOMIC
   indicates the chunk's persisted checksum or guard check
   failed at read time, in which case cr_chunk content
   is undefined; see {{sec-NFS4ERR_PAYLOAD_NOT_ATOMIC}}.
   NFS4ERR_NOENT indicates the chunk is EMPTY (no
   COMMITTED generation has been written at this offset).

cr_chunk:
:  the chunk payload bytes.  Empty for cr_status values
   other than NFS4_OK.

A chunk that is EMPTY at the requested offset is returned
as a synthetic zero-filled chunk: cr_status is
NFS4ERR_NOENT, cr_chunk is zero-filled to the layout's
chunk_size, cr_owner is set to all-zeros (with co_client_id
= CHUNK_GUARD_CLIENT_ID_NONE, see {{sec-chunk_guard_none}}),
cr_guard is set to the all-zeros pair (cg_gen_id = 0 and
cg_client_id = CHUNK_GUARD_CLIENT_ID_NONE), and
cr_checksum is the checksum of the synthetic zero-filled
payload.  This lets a client reconstruct holes without a
special-casing path.

The data server MAY signal end-of-file by setting crr_eof
to TRUE.  If the CHUNK_READ ended at the last chunk that
exists on this data server (the read returned chunks up to
and including the data server's last chunk) or extended
beyond it, crr_eof MUST be TRUE.  Otherwise crr_eof is
FALSE.  A successful CHUNK_READ of an empty file always
returns crr_eof as TRUE with crr_chunks empty.  Note that
crr_eof reflects the state at the data server only; in a
multi-data-server erasure-coded layout the file's logical
size is reconstructed at the client from the chunk-index
positions at which surviving shards hold non-EMPTY chunks
(observed via successive CHUNK_READs at known offsets),
not from any single data server's crr_eof.  Because co_id
is opaque per {{sec-chunk_owner4}}, the reconstructing
client MUST NOT derive positional information from the
chunk_owner4 values themselves.

Except when special stateids are used, the cra_stateid
value represents a layout stateid returned by a prior
LAYOUTGET against the metadata server (see Section 18.43
of {{RFC8881}}).  The data server uses cra_stateid to
verify that the client holds a valid layout that
authorizes reading this file.  Under trusted stateid tight
coupling ({{sec-TRUST_STATEID}}), the data server
additionally checks that the metadata server has
registered the stateid via TRUST_STATEID; an unregistered
stateid (other than a special stateid) returns
NFS4ERR_BAD_STATEID.

For a CHUNK_READ with a cra_stateid value of all bits
equal to zero, the data server MAY allow the CHUNK_READ
to be serviced subject to the chunk-lock state recorded in
cr_locked.  For a CHUNK_READ with a cra_stateid value of
all bits equal to one, the data server MAY allow CHUNK_READ
to bypass lock-state reporting at the data server.  These
special-stateid behaviours mirror the corresponding READ
semantics in {{RFC8881}} adapted to the chunk-locking
model ({{sec-CHUNK_LOCK}}) rather than the byte range
locking model of {{RFC8881}} Section 12.

If the current filehandle is not an ordinary file, an
error MUST be returned.  If the current filehandle
represents an object of type NF4DIR, NFS4ERR_ISDIR is
returned.  If the current filehandle designates a symbolic
link, NFS4ERR_SYMLINK is returned.  In all other cases of
non-regular-file filehandles, NFS4ERR_WRONG_TYPE is
returned.

{{fig-example-CHUNK_READ4args}} shows a client requesting
4 chunks starting at chunk index 2.  Data Server 2
responds as in {{fig-example-CHUNK_READ4resok}}: there is
valid data for chunks 2 and 4, a synthetic zero-filled
hole at chunk 3, and no data for chunk 5 (the data server's
last chunk is chunk 4, so crr_eof is TRUE).  The data
server calculates a valid cr_checksum for chunk 3 based on the
synthetic zero-filled payload.

~~~
        Data Server 2
  +--------------------------------+
  | CHUNK_READ4args                |
  +--------------------------------+
  | cra_stateid: 0                 |
  | cra_offset: 2                  |
  | cra_count: 4                   |
  +--------------------------------+
~~~
{: #fig-example-CHUNK_READ4args title="Example: CHUNK_READ4args parameters" }

~~~ art
        Data Server 2
  +--------------------------------+
  | CHUNK_READ4resok               |
  +--------------------------------+
  | crr_eof: true                  |
  | crr_chunks[0]:                 |
  |     cr_checksum: 0x3faddace    |
  |     cr_owner:                  |
  |         co_cohort_id: 0x2a     |
  |         co_client_id: 6        |
  |         co_id: 2               |
  |     cr_payload_id: 1           |
  |     cr_chunk: ....             |
  | crr_chunks[1]:                 |
  |     cr_checksum: 0xdeade4e5    |
  |     cr_owner:                  |
  |         co_cohort_id: 0x0      |
  |         co_client_id: 0        |
  |         co_id: 0               |
  |     cr_payload_id: 1           |
  |     cr_chunk: 0000...00000     |
  | crr_chunks[2]:                 |
  |     cr_checksum: 0x7778abcd    |
  |     cr_owner:                  |
  |         co_cohort_id: 0x2a     |
  |         co_client_id: 6        |
  |         co_id: 4               |
  |     cr_payload_id: 1           |
  |     cr_chunk: ....             |
  +--------------------------------+
~~~
{: #fig-example-CHUNK_READ4resok title="Example: Resulting CHUNK_READ4resok reply" }

### RESPONSE CODES

NFS4_OK:
:  the requested chunks have been returned.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to read this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_FHEXPIRED:
:  the current filehandle has expired.

NFS4ERR_IO:
:  an I/O error occurred while reading the chunks.

NFS4ERR_NOTSUPP:
:  the data server does not implement CHUNK_READ.

NFS4ERR_PAYLOAD_NOT_ATOMIC:
:  one or more chunks failed their
   persisted guard or CRC check.  See {{sec-NFS4ERR_PAYLOAD_NOT_ATOMIC}}.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

NFS4ERR_STALE:
:  the current filehandle no longer identifies a
   valid file.

## Operation 84: CHUNK_REPAIRED - Confirm Repair of Errored Chunk Data {#sec-CHUNK_REPAIRED}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_REPAIRED4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cra_stateid;
   ///     offset4         cra_offset;
   ///     count4          cra_count;
   ///     chunk_owner4    cra_owner;
   /// };
~~~
{: #fig-CHUNK_REPAIRED4args title="XDR for CHUNK_REPAIRED4args" }

### RESULTS

~~~ xdr
   /// union CHUNK_REPAIRED4res switch (nfsstat4 crr_status) {
   ///     case NFS4_OK:
   ///         void;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_REPAIRED4res title="XDR for CHUNK_REPAIRED4res" }

### DESCRIPTION

CHUNK_REPAIRED signals that chunks previously marked as
errored (via CHUNK_ERROR, see {{sec-CHUNK_ERROR}}) have been
repaired and the errored state can be cleared.  The repair
client writes replacement data via CHUNK_WRITE_REPAIR
({{sec-CHUNK_WRITE_REPAIR}}), advances the new chunks
through CHUNK_FINALIZE ({{sec-CHUNK_FINALIZE}}) and
CHUNK_COMMIT ({{sec-CHUNK_COMMIT}}), and only then issues
CHUNK_REPAIRED to make the repaired chunks visible to
normal CHUNK_READ traffic again.

CHUNK_REPAIRED has no direct analog in {{RFC8881}}; it is
the chunk-protocol equivalent of clearing a "needs scrub"
flag after a RAID controller has rewritten a parity stripe.
Together with CHUNK_ERROR it forms the data-server-side
state-bit pair that quarantines damaged chunks from
ordinary reads during the repair window.

The client provides:

cra_stateid:
:  the layout stateid the metadata server granted to the
   repair actor.  Under trusted stateid tight coupling
   ({{sec-TRUST_STATEID}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cra_offset:
:  starting chunk index of the repaired range (not a byte
   offset).

cra_count:
:  number of chunks the repaired range covers, starting
   at cra_offset.  The cra_offset / cra_count range MUST
   match the range named in the original CHUNK_ERROR that
   marked these chunks errored; mismatched ranges are
   rejected with NFS4ERR_INVAL.

cra_owner:
:  the chunk_owner4 ({{fig-chunk_owner4}}) identifying the
   repair actor.  The data server uses this to record
   which actor cleared the errored state.  The reserved
   sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear in cra_owner;
   see {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.

CHUNK_REPAIRED returns a single top-level status; there is
no per-chunk status array because the data server either
accepts the confirmation for the whole range or returns a
top-level error.

The data server MUST verify before accepting the
confirmation that:

-  every chunk in [cra_offset, cra_offset + cra_count) is
   currently in the errored state, and

-  every chunk in the range has been advanced to COMMITTED
   by a CHUNK_WRITE_REPAIR / CHUNK_FINALIZE / CHUNK_COMMIT
   sequence since the CHUNK_ERROR that marked them errored.

If either precondition fails, the data server returns
NFS4ERR_INVAL and the errored state is left in place.  A
repair actor that sees NFS4ERR_INVAL SHOULD verify the
chunks via CHUNK_HEADER_READ ({{sec-CHUNK_HEADER_READ}})
before retrying.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the repair confirmation has been recorded.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to confirm repair on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_INVAL:
:  the chunks named were not in an errored state,
   or the repair did not match the recorded error.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   CHUNK_REPAIRED.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 85: CHUNK_ROLLBACK - Rollback Changes on Cached Chunk Data {#sec-CHUNK_ROLLBACK}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_ROLLBACK4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cra_stateid;
   ///     offset4         cra_offset;
   ///     count4          cra_count;
   ///     chunk_owner4    cra_chunks<>;
   /// };
~~~
{: #fig-CHUNK_ROLLBACK4args title="XDR for CHUNK_ROLLBACK4args" }

### RESULTS

~~~ xdr
   /// struct CHUNK_ROLLBACK4resok {
   ///     verifier4       crr_writeverf;
   ///     nfsstat4        crr_chunk_status<>;
   /// };
~~~
{: #fig-CHUNK_ROLLBACK4resok title="XDR for CHUNK_ROLLBACK4resok" }

~~~ xdr
   /// union CHUNK_ROLLBACK4res switch (nfsstat4 crr_status) {
   ///     case NFS4_OK:
   ///         CHUNK_ROLLBACK4resok   crr_resok4;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_ROLLBACK4res title="XDR for CHUNK_ROLLBACK4res" }

### DESCRIPTION

CHUNK_ROLLBACK reverts chunks from the PENDING or
FINALIZED state to their previous state, effectively
undoing a CHUNK_WRITE ({{sec-CHUNK_WRITE}}) that has not
yet reached COMMITTED via CHUNK_COMMIT
({{sec-CHUNK_COMMIT}}).  The reversion target is the
prior COMMITTED generation, if one exists for the
affected chunk; otherwise the chunk returns to the EMPTY
state ({{fig-chunk-state-machine}}).  CHUNK_ROLLBACK
against a chunk already in the COMMITTED state is
permitted only on the repair path; see "Rollback of
COMMITTED Chunks" below.

CHUNK_ROLLBACK has no direct analog in {{RFC8881}}: NFS
WRITE has no separate finalization or commit step that a
client could undo without contacting other components.
CHUNK_ROLLBACK exists because the chunk state machine
exposes the PENDING and FINALIZED states explicitly, and
the writer needs a way to abandon a non-committed
generation without committing it.

The client provides cra_offset and cra_count to bound the
chunk range, and cra_chunks to name the specific
(chunk_owner4) generations within that range to roll back:

cra_offset:
:  starting chunk index in the file (not a byte offset).

cra_count:
:  number of chunks the range covers, starting at
   cra_offset.

cra_chunks:
:  an array of chunk_owner4 entries
   ({{fig-chunk_owner4}}) naming the specific
   (co_cohort_id, co_client_id, co_id) generations to roll
   back.  For each entry the data server looks up the
   chunk index it associated with the complete
   (co_cohort_id, co_client_id, co_id) triple when the
   client wrote it via CHUNK_WRITE or
   CHUNK_WRITE_REPAIR.  That recorded chunk index MUST
   lie in [cra_offset, cra_offset + cra_count); if the
   triple does not match any recorded owner association
   on this data server for this file, or the recorded
   chunk index lies outside the requested range, the
   entry is rejected with NFS4ERR_INVAL in the
   corresponding crr_chunk_status slot.  The co_id
   itself is opaque per {{sec-chunk_owner4}} and is NOT
   compared numerically with cra_offset or cra_count.
   The reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   co_client_id of any cra_chunks entry; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.

The CHUNK_ROLLBACK result returns:

crr_writeverf:
:  a verifier identifying the data server's incarnation.
   Semantics match cwr_writeverf in CHUNK_WRITE.

crr_chunk_status:
:  per-chunk rollback status, one entry per cra_chunks
   entry, co-indexed.  NFS4_OK indicates that the named
   generation was reverted (either to a retained
   predecessor COMMITTED or FINALIZED generation, or to
   EMPTY when no predecessor exists).  NFS4ERR_INVAL
   indicates the data server holds a concrete
   invalidation context that identifies the presented
   triple (structurally invalid, or released by an
   explicit CHUNK_ROLLBACK delete case within the
   session slot's replay-cache window), or the recorded
   chunk index lies outside [cra_offset, cra_offset +
   cra_count).  NFS4ERR_NO_PREDECESSOR indicates the
   data server holds no association for the presented
   triple and no concrete invalidation context -- the
   release-scope split is defined normatively at
   {{sec-NFS4ERR_NO_PREDECESSOR}}.  Other per-entry
   failures use the appropriate NFS4ERR_* code; the
   top-level operation status is NFS4_OK as long as the
   data server could evaluate each entry.

CHUNK_ROLLBACK has two principal scenarios:

1.  A writer in multiple-writer mode that observed
    per-chunk failures in the CHUNK_WRITE response (e.g.,
    NFS4ERR_CHUNK_GUARDED on a subset of chunks) needs to
    abandon the partial write before issuing CHUNK_FINALIZE
    on the chunks that did succeed.  CHUNK_ROLLBACK on the
    abandoned chunks releases their PENDING generation
    cleanly.

2.  A repair actor that wrote reconstructed data via
    CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}) and
    subsequently discovered the reconstruction was wrong
    (for example, a CRC mismatch detected during
    cross-mirror verification) needs to abandon the
    repair before any client commits it.

The data server effects the rollback as follows:

Chunks in PENDING with a matching chunk_owner4:

: the data server deletes the PENDING payload and restores
  the chunk to its prior state (EMPTY, or the prior COMMITTED
  generation if the rollback invariant in
  {{sec-system-model-consistency}} required retention).

Chunks in FINALIZED with a matching chunk_owner4:

: the data server deletes the FINALIZED payload and the
  persisted finalization metadata, restoring the chunk to its
  prior state.

Chunks not in PENDING or FINALIZED at the named generation, or whose chunk_owner4 does not match:

: the corresponding crr_chunk_status slot reports
  NFS4ERR_INVAL or NFS4ERR_NO_PREDECESSOR per the
  release-scope split at {{sec-NFS4ERR_NO_PREDECESSOR}}, and
  the chunk is left unchanged.

#### Deletion Atomicity and Invalidated Triples

CHUNK_ROLLBACK's delete case (successful rollback of a
PENDING or FINALIZED generation, or the abandonment sub-case
of the rollback of COMMITTED chunks below where a displaced
successor is discarded) removes BOTH the payload AND the
recorded owner-to-index association for that generation, in
one atomic step, per the payload/association biconditional
({{sec-system-model-payload-association-biconditional}}).
The generation's (co_cohort_id, co_client_id, co_id) triple
is then INVALIDATED at that chunk index: it names no
generation the data server holds, and no future CHUNK_WRITE
recreates an association under the same triple.

A subsequent lifecycle operation (CHUNK_COMMIT
({{sec-CHUNK_COMMIT}}), CHUNK_FINALIZE
({{sec-CHUNK_FINALIZE}}), CHUNK_ROLLBACK) that names an
invalidated triple MUST NOT be treated as resurrecting
the deleted generation; the data server MUST NOT attempt
to match the triple against any other record.  The error
returned in the corresponding per-chunk slot depends on
the release scope observable to the caller:

- Within the session slot's replay-cache window of the
  CHUNK_ROLLBACK that performed the delete case (or an
  equivalent slotted retransmission of it), the slot
  reports NFS4ERR_INVAL -- the caller could have observed
  the specific invalidating operation.
- After that replay-cache window has elapsed, or for
  release under any other terminal transition (lease
  expiry, storage-pressure release, retention-scope
  release of an already-invalidated triple), the slot
  reports NFS4ERR_NO_PREDECESSOR -- the data server holds
  no association for the presented triple and cannot
  distinguish it from any other released generation.

Both errors carry the same non-resurrection guarantee
above; they differ only in what the caller can observe
about how the association was released (see
{{sec-NFS4ERR_NO_PREDECESSOR}}).

The invalidation is on the FULL owner triple, not on any
sub-part.  A client that legitimately reuses the same
co_id value under a different co_cohort_id (or against a
different co_client_id) creates a distinct triple and
therefore a distinct generation identity; that new triple
is unaffected by the earlier deletion.  This is what
allows a writer that abandoned a generation via
CHUNK_ROLLBACK to retry with a fresh co_cohort_id -- the
retry is a new generation, not a resurrection of the
deleted one.

The uncertain-replay carve-out
(the CHUNK_ROLLBACK "Idempotence and Uncertain-Replay
Carve-Out" text below) is a narrow exception:
an EXACT reissue of the same CHUNK_ROLLBACK op whose
prior completion was uncertain MAY be treated as
postcondition-equivalent success when the client
independently verifies the deletion postcondition
holds.  This is separate from -- and does NOT resurrect --
the invalidated triple; it merely acknowledges that the
prior op already achieved the deletion the caller
requested.

#### Rollback of COMMITTED Chunks

CHUNK_ROLLBACK against a COMMITTED chunk is permitted
ONLY on the repair path, when a repair actor is
restoring a prior COMMITTED generation that another
client incorrectly advanced.  Two cases separate by
whether the predecessor generation the caller wants to
restore is still present on the data server:

Case (a) -- retained predecessor:

: The predecessor
generation named in the cra_chunks entry is still held
by the data server (typically the prior COMMITTED
retained under the rollback invariant
({{sec-system-model-retention-scope}}) alongside the
displaced successor, and MUST have survived with its
payload+association pair intact per the biconditional
({{sec-system-model-payload-association-biconditional}})).
The data server:

- restores the retained predecessor as the current
  COMMITTED generation UNDER ITS ORIGINAL owner triple
  (the (co_cohort_id, co_client_id, co_id) the predecessor
  was written with) -- its owner-to-index association is
  preserved, so the restored generation MUST remain
  recognizable to subsequent lifecycle operations by
  the same triple; AND
- atomically invalidates the displaced successor's
  triple via the delete case above ("Deletion
  Atomicity and Invalidated Triples") -- the displaced
  successor's payload+association pair is released as
  one unit; a subsequent lifecycle op naming the
  displaced triple returns NFS4ERR_INVAL within the
  session slot's replay-cache window of this
  CHUNK_ROLLBACK, and NFS4ERR_NO_PREDECESSOR after
  that window has elapsed, per the release-scope
  split at {{sec-NFS4ERR_NO_PREDECESSOR}}.

The restore is atomic with the delete: no intermediate
state exposes both generations as current, and no
intermediate state exposes neither.

Case (b) -- predecessor no longer retained:

: If the predecessor generation named in the cra_chunks
  entry is NOT held by the data server (its
payload+association pair was released some time earlier
under the retention scope rule, whether by lease
expiry, by an even earlier CHUNK_ROLLBACK delete case,
or by any other terminal transition), the CHUNK_ROLLBACK
CANNOT restore it: the deleted association is not
recreated by any operation defined in this document.
The corresponding crr_chunk_status slot reports
NFS4ERR_NO_PREDECESSOR in the ordinary case (release
under the retention scope rule, or eventual release of
an already-invalidated triple after the delete case's
replay-cache window has elapsed) and NFS4ERR_INVAL only
when the caller has named a triple released by an
explicit CHUNK_ROLLBACK delete case within the current
session slot's replay-cache window (see
{{sec-NFS4ERR_NO_PREDECESSOR}} for the choice between
them).  Either way, the caller consults whatever
fallback the deployment provides -- a repair
client MAY reconstruct authoritative bytes from
surviving shards and issue CHUNK_WRITE_REPAIR
({{sec-CHUNK_WRITE_REPAIR}}) to write a new
generation carrying those bytes under a new owner
triple.  That new generation is a distinct generation
for lifecycle purposes; it is not the deleted
predecessor resurrected.  Any client that requires the restored
generation to retain the predecessor's original owner
triple in cases where the retention scope
({{sec-system-model-retention-scope}}) would otherwise
permit release MUST use the metadata-server escrow control plane
({{sec-CHUNK_ESCROW_INSTALL}} through
{{sec-CHUNK_ESCROW_TAKEOVER}}), which pins the
predecessor's payload and its owner-to-index
association jointly against that release rule for as
long as the escrow-lock or a client-owned lock
adopted from it remains in continuous custody (see
{{sec-composed-rollback}}).

A non-repair CHUNK_ROLLBACK against a COMMITTED chunk
is rejected with NFS4ERR_INVAL regardless of case.

#### Stateid and Authorization

Like CHUNK_COMMIT ({{sec-CHUNK_COMMIT}}), CHUNK_ROLLBACK
carries an explicit layout stateid in cra_stateid.  The
data server authorizes CHUNK_ROLLBACK by validating
cra_stateid against the file identified by the current
filehandle: cra_stateid MUST be the layout stateid the
metadata server issued to the caller for the current
filehandle, or the special anonymous stateid (see below).
Under trusted stateid tight coupling
({{sec-TRUST_STATEID}}), the data server rejects
CHUNK_ROLLBACK with NFS4ERR_BAD_STATEID unless
cra_stateid is present in the data server's trust table
for the current filehandle.  The explicit field ensures
that a CHUNK_ROLLBACK in its own standalone compound
(typical for retry after a failed CHUNK_WRITE cohort)
carries the authorization the data server needs.
Passing the special anonymous stateid is permitted only
when the underlying security regime authorizes an
unattributed writer.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

#### Idempotence and Uncertain-Replay Carve-Out

CHUNK_ROLLBACK is idempotent on its target: a second
CHUNK_ROLLBACK naming the same generations after the
first has succeeded finds those generations already in
the state the first produced.  Under the ordinary
per-entry rules the second call returns NFS4ERR_INVAL in
each crr_chunk_status slot within the session slot's
replay-cache window of the first call (the first call's
delete case invalidated the triples per "Deletion
Atomicity and Invalidated Triples" above, or the
retained-predecessor restore invalidated the displaced
successor's triple per "Rollback of COMMITTED Chunks"
above); after that window has elapsed the second call
returns NFS4ERR_NO_PREDECESSOR per the release-scope
split at {{sec-NFS4ERR_NO_PREDECESSOR}}.

Uncertain-replay carve-out:

: When the first
CHUNK_ROLLBACK completed at the data server but its
response was lost (network error, dropped connection,
data server restart before the reply was received), the
client cannot distinguish "the op did not run" from
"the op ran and its reply was lost."  A client that
issues an EXACT REISSUE of the same CHUNK_ROLLBACK op
under these conditions MAY treat the resulting
per-chunk NFS4ERR_INVAL (within the replay-cache
window) or NFS4ERR_NO_PREDECESSOR (after the window has
elapsed) as POSTCONDITION-EQUIVALENT SUCCESS on a
slot-by-slot basis, PROVIDED all of the following hold
for that slot:

- the reissue is byte-identical to the original op
  (same cra_offset, same cra_count, same cra_chunks
  array entry) -- a fresh op with an accidentally-matching
  triple does NOT qualify;
- the prior completion is genuinely uncertain (the
  client never observed a per-entry response for that
  slot); AND
- the client INDEPENDENTLY verifies that the target
  postcondition holds.  For the delete case, this
  means observing that the named generation is absent
  at the target chunk index (via CHUNK_HEADER_READ
  ({{sec-CHUNK_HEADER_READ}}) or CHUNK_READ
  ({{sec-CHUNK_READ}}) with the retention-scope rules
  understood).  For the retained-predecessor restore
  case, this means observing that the predecessor's
  original triple is now the current COMMITTED
  generation.

The carve-out is narrow by construction: a fresh op
receiving NFS4ERR_INVAL or NFS4ERR_NO_PREDECESSOR never
qualifies, and a reissue that cannot verify the
postcondition also does not qualify -- the client MUST
treat the error as a terminal per-entry failure in
either case.  This prevents the carve-out from being
conflated with the underlying non-resurrection
guarantee, which is unconditional and prohibits the
data server from resurrecting any deleted generation
("Deletion Atomicity and Invalidated Triples" above).
Similar reasoning applies
to exact uncertain reissues of CHUNK_COMMIT
({{sec-CHUNK_COMMIT}}) and CHUNK_FINALIZE
({{sec-CHUNK_FINALIZE}}), which are also idempotent on
their targets under the same three predicates.

### RESPONSE CODES

NFS4_OK:
:  the named chunks have been rolled back.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to roll back chunks on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_INVAL:
:  arguments named chunks not eligible for rollback
   or outside the file's mirror set.

NFS4ERR_NO_PREDECESSOR:
:  the named predecessor has no recorded owner-to-index
   association on the data server (retention scope
   released it, or the delete case's replay-cache window
   has elapsed).  See {{sec-NFS4ERR_NO_PREDECESSOR}} for
   the split against NFS4ERR_INVAL.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   CHUNK_ROLLBACK.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 86: CHUNK_UNLOCK - Unlock Cached Chunk Data {#sec-CHUNK_UNLOCK}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_UNLOCK4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cua_stateid;
   ///     offset4         cua_offset;
   ///     count4          cua_count;
   ///     chunk_owner4    cua_owner;
   /// };
~~~
{: #fig-CHUNK_UNLOCK4args title="XDR for CHUNK_UNLOCK4args" }

### RESULTS

~~~ xdr
   /// union CHUNK_UNLOCK4res switch (nfsstat4 cur_status) {
   ///     case NFS4_OK:
   ///         void;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_UNLOCK4res title="XDR for CHUNK_UNLOCK4res" }

### DESCRIPTION

CHUNK_UNLOCK releases the exclusive chunk-range lock
previously acquired by CHUNK_LOCK ({{sec-CHUNK_LOCK}}).
CHUNK_UNLOCK is loosely analogous to LOCKU ({{RFC8881}}
Section 18.12) in that it releases an exclusive guard,
but it operates on chunk-range coordinates and is
matched against the chunk_owner4 that acquired the
lock rather than against an open / lock stateid.

The client provides:

cua_stateid:
:  the layout stateid the metadata server granted for
   this file.  Under trusted stateid tight coupling
   ({{sec-TRUST_STATEID}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cua_offset:
:  starting chunk index of the range to unlock (not a
   byte offset).

cua_count:
:  number of chunks the unlock range covers, starting at
   cua_offset.  The range MUST match exactly the range
   of an outstanding CHUNK_LOCK held by cua_owner;
   partial-range unlock is not supported.

cua_owner:
:  the chunk_owner4 ({{fig-chunk_owner4}}) that holds
   the lock.  The co_client_id MUST match the
   chunk_owner4 that was supplied on the CHUNK_LOCK that
   acquired the lock (including the case of a lock
   transferred via CHUNK_LOCK_FLAGS_ADOPT, in which the
   adopter's chunk_owner4 is the current holder).  The
   reserved sentinel values CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   co_client_id of cua_owner; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.
   In particular, a repair actor releasing a lock it
   adopted from the metadata-server escrow owner uses its own
   co_client_id in cua_owner, not
   CHUNK_GUARD_CLIENT_ID_MDS.

The CHUNK_UNLOCK result returns a single top-level
status; there is no per-chunk status array because the
unlock either succeeds for the whole range or returns a
top-level error.

CHUNK_UNLOCK is idempotent in the sense that releasing
chunks that are not currently locked returns NFS4_OK
without effect.  Releasing chunks that are locked by a
different cua_owner returns NFS4ERR_INVAL and leaves the
lock in place.

A client SHOULD issue CHUNK_UNLOCK promptly after
completing the write, write-repair, or commit sequence
that the lock guarded.  Locks not explicitly released
are released implicitly when the holder's lease expires;
if the metadata server has revoked the holder's stateid
via REVOKE_STATEID ({{sec-REVOKE_STATEID}}) before the
lease lapses, the lock transitions to the metadata-server escrow
owner per the lock-continuity invariant in
{{sec-system-model-consistency}} rather than being
released outright.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the named chunks have been unlocked, or no lock was
   held (idempotent).

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to unlock chunks on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_INVAL:
:  arguments named chunks not in a locked state
   owned by this caller.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   CHUNK_UNLOCK.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 87: CHUNK_WRITE - Write Chunks to File {#sec-CHUNK_WRITE}

### ARGUMENTS

~~~ xdr
   /// union write_chunk_guard4 switch (bool cwg_check) {
   ///     case TRUE:
   ///         chunk_guard4   cwg_guard;
   ///     case FALSE:
   ///         void;
   /// };
~~~
{: #fig-write_chunk_guard4 title="XDR for write_chunk_guard4" }

~~~ xdr
   /// const CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY = 0x00000001;
   ///
   /// struct CHUNK_WRITE4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4           cwa_stateid;
   ///     offset4            cwa_offset;
   ///     stable_how4        cwa_stable;
   ///     chunk_cohort_id4   cwa_cohort_id;
   ///     uint32_t           cwa_client_id;
   ///     uint32_t           cwa_co_ids<>;
   ///     uint32_t           cwa_payload_id;
   ///     uint32_t           cwa_flags;
   ///     write_chunk_guard4 cwa_guard;
   ///     uint32_t           cwa_chunk_size;
   ///     checksum4          cwa_checksums<>;
   ///     opaque             cwa_chunks<>;
   /// };
~~~
{: #fig-CHUNK_WRITE4args title="XDR for CHUNK_WRITE4args" }

### RESULTS

~~~ xdr
   /// struct CHUNK_WRITE4resok {
   ///     count4          cwr_count;
   ///     stable_how4     cwr_committed;
   ///     verifier4       cwr_writeverf;
   ///     nfsstat4        cwr_block_status<>;
   ///     bool            cwr_block_activated<>;
   ///     chunk_owner4    cwr_owners<>;
   /// };
~~~
{: #fig-CHUNK_WRITE4resok title="XDR for CHUNK_WRITE4resok" }

~~~ xdr
   /// union CHUNK_WRITE4res switch (nfsstat4 cwr_status) {
   ///     case NFS4_OK:
   ///         CHUNK_WRITE4resok    cwr_resok4;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_WRITE4res title="XDR for CHUNK_WRITE4res" }

### DESCRIPTION

The CHUNK_WRITE operation is based upon the NFSv4.1 WRITE
operation (see Section 18.32 of {{RFC8881}}) and similarly
writes data to the regular file identified by the current
filehandle, with the difference that CHUNK_WRITE operates
on the chunk coordinate system used by Flexible File
Version 2 layouts rather than on the byte coordinate
system.  Successful chunk writes initially enter the
PENDING state in the chunk state machine
({{fig-chunk-state-machine}}); a subsequent CHUNK_FINALIZE
({{sec-CHUNK_FINALIZE}}) and CHUNK_COMMIT
({{sec-CHUNK_COMMIT}}) (or the activation shortcut
described below) progress them to COMMITTED.

The client provides a cwa_offset of where the CHUNK_WRITE
is to start and a payload consisting of one or more chunks
packed into the cwa_chunks opaque field.  cwa_offset is
the starting chunk index in the file (not a byte offset);
each chunk occupies cwa_chunk_size bytes within cwa_chunks
except the last, which MAY be shorter when the file size
is not chunk-aligned or when the payload encodes a
variable-size Mojette parity shard
({{sec-mojette-encoding}}).  The number of chunks in the
payload is ceil(len(cwa_chunks) / cwa_chunk_size).

The writer supplies the cohort identity of the payload in
compact form: cwa_cohort_id carries the shared
chunk_cohort_id4 for every chunk in the batch, cwa_client_id
carries the writer's layout-granted identity, and cwa_co_ids
is an array of writer-chosen opaque per-chunk co_id values,
one per chunk in the payload (see {{sec-chunk_owner4}}).
The full cohort triple recorded on the data server for the
chunk at zero-based position i within the payload is
`(cwa_cohort_id, cwa_client_id, cwa_co_ids[i])`.

`cwa_client_id` identifies the writer.  It is
client-presented, metadata-server-assigned: the client presents the
32-bit layout-granted identity that the metadata server
established in ffv2m_client_id (see {{sec-ffv2-mirror4}}) at
layout-grant time; the client MUST NOT substitute any other
value.  Because encodings that use CHUNK operations require tight coupling
({{sec-ff_device_addr4}}), the data server always has an
authoritative binding for this identity: the metadata server
registers it via tsa_client_id in TRUST_STATEID
({{sec-TRUST_STATEID}}) alongside the layout stateid.  The
data server MUST compare cwa_client_id against the
tsa_client_id recorded in its trust table for the presented
layout stateid, and MUST reject a mismatch with
NFS4ERR_BAD_STATEID: a client that presents a cwa_client_id
different from its layout's ffv2m_client_id is spoofing
another writer's identity.  `cwa_client_id` MUST NOT be the
reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE or
CHUNK_GUARD_CLIENT_ID_MDS (see {{sec-chunk_guard_none}} and
{{sec-chunk_guard_mds}}); those sentinels are reserved for
data-server-observed cg_client_id values in chunk_guard4
CAS state, not for use as a writer's own identity.
`cwa_cohort_id` is the writer's opaque per-transaction
identifier, shared by every chunk in the payload; the
writer chooses a new `cwa_cohort_id` per distinct write
transaction so that lifecycle operations can distinguish
transactions across all data files (see the discussion of
chunk_cohort_id4 in {{sec-chunk_guard4}}).  The
per-chunk CAS state (chunk_guard4) is carried separately
via cwa_guard.cwg_guard when compare-and-swap is required
({{sec-multi-writer}}).

`cwa_co_ids<>` contains exactly one entry per chunk in the
payload (i.e., `cwa_co_ids_len` MUST equal
`ceil(len(cwa_chunks) / cwa_chunk_size)`); the data server
rejects any other length with NFS4ERR_INVAL.  Within a
single `(cwa_cohort_id, cwa_client_id)`, the `cwa_co_ids`
values in this request MUST be distinct so that lifecycle
operations (CHUNK_FINALIZE, CHUNK_COMMIT, CHUNK_ROLLBACK)
can name individual chunks unambiguously by full triple.  The data
server treats each `cwa_co_ids[i]` as opaque; it does NOT
interpret the value beyond equality comparison, and it MUST
NOT require `cwa_co_ids[i]` to equal `cwa_offset + i` or
any other derived index.  A writer that finds it convenient
to use monotonic per-writer serials or file-index-derived
values MAY do so, but the wire semantics do not privilege
that choice.

cwa_payload_id is a writer-chosen identifier that lets a
repair coordinator correlate chunks of the same logical
write across data servers.

cwa_checksums, when non-empty, MUST contain one checksum
entry per chunk in the payload.  Each entry's cs_algorithm
MUST match ffv2m_checksum_algorithm of the mirror named in
the layout (see {{sec-ffv2-mirror4}}); a mismatch is rejected
with NFS4ERR_INVAL.  The data server validates each chunk's
checksum at CHUNK_WRITE time and rejects mismatched chunks
with NFS4ERR_IO in the corresponding cwr_block_status slot.
An empty cwa_checksums array (cwa_checksums_len == 0)
indicates the client did not supply per-chunk checksums; the
data server still computes and persists per-chunk checksums
from the payload bytes for later integrity verification but
cannot detect transport corruption at CHUNK_WRITE time
without the client's
reference values.

cwa_flags carries CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY (see
"Stability and Activation" below).

cwa_guard ({{fig-write_chunk_guard4}}) controls the chunk-guard
CAS check (see "Guarding the Write" below).

A cwa_offset of zero starts writing at the first chunk of
the file.  Unlike READ in {{RFC8881}}, a CHUNK_WRITE whose
cwa_offset extends beyond the current end of the file is
not an error: the data server extends the file's chunk
store to cover the new chunks, with intervening offsets
remaining EMPTY ({{sec-system-model-chunk-state}}) until
they too are written.  If the cwa_chunks payload is empty
(zero bytes), the CHUNK_WRITE succeeds and writes zero
chunks (cwr_count == 0).

In all situations the data server MAY choose to write
fewer chunks than the client requested; the client must be
prepared to handle a short write and reissue CHUNK_WRITE
for the remaining chunks.

The CHUNK_WRITE result includes per-chunk outcomes in
cwr_block_status, cwr_block_activated, and cwr_owners, all
co-indexed and one entry per chunk in the payload:

cwr_count:
:  the number of chunks the data server successfully
   accepted.  Chunks that failed their guard check, checksum
   check, or any other local precondition do not
   contribute to cwr_count.

cwr_committed:
:  the stable_how4 level the data server actually applied
   for accepted chunks.  This MUST be at least as durable
   as cwa_stable; see "Stability and Activation" below.

cwr_writeverf:
:  a verifier identifying the data server's incarnation.
   A client uses cwr_writeverf to detect a data server
   restart that lost UNSTABLE4 writes: if the client's
   subsequent CHUNK_COMMIT returns a different writeverf
   than was returned by an UNSTABLE4 CHUNK_WRITE earlier,
   the chunks may have been lost and the client SHOULD
   re-issue CHUNK_WRITE.  cwr_writeverf changes on every
   data server restart that loses uncommitted state.

cwr_block_status:
:  per-chunk acceptance status; see "Per-Block Acceptance
   Semantics" below.

cwr_block_activated:
:  per-chunk activation flag.  TRUE indicates that the
   chunk is COMMITTED on return from CHUNK_WRITE -- the
   activation shortcut described under "Stability and
   Activation" below.  FALSE indicates that the chunk is
   in the PENDING state and requires a subsequent
   CHUNK_FINALIZE and CHUNK_COMMIT to become COMMITTED.

cwr_owners:
:  per-chunk chunk_owner4 the data server recorded, one
   entry per chunk in the payload (co-indexed with
   cwa_co_ids and cwr_block_status).  Each entry is the
   complete cohort triple `(cwa_cohort_id, cwa_client_id,
   cwa_co_ids[i])` that the data server recorded (or, for
   a rejected slot, the requested triple echoed for
   positional correlation with the failure status in
   `cwr_block_status[i]`).  The data server does NOT
   synthesize per-chunk identity by modifying the writer's
   cohort; the returned triple is the value the client
   supplied, so a client that lost track of its own
   transmitted co_ids array can recover the data server's
   view.  Under the compact carrier the cohort pair
   (cwa_cohort_id, cwa_client_id) is shared across every
   returned entry -- the per-chunk distinction is carried
   entirely by the co_id.

Except when special stateids are used, cwa_stateid
represents a layout stateid returned by a prior LAYOUTGET
against the metadata server (see Section 18.43 of
{{RFC8881}}) that authorizes write access to this file.
Under trusted stateid tight coupling
({{sec-TRUST_STATEID}}), the data server additionally
checks that the metadata server has registered the
stateid via TRUST_STATEID; an unregistered stateid (other
than a special stateid) returns NFS4ERR_BAD_STATEID.

For a CHUNK_WRITE with a cwa_stateid value of all bits
equal to zero, the data server MAY allow the CHUNK_WRITE
to be serviced subject to any CHUNK_LOCK currently held
on the target chunks.  For a CHUNK_WRITE with a
cwa_stateid value of all bits equal to one, the data
server MAY allow CHUNK_WRITE to bypass lock-state
checking at the data server.  These special-stateid
behaviours mirror the corresponding WRITE semantics in
{{RFC8881}} adapted to the chunk-locking model
({{sec-CHUNK_LOCK}}) rather than the byte range locking
model of {{RFC8881}} Section 12.

If the current filehandle is not an ordinary file, an
error MUST be returned.  If the current filehandle
represents an object of type NF4DIR, NFS4ERR_ISDIR is
returned.  If the current filehandle designates a
symbolic link, NFS4ERR_SYMLINK is returned.  In all other
cases of non-regular-file filehandles, NFS4ERR_WRONG_TYPE
is returned.

#### Stability and Activation

The cwa_stable field controls the durability level the
data server guarantees before returning.  The durability
floor for each level covers BOTH the chunk payload AND
its owner-to-index association, so a subsequent
lifecycle operation naming the full owner triple can
locate the recorded chunk index; see
{{sec-system-model-owner-persistence}} for the normative
coupling rule and the "MUST NOT retain payload without
association" invariant.

FILE_SYNC4:
:  The data server MUST commit all written chunks plus
   all chunk-store metadata to stable storage before
   returning.

DATA_SYNC4:
:  The data server MUST commit all written chunk payloads
   to stable storage and enough of the chunk-store
   metadata to retrieve the data before returning.  An
   implementation MAY treat DATA_SYNC4 identically to
   FILE_SYNC4 at a possible performance cost.

UNSTABLE4:
:  The data server is free to commit any portion of the
   chunk payload and metadata to stable storage before
   returning, including all or none.  The data server
   makes only two guarantees: it will not destroy any
   chunk payload it accepted without changing
   cwr_writeverf, and the durability level it ultimately
   applies will not be less than that requested.

The CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY flag in cwa_flags
requests an activation shortcut for first-time writes: a
chunk that was EMPTY before the CHUNK_WRITE and whose
write reaches FILE_SYNC4 or DATA_SYNC4 durability MAY be
transitioned directly to COMMITTED by the data server,
with the corresponding cwr_block_activated entry set to
TRUE in the response.
Without the flag, or for chunks that were not EMPTY
before the write, or for writes at UNSTABLE4 durability,
the chunk enters the PENDING state and reaches COMMITTED
only after a subsequent CHUNK_FINALIZE and CHUNK_COMMIT.

The activation shortcut interacts with concurrent writers
and unstable writes in subtle ways:

-  A chunk written with cwa_stable == UNSTABLE4 cannot be
   activated by CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY
   because the payload has not been committed to stable
   storage; the chunk enters the PENDING state regardless
   of the flag.

-  In the multi-writer mode ({{sec-multi-writer}}) a
   client MUST NOT set CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY
   on any CHUNK_WRITE.  The activation shortcut bypasses
   CHUNK_FINALIZE, so a chunk that reached COMMITTED via
   the shortcut cannot be reverted by the loser's
   CHUNK_ROLLBACK flow described in
   {{sec-chunk_guard4}}; two racing writers whose EMPTY
   activations landed on disjoint subsets of the mirror set
   would leave the stripe permanently non-atomic with no
   protocol path to recovery.  A data server that receives
   a multi-writer-mode CHUNK_WRITE with
   CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY set MUST reject the
   request with NFS4ERR_INVAL in the corresponding
   cwr_block_status slot; the client MUST re-issue without
   the flag, allowing the chunk to enter PENDING and
   proceed through the standard CHUNK_FINALIZE +
   CHUNK_COMMIT path.  The shortcut remains available in
   single writer mode where CAS contention cannot arise.

-  A client that issues an UNSTABLE4 CHUNK_WRITE and
   observes a FALSE entry in cwr_block_activated for a
   chunk MAY still find that chunk COMMITTED on a
   subsequent CHUNK_READ -- another client could have
   activated it via the shortcut after this one's
   response was sent.  cwr_block_activated reflects the
   state at the moment the CHUNK_WRITE result was
   constructed, not a commitment to that state's
   persistence.

#### Guarding the Write

A guarded CHUNK_WRITE is when the writing of a block MUST fail if
cwa_guard.cwg_check is TRUE and the target chunk does not have the
same cg_gen_id as cwa_guard.cwg_guard.cg_gen_id.  This is
useful in read-update-write scenarios.  The client reads a block,
updates it, and is prepared to write it back.  It guards the write
such that if another writer has modified the block, the data server
will reject the modification.

As the chunk_guard4 (see {{fig-chunk_guard4}}) does not have a
chunk_id and the CHUNK_WRITE applies to all blocks in the range of
cwa_offset to the length of cwa_data, then each of the target blocks
MUST have the same cg_gen_id and cg_client_id.  The client SHOULD
present the smallest set of blocks as possible to meet this
requirement.

#### Per-Block Acceptance Semantics

A CHUNK_WRITE targets a contiguous range of blocks on a single
data server.  The data server evaluates each block independently
and reports the outcome per block in cwr_block_status (see
{{fig-CHUNK_WRITE4resok}}):

-  Each block is subjected to the guard check (when
   cwa_guard.cwg_check is TRUE), the cg_client_id validation
   (see {{sec-chunk_guard4}}), and any other local preconditions
   (storage-space limits, tight coupling trust-table state,
   etc.).

-  Blocks that pass their preconditions are written and their
   cwr_block_status entry is NFS4_OK.  Blocks that fail produce
   the appropriate error code
   (NFS4ERR_CHUNK_GUARDED, NFS4ERR_NOSPC, etc.) in the
   corresponding cwr_block_status slot, and their data is
   NOT persisted.

-  cwr_count reflects only the blocks that were written
   successfully; failed blocks do not contribute.

-  The top-level cwr_status is NFS4_OK when the call itself was
   structurally valid and the data server could evaluate each
   block.  Per-block failures are reported in cwr_block_status,
   not by failing the whole operation.  The data server returns
   a top-level error only if it could not evaluate the request
   at all (for example, NFS4ERR_BADXDR, NFS4ERR_SERVERFAULT).

This is the "continue and report" discipline.  It is
intentionally not all-or-none: atomicity is already per-chunk
(see {{sec-system-model-consistency}}), so there is no
file-level correctness reason to reject the entire compound
because of a single chunk guard failure.  Per-block reporting
gives the client the information it needs to construct a
targeted CHUNK_ROLLBACK or CHUNK_WRITE retry that covers only
the blocks that failed.

The data server does not hold a file-wide lock across the
per-block evaluation.  The chunk_guard4 CAS is evaluated
atomically per chunk at the point the data server updates that
chunk's state, so an interleaving CHUNK_WRITE from a different
client that arrives mid-compound will either win its own CAS
race (and the losing client sees NFS4ERR_CHUNK_GUARDED for the
contested block) or be rejected itself, without introducing
data-server-level locking beyond the per-chunk scope.

### RESPONSE CODES

NFS4_OK:
:  the chunks have been written and are in the PENDING
   state.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to write to this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_CHUNK_GUARDED:
:  the chunk_guard4 condition supplied by
   the client did not match the persisted state.

NFS4ERR_CHUNK_LOCKED:
:  one or more chunks in the requested
   range are locked by another writer.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_FHEXPIRED:
:  the current filehandle has expired.

NFS4ERR_IO:
:  an I/O error occurred while persisting the chunks.

NFS4ERR_NOSPC:
:  there is insufficient space at the data server.

NFS4ERR_NOTSUPP:
:  the data server does not implement CHUNK_WRITE.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

NFS4ERR_STALE:
:  the current filehandle no longer identifies a
   valid file.

## Operation 88: CHUNK_WRITE_REPAIR - Write Repaired Cached Chunk Data {#sec-CHUNK_WRITE_REPAIR}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_WRITE_REPAIR4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4           cwra_stateid;
   ///     offset4            cwra_offset;
   ///     stable_how4        cwra_stable;
   ///     chunk_cohort_id4   cwra_cohort_id;
   ///     uint32_t           cwra_client_id;
   ///     uint32_t           cwra_co_ids<>;
   ///     uint32_t           cwra_payload_id;
   ///     uint32_t           cwra_chunk_size;
   ///     checksum4          cwra_checksums<>;
   ///     opaque             cwra_chunks<>;
   /// };
~~~
{: #fig-CHUNK_WRITE_REPAIR4args title="XDR for CHUNK_WRITE_REPAIR4args" }

### RESULTS

~~~ xdr
   /// struct CHUNK_WRITE_REPAIR4resok {
   ///     count4          cwrr_count;
   ///     stable_how4     cwrr_committed;
   ///     verifier4       cwrr_writeverf;
   ///     nfsstat4        cwrr_block_status<>;
   ///     chunk_owner4    cwrr_owners<>;
   /// };
~~~
{: #fig-CHUNK_WRITE_REPAIR4resok title="XDR for CHUNK_WRITE_REPAIR4resok" }

~~~ xdr
   /// union CHUNK_WRITE_REPAIR4res switch (nfsstat4 cwrr_status) {
   ///     case NFS4_OK:
   ///         CHUNK_WRITE_REPAIR4resok   cwrr_resok4;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-CHUNK_WRITE_REPAIR4res title="XDR for CHUNK_WRITE_REPAIR4res" }

### DESCRIPTION

CHUNK_WRITE_REPAIR is the repair-path variant of CHUNK_WRITE
({{sec-CHUNK_WRITE}}).  It writes reconstructed chunk data
to a data server whose chunks have been reported errored
(via CHUNK_ERROR, see {{sec-CHUNK_ERROR}}) or to a
replacement data server selected during whole-file repair.
The data server applies repair-specific policies to the
write that are not appropriate for normal client writes:
the chunk_guard4 CAS check is bypassed (the repair actor
is writing a reconstructed value rather than competing in
a multiple-writer race), and the data server MAY log the
repair separately for operator audit.

CHUNK_WRITE_REPAIR has no direct analog in {{RFC8881}}; it
is the chunk-protocol equivalent of writing reconstructed
data into a RAID stripe whose other members are known
healthy.  The reconstructed data is produced by the repair
client from surviving shards via the erasure-coding
algorithm of the file's layout.

The repair workflow that invokes CHUNK_WRITE_REPAIR is:

1.  The repair actor (selected per
    {{sec-repair-selection}}) reads surviving chunks from
    the remaining data servers via CHUNK_READ
    ({{sec-CHUNK_READ}}).

2.  The repair actor reconstructs the missing chunks
    using the erasure-coding algorithm of the file's
    layout.

3.  The repair actor acquires a CHUNK_LOCK
    ({{sec-CHUNK_LOCK}}) on the target data server to
    prevent concurrent writes during repair.  For repair
    that adopts a metadata-server escrow lock, the CHUNK_LOCK
    carries CHUNK_LOCK_FLAGS_ADOPT
    ({{sec-chunk_guard_mds}}).

4.  The repair actor writes the reconstructed data via
    CHUNK_WRITE_REPAIR.

5.  The repair actor issues CHUNK_FINALIZE
    ({{sec-CHUNK_FINALIZE}}) and CHUNK_COMMIT
    ({{sec-CHUNK_COMMIT}}) to persist the repair.

6.  The repair actor issues CHUNK_REPAIRED
    ({{sec-CHUNK_REPAIRED}}) to clear the errored state.

7.  The repair actor releases the lock via CHUNK_UNLOCK
    ({{sec-CHUNK_UNLOCK}}).

CHUNK_WRITE_REPAIR is also the fallback path used by a
client that received NFS4ERR_NO_PREDECESSOR
({{sec-NFS4ERR_NO_PREDECESSOR}}) from CHUNK_ROLLBACK's
restore case ({{sec-CHUNK_ROLLBACK}} "Rollback of
COMMITTED Chunks", case (b)) -- the named predecessor was
released under the retention scope
({{sec-system-model-retention-scope}}) and CHUNK_ROLLBACK
cannot restore it.  Under this fallback the client
reconstructs authoritative bytes from surviving shards
(or from any other authoritative source it holds) and
writes them via CHUNK_WRITE_REPAIR under a new owner
triple of its own choosing.  The result is a distinct
generation for lifecycle purposes: it carries the
repair actor's own (co_cohort_id, co_client_id, co_id)
triple, NOT the released predecessor's triple.  The released
predecessor is not resurrected by any operation defined
in this document, including this fallback; a subsequent
lifecycle operation naming the released predecessor's
triple returns NFS4ERR_NO_PREDECESSOR under the release-scope
split at {{sec-NFS4ERR_NO_PREDECESSOR}} -- the
predecessor was released under the retention scope, not
by an explicit CHUNK_ROLLBACK delete case within a live
replay-cache window.  A client that requires the
restored generation to carry the released predecessor's
original triple MUST use a guaranteed-pinning mechanism
as noted in {{sec-NFS4ERR_NO_PREDECESSOR}}, since
CHUNK_WRITE_REPAIR's semantics only produce a new
generation.  When no authoritative source exists for
reconstruction, the fallback itself may terminate at
NFS4ERR_PAYLOAD_LOST ({{sec-NFS4ERR_PAYLOAD_LOST}})
via CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}).

The arguments mirror CHUNK_WRITE except that
CHUNK_WRITE_REPAIR has no cwa_flags field (the
activation-shortcut behavior is not offered on the repair
path) and no cwa_guard field (the guard CAS is bypassed
by construction):

cwra_stateid:
:  the layout stateid the metadata server granted to the
   repair actor.  Under trusted stateid tight coupling
   ({{sec-TRUST_STATEID}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cwra_offset:
:  starting chunk index in the file (not a byte offset).

cwra_stable:
:  the stable_how4 durability level the data server MUST
   apply before returning.  Semantics match cwa_stable in
   CHUNK_WRITE (see {{sec-CHUNK_WRITE}} "Stability and
   Activation").

cwra_cohort_id / cwra_client_id / cwra_co_ids:
:  the compact cohort-identity carrier the repair actor
   uses for the reconstructed payload, mirroring
   CHUNK_WRITE's cwa_cohort_id + cwa_client_id + cwa_co_ids
   per {{sec-CHUNK_WRITE}}.  cwra_cohort_id carries the
   shared chunk_cohort_id4 for every reconstructed chunk
   in the batch; cwra_client_id is the repair actor's
   layout-granted identity; cwra_co_ids is a co-indexed
   array of writer-chosen opaque co_id values, one per
   chunk in cwra_chunks (exactly `ceil(len(cwra_chunks) /
   cwra_chunk_size)` entries; a length mismatch is
   rejected with NFS4ERR_INVAL).  The full cohort triple
   for reconstructed chunk position i is
   `(cwra_cohort_id, cwra_client_id, cwra_co_ids[i])`.
   cwra_client_id MUST be the repair actor's own
   ffv2m_client_id (not CHUNK_GUARD_CLIENT_ID_MDS); the
   cwra_cohort_id is the repair actor's locally chosen
   per-transaction opaque identifier.  The reserved
   sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear in
   cwra_client_id; see {{sec-chunk_guard_none}} and
   {{sec-chunk_guard_mds}}.  Within a single
   (cwra_cohort_id, cwra_client_id), the cwra_co_ids
   values MUST be distinct so that lifecycle operations
   can name individual reconstructed chunks unambiguously
   by full triple.

cwra_payload_id:
:  the payload-id the repair actor associates with the
   reconstructed payload, used by the repair coordinator
   to correlate this repair across mirrors.

cwra_chunk_size:
:  the nominal chunk size of the reconstructed payload,
   in bytes.

cwra_checksums:
:  per-chunk checksum4 ({{sec-checksum4}}) array.  Semantics
   match cwa_checksums in CHUNK_WRITE: each entry's
   cs_algorithm MUST match ffv2m_checksum_algorithm of the
   mirror named in the layout
   ({{sec-ffv2-mirror4}}), with NFS4ERR_INVAL on mismatch.

cwra_chunks:
:  the reconstructed chunk payload as an opaque blob,
   packed identically to cwa_chunks in CHUNK_WRITE.

The CHUNK_WRITE_REPAIR result reports per-chunk outcomes:

cwrr_count:
:  the number of chunks the data server successfully
   accepted.

cwrr_committed:
:  the stable_how4 level the data server actually applied.
   MUST be at least as durable as cwra_stable.

cwrr_writeverf:
:  a verifier identifying the data server's incarnation.
   Semantics match cwr_writeverf in CHUNK_WRITE.

cwrr_block_status:
:  per-chunk acceptance status, one entry per chunk in
   the payload, co-indexed with cwra_co_ids and
   cwrr_owners.  The top-level CHUNK_WRITE_REPAIR status
   is NFS4_OK as long as the data server could evaluate
   each chunk; per-chunk failures are reported in
   cwrr_block_status rather than by failing the whole
   operation.  (Renamed from cwrr_status to align with
   CHUNK_WRITE's cwr_block_status naming; a top-level
   status remains distinct from the per-chunk array.)

cwrr_owners:
:  per-chunk chunk_owner4 the data server recorded, one
   entry per chunk in the payload (co-indexed with
   cwra_co_ids and cwrr_block_status).  Each entry is
   the complete cohort triple
   `(cwra_cohort_id, cwra_client_id, cwra_co_ids[i])`
   that the data server recorded (or, for a rejected
   slot, the requested triple echoed for positional
   correlation with the failure status in
   `cwrr_block_status[i]`).  The data server does NOT
   synthesize per-chunk identity by modifying the
   repair actor's cohort.

The target chunks SHOULD be in the errored state (set by
a prior CHUNK_ERROR) or EMPTY.  If a target chunk is
COMMITTED with valid data, the data server MAY reject the
repair-write with NFS4ERR_INVAL in the corresponding
cwrr_block_status slot to prevent overwriting good data;
the repair actor SHOULD re-verify the chunk before
attempting another repair-write on the same range.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the repair-write succeeded.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to write repair data to this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_FHEXPIRED:
:  the current filehandle has expired.

NFS4ERR_IO:
:  an I/O error occurred while persisting the repair
   data.

NFS4ERR_NOSPC:
:  there is insufficient space at the data server.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   CHUNK_WRITE_REPAIR.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

NFS4ERR_STALE:
:  the current filehandle no longer identifies a
   valid file.

## Operation 89: TRUST_STATEID - Register Layout Stateid on Data Server {#sec-TRUST_STATEID}

### ARGUMENTS

~~~ xdr
   /// struct TRUST_STATEID4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        tsa_layout_stateid;
   ///     uint32_t        tsa_client_id;
   ///     layoutiomode4   tsa_iomode;
   ///     nfstime4        tsa_expire;
   ///     utf8str_cs      tsa_principal;
   /// };
~~~
{: #fig-TRUST_STATEID4args title="XDR for TRUST_STATEID4args" }

### RESULTS

~~~ xdr
   /// union TRUST_STATEID4res switch (nfsstat4 tsr_status) {
   ///     case NFS4_OK:
   ///         void;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-TRUST_STATEID4res title="XDR for TRUST_STATEID4res" }

### DESCRIPTION

TRUST_STATEID registers a layout stateid with the data
server so that subsequent CHUNK operations presenting that
stateid can be validated against the data server's per-file
trust table.  The registration also binds the stateid to the
ffv2m_client_id (tsa_client_id) the metadata server assigned
to the client at LAYOUTGET time; the data server uses that
binding to authorize the writer identity carried in
cwa_client_id on CHUNK_WRITE and in cg_client_id in any
chunk_guard4 CAS ({{sec-chunk_guard4}}).  TRUST_STATEID is
the mechanism by which tight coupling (see
{{sec-tight-coupling-control}}) is established between the
metadata server and the data server for a particular layout.

TRUST_STATEID has no analog in {{RFC8881}}: pNFS layouts in
{{RFC8881}} do not register the layout stateid with data
servers; data servers in the loose coupling model trust the
synthetic uid/gid the metadata server inserts on each I/O
({{sec-Fencing-Clients}}).  TRUST_STATEID is the new
metadata-server-to-data-server control-plane operation
that replaces synthetic-uid
fencing with per-client stateid-table validation for
deployments that opt into tight coupling.

TRUST_STATEID is a metadata-server-to-data-server operation; pNFS clients MUST
NOT send it.  The data server MUST verify that the
operation arrived on a session whose owning client presented
EXCHGID4_FLAG_USE_PNFS_MDS at EXCHANGE_ID and reject any
TRUST_STATEID received on a regular client session with
NFS4ERR_PERM.  TRUST_STATEID operates on the current
filehandle; a PUTFH naming the data server's file MUST
precede it in the same compound (except in the capability
probe case, where the current filehandle is the root).

The metadata server provides:

tsa_layout_stateid:
:  the stateid the metadata server issued in the
   LAYOUTGET that produced this layout.  MUST NOT be a
   special stateid (anonymous, invalid, read-bypass, or
   current).  The sole exception is the capability probe
   described in {{sec-tight-coupling-probe}}: when the
   metadata server sends TRUST_STATEID with
   tsa_layout_stateid set to the anonymous stateid
   against the root filehandle, the data server MUST
   reject the request with NFS4ERR_INVAL -- that
   rejection is the positive response to the probe.

tsa_client_id:
:  the ffv2m_client_id ({{sec-ffv2-mirror4}}) the
   metadata server assigned to the client in the
   layout that produced tsa_layout_stateid.  The data
   server records tsa_client_id alongside
   tsa_layout_stateid in the trust-table entry and
   uses it as the authoritative writer identity for
   subsequent CHUNK operations: cwa_client_id on
   CHUNK_WRITE ({{sec-CHUNK_WRITE}}) MUST equal the
   trust-table's tsa_client_id, and cg_client_id in
   any chunk_guard4 CAS submitted with the same
   stateid MUST also match.  A mismatch MUST be
   rejected with NFS4ERR_BAD_STATEID.  In the
   capability probe the metadata server SHOULD set
   tsa_client_id to zero (which is the reserved
   CHUNK_GUARD_CLIENT_ID_NONE, see
   {{sec-chunk_guard_none}}); the data server's
   NFS4ERR_INVAL response to the probe is unaffected
   by the field's value.

tsa_iomode:
:  the iomode of the layout (LAYOUTIOMODE4_READ or
   LAYOUTIOMODE4_RW).  The data server MAY enforce this
   against the CHUNK operation presented later: a
   READ-iomode trust entry does not authorize
   CHUNK_WRITE.

tsa_expire:
:  the absolute time at which the trust entry becomes
   invalid if not renewed; see
   {{sec-tight-coupling-lease}} for the clock-synchronization
   assumption and lease-computation rule.  The data server
   MUST reject a TRUST_STATEID whose tsa_expire has
   tv_nseconds >= 10^9 with NFS4ERR_INVAL.

tsa_principal:
:  the client's authenticated identity as verified by
   the metadata server at LAYOUTGET time.  For
   RPCSEC_GSS clients this is the GSS display name
   (e.g., "alice@REALM").  For AUTH_SYS and TLS
   clients, tsa_principal MUST be the empty string,
   indicating that no principal binding is enforced on
   subsequent CHUNK operations.  See
   {{sec-tight-coupling-principal}}.

If a trust entry already exists for the same
tsa_layout_stateid on the same current filehandle,
TRUST_STATEID atomically updates tsa_expire and
tsa_principal; this is the renewal path (see
{{sec-tight-coupling-lease}}).

At registration time the data server tags the new trust
entry with the identity of the metadata server, derived
from the clientid of the owning client of the control
session on which TRUST_STATEID arrived.  This tag is
consulted by REVOKE_STATEID ({{sec-REVOKE_STATEID}}) and
BULK_REVOKE_STATEID ({{sec-BULK_REVOKE_STATEID}}) so that
revocation only affects entries registered by the same
metadata server.  In a multi-metadata-server deployment
sharing a single data server, each metadata server
registers and revokes only its own entries; the tag is
opaque to pNFS clients and is not carried on the wire.

TRUST_STATEID returns only a top-level status; there is
no result body beyond the nfsstat4 discriminant.

If the current filehandle is not an ordinary file
(except in the capability-probe case, where the current
filehandle is the root and the operation is expected to
be rejected with NFS4ERR_INVAL), an error MUST be
returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the trust entry is registered (or updated).

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  tsa_layout_stateid was a special stateid
   other than the anonymous stateid on the root filehandle.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request; the metadata server SHOULD retry.

NFS4ERR_INVAL:
:  tsa_layout_stateid was the anonymous stateid
   and the current filehandle is not the root filehandle;
   tsa_expire is malformed; or the current filehandle is a
   directory (except in the capability-probe case).

NFS4ERR_NOFILEHANDLE:
:  no current filehandle is set.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   TRUST_STATEID.  This is the capability-probe response (see
   {{sec-tight-coupling-probe}}).

NFS4ERR_PERM:
:  the request arrived on a session whose owning
   client did not present EXCHGID4_FLAG_USE_PNFS_MDS.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 90: REVOKE_STATEID - Revoke Registered Stateid on Data Server {#sec-REVOKE_STATEID}

### ARGUMENTS

~~~ xdr
   /// struct REVOKE_STATEID4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        rsa_layout_stateid;
   /// };
~~~
{: #fig-REVOKE_STATEID4args title="XDR for REVOKE_STATEID4args" }

### RESULTS

~~~ xdr
   /// union REVOKE_STATEID4res switch (nfsstat4 rsr_status) {
   ///     case NFS4_OK:
   ///         void;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-REVOKE_STATEID4res title="XDR for REVOKE_STATEID4res" }

### DESCRIPTION

REVOKE_STATEID invalidates a single trust entry on the
data server.  Subsequent CHUNK operations that present
the revoked stateid MUST fail with NFS4ERR_BAD_STATEID.
REVOKE_STATEID is the per-file revoke counterpart to
TRUST_STATEID ({{sec-TRUST_STATEID}}) -- registration and
revocation form the matched pair that drives the per-file
trust table for a tightly coupled deployment.

REVOKE_STATEID has no analog in {{RFC8881}}.  {{RFC8881}}
revokes pNFS layouts via LAYOUTRETURN with a special
all-files marker or via implicit lease expiry;
REVOKE_STATEID is the new metadata-server-to-data-server operation
that lets the metadata server force per-client invalidation at the
data
server without waiting for tsa_expire and without
unsetting other clients' trust entries.

REVOKE_STATEID is a metadata-server-to-data-server operation; pNFS clients
MUST NOT send it.  The data server MUST verify that the
operation arrived on a session whose owning client
presented EXCHGID4_FLAG_USE_PNFS_MDS at EXCHANGE_ID and
reject any REVOKE_STATEID received on a regular client
session with NFS4ERR_PERM.  REVOKE_STATEID operates on
the current filehandle; a PUTFH naming the data server's
file MUST precede it in the same compound.

The metadata server provides:

rsa_layout_stateid:
:  the stateid to revoke.  Together with the current
   filehandle this identifies the trust entry to remove.
   MUST NOT be a special stateid; the anonymous stateid
   is rejected with NFS4ERR_INVAL and other special
   stateids with NFS4ERR_BAD_STATEID.

The metadata server calls REVOKE_STATEID in any of the
following situations:

CB_LAYOUTRECALL timeout:

: the client did not return the layout within the recall
  timeout.  REVOKE_STATEID terminates the client's ability
  to issue further I/O to the data server without waiting
  for tsa_expire.

LAYOUTERROR with NFS4ERR_ACCESS or NFS4ERR_PERM:

: the data server rejected the client's I/O; the trust entry
  is stale and must be removed.  This mirrors the fencing
  case in the loose-coupled model ({{sec-Fencing-Clients}}).

Explicit LAYOUTRETURN:

: the client returned the layout cleanly.  The metadata
  server MAY issue REVOKE_STATEID at this time or MAY rely
  on tsa_expire; either is correct.

In-flight CHUNK operations that arrived before
REVOKE_STATEID completes MAY be allowed to finish.  The
data server MUST NOT process new CHUNK operations
presenting rsa_layout_stateid after REVOKE_STATEID
returns.

Lock state (see {{sec-CHUNK_LOCK}}) held by the revoked
stateid is NOT released as part of REVOKE_STATEID; the
data server MUST transfer each held lock to the
metadata-server escrow owner (see {{sec-chunk_guard_mds}}).
Dropping a chunk lock during revocation would permit a
write hole and is prohibited; the repair coordination
sequence in {{sec-repair-selection}} assumes that locks
held by a revoked writer remain held until a repair
client adopts them via CHUNK_LOCK with
CHUNK_LOCK_FLAGS_ADOPT.

REVOKE_STATEID is scoped to the issuing metadata
server's entries (see the tagging rule in
{{sec-TRUST_STATEID}}).  The data server MUST NOT
remove an entry that was registered by a different
metadata server, even if rsa_layout_stateid happens to
match.  In a multi-metadata-server deployment, one
metadata server therefore cannot revoke another
metadata server's entries.

REVOKE_STATEID is idempotent: revoking a stateid that
has no matching trust entry (either no entry exists, or
the entry was registered by a different metadata
server) returns NFS4_OK.  The metadata server therefore
does not need to track precisely which entries are
currently live on which data server in order to revoke
safely.

REVOKE_STATEID returns only a top-level status; there
is no result body beyond the nfsstat4 discriminant.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the trust entry was removed, or no matching entry
   existed (idempotent).

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  rsa_layout_stateid was a special stateid.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_INVAL:
:  rsa_layout_stateid was the anonymous stateid.

NFS4ERR_NOFILEHANDLE:
:  no current filehandle is set.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   REVOKE_STATEID.

NFS4ERR_PERM:
:  the request arrived on a session whose owning
   client did not present EXCHGID4_FLAG_USE_PNFS_MDS.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 91: BULK_REVOKE_STATEID - Revoke All Stateids for a Client {#sec-BULK_REVOKE_STATEID}

### ARGUMENTS

~~~ xdr
   /// struct BULK_REVOKE_STATEID4args {
   ///     clientid4       brsa_clientid;
   /// };
~~~
{: #fig-BULK_REVOKE_STATEID4args title="XDR for BULK_REVOKE_STATEID4args" }

### RESULTS

~~~ xdr
   /// union BULK_REVOKE_STATEID4res switch (nfsstat4 brsr_status) {
   ///     case NFS4_OK:
   ///         void;
   ///     default:
   ///         void;
   /// };
~~~
{: #fig-BULK_REVOKE_STATEID4res title="XDR for BULK_REVOKE_STATEID4res" }

### DESCRIPTION

BULK_REVOKE_STATEID removes every trust entry on the data
server that was registered on behalf of a single named
client.  Unlike REVOKE_STATEID ({{sec-REVOKE_STATEID}}),
which removes one entry identified by a (filehandle,
stateid) pair, BULK_REVOKE_STATEID does not target a
specific filehandle or stateid; it instructs the data
server to scan its trust table and remove every entry
whose owning pNFS client matches brsa_clientid (and whose
issuing metadata server matches the calling metadata server).

BULK_REVOKE_STATEID has no analog in {{RFC8881}}.  {{RFC8881}}
recall-all is expressed at the layout layer
(CB_LAYOUTRECALL with LAYOUTRECALL4_ALL); the per-client
trust-table sweep introduced here is the data-server-side
complement, replacing the N per-file REVOKE_STATEID
compounds that per-entry revocation would require with a
single round-trip.

BULK_REVOKE_STATEID is a metadata-server-to-data-server operation; pNFS
clients MUST NOT send it.  The data server MUST verify
that the operation arrived on a session whose owning
client presented EXCHGID4_FLAG_USE_PNFS_MDS at EXCHANGE_ID
and reject any BULK_REVOKE_STATEID received on a regular
client session with NFS4ERR_PERM.  BULK_REVOKE_STATEID
does not operate on the current filehandle; no PUTFH is
required in the compound.

The metadata server provides:

brsa_clientid:
:  the clientid of the pNFS client whose trust entries
   are to be removed.  The special all-zeros value means
   "remove every trust entry owned by the calling
   metadata server, regardless of which pNFS client
   registered it"; the data server MUST interpret this
   value as a sweep of its own entries only, NOT as the
   pNFS client whose clientid happens to be zero and NOT
   as a global cross-metadata-server table clear.

The metadata server calls BULK_REVOKE_STATEID in any of
the following situations:

Client lease expiry:

: when a client's lease on the metadata server expires, the
  metadata server revokes all of that client's layouts.  A
  single BULK_REVOKE_STATEID with brsa_clientid set to the
  expired client's clientid sweeps every per-file trust entry
  the metadata server had registered for that client.

CB_LAYOUTRECALL with LAYOUTRECALL4_ALL:

: the metadata server is recalling all layouts for a client.
  BULK_REVOKE_STATEID is the data-server-side complement.

Metadata server restart cleanup:

: after the metadata server reconnects to a data server, it
  MAY issue BULK_REVOKE_STATEID with brsa_clientid set to
  all-zeros to clear the prior trust table before re-issuing
  TRUST_STATEID as clients reclaim.  See
  {{sec-tight-coupling-mds-crash}}.

BULK_REVOKE_STATEID is scoped to the issuing metadata
server's entries (see the tagging rule in
{{sec-TRUST_STATEID}}).  The data server MUST NOT affect
entries registered by a different metadata server.
Consequently, in a multi-metadata-server deployment
sharing a single data server, one metadata server cannot
clear another metadata server's entries via
BULK_REVOKE_STATEID.

Like REVOKE_STATEID, BULK_REVOKE_STATEID is idempotent
(no error is returned if there are no matching entries)
and preserves chunk locks held under any revoked stateid
by transferring them to the metadata-server escrow owner (see
{{sec-chunk_guard_mds}}), rather than dropping them.
Subsequent CHUNK operations from the revoked client
fail with NFS4ERR_BAD_STATEID; locks held under those
revoked stateids remain until adopted by a repair
client via CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT
({{sec-CHUNK_LOCK}}).

BULK_REVOKE_STATEID returns only a top-level status;
there is no result body beyond the nfsstat4 discriminant.

### RESPONSE CODES

NFS4_OK:
:  the matching entries were removed, or there were
   none (idempotent).

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_DELAY:
:  the data server is temporarily unable to process
   the request.

NFS4ERR_NOTSUPP:
:  the data server does not implement
   BULK_REVOKE_STATEID.

NFS4ERR_PERM:
:  the request arrived on a session whose owning
   client did not present EXCHGID4_FLAG_USE_PNFS_MDS.

NFS4ERR_SERVERFAULT:
:  the data server failed while processing
   the request.

## Operation 92: CHUNK_ESCROW_INSTALL - Install a metadata-server escrow lock {#sec-CHUNK_ESCROW_INSTALL}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_ESCROW_INSTALL4args {
   ///     /* CURRENT_FH: file */
   ///     uint64_t        ceia_mds_epoch;
   ///     offset4         ceia_offset;
   ///     count4          ceia_count;
   ///     escrow_id4      ceia_escrow_id;
   /// };
~~~
{: #fig-CHUNK_ESCROW_INSTALL4args title="XDR for CHUNK_ESCROW_INSTALL4args" }

### RESULTS

~~~ xdr
   /// union CHUNK_ESCROW_INSTALL4res
   ///     switch (nfsstat4 ceir_status) {
   /// case NFS4_OK:
   ///     escrow_id4      ceir_escrow_id;
   /// default:
   ///     void;
   /// };
~~~
{: #fig-CHUNK_ESCROW_INSTALL4res title="XDR for CHUNK_ESCROW_INSTALL4res" }

### DESCRIPTION

CHUNK_ESCROW_INSTALL is sent by the metadata server
to a data server on the metadata-server-to-data-server control session to
install a metadata-server escrow lock ({{sec-chunk_guard_mds}})
over the chunk range [ceia_offset,
ceia_offset+ceia_count) on the file selected by
CURRENT_FH.  The lock is created with the specified
ceia_escrow_id, which the metadata server will later
present to reference this specific installation on
CHUNK_ESCROW_RELEASE ({{sec-CHUNK_ESCROW_RELEASE}}),
in CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}), and in
the corresponding CHUNK_LOCK adoption
({{sec-CHUNK_LOCK}}).

ceia_mds_epoch is the metadata server's current
epoch on this data server; the data server rejects
the operation with NFS4ERR_STALE_MDS_EPOCH
({{sec-NFS4ERR_STALE_MDS_EPOCH}}) if the epoch does
not match its recorded value or if the current
epoch's expires_at has passed.

The install is all-or-nothing across the range: if
any chunk in [ceia_offset, ceia_offset+ceia_count)
carries an incompatible existing lock, the operation
fails with the corresponding per-chunk error at the
operation level (typically NFS4ERR_CHUNK_LOCKED).

On success, ceir_escrow_id echoes ceia_escrow_id
to confirm the identity the data server recorded.
The metadata server MUST retain this identity in
its durable escrow-tuple set before issuing the
call and MUST NOT reuse an escrow_id4 whose
lifecycle is not provably complete
({{sec-escrow_id4}}).

### RESPONSE CODES

NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR,
NFS4ERR_CHUNK_LOCKED, NFS4ERR_INVAL, NFS4ERR_NOTSUPP,
NFS4ERR_PERM, NFS4ERR_SERVERFAULT,
NFS4ERR_STALE_MDS_EPOCH.

## Operation 93: CHUNK_ESCROW_RELEASE - Release a metadata-server escrow lock {#sec-CHUNK_ESCROW_RELEASE}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_ESCROW_RELEASE4args {
   ///     /* CURRENT_FH: file */
   ///     uint64_t        cera_mds_epoch;
   ///     offset4         cera_offset;
   ///     count4          cera_count;
   ///     escrow_id4      cera_escrow_id;
   /// };
~~~
{: #fig-CHUNK_ESCROW_RELEASE4args title="XDR for CHUNK_ESCROW_RELEASE4args" }

### RESULTS

~~~ xdr
   /// union CHUNK_ESCROW_RELEASE4res
   ///     switch (nfsstat4 cerr_status) {
   /// case NFS4_OK:
   ///     void;
   /// default:
   ///     void;
   /// };
~~~
{: #fig-CHUNK_ESCROW_RELEASE4res title="XDR for CHUNK_ESCROW_RELEASE4res" }

### DESCRIPTION

CHUNK_ESCROW_RELEASE is sent by the metadata server
to release a metadata-server escrow lock it previously
installed with CHUNK_ESCROW_INSTALL
({{sec-CHUNK_ESCROW_INSTALL}}).  The release is
compare-and-release: the operation succeeds only
when an escrow lock covering the requested range
exists on the data server AND its escrow_id4
matches cera_escrow_id.  If no escrow covers the
range, or the covering escrow's identity differs,
the data server returns NFS4ERR_STALE_ESCROW
({{sec-NFS4ERR_STALE_ESCROW}}) and MUST NOT alter
any current lock or escrow state as a side effect.

The compare-and-release rule ensures that a
metadata server which has been superseded by a
newer incarnation cannot release an escrow the
newer incarnation has since re-installed under a
different identity.

cera_mds_epoch is treated as in
{{sec-CHUNK_ESCROW_INSTALL}}; a stale epoch returns
NFS4ERR_STALE_MDS_EPOCH.

Interaction with adopted locks (see
{{sec-chunk_guard_mds}}): if a repair actor has
already adopted this escrow via CHUNK_LOCK with
CHUNK_LOCK_FLAGS_ADOPT ({{sec-CHUNK_LOCK}}), the
escrow no longer exists on the data server as a
distinct lock (the adoption consumes it and
transfers ownership to the client); a subsequent
CHUNK_ESCROW_RELEASE naming that identity returns
NFS4ERR_STALE_ESCROW and MUST NOT affect the
client-owned adopted lock.  The metadata server
interprets NFS4ERR_STALE_ESCROW after possible
adoption as "the escrow was consumed by ADOPT;
wait for the CB_CHUNK_REPAIR response or a
subsequent revocation-transfer signal before
removing durable escrow-tuple bookkeeping."

### RESPONSE CODES

NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR,
NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM,
NFS4ERR_SERVERFAULT, NFS4ERR_STALE_ESCROW,
NFS4ERR_STALE_MDS_EPOCH.

## Operation 94: CHUNK_ESCROW_ENUMERATE - Enumerate metadata-server escrow locks on a file {#sec-CHUNK_ESCROW_ENUMERATE}

### ARGUMENTS

~~~ xdr
   /// /* Upper bound on the ENUMERATE pagination
   ///  * cookie length, applied to both the request
   ///  * ceea_cookie and the response ceer_cookie. */
   /// const CHUNK_ESCROW_ENUMERATE_COOKIE_MAX4 = 256;
   ///
   /// struct CHUNK_ESCROW_ENUMERATE4args {
   ///     /* CURRENT_FH: file */
   ///     uint64_t        ceea_mds_epoch;
   ///     offset4         ceea_offset;
   ///     count4          ceea_count;
   ///     uint32_t        ceea_maxcount;
   ///     opaque
   ///         ceea_cookie<CHUNK_ESCROW_ENUMERATE_COOKIE_MAX4>;
   /// };
~~~
{: #fig-CHUNK_ESCROW_ENUMERATE4args title="XDR for CHUNK_ESCROW_ENUMERATE4args" }

### RESULTS

~~~ xdr
   /// /* Upper bound on the number of escrow_enum_entry4
   ///  * values returned in a single ENUMERATE call.
   ///  * Bounds ceer_entries; the caller may still page
   ///  * via ceer_cookie for larger snapshots. */
   /// const CHUNK_ESCROW_ENUMERATE_MAX4 = 256;
   ///
   /// struct escrow_enum_entry4 {
   ///     offset4         eee_offset;
   ///     count4          eee_count;
   ///     escrow_id4      eee_escrow_id;
   /// };
   ///
   /// struct CHUNK_ESCROW_ENUMERATE4resok {
   ///     bool                 ceer_eof;
   ///     opaque
   ///         ceer_cookie<CHUNK_ESCROW_ENUMERATE_COOKIE_MAX4>;
   ///     escrow_enum_entry4
   ///         ceer_entries<CHUNK_ESCROW_ENUMERATE_MAX4>;
   /// };
   ///
   /// union CHUNK_ESCROW_ENUMERATE4res
   ///     switch (nfsstat4 ceer_status) {
   /// case NFS4_OK:
   ///     CHUNK_ESCROW_ENUMERATE4resok ceer_resok4;
   /// default:
   ///     void;
   /// };
~~~
{: #fig-CHUNK_ESCROW_ENUMERATE4res title="XDR for CHUNK_ESCROW_ENUMERATE4res" }

### DESCRIPTION

CHUNK_ESCROW_ENUMERATE is sent by the metadata
server to discover which metadata-server escrow locks the
data server currently holds on the file selected
by CURRENT_FH.  Each returned entry names an
installed escrow's range and identity.

ceea_offset and ceea_count bound the inspection
range; ceea_maxcount is the maximum number of
entries the caller is willing to receive
(ceea_maxcount = 0 is legal and is the
op-family capability probe: the data server MUST
return NFS4_OK with an empty ceer_entries array
and ceer_eof = TRUE when it implements the
operation, regardless of any escrows present.
A data server that does not implement the
operation returns NFS4ERR_OP_ILLEGAL at COMPOUND
decode time per {{RFC8881}} Section 16.2, which is
distinct from NFS4ERR_NOTSUPP).

Pagination uses ceea_cookie: on the first call the
caller supplies an empty cookie; the data server
returns a snapshot verifier-plus-cursor in
ceer_cookie that the caller supplies on the next
call to continue enumeration.  The data server
MUST return a verifier-consistent snapshot: no
escrow installed after the first call in a
pagination sequence appears in subsequent calls,
and no escrow released after the first call
disappears from subsequent calls (implementations
may achieve this by snapshotting the escrow set
at first-call time and streaming from the
snapshot).  ceer_eof = TRUE signals the end of
the enumeration.

Non-mutating: the operation observes but does not
modify escrow state.

ceea_mds_epoch is treated as in the sibling
operations; a stale epoch returns
NFS4ERR_STALE_MDS_EPOCH.

### RESPONSE CODES

NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR,
NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM,
NFS4ERR_SERVERFAULT, NFS4ERR_STALE_MDS_EPOCH.

## Operation 95: CHUNK_ESCROW_TAKEOVER - Advance metadata-server epoch after incarnation change {#sec-CHUNK_ESCROW_TAKEOVER}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_ESCROW_TAKEOVER4args {
   ///     /* CURRENT_FH: file (implementation-defined;
   ///      * the operation is per-data-server, not
   ///      * per-file; CURRENT_FH is provided per
   ///      * NFSv4.2 COMPOUND convention). */
   ///     uint64_t             ceta_expected_prior_epoch;
   ///     uint64_t             ceta_new_epoch;
   ///     proof_profile_id4    ceta_proof_profile;
   ///     opaque               ceta_proof_data<CETA_INCARNATION_PROOF_MAX4>;
   /// };
~~~
{: #fig-CHUNK_ESCROW_TAKEOVER4args title="XDR for CHUNK_ESCROW_TAKEOVER4args" }

### RESULTS

~~~ xdr
   /// union CHUNK_ESCROW_TAKEOVER4res
   ///     switch (nfsstat4 cetar_status) {
   /// case NFS4_OK:
   ///     void;
   /// default:
   ///     void;
   /// };
~~~
{: #fig-CHUNK_ESCROW_TAKEOVER4res title="XDR for CHUNK_ESCROW_TAKEOVER4res" }

### DESCRIPTION

CHUNK_ESCROW_TAKEOVER is the recovery path a
metadata server uses to assume the escrow-control
role on a data server after an incarnation change
(a failover, a restart, or an operator-mediated
recovery).  It carries an incarnation-lease proof
issued by an authority external to the metadata
server (see {{sec-proof-profile}}) which the data
server verifies before advancing its recorded
metadata-server epoch.

The operation is a compare-and-advance:

- ceta_expected_prior_epoch MUST equal the data
  server's currently-recorded metadata-server
  epoch;
- ceta_new_epoch MUST either exceed the prior
  epoch (ordinary takeover / advance) or equal the
  prior epoch when the caller is renewing the
  lease under the same incarnation (renewal
  form; both values equal the data server's
  current epoch, and only the epoch_expires_at
  field is refreshed);
- ceta_proof_profile MUST name a profile the data
  server supports; and
- ceta_proof_data MUST verify under that profile
  per {{sec-proof-profile}}.

All four conditions are evaluated atomically; on
success the data server updates its recorded
epoch and epoch_expires_at values in a single
step, and subsequent CHUNK_ESCROW_INSTALL,
CHUNK_ESCROW_RELEASE, and CHUNK_ESCROW_ENUMERATE
operations from the new epoch are accepted.
Concurrent takeovers serialize: exactly one
same-expected-prior request wins, and any other
sees NFS4ERR_STALE_MDS_EPOCH on its second
attempt because the prior has advanced.

The strict evaluation order per
{{sec-proof-profile}} is followed:
session-replay-cache lookup first, then
presenter authorization (NFS4ERR_ACCESS on
failure), then profile support (NFS4ERR_NOTSUPP
on unknown profile), then proof verification
(NFS4ERR_ACCESS on failure), then epoch
compare-and-advance (NFS4ERR_STALE_MDS_EPOCH on
mismatch).  This ordering ensures unauthenticated
callers learn nothing about supported profiles
or current epoch state.

Unlike the other CHUNK_ESCROW operations,
CHUNK_ESCROW_TAKEOVER is EXEMPT from the
ongoing epoch_expires_at check applied to
INSTALL, RELEASE, and ENUMERATE: TAKEOVER is
itself the recovery path out of an expired
epoch and carries its own compare-and-advance +
proof-verification semantics.  A metadata server
that has been fenced by a superseding takeover
cannot recover by presenting another
CHUNK_ESCROW_TAKEOVER unless it obtains a valid
fresh incarnation-lease proof from the
authority.

Older escrow state is NOT invalidated by an
epoch advance: escrows installed under the prior
epoch survive; the new incarnation reconciles
them via CHUNK_ESCROW_ENUMERATE and adopts,
releases, or reissues each per its durable
recovery state.  Fencing applies to control
traffic on old epochs, not to the state those
epochs installed.

### RESPONSE CODES

NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR,
NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_PERM,
NFS4ERR_SERVERFAULT, NFS4ERR_STALE_MDS_EPOCH.

# New NFSv4.2 Callback Operations

~~~ xdr
   ///
   /// /* New callback operations for Erasure Coding start here */
   ///
   ///  OP_CB_CHUNK_REPAIR     = 16,
   ///
~~~
{: #fig-cb-ops-xdr title="Callback Operations XDR" }

The following amendment blocks extend the nfs_cb_argop4 and
nfs_cb_resop4 dispatch unions defined in {{RFC7863}} with arms
for the new callback operation defined in this document.

~~~ xdr
   /// /* nfs_cb_argop4 amendment block */
   ///
   /// case OP_CB_CHUNK_REPAIR: CB_CHUNK_REPAIR4args opcbchunkrepair;
~~~
{: #fig-nfs_cb_argop4-amend title="nfs_cb_argop4 amendment block"}

~~~ xdr
   /// /* nfs_cb_resop4 amendment block */
   ///
   /// case OP_CB_CHUNK_REPAIR: CB_CHUNK_REPAIR4res opcbchunkrepair;
~~~
{: #fig-nfs_cb_resop4-amend title="nfs_cb_resop4 amendment block"}

## Callback Operation 16: CB_CHUNK_REPAIR - Request Repair of Inconsistent Chunk Ranges {#sec-CB_CHUNK_REPAIR}

### ARGUMENTS

~~~ xdr
   /// enum cb_chunk_repair_reason4 {
   ///     CB_REPAIR_REASON_RACE  = 1,
   ///     CB_REPAIR_REASON_SCRUB = 2
   /// };
   ///
   /// struct cb_chunk_range4 {
   ///     offset4         ccr_offset;
   ///     count4          ccr_count;
   ///     nfsstat4        ccr_error;
   /// };
   ///
   /// /* Upper bound on the number of ranges named in a
   ///  * single CB_CHUNK_REPAIR (bounds both ccra_ranges
   ///  * and its co-indexed ccrr_range_status).  A repair
   ///  * batch that exceeds this bound is split across
   ///  * multiple callbacks. */
   /// const CB_CHUNK_REPAIR_MAX_RANGES4 = 64;
   ///
   /// struct CB_CHUNK_REPAIR4args {
   ///     nfs_fh4                     ccra_fh;
   ///     stateid4                    ccra_layout_stateid;
   ///     nfstime4                    ccra_deadline;
   ///     cb_chunk_repair_reason4     ccra_reason;
   ///     escrow_id4                  ccra_escrow_id;
   ///     cb_chunk_range4
   ///         ccra_ranges<CB_CHUNK_REPAIR_MAX_RANGES4>;
   /// };
~~~
{: #fig-CB_CHUNK_REPAIR4args title="XDR for CB_CHUNK_REPAIR4args" }

### RESULTS

~~~ xdr
   /// struct CB_CHUNK_REPAIR4res {
   ///     nfsstat4        ccrr_status;
   ///     nfsstat4
   ///         ccrr_range_status<CB_CHUNK_REPAIR_MAX_RANGES4>;
   /// };
~~~
{: #fig-CB_CHUNK_REPAIR4res title="XDR for CB_CHUNK_REPAIR4res" }

### DESCRIPTION

CB_CHUNK_REPAIR is sent by the metadata server to a
selected pNFS client to request that the client repair one
or more non-atomic chunk ranges on the file's data
servers.  CB_CHUNK_REPAIR is the back-channel companion to
the chunk repair flow: the metadata server selects a
repair actor per {{sec-repair-selection}} (those rules
are normative for how the client MUST respond on receipt
of this callback) and uses CB_CHUNK_REPAIR to deliver the
work item.

CB_CHUNK_REPAIR has no analog in {{RFC8881}}.  {{RFC8881}}
back-channel callbacks operate at the layout layer
(CB_LAYOUTRECALL) or the file-state layer (CB_RECALL,
CB_NOTIFY); CB_CHUNK_REPAIR is the new chunk-layer
callback that drives reconstruction or rollback of
non-atomic chunks without requiring a full layout return.

The metadata server provides:

ccra_fh:
:  the filehandle of the file whose chunks are non-atomic.
   The callback compound carries the filehandle directly;
   there is no preceding PUTFH in callback compounds.

ccra_layout_stateid:
:  the recipient client's current layout stateid for the
   file if one is held.  A client that does not hold a
   layout on ccra_fh MUST ignore ccra_layout_stateid (it
   will be the anonymous stateid in that case) and MUST
   acquire one via LAYOUTGET before issuing any CHUNK
   operation on the ranges.

ccra_deadline:
:  an absolute nfstime4 (seconds and nanoseconds since
   the epoch, as defined in Section 3.3.1 of {{RFC8881}})
   by which the client is expected to have driven every
   range to completion (CHUNK_REPAIRED on the
   reconstruction path, or CHUNK_UNLOCK on the rollback
   path).  As with `tsa_expire`
   ({{sec-tight-coupling-lease}}), the wall-clock
   representation assumes the metadata server and the
   repair actor maintain clock synchronization within one
   metadata-server lease period (see the clock-sync
   paragraph in {{sec-tight-coupling-lease}} for the
   deployment options when this cannot be guaranteed);
   under skew, missing the deadline is not
   safety-critical because state cannot be corrupted, but
   spurious deadline expiry SHOULD be avoided by setting
   `ccra_deadline` to at least (current-wall-clock +
   deadline-budget + expected-skew).
   Missing the deadline does not corrupt state -- the
   metadata server MAY re-select another repair actor
   after the deadline elapses -- but a client that has
   missed the deadline MUST re-verify its layout and the
   chunk lock state before continuing any repair-related
   CHUNK operation.

ccra_reason:
:  distinguishes the two flows that cause the metadata
   server to issue a repair callback:

   CB_REPAIR_REASON_RACE:
   :  A live-race repair.  A client (not necessarily the
      recipient of this callback) detected a chunk-level
      non-atomicity at write or read time and reported it
      via LAYOUTERROR.  The metadata server is driving
      repair synchronously because the affected chunk is
      on the critical path of some I/O.  The recipient
      SHOULD prioritise the callback over background
      work.

   CB_REPAIR_REASON_SCRUB:
   :  A background scrub.  The metadata server has
      detected stale or non-atomic payloads during a
      scheduled integrity sweep and is opportunistically
      driving repair.  No client is currently blocked on
      these ranges.  The recipient MAY schedule the
      callback at lower priority than
      CB_REPAIR_REASON_RACE, and MAY return NFS4ERR_DELAY
      to defer repair to a more convenient time; the
      metadata server will retry.

   The two reasons share all other semantics: the same
   ccra_ranges encoding, the same response codes, the same
   deadline contract.  Only the priority and retry
   behavior differs.

ccra_escrow_id:
:  the escrow_id4 ({{sec-escrow_id4}}) of the metadata-server escrow
   lock the metadata server installed to cover every
   range in this callback.  The client presents this
   same escrow_id4 in the cla_adopt discriminant of the
   CHUNK_LOCK request that adopts the escrow (see
   {{sec-CHUNK_LOCK}} "Lock Transfer via
   CHUNK_LOCK_FLAGS_ADOPT"); the data server matches on
   full identity, so a callback ranges over a single
   escrow identity.  If the repair spans ranges the
   metadata server installed under distinct escrow
   identities (for example, when a multi-data-server
   repair needs its own escrow per data server), the
   metadata server MUST issue one CB_CHUNK_REPAIR per
   escrow identity rather than mixing them into a
   single callback.

ccra_ranges:
:  the list of every chunk range the metadata server
   requests the client to repair.  Each entry carries its
   own ccr_error describing the failure mode the client
   is being asked to remedy.  The repair strategy depends
   on the error code; see {{sec-repair-selection}} for
   the normative and guidance split.  The array is
   bounded by CB_CHUNK_REPAIR_MAX_RANGES4; if a repair
   set exceeds that bound, the metadata server splits
   it across multiple callbacks.

The metadata server SHOULD keep each CB_CHUNK_REPAIR
compound within the back-channel maximum
(ca_maxrequestsize) negotiated in CREATE_SESSION (see
Section 18.36.3 of {{RFC8881}}).  If the set of affected
ranges would exceed that maximum, the metadata server MAY
issue multiple CB_CHUNK_REPAIR callbacks to the same
client.  Each callback is independent; the client drives
each to completion before the deadline on that callback's
ranges.

The fact that a range appears in ccra_ranges implies the
data server holds a chunk lock on the range (the failure
occurred in or around a PENDING or FINALIZED state that
established the lock).  The repair actor MUST use
CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT
({{sec-CHUNK_LOCK}}) to take ownership of the lock before
issuing CHUNK_WRITE_REPAIR, CHUNK_ROLLBACK, or CHUNK_WRITE
on any chunk in a requested range.

CB_CHUNK_REPAIR returns a top-level ccrr_status plus a
co-indexed per-range status array ccrr_range_status:

Operation-wide errors (decode failure, authorization failure, session-stale, and other conditions that fail every range at once):

: the
  operation-wide error is placed in ccrr_status and
  ccrr_range_status MUST be empty (zero entries).
Per-range dispositions (the callback is otherwise well-formed and evaluated per range):

: ccrr_range_status carries exactly one nfsstat4 per
  entry in ccra_ranges, co-indexed.  The top-level
  ccrr_status in this case is one of:
    - **NFS4_OK**: every range reached CHUNK_REPAIRED
      or CHUNK_UNLOCK per the completion contract;
      every ccrr_range_status entry is NFS4_OK.
    - **NFS4ERR_PARTIAL** ({{sec-NFS4ERR_PARTIAL}}): at
      least one range did not reach the completion
      state.  The metadata server MUST consume the
      ccrr_range_status array to determine per-range
      outcome; the array is authoritative.  An
      NFS4ERR_PARTIAL response with an empty array
      is malformed and MUST be rejected.

The precedence rule between top-level and per-range
status is that a non-empty ccrr_range_status pairs
only with NFS4_OK or NFS4ERR_PARTIAL at the top
level; every other top-level nfsstat4 carries an
empty ccrr_range_status.

See "RESPONSE CODES" below for the normative
meanings the metadata server attaches to each
returned top-level nfsstat4.

### RESPONSE CODES

The ccrr_status value returned by the client has the following
normative meanings to the metadata server:

NFS4_OK:
:  The client has accepted the request and driven every range in
this callback to completion (CHUNK_REPAIRED or CHUNK_UNLOCK on
every affected chunk).  The metadata server clears the repair
queue entry.

NFS4ERR_DELAY:
:  The client has accepted the request but requires more time.
The metadata server MAY extend the deadline by issuing a new
CB_CHUNK_REPAIR with a later ccra_deadline, or MAY re-select
another client.  The client continues to hold any locks it has
adopted until the original or extended deadline.

NFS4ERR_CODING_NOT_SUPPORTED:
:  The client does not implement the encoding type of the layout
and cannot reconstruct.  The metadata server MUST NOT retry with
the same client and SHOULD select a different client.

NFS4ERR_PAYLOAD_LOST:
:  The client has concluded that the identified ranges cannot
be repaired -- there are not enough surviving shards to
reconstruct and rollback is also impossible.  The metadata
server MUST NOT retry the repair and transitions the affected
ranges into an implementation-defined damaged state.  See
{{sec-NFS4ERR_PAYLOAD_LOST}}.

NFS4ERR_PARTIAL:
:  At least one range in the callback did not reach the
completion contract.  The metadata server MUST consume the
co-indexed ccrr_range_status array to determine the per-range
outcome; NFS4ERR_PARTIAL is not a whole-callback retriable
error and MUST NOT be treated as one.  The array is
authoritative: each ccrr_range_status entry maps directly to
the co-indexed entry in ccra_ranges and is evaluated on its
own terms (NFS4_OK, NFS4ERR_DELAY, NFS4ERR_CODING_NOT_SUPPORTED,
NFS4ERR_PAYLOAD_LOST, or another per-range disposition) per
the result contract above.  An NFS4ERR_PARTIAL response with an
empty ccrr_range_status array is malformed and the metadata
server MUST reject the callback response.  See
{{sec-NFS4ERR_PARTIAL}}.

All other error codes listed in {{tbl-cb-ops-and-errors}} are
treated by the metadata server as retriable: the metadata server
MAY issue a subsequent CB_CHUNK_REPAIR to the same or a
different client.  If the client becomes unreachable (no
response within the deadline), the metadata server re-selects
per {{sec-repair-selection}}.

#  Composed Rollback Guarantee and Error Decision Tree {#sec-composed-rollback}

The flexible file v2 layout chunk protocol combines three
related mechanisms -- writer-supplied opaque owner identity
({{sec-chunk_owner4}}), best-effort predecessor
discovery ({{sec-CHUNK_HEADER_READ}} /
{{sec-NFS4ERR_NO_PREDECESSOR}}), and metadata-server escrow
control-plane pinning ({{sec-CHUNK_ESCROW_INSTALL}} /
{{sec-CHUNK_ESCROW_RELEASE}} /
{{sec-CHUNK_ESCROW_ENUMERATE}} /
{{sec-CHUNK_ESCROW_TAKEOVER}},
{{sec-chunk_guard_mds}}) -- that together deliver a
CONDITIONAL rollback guarantee.  This section states the
guarantee scope precisely and specifies the client-side
decision tree over the composed error set.

##  Guarantee Scope {#sec-composed-rollback-scope}

The composed guarantee is against protocol-level
garbage collection and owner-association release only,
NOT against storage or integrity failures.  It applies
only when three conditions all hold at the moment a
CHUNK_ROLLBACK ({{sec-CHUNK_ROLLBACK}}) is issued
against the named predecessor:

1. **Present at acquisition.**  The predecessor
   generation must have existed on the data server at
   the time the qualifying CHUNK_LOCK or metadata-server escrow
   was acquired.  Predecessors that had already been
   released under the retention scope
   ({{sec-system-model-retention-scope}}) before any
   qualifying lock or escrow was acquired are not
   covered.
2. **Continuous custody.**  The lock or escrow
   custody chain must have remained uninterrupted
   through the rollback decision window.  Custody
   handoffs are permitted (a client-owned lock
   adopted from a metadata-server escrow lock preserves the
   escrow_id4 per {{sec-chunk_guard_mds}}, and a
   subsequent revocation-transfer re-emits the same
   escrow_id4 to a new metadata-server escrow lock, keeping the
   custody chain continuous), but any interval in
   which the predecessor was covered by neither a
   qualifying lock nor a metadata-server escrow lock breaks
   continuity.
3. **Payload remains AVAILABLE.**  The predecessor's
   payload MUST be in the AVAILABLE read-time state
   ({{sec-system-model-read-time-status}}).  A
   predecessor whose payload has become ERRORED
   through media loss, unrecoverable corruption,
   loss of all redundant data servers, or non-conforming
   data-server behavior is not covered
   -- an ERRORED predecessor follows the best-effort
   reconstruction path
   ({{sec-CHUNK_WRITE_REPAIR}}) and MAY terminate
   at NFS4ERR_PAYLOAD_LOST via CB_CHUNK_REPAIR
   ({{sec-CB_CHUNK_REPAIR}}).

When all three conditions hold, a CHUNK_ROLLBACK
that names the predecessor's original owner triple
is guaranteed to restore the predecessor as the
current COMMITTED generation with its original
triple intact
({{sec-CHUNK_ROLLBACK}} "Rollback of COMMITTED
Chunks", case (a)).  When any condition fails, the
call may return NFS4ERR_NO_PREDECESSOR
({{sec-NFS4ERR_NO_PREDECESSOR}}) or NFS4ERR_INVAL
and the caller falls back to best-effort
reconstruction as described in
{{sec-CHUNK_WRITE_REPAIR}} -- best-effort
reconstruction into a NEW generation under a NEW
owner triple, or terminal NFS4ERR_PAYLOAD_LOST
when no authoritative source exists.

The guarantee is a protocol-level protection against
premature release: flexible file v2 layout implementations
MUST NOT release the payload or owner-to-index association of
a predecessor covered by an active qualifying lock or
metadata-server escrow lock, per the payload/association
biconditional
({{sec-system-model-payload-association-biconditional}})
and the retention scope
({{sec-system-model-retention-scope}}) as extended
by the escrow-pin mechanism.  It is not a
guarantee against exogenous failures of the
storage substrate.

##  Client-Side Error Decision Tree {#sec-composed-rollback-tree}

A client operating over the composed error set
distinguishes control-plane failures (which the
metadata server must resolve) from data-plane
failures (which the client can address via
fallback).  Ordering matters: control-plane
failures must be resolved before data-plane
recovery is attempted.

CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT -> NFS4ERR_NO_ADOPTABLE_LOCK ({{sec-NFS4ERR_NO_ADOPTABLE_LOCK}}):

: custody / control-plane failure BEFORE any usable lock is
  in hand.  The four state causes (no escrow / identity
  mismatch / reconciliation hold / already-adopted) are all
  conditions the metadata server is best placed to resolve.
  The client MUST report the outcome via the
  ccrr_range_status array ({{sec-CB_CHUNK_REPAIR}}) and MUST
  NOT unilaterally retry the adoption or begin the
  CHUNK_WRITE_REPAIR fallback path
  ({{sec-CHUNK_WRITE_REPAIR}}); that fallback assumes a
  usable lock, and no lock exists here to fall back under.

CHUNK_LOCK -> NFS4ERR_ACCESS:

: presenter authorization failure.  Report to the metadata
  server; do not retry.

After successful CHUNK_LOCK / ADOPT -> CHUNK_HEADER_READ ({{sec-CHUNK_HEADER_READ}}):

: read the primary owner and chrr_predecessors array.  If the
  intended predecessor's triple appears in the list, proceed
  to CHUNK_ROLLBACK.  If absent, the CHUNK_WRITE_REPAIR
  fallback path may begin directly (do not issue
  CHUNK_ROLLBACK against a predecessor known-absent).

CHUNK_ROLLBACK -> NFS4ERR_NO_PREDECESSOR ({{sec-NFS4ERR_NO_PREDECESSOR}}):

: data-plane result AFTER a usable lock is in hand.  The
  actor has the lock; there is simply no restorable
  predecessor.  The client MAY invoke best-effort
  reconstruction via CHUNK_WRITE_REPAIR under a new owner
  triple ({{sec-CHUNK_WRITE_REPAIR}}); fallback MAY terminate
  at NFS4ERR_PAYLOAD_LOST ({{sec-NFS4ERR_PAYLOAD_LOST}}) if
  no authoritative source exists.

CHUNK_ROLLBACK -> NFS4ERR_INVAL or NFS4ERR_NO_PREDECESSOR for a fresh op naming a released triple:

: terminal per-entry failure.  Caller holds a stale
  reference; no operation defined in this document
  resurrects the deleted generation.  The data server
  returns NFS4ERR_INVAL within the delete case's
  session-slot replay-cache window and NFS4ERR_NO_PREDECESSOR
  after the window has elapsed or for any other terminal
  release (per the release-scope split at
  {{sec-NFS4ERR_NO_PREDECESSOR}}).  Compare either code to
  the uncertain-replay carve-out ({{sec-CHUNK_ROLLBACK}}
  "Idempotence and Uncertain-Replay Carve-Out") which
  permits an EXACT reissue after uncertain prior completion
  to treat NFS4ERR_INVAL or NFS4ERR_NO_PREDECESSOR as
  postcondition-equivalent success, but ONLY when the caller
  independently verifies the postcondition holds.

Any CHUNK_ESCROW operation -> NFS4ERR_STALE_ESCROW ({{sec-NFS4ERR_STALE_ESCROW}}):

: control-plane identity mismatch or no covering escrow on
  the metadata server's own CHUNK_ESCROW_RELEASE.  The
  response never authorizes tuple removal by itself when
  adoption may have consumed the escrow (see
  {{sec-CHUNK_ESCROW_RELEASE}}).

Any CHUNK_ESCROW operation -> NFS4ERR_STALE_MDS_EPOCH ({{sec-NFS4ERR_STALE_MDS_EPOCH}}):

: the metadata server has been fenced by a superseding
  CHUNK_ESCROW_TAKEOVER.  The metadata server MUST obtain a
  fresh incarnation-lease token and reissue via
  CHUNK_ESCROW_TAKEOVER ({{sec-CHUNK_ESCROW_TAKEOVER}});
  TAKEOVER is exempt from this rejection.

CB_CHUNK_REPAIR response -> NFS4ERR_PARTIAL ({{sec-NFS4ERR_PARTIAL}}):

: at least one named range did not reach completion; the
  metadata server MUST consume the per-range
  ccrr_range_status array ({{sec-CB_CHUNK_REPAIR}}) to
  determine per-range outcome.

The essential distinction is that
NFS4ERR_NO_ADOPTABLE_LOCK and
NFS4ERR_NO_PREDECESSOR both prevent the direct
rollback path, but at different lifecycle stages
and with different recovery authorities:
NFS4ERR_NO_ADOPTABLE_LOCK is a custody / control-plane
failure BEFORE the actor obtains usable
custody (unrecoverable unilaterally), while
NFS4ERR_NO_PREDECESSOR is a data-plane result
AFTER successful adoption where the actor
already holds the lock but finds no restorable
predecessor data (the actor MAY invoke
best-effort reconstruction via
CHUNK_WRITE_REPAIR).  A client that receives one MUST NOT
treat it as the other.

##  Worked Example: Composed Rollback and Fallback {#sec-composed-rollback-trace}

The following worked example exercises the three
composed conditions.  A single file has chunk index
5 previously written by client 7 with co_cohort_id
41 and co_id 100 (owner triple (41, 7, 100)) and then
overwritten by client 7 with co_cohort_id 42 and co_id
101 (owner triple (42, 7, 101)), which reached the
COMMITTED state.  The metadata server determines
that the (42, 7, 101) commit was incorrect and
initiates rollback.  The trace shows the happy
path, the lost-callback branch, and the fallback
contrast.

Note that the owner triple is (co_cohort_id,
co_client_id, co_id) throughout, per
{{sec-chunk_owner4}}; per-chunk CAS state
(cg_gen_id, cg_client_id) is data-server-managed and is
distinct from these owner-identity numbers.

Happy path (all three conditions hold):

1. The metadata server proactively installs an
   metadata-server escrow lock over chunk index 5 by sending
   CHUNK_ESCROW_INSTALL with escrow_id4 E1 while
   the (41, 7, 100) predecessor is still
   AVAILABLE on the data server.  The data server
   accepts and echoes E1 in ceir_escrow_id.  Per
   {{sec-composed-rollback-scope}} conditions 1
   and 3, the predecessor is now under continuous
   metadata-server escrow custody and remains AVAILABLE.

2. The metadata server sends CB_CHUNK_REPAIR to a
   selected repair actor with ccra_escrow_id =
   E1 and a range naming chunk index 5.

3. The repair actor issues CHUNK_LOCK with
   CHUNK_LOCK_FLAGS_ADOPT and cla_adopt = { TRUE,
   cla_escrow_id = E1 }.  The data server
   validates identity and atomically transfers
   custody: E1 dissolves as a metadata-server escrow lock,
   the client owns the lock, the predecessor's
   payload and owner association survive intact,
   and E1 is retained as durable custody metadata
   on the client-owned lock (per
   {{sec-chunk_guard_mds}}).  Condition 2
   (continuous custody) is preserved through the
   adoption.

4. The repair actor issues CHUNK_HEADER_READ over
   chunk index 5.  The response shows chrr_chunks
   as the (42, 7, 101) current generation and
   `chrr_predecessors[0]` as the (41, 7, 100)
   retained predecessor
   ({{sec-CHUNK_HEADER_READ}}).

5. The repair actor issues CHUNK_ROLLBACK naming
   the predecessor's triple (41, 7, 100).  The
   data server executes "Rollback of COMMITTED
   Chunks" case (a)
   ({{sec-CHUNK_ROLLBACK}}): the retained
   predecessor is restored as the current
   COMMITTED generation under its original triple
   (41, 7, 100), and the displaced successor's
   triple (42, 7, 101) is atomically invalidated
   ("Deletion Atomicity and Invalidated
   Triples").

6. The repair actor issues CHUNK_UNLOCK.  The
   client-owned lock is released; the preserved
   escrow_id4 custody metadata is cleared.

7. The repair actor returns NFS4_OK on the
   CB_CHUNK_REPAIR response with a co-indexed
   NFS4_OK in ccrr_range_status.  The metadata
   server issues CHUNK_ESCROW_RELEASE with
   cera_escrow_id = E1.  Because E1 was consumed
   by the adoption in step 3, the data server
   returns NFS4ERR_STALE_ESCROW; the metadata
   server interprets this as "the escrow was
   consumed by ADOPT and the callback response
   confirms completion," and clears its
   durable escrow-tuple record for (file, E1,
   {this data server}).

Lost-callback branch:

: Steps 1-6 proceed as
above but the CB_CHUNK_REPAIR response is lost in
transit (data server restart or network failure
before the metadata server receives the reply).
The metadata server never observes step-7 confirmation.
The repair actor's lock lease eventually expires
without an explicit release, and the data server
transitions the lock through the revocation-transfer
path (see {{sec-chunk_guard_mds}}): a new metadata-server escrow
lock is installed on the same range with the same
preserved escrow_id4 = E1.  On the next
CHUNK_ESCROW_ENUMERATE
({{sec-CHUNK_ESCROW_ENUMERATE}}) the metadata server
observes the reappeared E1 and reissues repair
under it.

Fallback contrast (condition 1 fails):

: Under
an alternative setup where the metadata server did
NOT install a metadata-server escrow before the retention
scope
({{sec-system-model-retention-scope}}) released the
(41, 7, 100) predecessor, condition 1 fails.  By
the time repair is initiated the predecessor is
ABSENT on the data server, and the escrow the
metadata server installs pins only what still
exists (there is no predecessor to pin).  The
repair actor's CHUNK_LOCK / CHUNK_HEADER_READ
sequence discovers no retained predecessor for
index 5.  A subsequent CHUNK_ROLLBACK against the
(41, 7, 100) triple returns NFS4ERR_NO_PREDECESSOR
({{sec-NFS4ERR_NO_PREDECESSOR}}).  The client
falls back to CHUNK_WRITE_REPAIR
({{sec-CHUNK_WRITE_REPAIR}}), reconstructing
authoritative bytes from surviving data-server
shards and writing them under a new owner triple
of its own choosing -- for example (43, 7, 102).
The resulting COMMITTED generation carries the
new triple, NOT the released (41, 7, 100).  Any
subsequent lifecycle operation that names the
released (41, 7, 100) triple returns
NFS4ERR_NO_PREDECESSOR -- the (41, 7, 100)
association was released under the retention scope,
not by an explicit CHUNK_ROLLBACK delete case within
a live replay-cache window, so the release-scope
split at {{sec-NFS4ERR_NO_PREDECESSOR}} routes to the
NO_PREDECESSOR arm consistent with the previous
CHUNK_ROLLBACK outcome in this trace: the fallback
creates a new generation, it does not resurrect the
released predecessor.  When no authoritative
source exists for reconstruction, the fallback
itself terminates at NFS4ERR_PAYLOAD_LOST
({{sec-NFS4ERR_PAYLOAD_LOST}}) via
CB_CHUNK_REPAIR.

#  Security Considerations

The combination of components in a pNFS system is required to
preserve the security properties of NFSv4.1+ with respect to an
entity accessing data via a client.  The pNFS feature partitions
the NFSv4.1+ file system protocol into two parts: the control
protocol and the data protocol.  As the control protocol in this
document is NFS, the security properties are equivalent to the
version of NFS being used.  The flexible file v2 layout further divides
the data protocol into metadata and data paths.  The security
properties of the metadata path are equivalent to those of NFSv4.1x
(see Sections 1.7.1 and 2.2.1 of {{RFC8881}}).  And the security
properties of the data path are equivalent to those of the version
of NFS used to access the storage device, with the provision that
the metadata server is responsible for authenticating client access
to the data file.  The metadata server provides appropriate credentials
to the client to access data files on the storage device.  It is
also responsible for revoking access for a client to the storage
device.

The metadata server enforces the file access control policy at
LAYOUTGET time.  The client MUST use RPC authorization credentials
for getting the layout for the requested iomode (LAYOUTIOMODE4_READ
or LAYOUTIOMODE4_RW), and the server verifies the permissions and
ACL for these credentials, possibly returning NFS4ERR_ACCESS if the
client is not allowed the requested iomode.  If the LAYOUTGET
operation succeeds, the client receives, as part of the layout, a
set of credentials allowing it I/O access to the specified data
files corresponding to the requested iomode.  When the client acts
on I/O operations on behalf of its local users, it MUST authenticate
and authorize the user by issuing respective OPEN and ACCESS calls
to the metadata server, similar to having NFSv4 data delegations.

The combination of filehandle, synthetic uid, and gid in the layout
is the way that the metadata server enforces access control to the
data server.  The client only has access to filehandles of file
objects and not directory objects.  Thus, given a filehandle in a
layout, it is not possible to guess the parent directory filehandle.
Further, as the data file permissions only allow the given synthetic
uid read/write permission and the given synthetic gid read permission,
knowing the synthetic ids of one file does not necessarily allow
access to any other data file on the storage device.

The metadata server can also deny access at any time by fencing the
data file, which means changing the synthetic ids.  In turn, that
forces the client to return its current layout and get a new layout
if it wants to continue I/O to the data file.

If access is allowed, the client uses the corresponding (read-only
or read/write) credentials to perform the I/O operations at the
data file's storage devices.  When the metadata server receives a
request to change a file's permissions or ACL, it SHOULD recall all
layouts for that file and then MUST fence off any clients still
holding outstanding layouts for the respective files by implicitly
invalidating the previously distributed credential on all data file
comprising the file in question.  It is REQUIRED that this be done
before committing to the new permissions and/or ACL.  By requesting
new layouts, the clients will reauthorize access against the modified
access control metadata.  Recalling the layouts in this case is
intended to prevent clients from getting an error on I/Os done after
the client was fenced off.

##  Checksum Integrity Scope {#sec-security-checksum-scope}

The checksum values carried in CHUNK_WRITE and returned from
CHUNK_READ defend against accidental data corruption during
storage or transmission -- bit flips on storage media, network
errors, software bugs in the erasure transform.  The threat
model an individual deployment achieves depends on which
checksum_algorithm4 ({{sec-checksum4}}) the metadata server
selects for the file's mirrors via ffv2m_checksum_algorithm
({{sec-ffv2-mirror4}}):

Bit-flip-class algorithms (CRC32, CRC32C, Fletcher4):
:  Detect accidental bit-level corruption with high
   probability.  Do NOT defend against an adversary who can
   modify the payload and recompute a valid checksum, because
   these algorithms are not cryptographic and the algorithm
   identifier and parameters are public.  Suitable when the
   threat model excludes adversaries on the wire and at rest.

Cryptographic-strength algorithms (SHA-256, SHA-512, BLAKE3):
:  Detect accidental corruption with cryptographic-strength
   collision resistance.  These are UNKEYED hashes carried
   alongside the payload on the wire, so they do NOT by
   themselves defend against an adversary who can modify a
   chunk and recompute a valid hash: the attacker knows the
   algorithm and can substitute a matching digest.  Content
   authentication against active adversaries requires a keyed
   MAC or signature scheme (e.g., RPCSEC_GSS_KRB5I,
   RPC-over-TLS with mutual authentication, or an
   application-layer signed manifest) applied at the trust
   boundary; the checksum mechanism defined here provides
   corruption detection, not content authentication.
   Suitable when chunks may be at rest on storage the
   deployment does not fully control and the deployment
   layers cryptographic transport or storage integrity on
   top of the checksum for adversarial protection.

CHECKSUM_ALG_NONE:
:  No protocol-level integrity check.  The deployment is
   relying on transport-layer integrity (RPC-over-TLS
   {{RFC9289}}, RPCSEC_GSS_KRB5I) or storage-layer integrity
   (filesystem checksums on the data server, RAID-level
   integrity) instead.  Suitable when those other layers are
   reliably present end-to-end and the per-chunk wire
   protection would be redundant.

Deployments requiring protection against active attackers
SHOULD select one of the cryptographic algorithms, OR use
CHECKSUM_ALG_NONE in conjunction with RPC-over-TLS
({{sec-tls}}) or RPCSEC_GSS, whichever fits the deployment's
existing security architecture.

An authenticated client is in the "active attacker" role with
respect to its own chunks, in a restricted sense.  The data
server validates the checksum against the bytes the client
provided, so an authenticated client that chooses to send
semantically-invalid bytes with a correctly computed checksum will
have those bytes accepted.  The residual risk differs per
authentication model:

-  Under AUTH_SYS with loose coupling, the residual risk is
   essentially the pre-existing attack surface of NFSv3 writes:
   any host that can reach the data server with a valid uid can
   write nonsense to chunks that uid owns.  This is the Flex
   Files v1 authorization model, which flexible file v2 layout inherits
   without modification for this path.

-  Under RPCSEC_GSS or TLS with mutual authentication, the
   residual risk reduces to: only the authenticated client
   can write nonsense into chunks it owns.  Cross-client
   corruption is prevented because the data server verifies the
   principal before accepting the write.  The remaining
   exposure is at the client's own integrity: any deployment
   that relies on data integrity above the wire MUST apply
   application-level content validation.

Flexible file v2 layout does not attempt to defend against this
authenticated-but-malicious case.  The checksum mechanism is a
transport-integrity check, not a content-integrity check; the
system trust model assumes that an authenticated principal is
entitled to destroy the content of chunks it owns.

##  Chunk Lock and Lease Expiry

When a client holds a chunk lock (acquired via CHUNK_LOCK) and its
lease expires or the client crashes, the lock is released implicitly
by the data server.  This opens a window in which another client
may write to the previously locked range before the original client's
repair is complete.  Implementations SHOULD ensure that the lease
period for chunk locks is sufficient to complete repair operations,
and SHOULD implement CHUNK_UNLOCK explicitly on abort paths.  The
metadata server's LAYOUTERROR and LAYOUTRETURN mechanisms provide
the coordination point for detecting and resolving such races.

##  Error Code Information Disclosure

The new error codes NFS4ERR_CHUNK_LOCKED (10099) and
NFS4ERR_PAYLOAD_NOT_ATOMIC (10098) convey information about
chunk state to the caller.  Both of these errors MAY be returned
to callers whose credentials have not been verified by the data
server (e.g., when the AUTH_SYS uid presented does not match the
synthetic uid on the data file).  The information they reveal --
that a chunk is locked, or that a CRC mismatch occurred -- does
not directly disclose file contents but may indicate concurrent
write activity.  Implementations that are concerned about this
level of disclosure SHOULD require that CHUNK operations
only succeed after credential verification and return
NFS4ERR_ACCESS for unverified callers rather than the more
specific error codes.

This document adds NFS4ERR_NO_PREDECESSOR (10103),
NFS4ERR_NO_ADOPTABLE_LOCK (10104), NFS4ERR_STALE_ESCROW (10105),
NFS4ERR_STALE_MDS_EPOCH (10106), and NFS4ERR_PARTIAL (10107).
All five reveal control-plane or discovery state that a
compromised or curious caller could aggregate into a picture of
which files are under repair, which are pinned, and which epoch
is current.  A data server SHOULD enforce presenter
authorization before returning any of these codes so that an
unauthorized caller receives NFS4ERR_ACCESS rather than the
specific state indicator.  In particular, NFS4ERR_STALE_MDS_EPOCH
and unknown-profile NFS4ERR_NOTSUPP on CHUNK_ESCROW_TAKEOVER are
gated behind presenter authorization by the strict evaluation
order in {{sec-proof-profile}}; that ordering is a security
requirement, not merely a diagnostic preference.

##  Escrow Control Plane and Incarnation Proofs {#sec-security-escrow}

This document's escrow control plane introduces four operations
(CHUNK_ESCROW_INSTALL, CHUNK_ESCROW_RELEASE,
CHUNK_ESCROW_ENUMERATE, CHUNK_ESCROW_TAKEOVER --
{{sec-CHUNK_ESCROW_INSTALL}} through
{{sec-CHUNK_ESCROW_TAKEOVER}}) and one proof envelope
({{sec-proof-profile}}) whose security properties merit
dedicated treatment.

###  Authorization scope

CHUNK_ESCROW_INSTALL, CHUNK_ESCROW_RELEASE, and
CHUNK_ESCROW_ENUMERATE MUST be invoked only by the metadata
server currently holding the incarnation lease.  A data server
MUST authenticate the presenter via RPCSEC_GSS
({{!RFC7861}}) and verify the presenter's principal against
the deployment-configured metadata-server principal(s) for
the file's device before accepting any escrow-family
operation; presenter authorization failure returns
NFS4ERR_ACCESS with no side effect on escrow state.  This
authorization is orthogonal to the ordinary client-facing
NFSv4 access controls: an authenticated pNFS client's
credentials MUST NOT authorize an escrow-family operation
even if the client is otherwise permitted to read or write
the file.  A data server that receives any escrow-family
operation on a session belonging to a non-metadata-server
principal MUST reject with NFS4ERR_ACCESS or NFS4ERR_PERM
per the ordinary NFSv4 rules.

###  Trust anchor lifecycle

The proof profile depends on a deployment-provisioned trust
anchor at each data server ({{sec-proof-profile}} "Trust
Anchor Provisioning").  Anchor compromise permits an
adversary to forge incarnation-lease tokens and stage
takeovers of the escrow control plane; anchor
unavailability blocks legitimate takeovers and inhibits
recovery from an incarnation failure.  Deployments SHOULD:

- provision separate anchors per proof profile so revocation
  of one profile does not require replacing keys for others;
- rotate anchors on a schedule consistent with the
  authority's own key-management posture (this specification
  does not mandate a rotation interval); and
- retain the ability to revoke an anchor out-of-band without
  requiring a wire-level protocol message, because a
  compromised anchor's tokens will otherwise satisfy the
  data server's strict-ordering checks by construction.

An incarnation-lease authority MUST NOT delegate signing to
any component the metadata server can spoof; the security of
the proof mechanism rests on the assumption that the
authority is a distinct entity from any metadata server and
can independently attest current single writer ownership.

###  Replay-cache exhaustion and durability

The token_id replay cache at the data server
({{sec-proof-profile}} "Presentation and Verification") is a
finite resource.  A hostile presenter that can obtain many
valid tokens for the same profile MAY attempt to grow the
cache without bound.  A data server SHOULD bound the cache
size and expire entries no later than their token's
expires_at; entries older than the longest admissible
issued_at-to-expires_at window MAY be evicted.  Eviction
does not sacrifice lost-response recovery: the byte-identical
uncertain-completion recovery path
({{sec-CHUNK_ESCROW_TAKEOVER-uncertain-completion}})
recognizes both the cache-hit and the cache-miss form of
the same reissue, so a token whose replay entry has aged
out still resolves to NFS4_OK when its ceta_new_epoch
equals the data server's currently-recorded epoch and its
ceta_expected_prior_epoch is strictly prior.  A hostile
presenter cannot exploit the cache-miss form to advance
the epoch: proof verification still gates on the token's
signature and principal, and once a subsequent successful
TAKEOVER advances past ceta_new_epoch the reissue no
longer satisfies the postcondition-equivalent predicates.

Data servers that persist the token_id cache across restart
MUST persist and evict entries coherently with expires_at
values.  A data server that does not persist the cache
returns to the freshly-initialized state after restart;
lost-response reissues still resolve through the cache-miss
form of the uncertain-completion recovery path.

###  Discovery information disclosure

CHUNK_ESCROW_ENUMERATE and the CHUNK_HEADER_READ
predecessor arm ({{sec-CHUNK_HEADER_READ}}) disclose
control-plane and discovery information.
CHUNK_ESCROW_ENUMERATE is gated behind the escrow-role
authorization above; CHUNK_HEADER_READ's predecessor list is
available to any pNFS client holding a valid layout for the
file.  A deployment where predecessor identity is itself
sensitive (for example, because owner triples encode
information about the writer's identity that ordinary read
authorization does not disclose) SHOULD scope the layout so
that only appropriately-authorized clients can obtain it.
The specification does not require the data server to
suppress predecessor disclosure on a per-client basis; where
that is required, deploy at the layout-authorization layer.

###  Resource exhaustion via long-lived escrows

A compromised or faulty metadata server can install an
arbitrary number of long-lived metadata-server escrow locks via
CHUNK_ESCROW_INSTALL, each of which forces retention of a
predecessor generation the data server would otherwise
release under the retention scope rule
({{sec-system-model-retention-scope}}).  Sustained abuse
could exhaust data-server storage.  A data server MAY apply
implementation-defined admission control on the total number
of metadata-server escrow locks it holds concurrently, rejecting further
CHUNK_ESCROW_INSTALL with NFS4ERR_SERVERFAULT or a
resource-exhaustion error when the bound is reached; the
metadata server can then release older escrows or wait for
their natural completion before retrying.  This
specification does not prescribe a concrete bound; the
choice is deployment-local and interacts with the
data-server's storage-management policy.

###  Consequence of losing durable adopted-lock escrow identity

The client-owned lock that adopted a metadata-server escrow retains the
adopted escrow_id4 as durable custody metadata per
{{sec-chunk_guard_mds}}; on data-server restart this
metadata must survive so a subsequent revocation-transfer
re-emits the same identity.  A data server that fails to
persist the adopted escrow_id4 (whether by implementation
defect or storage corruption) forces the metadata server's
tuple bookkeeping into an unresolvable state: the recovered
metadata-server escrow appears with a fresh identity that no durable
tuple matches, and the composed rollback guarantee
({{sec-composed-rollback}}) is broken for repairs that
crossed the restart.  A deployment SHOULD monitor for
missing-adopted-id events and treat them as a data-server
failure requiring operator investigation.

##  Transport Layer Security {#sec-tls}

RPC-over-TLS {{RFC9289}} MAY be used to protect traffic between the
client and the metadata server and between the client and data servers.
When RPC-over-TLS is in use on the data server path, the synthetic
uid/gid credentials carried in AUTH_SYS remain the access control
mechanism; TLS provides confidentiality and integrity for the transport
but does not replace the fencing model described in {{sec-Fencing-Clients}}.
Servers that require transport security SHOULD advertise this via the
SECINFO mechanism rather than silently dropping connections.

##  RPCSEC_GSS and Security Services

This document does not specify how RPCSEC_GSS {{RFC7861}} is
used between the client and a storage device in the loosely
coupled model, and the reasons differ between the two coupling
models.  Because the loosely coupled model uses synthetic
credentials that are managed by the metadata server rather than
shared with the storage device, a full RPCSEC_GSS integration
would require protocol work (RPCSEC_GSSv3 structured privilege
assertions, per {{RFC7861}}) on all three of the metadata
server, the storage device, and the client.  In the tightly
coupled model the principal used to access the data file is the
same as the one used to access the metadata file, so
RPCSEC_GSS applies unchanged.  The two subsections below treat
each model in turn.

###  Loosely Coupled

RPCSEC_GSS version 3 (RPCSEC_GSSv3) {{RFC7861}} contains facilities
that would allow it to be used to authorize the client to the storage
device on behalf of the metadata server.  Doing so would require
that each of the metadata server, storage device, and client would
need to implement RPCSEC_GSSv3 using an RPC-application-defined
structured privilege assertion in a manner described in Section
4.9.1 of {{RFC7862}}.  The specifics necessary to do so are not
described in this document.  This is principally because any such
specification would require extensive implementation work on a wide
range of storage devices, which would be unlikely to result in a
widely usable specification for a considerable time.

As a result, the layout type described in this document will not
provide support for use of RPCSEC_GSS together with the loosely
coupled model.  However, future layout types could be specified,
which would allow such support, either through the use of RPCSEC_GSSv3
or in other ways.

###  Tightly Coupled

With tight coupling, the principal used to access the metadata file
is exactly the same as used to access the data file.  The storage
device can use the control protocol to validate any RPC credentials.
As a result, there are no security issues related to using RPCSEC_GSS
with a tightly coupled system.  For example, if Kerberos V5 Generic
Security Service Application Program Interface (GSS-API) {{RFC4121}}
is used as the security mechanism, then the storage device could
use a control protocol to validate the RPC credentials to the
metadata server.

##  Trusted Stateids {#sec-security-trust-stateid}

The TRUST_STATEID, REVOKE_STATEID, and BULK_REVOKE_STATEID
operations ({{sec-TRUST_STATEID}}, {{sec-REVOKE_STATEID}},
{{sec-BULK_REVOKE_STATEID}}) introduce a per-stateid
authorization channel between the metadata server and the
data server.  The security implications of that channel are
distinct from those of the loosely coupled synthetic-uid
model ({{sec-Fencing-Clients}}) and warrant their own
treatment.

###  Interaction with Kerberos and RPCSEC_GSS

Trusted stateids decouple the credential the data server
uses to authorize I/O from the credential the client uses
to authenticate to the data server.  Under loose coupling
({{sec-Fencing-Clients}}), the metadata server inserts a
synthetic uid/gid into the layout and the client presents
that synthetic credential on every data-server RPC; the
data server has no independent verification of the
client's identity, and a client that learns another
client's synthetic uid/gid can impersonate it on the data
path.  Tight coupling via TRUST_STATEID changes this in
three ways:

-  The metadata server records the client's authenticated
   principal in the trust entry via tsa_principal at
   TRUST_STATEID time ({{sec-TRUST_STATEID}}).  Under
   RPCSEC_GSS (typically Kerberos V5 GSS-API per
   {{RFC4121}}), tsa_principal is the GSS display name
   (for example, "alice@REALM"); under AUTH_SYS and TLS,
   tsa_principal is the empty string.

-  The client presents its own RPCSEC_GSS context on each
   CHUNK operation against the data server.  Under
   tight coupling with GSS, the data server MUST verify
   that the principal carried in the inbound RPC's
   RPCSEC_GSS context matches the tsa_principal recorded
   for the stateid in its trust table; a mismatch returns
   NFS4ERR_ACCESS.  A client that learned another
   client's layout stateid (from a log file, a packet
   capture of cleartext RPC, or any other leak) cannot
   use it because their own GSS principal would not
   match.

-  The data server does NOT need its own Kerberos keytab
   to validate each client principal individually.  In a
   loose coupling Kerberos deployment the data server
   would have to be a service principal in every realm
   it serves clients from; under tight coupling the data
   server's keytab is only required for its session with
   the metadata server (the control session,
   {{sec-tight-coupling-control}}).  Operational
   complexity of Kerberos deployment is meaningfully
   reduced.

The mechanism does not authenticate the metadata server
to the client; it authenticates the client to the data
server using credentials the metadata server vouched for
at LAYOUTGET time.  Compromise of the metadata server
allows an attacker to register arbitrary trust entries;
the metadata server is the trust anchor for the layout
grant, unchanged from the existing pNFS layout-issuance
model.

###  Attack Surfaces and Mitigations

Compromised metadata server:
:  An attacker controlling the metadata server can issue
   TRUST_STATEID for any (layout stateid, principal)
   pair.  This is the same trust assumption pNFS already
   makes -- the metadata server grants layouts and the
   data servers honor them.  Deployment defense is the
   same: restrict administrative access to the metadata
   server, require RPCSEC_GSS or RPC-over-TLS
   ({{RFC9289}}) with mutual authentication on the
   control session ({{sec-tight-coupling-control}}), and
   monitor for anomalous TRUST_STATEID volume.

Compromised data server:
:  A compromised data server sees plaintext chunk
   payloads at rest and on the wire (subject to whatever
   the deployment uses for at-rest encryption and
   transport security).  It can return arbitrary content
   on CHUNK_READ with a correctly computed checksum; the
   checksum protects against transport corruption, not
   adversarial content ({{sec-security-checksum-scope}}).
   This is the same as the RAID-stripe trust model:
   each shard host can lie about its shard.  Deployment
   defences are encryption at rest, an integrity-protected
   transport (RPCSEC_GSS_KRB5I or TLS), and
   physical or logical isolation of data servers.

Stateid leak from client to attacker:
:  Under tight coupling with RPCSEC_GSS, a leaked
   stateid is not exploitable: the attacker's own RPC
   principal will not match tsa_principal in the trust
   table, and the data server returns NFS4ERR_ACCESS.
   Under tight coupling with AUTH_SYS over TLS (where
   tsa_principal is empty), a leaked stateid is
   exploitable by any attacker who can also forge the
   source-address binding the data server's TLS session
   expects; this is the standard AUTH_SYS-over-TLS
   trust model, unchanged.

Replay of revoked stateid:
:  After REVOKE_STATEID or BULK_REVOKE_STATEID the data
   server removes the trust entry and subsequent CHUNK
   operations presenting the revoked stateid fail with
   NFS4ERR_BAD_STATEID ({{sec-REVOKE_STATEID}}).  An
   in-flight CHUNK operation that arrived before the
   revoke completed MAY be allowed to finish; the
   chunk_guard4 CAS ({{sec-chunk_guard4}}) bounds the
   worst-case damage from such in-flight I/O to the
   chunks already PENDING at revocation time, and the
   lock-transfer-to-metadata-server escrow rule
   ({{sec-chunk_guard_mds}}) prevents a write hole from
   opening during revocation.

Compromised control session:
:  An attacker who controls the metadata-server-to-data-server
   control session can register or revoke
   arbitrary trust entries.  The control session is the
   most security-sensitive element introduced by tight
   coupling.  Deployment MUST protect it with RPCSEC_GSS
   ({{RFC7861}}) using a service principal both sides
   trust, or with RPC-over-TLS ({{RFC9289}}) using
   mutual authentication and allowlisted certificates.
   The data server enforces that TRUST_STATEID,
   REVOKE_STATEID, and BULK_REVOKE_STATEID only arrive
   on sessions whose owning client presented
   EXCHGID4_FLAG_USE_PNFS_MDS at EXCHANGE_ID
   ({{sec-TRUST_STATEID}}), but that flag alone does not
   authenticate the metadata server.

Resource exhaustion via trust-table flood:
:  A misbehaving metadata server could register an
   unbounded number of TRUST_STATEID entries to exhaust
   the data server's trust-table memory.  The mechanism
   defending against this is the tsa_expire lease on
   each entry: trust entries that are not renewed
   before expiry are reaped by the data server.  A data
   server under memory pressure MAY also return
   NFS4ERR_DELAY on new TRUST_STATEID requests, forcing
   the metadata server to back off.

Cross-metadata-server isolation:
:  In a deployment where two metadata servers share a
   single data server, the per-entry metadata-server
   tag (derived from the control session's owning
   client; see {{sec-TRUST_STATEID}}) ensures that
   REVOKE_STATEID and BULK_REVOKE_STATEID from one
   metadata server cannot remove entries registered by
   the other.  A compromised metadata server can,
   however, register entries against any filehandle the
   data server exposes to it.  Deployments concerned
   about cross-metadata-server isolation MUST partition
   the data server's filesystem namespace into
   per-metadata-server exports at the data server,
   rather than rely on the trust table alone to enforce
   file-level boundaries between metadata servers.

A repair actor reconstructs and writes shards on behalf of other
clients via CHUNK_WRITE_REPAIR.  A malicious or buggy repair actor
is therefore a write path into data it did not originate; the
metadata server MUST validate repaired shards against the file's
registered checksum before accepting them, and integrity against a
malicious data server (as opposed to bit-flips) requires a
cryptographic checksum_algorithm together with transport security.
CHECKSUM_ALG_NONE and the CRC variants provide bit-flip detection
only.

#  IANA Considerations {#iana-considerations}

{{RFC8881}} introduced the "pNFS Layout Types Registry"; new layout
type numbers in this registry need to be assigned by IANA.  This
document defines a new layout type number: LAYOUT4_FLEX_FILES_V2
(see {{tbl_layout_types}}).

 | Layout Type Name      | Value | RFC      | How | Minor Versions |
 |---
 | LAYOUT4_FLEX_FILES_V2 | 0x6   | RFCTBD10 | L   | 1              |
{: #tbl_layout_types title="Layout Type Assignments"}

{{RFC8881}} also introduced the "NFSv4 Recallable Object Types
Registry".  This document defines new recallable objects for
RCA4_TYPE_MASK_FF2_LAYOUT_MIN and RCA4_TYPE_MASK_FF2_LAYOUT_MAX
(see {{tbl_recallables}}).

 | Recallable Object Type Name   | Value | RFC      |How| Minor Versions    |
 |---
 | RCA4_TYPE_MASK_FF2_LAYOUT_MIN | 20    | RFCTBD10 |L  | 1        |
 | RCA4_TYPE_MASK_FF2_LAYOUT_MAX | 21    | RFCTBD10 |L  | 1        |
{: #tbl_recallables title="Recallable Object Type Assignments"}

This document also requests IANA to register a new bit in the
"EXCHGID4_FLAG_*" flag space for the ExchangeID operation from
{{RFC8881}} Section 18.35.3.  The requested value is
`0x00100000`, outside the existing MASK_PNFS block (0x00070000);
IANA MAY assign a different value at its discretion, in which
case the numeric value in {{fig-EXCHGID4_FLAG_USE_ERASURE_DS}}
and its uses throughout the document are updated to match the
assignment.

 | Flag Name                     | Value      | RFC      | Reference                                        |
 |---
 | EXCHGID4_FLAG_USE_ERASURE_DS  | 0x00100000 | RFCTBD10 | {{fig-EXCHGID4_FLAG_USE_ERASURE_DS}}, this doc  |
{: #tbl_exchgid_flags title="EXCHGID4 Flag Assignments"}

This document requests IANA to allocate two attribute numbers in
the NFSv4 attribute-number registry (see Section 20 of {{RFC8881}}).

 | Attribute Number | Attribute Name                  | RFC      | Reference                            |
 |---
 | 89               | FATTR4_CODING_BLOCK_SIZE        | RFCTBD10 | {{sec-fattr4_coding_block_size}}     |
 | 90               | FATTR4_FFV2_CHUNKED_DATA_FILE   | RFCTBD10 | {{sec-fattr4_ffv2_chunked_data_file}} |
{: #tbl_attribute_assignments title="NFSv4 Attribute Assignments"}

This document introduces the 'Flexible File Version 2 Layout Type
Erasure Encoding Type Registry'.  The registry uses a 32-bit value
space partitioned into ranges based on the intended scope of the
encoding type (see {{tbl-coding-ranges}}).

 | Range | Purpose | Allocation Policy |
 | ---
 | 0x0000                | Reserved (uninitialised) | -- |
 | 0x0001-0x00FF         | Standards Track | IETF Review |
 | 0x0100-0x0FFF         | Experimental | Expert Review |
 | 0x1000-0x7FFF         | Vendor (open) | First Come First Served |
 | 0x8000-0xFFFE         | Private/proprietary | No registration required |
 | 0xFFFF                | Reserved | -- |
 | 0x00010000-0xFFFFFFFF | Reserved (upper range) | Reserved for future partition |
{: #tbl-coding-ranges title="Erasure Encoding Type Value Ranges (32-bit space)"}

The upper 16 bits of the 32-bit value space (0x00010000 through
0xFFFFFFFF) are reserved for future range extensions.  A receiver
that observes an `ffv2_encoding_type4` value in the reserved
region MUST treat it as an unsupported encoding type
(NFS4ERR_CODING_NOT_SUPPORTED).  Value 0x0000 is reserved as the
uninitialised-field sentinel and MUST NOT be allocated to an
encoding.

Standards Track (0x0000-0x00FF):
:  Enencoding types intended for broad interoperability.  The
specification MUST include a complete mathematical description
sufficient for independent interoperable implementations (see
{{encoding-type-interoperability}}).  Allocated by IETF Review.

Experimental (0x0100-0x0FFF):
:  Enencoding types under development or evaluation.  An Internet-Draft
is sufficient for allocation.  The specification SHOULD include
enough detail for interoperability testing.  Allocated by Expert
Review.

Vendor (open) (0x1000-0x7FFF):
:  Enencoding types with a published specification or patent reference.
Interoperability is expected among implementations that license or
implement the specification.  The registration MUST include either a
math specification or a patent reference.  Allocated First Come
First Served.

Private/proprietary (0x8000-0xFFFE):
:  Enencoding types for use within a single vendor's ecosystem.
No IANA registration is required.  Interoperability with other
implementations is not expected; accidental codepoint collisions
between independent vendors are possible and are managed
operationally rather than by protocol mechanism.  The encoding
type name SHOULD include an organizational identifier (e.g.,
`FFV2_ENCODING_ACME_FOOBAR`).  A client that encounters a
value in this range from an unrecognized server SHOULD treat
it as an unsupported encoding type
(`NFS4ERR_CODING_NOT_SUPPORTED`).

This partitioning prevents contention for small numbers in the
Standards Track range and provides a clear signal to clients about
what level of interoperability to expect.

This document defines seven encoding types: the flexible file v1 layout-compatible
PASSTHROUGH (see {{sec-encoding-passthrough}}), the chunked
MIRRORED (see {{sec-encoding-mirrored}}), and five chunked
erasure encoding types (see {{tbl-coding-types}}).

 | Encoding Type Name | Value | RFC      | How | Minor Versions    |
 | ---
 | FFV2_ENCODING_PASSTHROUGH            | 1     | RFCTBD10 | L   | 2        |
 | FFV2_ENCODING_MOJETTE_SYSTEMATIC     | 2     | RFCTBD10 | L   | 2        |
 | FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC | 3     | RFCTBD10 | L   | 2        |
 | FFV2_ENCODING_RS_VANDERMONDE         | 4     | RFCTBD10 | L   | 2        |
 | FFV2_ENCODING_MIRRORED               | 5     | RFCTBD10 | L   | 2        |
 | FFV2_ENCODING_XOR_PARITY             | 6     | RFCTBD10 | L   | 2        |
 | FFV2_ENCODING_LINUX_MD_RAID          | 7     | RFCTBD10 | L   | 2        |
{: #tbl-coding-types title="Flexible File Version 2 Layout Type Encoding Type Assignments"}

##  Checksum Algorithm Registry {#iana-checksum-algorithms}

This document introduces the "Flexible File Version 2
Layout Type Checksum Algorithm Registry".  Values in this
registry name the checksum_algorithm4
({{sec-checksum4}}) carried in checksum4 on the wire and
selected per-mirror via ffv2m_checksum_algorithm
({{sec-ffv2-mirror4}}).

The registry uses a 32-bit value space.  Registration
policy is Specification Required {{RFC8126}}; the Designated
Expert reviews each request for:

-  a complete and publicly available specification of the
   algorithm sufficient for independent interoperable
   implementations;

-  the exact length of the cs_value field for this
   algorithm (a single registered length per algorithm;
   variable-length variants register separately);

-  collision risk against existing registrations (the
   Expert MAY decline to register an algorithm whose
   output overlaps substantially with an existing
   registration).

Initial registrations are listed in
{{tbl-checksum-algorithms}}.

 | Name | Value | cs_value bytes | Class | RFC |
 | ---
 | CHECKSUM_ALG_NONE      | 0 | 0  | none           | RFCTBD10 |
 | CHECKSUM_ALG_CRC32     | 1 | 4  | bit-flip       | RFCTBD10 |
 | CHECKSUM_ALG_CRC32C    | 2 | 4  | bit-flip       | RFCTBD10 |
 | CHECKSUM_ALG_FLETCHER4 | 3 | 32 | bit-flip       | RFCTBD10 |
 | CHECKSUM_ALG_SHA256    | 4 | 32 | cryptographic  | RFCTBD10 |
 | CHECKSUM_ALG_SHA512    | 5 | 64 | cryptographic  | RFCTBD10 |
 | CHECKSUM_ALG_BLAKE3    | 6 | 32 | cryptographic  | RFCTBD10 |
{: #tbl-checksum-algorithms title="Initial Checksum Algorithm Registrations"}

CHECKSUM_ALG_NONE (value 0) indicates that no
protocol-level checksum is computed.  The deployment relies
on transport-layer integrity (RPC-over-TLS, RPCSEC_GSS_KRB5I)
or storage-layer integrity instead; see
{{sec-security-checksum-scope}}.

CHECKSUM_ALG_CRC32 (value 1) is the CRC-32 algorithm
specified in {{ITU-V42}} Section 8.1.1.6.2 (the same CRC
used in Ethernet {{IEEE802-3}} Section 3.2.9, PNG
{{RFC2083}} Annex D, and zlib {{RFC1950}}).  Concrete
parameters, which two independent implementations MUST
agree on to interoperate: generator polynomial
`0x04C11DB7` (equivalently, the reflected form
`0xEDB88320`); initial register value `0xFFFFFFFF`; final
XOR value `0xFFFFFFFF`; input reflected; output reflected.
The 4-byte `cs_value` carries the CRC as a big-endian
integer.  Covered bytes follow the uniform coverage rule
in {{sec-checksum4}} (chunk header + chunk payload with
the checksum field's bytes treated as zero, in
wire-transmission order).  Deployments SHOULD prefer
CHECKSUM_ALG_CRC32C for new files since CRC32C is
hardware-accelerated on every modern CPU.

CHECKSUM_ALG_CRC32C (value 2) is the CRC-32 with the
Castagnoli polynomial specified in {{RFC3720}} Section
12.1 and adopted by {{RFC4960}} Section 6.4 (SCTP), and
also as the SSE4.2 / ARMv8 / RISC-V CRC-32C
hardware-acceleration instructions.  Concrete parameters:
generator polynomial `0x1EDC6F41` (equivalently, the
reflected form `0x82F63B78`); initial register value
`0xFFFFFFFF`; final XOR value `0xFFFFFFFF`; input
reflected; output reflected.  The 4-byte `cs_value`
carries the CRC as a big-endian integer.  Covered bytes
follow the uniform coverage rule in {{sec-checksum4}}.

CHECKSUM_ALG_FLETCHER4 (value 3) is the ZFS Fletcher4
variant as documented in the OpenZFS on-disk format
specification {{OPENZFS-FLETCHER4}}.  Covered bytes
follow the uniform coverage rule in {{sec-checksum4}};
this algorithm additionally requires the covered input
(header + chunk with the checksum field's bytes treated
as zero) to be a multiple of 4 bytes, since the input is
processed as a sequence of little-endian 32-bit words.
Implementations that need to checksum a chunk whose
covered input is not a multiple of 4 bytes pad with zero
bytes and register the padded variant separately.
Concrete parameters: the four 64-bit accumulators `A`,
`B`, `C`, `D` are updated per word `wi` as
`A += wi; B += A; C += B; D += C` with 64-bit unsigned
wrap-around; the 32-byte `cs_value` is the concatenation
`A || B || C || D` with each accumulator serialized in
big-endian byte order.  Other Fletcher4 implementations
(different word width, different endianness, truncated
output) register separately.

CHECKSUM_ALG_SHA256 (value 4) and CHECKSUM_ALG_SHA512
(value 5) are the SHA-256 and SHA-512 hash algorithms
specified in {{FIPS-180-4}}, with output byte lengths 32
and 64 respectively.  The `cs_value` carries the hash
output in the byte order defined by {{FIPS-180-4}} Section
3.1 (most-significant word first, each word serialized
big-endian).  Covered bytes follow the uniform coverage
rule in {{sec-checksum4}}.

CHECKSUM_ALG_BLAKE3 (value 6) is the BLAKE3 hash algorithm
specified in {{BLAKE3-SPEC}} at its standard 32-byte
output length (BLAKE3 in its default mode, no keyed hash,
no key-derivation context, no XOF output at other
lengths).  Extended-output BLAKE3, keyed BLAKE3, and the
key-derivation mode register as separate algorithms.
Covered bytes follow the uniform coverage rule in
{{sec-checksum4}}; `cs_value` is the 32-byte hash output
in the byte order defined by {{BLAKE3-SPEC}} Section 2.4.

A checksum4 whose cs_value length does not match the
registered cs_value bytes for its cs_algorithm MUST be
rejected with NFS4ERR_INVAL.

The "Class" column in {{tbl-checksum-algorithms}} is
informational and indicates the threat model the algorithm
supports; see {{sec-security-checksum-scope}}.

##  Proof-Profile Registry {#iana-proof-profile}

This document introduces the "Flexible File Version 2
Proof-Profile Registry".  Values in this registry name
the proof_profile_id4 ({{sec-proof-profile}}) that a
metadata server presents in CHUNK_ESCROW_TAKEOVER
({{sec-CHUNK_ESCROW_TAKEOVER}}) to identify which
incarnation-lease proof format the accompanying
ceta_proof_data carries.

The registry uses a 32-bit value space.  Registration
policy is Specification Required {{RFC8126}}; the
Designated Expert reviews each request for:

-  a complete and publicly available specification of
   the proof format sufficient for independent
   interoperable implementations (envelope, signature
   algorithm, payload field set, replay-cache
   semantics, and expiry handling);

-  compatibility with the strict evaluation ordering
   specified in {{sec-proof-profile}} (session replay
   -> presenter authorization -> profile support ->
   proof verification -> epoch compare-and-advance);
   a registration whose verification cannot be
   evaluated after presenter authorization MUST be
   declined;

-  a clear statement of the trust anchor the profile
   relies on (deployment-provisioned public key set,
   Kerberos KDC, etc.), and whether the profile
   requires wire negotiation of any parameter (a
   profile that requires wire negotiation not
   defined in this document or its cited references
   MUST be declined).

Initial registrations are listed in
{{tbl-proof-profiles}}.

 | Name                                | Value | Reference |
 | ---
 | PROOF_PROFILE_UNSPECIFIED           | 0     | Reserved sentinel; see {{sec-proof-profile}} |
 | PROOF_PROFILE_HA_AUTHORITY_ED25519  | 1     | {{sec-proof-profile}} "Mandatory-to-Implement Profile" |
{: #tbl-proof-profiles title="Initial Proof-Profile Registrations"}

Additional profiles named in
{{sec-proof-profile}} (ECDSA-P256 alg -7,
RSASSA-PSS-SHA256 alg -37) MAY be added later per
the Specification Required policy above.

The value range 0xC0000000 to 0xFFFFFFFF is
reserved for Private Use per {{RFC8126}} Section
4.1; deployments MAY assign values from this range
for experimental, vendor-specific, or private
profiles without IANA registration, but such
values MUST NOT be presented on interoperability
boundaries and this specification makes no
compatibility guarantees for them.

#  XDR Description of the Flexible File Version 2 Layout Type

This document contains the External Data Representation (XDR)
{{RFC4506}} description of the flexible file v2 layout.  The XDR
description is embedded in this document in a way that makes it simple
for the reader to extract into a ready-to-compile form.  The reader can
feed this document into the shell script in {{fig-extract}} to produce
the machine-readable XDR description of the flexible file v2 layout.

~~~ shell
#!/bin/sh
grep '^ *///' $* | sed 's?^ */// ??' | sed 's?^ *///$??'
~~~
{: #fig-extract title="extract.sh"}

That is, if the above script is stored in a file called "extract.sh"
and this document is in a file called "spec.txt", then the reader can
run the script as in {{fig-extract-example}}.

~~~ shell
sh extract.sh < spec.txt > flex_files2_prot.x
~~~
{: #fig-extract-example title="Example use of extract.sh"}

The effect of the script is to remove leading blank space from each
line, plus a sentinel sequence of "///".

XDR descriptions with the sentinel sequence are embedded throughout
the document.

Note that the XDR code contained in this document depends on types
from the NFSv4.2 nfs4_prot.x file {{RFC7863}} (which itself builds on
{{RFC5662}}).  This includes both nfs types that end with a 4, such
as offset4, length4, etc., as well as more generic types such as
uint32_t and uint64_t.

While the XDR can be appended to that from {{RFC7863}}, the various
code snippets belong in their respective areas of that XDR.

--- back

# Implementation Status {#sec-implementation-status}
{:numbered="false" removeInRFC="true"}

This appendix records the implementation status of this
specification at the time of writing.  The purpose, per
{{RFC7942}}, is to help reviewers evaluate the protocol
against running code and to document which parts have
been validated end-to-end versus specified on paper.
This appendix is reviewer-aid material and is removed
from the final RFC.

##  reffs (metadata server, data server, and ec_demo client)
{:numbered="false"}

Organization:
:  Independent / open source.

License:
:  AGPL-3.0-or-later.

Source:
:  <https://github.com/loghyr/reffs>.

Implementation:
:  `reffs` is an NFSv4.2 server written in C that acts as both a
   metadata server and a data server in a flexible file v2 layout
   deployment.  A separate binary implements the proxy server role
   defined in the proxy server draft.  `ec_demo` is a client-side
   library with a demonstration driver that
   exercises the flexible file v2 layout data path over NFSv4.2.

Coverage:

- CHUNK_WRITE, CHUNK_READ, CHUNK_FINALIZE, and CHUNK_COMMIT (the
  happy-path data-plane operations) are implemented end-to-end
  and have been exercised against multiple encoding families.

- CHUNK_WRITE_REPAIR and CHUNK_REPAIRED (client-driven single-shard
  reconstruction with server-side layout-flag clearing)
  are implemented end-to-end and have been exercised across four
  file sizes, two encoding families, and one- and two-shard-loss
  patterns; end-to-end integrity verification passes on
  substantially all measured cells.

- The chunk_guard4 CAS primitive, including the conflict-detection
  and deterministic-tiebreaker rules in {{sec-chunk_guard4}}, is
  implemented on both the client and the data server.

- Per-chunk checksum integrity checking (see
  {{sec-security-checksum-scope}}) is implemented end-to-end.

- Per-inode persistent storage of chunk state (PENDING /
  FINALIZED / COMMITTED) is implemented using write-temp /
  fdatasync / rename for crash safety.

- Encoders for FFV2_ENCODING_MIRRORED, FFV2_ENCODING_PASSTHROUGH,
  FFV2_ENCODING_XOR_PARITY, FFV2_ENCODING_LINUX_MD_RAID,
  FFV2_ENCODING_RS_VANDERMONDE, FFV2_ENCODING_MOJETTE_SYSTEMATIC,
  and FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC are all implemented
  and cross-verified against the wire-compatibility relationships
  described in the per-encoding sections of this document.

- The tight coupling control protocol (TRUST_STATEID,
  REVOKE_STATEID, BULK_REVOKE_STATEID) is specified but not
  yet implemented.  Data servers currently advertise
  `ffv2dv_coupling = FFV2_COUPLING_SYNTHETIC_UIDS`, and
  synthetic
  AUTH_SYS credentials with fencing are used for access
  control.

- The proxy server mediated repair callback CB_PROXY_REPAIR is
  specified but not yet implemented.  Single-shard repair is
  currently client-driven via `ec_demo`.

Level of maturity:
:  Research-quality prototype.  The implementation demonstrates
   the protocol and has produced the benchmark data summarised
   below.  It is not production-ready.

Contact:
:  loghyr@gmail.com.

Last update:
:  August 2026.

##  Linux kernel flexible file v2 client
{:numbered="false"}

Organization:
:  Independent / open source.  Out-of-tree kernel module built
   against a mainline Linux release candidate.

License:
:  GPL-2.0.

Source:
:  Topic branch tracked against a mainline Linux release
   candidate; contact the author for the current tree pointer.

Implementation:
:  A native pNFS layout driver at `fs/nfs/flexfilesv2/`
   implementing the flexible file v2 layout for the Linux
   NFS client.  Layout registration, XDR decode of
   `ffv2_layout4`, device-info discovery, striped and mirrored
   read and write, and the CHUNK operation wire path are implemented as
   a peer layout driver alongside the existing flexible file v1
   driver.

Coverage:

- CHUNK_WRITE, CHUNK_READ, CHUNK_FINALIZE, and CHUNK_COMMIT are
  implemented end-to-end and wire-verified against the `reffs`
  metadata server + data server on a 64-bit ARM Linux host at
  the 7.2-rc series.

- Per-chunk checksum integrity, chunk_guard4 CAS,
  writeback-chain sequencing (CHUNK_WRITE -> CHUNK_FINALIZE ->
  CHUNK_COMMIT), and DENSE per-shard offset canonicalization
  are implemented.

- Encoders for FFV2_ENCODING_MIRRORED, FFV2_ENCODING_XOR_PARITY,
  FFV2_ENCODING_LINUX_MD_RAID, and FFV2_ENCODING_RS_VANDERMONDE
  are present.  FFV2_ENCODING_MOJETTE_SYSTEMATIC is scaffolded
  (returns -EOPNOTSUPP; native kernel implementation deferred).

- NFSv3 and NFSv4.2 data-server dispatch are both implemented.

- NFS4ERR_DELAY retry-with-backoff for concurrent writer
  contention on CHUNK_WRITE is not yet implemented; multi-writer
  workloads fall back to routing writes through the metadata
  server.

- Client-side single-shard repair write-back is not yet
  implemented in the kernel client.  Reconstruction is
  available via `ec_demo` against the same metadata server.

Level of maturity:
:  Developer preview.  Wire-verified on the CHUNK operation happy path
   against the `reffs` server.

Contact:
:  loghyr@gmail.com.

Last update:
:  August 2026.

##  Interoperability and Benchmarks
{:numbered="false"}

Two independent implementations of the client role now exist
(the `ec_demo` userspace library and the Linux kernel layout
driver above), and wire-compatibility between them on the
CHUNK operation data path has been demonstrated against the `reffs`
metadata server.  In addition, the Mojette encoders in this
document have been cross-verified against an independent
Mojette implementation with byte-identical output on the
FFV2_ENCODING_MOJETTE_SYSTEMATIC and
FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC surfaces.

The benchmark suite is now organized to distinguish two costs
that were previously conflated in a single-host Docker
measurement:

1. **Algorithm cost** -- the CPU + memory-bandwidth cost of
   encoding and decoding, measured against pre-allocated RAM
   buffers with no I/O and no network.  This is the encoder
   ceiling on a given host.
2. **Transmit cost** -- the end-to-end cost of a write or read
   on a real NFSv4.2 mount across three hosts on a LAN,
   including RPC round-trips, fsync commits, and network
   serialization.

The two-axis measurement makes explicit what the previous
single-host measurement obscured: on a real network, encoder
algorithm cost is a small fraction of end-to-end transmit
cost at typical operating points.

### Algorithm cost
{:numbered="false"}

Algorithm cost has been measured at k=4, m=2, 64 KiB shards
across the encoders defined in this document.  Reference hosts
spanned four CPU classes: Apple silicon (aarch64, NEON), Intel
x86_64 (SSE+AVX2), AMD Zen 2 mobile (SSE+AVX2), and ten uniform
AMD Zen 3 virtual machines (variance across the fleet under 5%
on all encoders).

Across these encoders and the four host classes, algorithm-cost
spread on the same host reaches approximately two orders of
magnitude at k=4, m=2 (the fastest SIMD-vectorised encoders
approach the memory-bandwidth ceiling in the tens of GB/s; the
slowest scalar encoders are compute-bound in the low hundreds
of MB/s).

Two hand-tuning passes on the Reed-Solomon Vandermonde encoder
in this document, performed without any change to the wire
format or test vectors, compounded to roughly 17x on aarch64
NEON and roughly 39x on x86_64 SSSE3 -- a precomputed field-multiplication
table pass followed by a SIMD byte-shuffle field
arithmetic pass (`vqtbl1q_u8` / `pshufb`).  A similar
implementation-only optimization pass on the Mojette encoder
wrapper yielded roughly 4.85x on x86_64 AVX2, again with
byte-identical output.

The generalization is that a naive per-encoder microbenchmark
cell measures implementation quality on that host, not the
encoding algorithm.  Wide reported spreads across encoders in
the literature reflect this in large part.

### Wire compatibility across encoders
{:numbered="false"}

Cross-encoder byte-identity holds among the GF(2^8) encoders
defined in this document at low parity counts, verified by
encoding on one implementation and decoding on another
byte-for-byte:

- At m = 1: FFV2_ENCODING_XOR_PARITY, the P row of
  FFV2_ENCODING_LINUX_MD_RAID, and the m=1 parity row of
  FFV2_ENCODING_RS_VANDERMONDE all emit byte-identical output
  for the same (k, data) input.
- At m = 2: FFV2_ENCODING_LINUX_MD_RAID and
  FFV2_ENCODING_RS_VANDERMONDE emit byte-identical output for
  the same (k, data) input, provided RS_VANDERMONDE uses the
  hand-crafted P+Q parity rows this document defines (see
  {{sec-encoding-linux-md-raid}}).
- At m >= 3: the encoders diverge; RS_VANDERMONDE reverts to
  normalized-Vandermonde bottom rows and no cross-encoder
  byte-identity holds.

The practical consequence is that a receiver that supports any
one of the m <= 2 members consumes bytes emitted by any of the
others without re-encoding.

### Transmit cost -- three-host real-network sweep
{:numbered="false"}

A three-host LAN measurement distributes the roles: one client
host (kernel NFSv4.2 mount), one proxy server host, and one
host running both the metadata server and the data servers.
Four wire-path variants are distinguished:

| Variant | Client wire        | Encoder location    | Path hops |
|---------|--------------------|---------------------|-----------|
| a       | FFv1 -> 1 DS       | none (baseline)     | 1         |
| b       | FFv1 striped       | none (fan-out only) | 1         |
| c       | FFv2 -> DSes       | client              | 1         |
| d       | FFv2 -> PS -> DSes | proxy server        | 2         |

A 180-cell sweep across five encoders x four variants x three
file sizes x three iterations verified end-to-end data
integrity in every cell.

Median write throughput at 1 MiB was:

- Variant a (FFv1, single data server): approximately
  3.2 to 5.1 MB/s across encoders.
- Variant b (FFv1, striped): approximately
  9.3 to 13.0 MB/s across encoders.
- Variant c (FFv2, client-direct): approximately
  10.0 to 13.5 MB/s across encoders.
- Variant d (FFv2, via proxy server): approximately
  1.1 to 2.2 MB/s across encoders.

The key finding: an approximately three-order-of-magnitude
algorithm-cost spread across encoders **collapses to
approximately 1.15x wire spread** at the client-direct FFv2
variant (variant c) at 1 MiB.  End-to-end throughput on this
topology is dominated by RPC round-trips, fsync commits, and
network serialization; encoder algorithm cost is a rounding-error
contributor at these operating points.

The approximately seven-fold variant d penalty (1.1-2.2 MB/s
vs 10.0-13.5 MB/s) is the extra client to proxy server hop,
not the encoder.

Decomposing a 1 MiB write on this topology into cost
components:

| Cost item                                        | ms/MiB     |
|--------------------------------------------------|-----------:|
| Fastest SIMD encode (algorithm only)             | 0.05       |
| Reed-Solomon Vandermonde SSSE3 encode            | 1.7        |
| Reed-Solomon Vandermonde scalar encode (pre-opt) | 66         |
| Variant a: FFv1 to 1 DS (no EC, baseline)        | 215        |
| Variant b: FFv1 striped (no EC, fan-out)         | 95         |
| Variant c: FFv2 direct to DSes (client EC)       | 92         |
| Variant d: FFv2 via PS (PS EC)                   | 610-910    |

The variant c wire floor of approximately 92 ms/MiB is where
end-to-end throughput lives; encoder algorithm cost accounts
for well under 2 ms of that budget for every SIMD-tuned
implementation measured.

### Cost of fault tolerance -- single-shard repair
{:numbered="false"}

Client-driven single-shard reconstruction, using the wire-level
`OP_CHUNK_WRITE_REPAIR` + `OP_CHUNK_REPAIRED` operations
this document defines, was benchmarked on a colocated topology
across the following axes:

- File sizes: 4 KB, 64 KB, 1 MB, 16 MB
- Encoding families: Reed-Solomon Vandermonde and Mojette
  systematic (both at k=4, m=2)
- Loss patterns: one shard missing, two shards missing
- Five iterations per cell (80 cells total)

Substantially all cells passed end-to-end integrity
verification.  Median repair time at 1 MB, RS 4+2, one shard
lost was approximately 80 ms; at 16 MB, approximately 990 ms.
Mojette systematic at the same operating points was
approximately 72 ms and 900 ms respectively.  Repair cost
decomposes as `degraded-read cost + write-back cost per lost
shard` (not (k+m) writes -- CHUNK_WRITE_REPAIR is targeted).

At file sizes >= 64 KB, repair cost is within one order of
magnitude of a healthy write of the same size -- not the
catastrophic overhead the phrase "erasure coding repair" might
imply.  Healthy no-loss reads on any systematic encoding pay
zero decode cost (the shard is copied through unchanged).

### Encoder-family trade-offs
{:numbered="false"}

The wire-spread convergence does not mean encoder choice is
irrelevant.  It means encoder choice is decided by properties
other than raw algorithm speed at typical operating points:

Fault tolerance and geometry:

: FFV2_ENCODING_RS_VANDERMONDE and the Mojette family support
  arbitrary (k, m); FFV2_ENCODING_XOR_PARITY is m = 1 only;
  FFV2_ENCODING_LINUX_MD_RAID is m = 2 only.

Interoperability:

: the m <= 2 byte-identical set described above lets a
  deployment mix implementations of different encoders at the
  same k and m without cross-encoding.

Reconstruction cost:

: systematic encodings (FFV2_ENCODING_RS_VANDERMONDE,
  FFV2_ENCODING_MOJETTE_SYSTEMATIC, FFV2_ENCODING_XOR_PARITY,
  FFV2_ENCODING_LINUX_MD_RAID) short-circuit no-loss reads at
  wire speed; FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC transforms
  every shard on every read.

Wide-geometry scaling:

: at k >= 8, m >= 4, the Mojette back-projection reconstruction
  cost scales with m (parity count) rather than k (data count),
  so its reconstruction overhead does not exhibit the O(k^3)
  growth Reed-Solomon matrix inversion incurs at wider
  geometries.

Implementation availability:

: FFV2_ENCODING_XOR_PARITY has no external dependency;
  FFV2_ENCODING_LINUX_MD_RAID's reference construction is
  present in every Linux kernel at `lib/raid6/`
  ({{LINUX-RAID6}}).  The remaining encoders in this document
  have reference implementations in the sources cited above.

A full benchmark report with per-cell tables, per-host medians,
and per-variant transmit decompositions is available alongside
the source code.

## Architectural Implication: Cost of Fault Tolerance {#sec-architectural-implication}
{:numbered="false"}

The headline question every storage audience asks of an
erasure-coding protocol is: "what does it cost when something goes
wrong?"  At the systematic-encoding operating points measured
(Mojette systematic at 4+2 and 8+2), the benchmark answer is
essentially zero.  Mojette systematic at 4+2 reconstructs a
missing data shard with read-latency overhead within run-to-run
noise of healthy operation.  Mojette systematic at 8+2 holds at
approximately +4%.

This shifts the deployment conversation away from "is erasure
coding cheap enough to enable" and toward "which encoding and
geometry minimise the compromise."  The compromise that remains is
not the cost of fault tolerance; it is the cost of write-time
encoding, which is bounded (under 60% at 1 MB, under 25% at 64 KB),
and the cost of crash-safe durability via the chunk state machine
(see {{sec-system-model-consistency}}), which is +7% to +22% on
writes and +2% to +10% on reads.

Wire-format performance objections raised earlier in the working
group's review of this work are addressed in
{{sec-rejected-alternatives}}: the per-RPC byte-shuffling cost of
the original Mojette-specific projection header has been replaced
with XDR-encoded chunk metadata (see {{sec-chunk_guard4}}), so the
remaining wire format cost is the XDR-encoded chunk header itself,
which is identical for every encoding and is part of the +7% to +22%
v2 write overhead measured above.

# Design Rationale: Rejected Alternatives {#sec-rejected-alternatives}
{:numbered="false"}

This appendix records design alternatives that were
considered and rejected during the development of this
specification.  It is reviewer-aid material in this draft
and is retained in the final RFC as design-history
context for future implementers; the alternatives below
are not part of the normative specification.

The design of flexible file v2 layout went through several iterations between
2024 and 2026 that are recorded here for the benefit of future
reviewers and implementers.  Each alternative below was considered
and rejected, with the specific concern that led to its rejection.
Understanding why these approaches were rejected may help reviewers
evaluate the current design against a fuller space of possibilities
and may guide future extensions or replacements.

##  Proprietary Projection Header Inside Opaque Payload
{:numbered="false"}

The earliest iteration placed a 16-byte Mojette-specific header at
the start of the READ/WRITE opaque payload, interpreted in the
endianness of the writer's host.  The motivation was concrete:
NFSv3 READ and WRITE arguments carry data as `opaque data<>` and
provide no XDR room for per-write structured metadata such as
encoding geometry, integrity, or write-ordering tiebreakers.  An
NFSv3 server cannot be extended; if a flexible file v2 layout deployment
wanted an NFSv3 server to participate as a data server in an
erasure-coded layout, the only place to put encoding metadata was
inside that opaque payload, prepended to the data bytes.  The data server
stored the entire opaque blob without interpreting it; the reader
peeled the 16-byte prefix off and acted on it.

This was rejected because:

-  It embedded a specific erasure encoding type (Mojette) into the
   generic replication-method framework, preventing alternate
   codings from reusing the same wire format.

-  The header bytes were not XDR-aligned, which required every
   implementation to handle endianness explicitly rather than
   relying on XDR's natural byte order.

-  Carrying integrity and identification data inside an opaque
   disrespected the XDR self-description model that the rest of
   NFSv4 relies on.  A generic NFSv3 inspector watching the wire
   could not tell those bytes apart from application data, which
   among other things made debugging, traffic analysis, and
   middlebox processing rely on out-of-band knowledge.

The endianness objection raised at IETF 120 (July 2024) was the
surface complaint; the structural objection -- that smuggling
structured fields through an opaque type bypasses XDR's
self-description -- was the deeper reason the working group
declined the approach.  Once the design accepted that data
servers in a flexible file v2 layout deployment would speak
NFSv4.2 (with new ops in this document), the constraint that
forced the smuggling disappeared: chunk metadata could be
expressed as proper XDR fields in CHUNK_WRITE / CHUNK_READ /
chunk_guard4, visible to every observer of the wire.

##  Per-Client Swap Files with metadata server MAPPING_RECALL
{:numbered="false"}

One proposal split logical and physical chunk addressing: the
metadata server maintained a mapping from logical offset to
physical location, and the client appended new chunks to a
per-client staging file on each data server before asking the
metadata server to atomically remap the file to the new chunks.
This was rejected because:

-  The MAPPING_RECALL operation required to atomically update the
   mapping would, in a multi-writer deployment, have to recall all
   outstanding read/write layouts on the file -- grinding the
   application to a halt during every remap.

-  Each client required its own staging file on every data server,
   producing N clients * M data servers staging files that had to
   be reconciled on client restart.

-  The approach was biased toward correctness at the expense of
   throughput, which inverted the expected workload mix where
   single writer cases dominate.

##  Server-Side Byte-Range Lock Manager per File
{:numbered="false"}

Another proposal relied on byte range locks obtained by clients
before writing, with the lock manager state spread across the data
servers.  This was rejected because:

-  A failed lock holder required a lock manager to arbitrate
   recovery, effectively reintroducing a centralized decision
   point for each chunk.

-  The lock recall path for HPC checkpoint workloads (many ranks
   writing disjoint regions) would have required thousands of
   locks per file, with recall storms on every phase transition.

-  The design did not specify how the lock manager itself would
   be replicated for high availability, deferring the hardest
   part of the problem.

The current design uses CHUNK_LOCK (see {{sec-CHUNK_LOCK}}) but
only on the repair path, not on the normal write path.

##  Modified Two-Touch Paxos on Each Chunk
{:numbered="false"}

A fully distributed-consensus proposal placed a lightweight
(modified two-touch) Paxos round on each chunk write, reaching
agreement among the data servers holding the mirror set.  This was
rejected because:

-  The constant-factor cost per write (two or three round trips,
   leader election overhead, majority quorum requirement) was
   unacceptable for workloads where single writer throughput
   dominates the deployment mix.

-  The approach demanded that data servers be peers in a
   consensus protocol, which is a substantially heavier
   requirement than being independent chunk stores.

-  A majority of (k+m) data servers must be reachable for any
   progress, which is a strictly stronger availability requirement
   than the k-of-(k+m) needed for erasure-coded reads.

Working-group feedback on this proposal was uniformly negative.
The current design retains the option -- nothing in this
specification prevents an implementation from running classical
consensus internally among metadata server replicas (see
{{sec-system-model-consensus}}) -- but does not require it per
write.

##  Automatic Commit of Empty Chunks
{:numbered="false"}

An earlier version included a WRITE_BLOCK_FLAGS_COMMIT_IF_EMPTY
flag (later renamed CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY) that
automatically committed a write to a previously-empty chunk
without a separate CHUNK_COMMIT round trip.  The flag is retained
in the current design but its scope was narrowed: it is
performant in the exclusive-writer case but produces blocks that
cannot be rolled back if a racing writer appears concurrently,
requiring either hole-punching or an extension of CHUNK_ROLLBACK
to work on committed blocks.  The narrow scope is documented in
the flag's definition; a broader version was rejected because it
created rollback liabilities that were disproportionate to the
single-RTT savings.

##  Global Clock or Wall-Clock-Based Generation Counter
{:numbered="false"}

An early design used a wall-clock timestamp as the cg_gen_id.
This was rejected because:

-  No global clock exists among the many clients of a
   multi-rack deployment.  Clock skew can cause a newer write
   to appear to have an earlier timestamp than an older one.

-  Timestamps at millisecond or microsecond resolution are not
   fine-grained enough to disambiguate bursty writes from the
   same client.

-  Mixing client identity bits into the low-order bits of a
   timestamp (to make it unique) reduces effective timestamp
   resolution without providing a useful total ordering.

The current design uses a per-chunk monotonic counter scoped to
the chunk on the data server, with cg_client_id as the
disambiguator across clients.  See {{sec-chunk_guard4}}.

##  Layout-Level Generation Counter
{:numbered="false"}

An alternative raised at IETF 122 (March 2025) was adding a
generation counter to the layout itself, transmitted to the
data servers alongside each I/O, so that the metadata server
could redirect writes to new data servers without issuing a
full CB_LAYOUTRECALL storm across every holder of the file.
This is a natural extension of the per-chunk cg_gen_id: where
cg_gen_id disambiguates successive writes to the same chunk, a
layout-level counter would disambiguate successive placements
of the same data.  This was rejected because:

-  The use case is already covered.  CB_CHUNK_REPAIR (see
   {{sec-CB_CHUNK_REPAIR}}) and the proxy server mechanism
   together handle mid-layout remap without requiring a
   layout-level epoch on the wire.  CB_CHUNK_REPAIR reaches the specific
   chunks that need redirection; the proxy server reaches the
   broader re-placement case; between them the full remap
   space is covered.

-  Adding a layout-level counter introduces a second,
   potentially-conflicting epoch alongside cg_gen_id.  The CAS
   semantics on the data server would have to compose the two
   generations (per-chunk and per-layout), which multiplies
   the states the data server must reason about without
   strengthening any guarantee the protocol offers today.

-  The CB_LAYOUTRECALL storm that motivated the proposal is a
   worst-case cost that the current design pays only during a
   genuine data-server retirement or full re-placement.
   Partial remaps -- the common case -- already flow through
   CB_CHUNK_REPAIR + layout refresh on LAYOUTGET without
   disturbing other holders.

If a future revision determines that layout-level generation is
needed, it can be added as a protocol extension: the on-wire
change is additive rather than a replacement, because
cg_gen_id's semantics are independent of any outer layout
epoch.

##  Declustered RAID with Dynamic Parity Mapping
{:numbered="false"}

An alternative raised at IETF 121 (November 2024) was
borrowing from declustered RAID designs: the
metadata server maintains, for every fixed-size region of each
file, a mapping from logical address to the specific data
servers that currently hold that region's data and parity
shards; writes do not update chunks in place but instead produce
a new parity stripe on a freshly allocated set of data servers,
and the mapping is atomically swapped on the metadata server
once the new stripe is durable.  The attraction is that
overwrite is replaced by remap, eliminating the write-hole
problem entirely at the cost of moving consistency into the
mapping table.  This was rejected because:

-  The mapping load scales with the file's chunk count, not with
   the file count.  A single large file with billions of chunks
   produces a billion-entry mapping that the metadata server
   must maintain with transactional semantics; the overhead is
   inverted from the usual "a few large files" regime that
   pNFS is designed for.

-  Remapping storms during rebalancing, data-server addition, or
   data-server failure require atomic updates to many mapping
   entries at once.  Providing those updates with the
   reasonable-latency bounds required by HPC checkpoint
   workloads is an open research problem, not a specifiable
   protocol.

-  The approach reintroduces the metadata-server scale bottleneck
   that client-side erasure coding is designed to avoid: every
   write traverses the mapping table, and the mapping table is
   the hot-spot under concurrent writes.

-  The mapping table becomes the single point of failure that
   the rest of the flexible file v2 layout architecture works hard to avoid;
   replicating it with strong consistency requires a consensus
   protocol on the metadata server, which the current design
   deliberately does not require (see {{sec-system-model-consensus}}).

The current design uses fixed per-file chunk placement decided
at LAYOUTGET time plus chunk_guard4 CAS for writes, which
localises consistency decisions to the chunks being written
rather than to a global mapping table.

# Working Group Concern: Encoding on Every Client {#sec-wg-concern-encoding-on-client}
{:numbered="false" removeInRFC="true"}

This appendix captures a working-group concern raised
during the review of an earlier revision of this draft:
the source of the concern, the question as the working
group asked it, the authors' understanding of what was
being asked, and how the current specification addresses
it.  This appendix is reviewer-aid material and is
removed from the final RFC.

## Source
{:numbered="false"}

Christoph Hellwig, IETF 120, NFSv4 Working Group session, during the
discussion of the original Flexible File Version 2 erasure-coding
proposal.

## The Question as Asked
{:numbered="false"}

Christoph stated that he was "very scared of the implications of
having every client be a full participant in a distributed storage
system."  He pointed out that any erasure-coding or replication
protocol that runs at the client requires every client implementation
to understand the encoding, and that encodings evolve over time as new
algorithms appear in the storage research literature.  He observed
that the same problem appears with replication ("simple two-, three-,
four-way replication"): a client power-failure event mid-write leaves
the participating data servers in inconsistent states, and the
recovery machinery (mirrored logs, write-ahead replay, partial-write
detection) is "a bit of overkill for simple replication."

David Black seconded the concern in the same session, stating that
"it's better to have the data protection algorithm be inside the
boundary of what you think the storage system is than outside."

## What We Believe Is Being Asked
{:numbered="false"}

Two coupled requirements:

1.  Encoding correctness and encoding evolution must not be a per-client
    burden.  An ecosystem in which every client must ship and update
    every supported encoding does not interoperate at scale: an
    organisation cannot upgrade its storage system's encoding without
    coordinating an upgrade across every client.

2.  The expensive recovery paths (partial writes, durable shard
    placement, mirrored logging) must not live at the client either.
    A protocol that exposes those paths to the client forces every
    client implementation to carry the failure-recovery machinery,
    which is precisely what RAID controllers and distributed storage
    systems put behind a service boundary so that hosts do not have
    to reason about it.

In short: the data-protection algorithm and its recovery story
belong inside a storage boundary, not at the client.

## How the Proxy Server Addresses This
{:numbered="false"}

The proxy server role is the storage boundary that Christoph
and David asked for.

A proxy server is a peer of the metadata server and the data servers that:

-  speaks the encoding on behalf of clients that cannot;
-  receives whole-stripe operations from an encoding-ignorant client;
-  encodes (or decodes) using whatever the layout's
    {{fig-ffv2_encoding_type4}} demands;
-  drives the CHUNK operations to the participating data servers;
-  carries the partial-write / FINALIZE / COMMIT recovery machinery
    that the encoding requires.

Three properties follow:

-  A legacy NFSv4.2 (or even NFSv3) client gets erasure-coded
    durability without speaking erasure coding.  The proxy server is where
    the encoding lives; the client does not have to be upgraded when
    the encoding is upgraded.

-  Encoding evolution is a server-side concern.  Adding a new entry
    to {{fig-ffv2_encoding_type4}} requires updating the proxy servers and data servers,
    not every client in the deployment.  This matches the operational
    pattern of every other distributed-storage protocol on the wire.

-  The recovery machinery (PENDING -> FINALIZED -> COMMITTED, the
    chunk-state machine, partial-write detection via
    {{sec-chunk_guard4}}) executes on the proxy server, not the client.  Clients
    see ordinary NFSv4.2 semantics; the proxy server is responsible for
    converting those semantics into the chunk state-machine the
    data servers implement.

An encoding-aware NFSv4.2 client is still permitted (and is the fast
path: no proxy hop, no double bandwidth on the proxy's link).  The
proxy server is the answer for clients that either cannot speak the encoding
or are too old to be upgraded.  In Christoph's framing, the proxy server is
the inside of the storage boundary; encoding-aware clients are
implementations that have been admitted into that boundary by
design.

The proxy server does carry a data-plane cost: client bytes traverse the
proxy on the way to the data servers, so the proxy's link sees roughly
twice the bandwidth of a direct client-to-data server path, and the proxy server pays
the encode/decode CPU.  This is the price of admission for clients
that do not speak the encoding; it is the same store-and-forward cost
any storage gateway pays.  It does not affect encoding-aware clients,
which talk to the data servers directly.

# Working Group Concern: Coherent Multi-data server Writes Without Recall Storms {#sec-wg-concern-recall-storms}
{:numbered="false" removeInRFC="true"}

This appendix captures a working-group concern raised
during the review of an earlier revision of this draft:
the source of the concern, the question as the working
group asked it, the authors' understanding of what was
being asked, and how the current specification addresses
it.  This appendix is reviewer-aid material and is
removed from the final RFC.

## Source
{:numbered="false"}

Christoph Hellwig, IETF 122, NFSv4 Working Group session, during
the flexible file v2 layout erasure-coding discussion.

## The Question as Asked
{:numbered="false"}

Christoph observed that performing erasure coding across a set of
data servers, where clients need a coherent view of the encoded
data while writes are in flight, is "just really complicated,
especially without recalling layouts."  He continued: "maybe we
need a more efficient network operation that doesn't recall layout
but updates layouts in a different way, and that might reduce
the overhead.  Basically any scheme would require either a fair
amount of intelligence on the data servers or some form of updating
outstanding layouts to point to a new right-out-of-place location."
He explicitly noted he was "leaning to updating the data servers
to be smarter."

The same conversation introduced the idea of a "generation counter
that gets sent over the wire to the data servers, which means the
data server now needs to look for a new location for the same
existing layout."

## What We Believe Is Being Asked
{:numbered="false"}

Two coupled requirements:

1.  The metadata server must be able to mutate where data lives -- replace a
    failing data server, redirect to a spare, rebalance, repair --
    without serialising every layout-holding client through a
    CB_LAYOUTRECALL round-trip.  A recall is global with respect
    to the layout: every client holding it must drain in-flight I/O
    and DELEGRETURN before the metadata server can mutate.  In an erasure-coded
    workload with many concurrent clients, this turns a localised
    data server hiccup into a global stall.

2.  The data servers must be smart enough to enforce per-client
    access on a finer grain than "the file is reachable from the
    network."  Anonymous-stateid I/O combined with synthetic-uid
    fencing is a coarse instrument: fencing one client's access
    to a file affects every client's access to that file.  The
    only way to selectively revoke is to teach the data server who is
    permitted, on which file, with which iomode -- which is the
    "smarter data server" Christoph was asking for.

## How TRUST_STATEID, REVOKE_STATEID, and BULK_REVOKE_STATEID Address This
{:numbered="false"}

Sections {{sec-TRUST_STATEID}}, {{sec-REVOKE_STATEID}}, and
{{sec-BULK_REVOKE_STATEID}} of this document define exactly the
"smarter data server" the working group asked for.

The mechanism:

-  At LAYOUTGET, the metadata server issues a real layout stateid and fans out
    TRUST_STATEID to each data server in the mirror set, registering
    `(stateid.other, fh, clientid, iomode, expire)` in a per-data server
    trust table.  CHUNK_WRITE and CHUNK_READ on the data server now validate
    against the trust table; an unknown, expired, or revoked
    stateid yields NFS4ERR_BAD_STATEID.

-  When the metadata server needs to mutate the layout for a particular client
    -- because that client misbehaved, because a data server the layout
    points at is being drained, because the file is being repaired
    -- it issues REVOKE_STATEID to the affected data server.  Other clients'
    trust entries on the same file are untouched.

-  When the metadata server needs to mutate at client-scope (lease expiry,
    client eviction), it issues BULK_REVOKE_STATEID, which removes
    every trust entry the named client has on the data server without
    affecting other clients.

The control-plane cost reshapes accordingly:

-  Layout mutation is no longer global.  The metadata server reroutes data to a
    spare data server, rebuilds shards from surviving copies, and revokes
    only the trust entries that pointed at the failing location.
    The other clients holding the layout are not contacted.

-  The revoked client only learns of the mutation lazily, on its
    next CHUNK_WRITE or CHUNK_READ to the affected stripe.  That
    operation returns NFS4ERR_BAD_STATEID; the client responds with
    LAYOUTERROR; the metadata server replies with a refreshed layout pointing
    at the new location; the client re-trusts and resumes.  A
    client that never touches the affected stripe never pays the
    cost at all.

-  With warm spares known to the metadata server, the entire repair can complete
    before any client notices.  The metadata server reconstructs onto a spare
    using server-to-server traffic, atomically swaps the layout slot
    in its in-memory state, and revokes only the trust entries on
    the now-evacuated data server.  Reading clients see no interruption (any
    k of the surviving shards reconstructs); writing clients pay
    one round-trip to refresh the layout when they next write the
    affected stripe.

The combination of TRUST_STATEID and a warm-spare data server pool is the
"more efficient network operation that updates layouts" Christoph
asked for.  It is not literally a layout update on the wire; it is
a primitive that makes layout updates a local event the metadata server can
resolve before the client has to pay a recall round-trip.

The chunk state machine (PENDING -> FINALIZED -> COMMITTED) and
{{sec-chunk_guard4}} address the orthogonal concern of partial-write
recovery, ensuring that even when the metadata server reroutes mid-write the
data servers can detect non-atomic stripes via per-chunk generation
checks rather than via a global wall-clock or consensus protocol.

## Combined Effect on the "Cluster Tax"
{:numbered="false"}

The proxy server addresses the encoding-distribution cost; the trust
stateid mechanism addresses the layout-mutation cost.  Together,
they confine the residual cluster overhead to:

-  the store-and-forward bandwidth on the proxy server link, paid only by
    clients that route through a proxy server rather than going data-server-direct;
    and

-  one LAYOUTERROR/LAYOUTGET round-trip per client per affected
    stripe, paid only by clients that actually try to use a stripe
    whose backing has changed.

Neither cost scales with the number of layout-holding clients,
which is the property the working group asked for.

# Acknowledgments
{:numbered="false"}

The following from Hammerspace were instrumental in driving Flexible
File Version 2 Layout Type: David Flynn, Trond Myklebust, Didier
Feron, Jean-Pierre Monchanin, Pierre Evenou, and Brian Pawlowski.

The Mojette Transform encoding type specification in
{{sec-mojette-encoding}} -- including the algebra, the bin
convention, the projection sizing, and the reconstruction
algorithms -- was contributed by Pierre Evenou, drawing on the
work of Nicolas Normand, Benoit Parrein, and the discrete
geometry research group at the University of Nantes.

Christoph Hellwig was instrumental in making sure the Flexible File
Version 2 Layout Type was applicable to more than the Mojette
Transformation.

David Black clarified at IETF 124 that the consistency goal of
flexible file v2 layout is RAID consistency across the shards of a stripe
rather than POSIX write ordering across application writes; that
framing is reflected in {{sec-motivation}} and in the Non-Goals
of {{sec-system-model-consistency}}.

The authors thank Dave Noveck, Chuck Lever, Tigran
Mkrtchyan, Rick Macklem, Christoph Hellwig, and Sorin
Faibish for their detailed review of earlier revisions of
this draft.  Their comments shaped the system model
presentation, the chunk lifecycle and guard semantics, the
trusted stateid design, and many smaller choices recorded
throughout the
document.

Chris Inacio, Brian Pawlowski, Chuck Lever, Zahed Sarker, and
Gorry Fairhurst guided this process.
