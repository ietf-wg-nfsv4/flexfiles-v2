---
title: Requirements and Rationale for the Flexible File Version 2 Layout Type
abbrev: FFv2 Requirements
docname: draft-haynes-nfsv4-flexfiles-v2-requirements-latest
category: info
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: [pNFS, flexfiles, requirements]

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping, comments]

author:
 -
    ins: T. Haynes
    name: Thomas Haynes
    organization: Hammerspace
    email: loghyr@gmail.com

normative:
  RFC5661:
  RFC7862:
  RFC8434:
  RFC8435:
  RFC8881:

informative:
  RFC1813:
  RFC5662:
  RFC7530:
  RFC7863:
  RFC7942:
  RFC8126:
  RFC8178:
  I-D.haynes-nfsv4-flexfiles-v2-trust-stateid:
  I-D.haynes-nfsv4-flexfiles-v2-layout:
  I-D.haynes-nfsv4-flexfiles-v2-chunks:
  I-D.haynes-nfsv4-flexfiles-v2-encoding-registry:
  I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde:
  I-D.haynes-nfsv4-flexfiles-v2-mojette:
  I-D.haynes-nfsv4-flexfiles-v2-proxy-server:

--- abstract

This document is the requirements and rationale companion to the
Flexible File Version 2 Layout Type family of NFSv4.2
specifications.  It carries the motivation (why the family
exists), the use cases (which deployments the family targets),
the family-wide definitions, the implementation-status
provenance, and the design rationale for choices the family
made and alternatives it rejected.  This document does not
define wire-protocol operations; those are specified in the
family's Standards-Track companion documents (trust-stateid,
layout, chunk substrate, encoding registry, and per-encoding
specifications).

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

The Flexible File Version 2 Layout Type is specified as a
family of NFSv4.2 Internet-Drafts:

- **This document**:
  requirements, use cases, definitions, and design rationale.
- {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}: the
  Metadata-Server-to-Data-Server trust-stateid control protocol
  and the three new NFSv4.2 operations (TRUST_STATEID,
  REVOKE_STATEID, BULK_REVOKE_STATEID).
- {{I-D.haynes-nfsv4-flexfiles-v2-layout}}: the layout XDR
  types, device addressing, striping, layout-return / error /
  stats, and layout recall.
- {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}: the chunk substrate,
  the correctness model, the 11 CHUNK operations, and the
  CB_CHUNK_REPAIR callback.
- {{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}: the IANA
  registry for erasure encoding types and the mixing-of-coding-
  types framework.
- {{I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde}}: the
  Reed-Solomon Vandermonde encoding specification.
- {{I-D.haynes-nfsv4-flexfiles-v2-mojette}}: the Mojette
  Transform encoding specification (systematic and
  non-systematic).
- {{I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}: the Proxy
  Server companion for encoding-ignorant clients.

The remainder of this document carries the motivation, use
cases, definitions, implementation status, and design rationale
that ground the family as a whole.

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
protocol must specify how the partial state is reconciled.
This is the load-bearing constraint that shapes the rest
of the design.

A natural-looking answer is to add a distributed-consensus
protocol between the data servers and have them agree on
which write committed.  That answer is rejected here.
Distributed consensus is operationally expensive,
introduces a synchronisation cost on every write, and
makes the data servers themselves stateful peers in a way
that closes off the simpler implementations the protocol
should accommodate.  Instead, this draft uses two
narrowly-scoped primitives that together provide just
enough on-wire reconciliation: the chunk_guard4
compare-and-swap (CAS) and the CB_CHUNK_REPAIR callback.

Every CHUNK_WRITE carries a chunk_guard4 -- a 32-bit
per-chunk generation counter and a 32-bit owning-client
short-id -- and the data server performs a per-chunk CAS
on receipt.  If two writers race for the same chunk,
exactly one wins on each data server, the loser receives
NFS4ERR_CHUNK_GUARDED for that chunk, and the chunks the
loser intended to write are left unchanged.  No data
server needs to consult its peers; the CAS is local.  The
cost on the metadata server is bounded by the 8-byte
chunk_guard4 header per chunk plus a 32-bit per-layout
client identifier ({{I-D.haynes-nfsv4-flexfiles-v2-chunks}},
{{I-D.haynes-nfsv4-flexfiles-v2-layout}}).  Independent collisions on
different chunks resolve independently; there is no
file-wide lock and no global ordering across writes.

When the per-chunk CAS detects that a stripe ended up
non-atomic -- some shards under writer A's guard, others
under writer B's, or a writer crashed mid-fan-out -- the
metadata server selects a repair client via
CB_CHUNK_REPAIR ({{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) and that client
drives the repair: it acquires CHUNK_LOCK on the affected
range, reads the surviving shards, decodes through the
erasure transform, writes the reconstructed shards via
CHUNK_WRITE_REPAIR, and clears the errored state via
CHUNK_REPAIRED.  The repair client is exactly one actor
holding a chunk-range lock; the data servers still do not
coordinate among themselves.  The repair-client selection
rule is given in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

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

The CHUNK_* operation set in this draft is the minimum
sufficient to drive the chunk state machine
({{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) plus the repair flow
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
the operation set is in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

The same design discipline shapes the rest of the
specification.  The protocol describes wire format and
server obligations; it does not pin a data-server
backend, a control protocol between metadata server and
data server, a checksum algorithm, or a file-attribute
representation on the data server.  Different
implementations resolve these choices differently and
remain conformant.  TRUST_STATEID
({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}) is one such control
protocol that this draft defines; storage devices with
their own established control protocols are conformant
without implementing it.  The tagged checksum4
({{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) lets the metadata server pick any
registered checksum algorithm per file.  The
authorization-outcome parity rule
({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}) lets data servers that do not
expose a POSIX file namespace satisfy the tight-coupling
requirements without materialising POSIX uid/gid bits.

A protocol-level consequence of placing erasure coding at
the client is that the layout must be able to describe a
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
those shards -- so that readers and repair clients never
observe a half-applied stripe.  Readers who need
cross-write ordering beyond a single stripe MUST use the
existing NFSv4 locking primitives.

#  Use Cases {#sec-use-cases}

The protocol is designed around three workload classes.  The
percentages below reflect the expected deployment mix in
installations that choose flexible file v2 layout for its combination of
integrity and performance; individual deployments may diverge.

Single writer, multiple readers:
:  Approximately 90% of expected deployments.  The common case is a
   file written by one client and subsequently read by many.
   Examples include artifacts deposited by batch jobs, container
   images, and media files.  The protocol is optimized for this
   case; see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

Multiple writers without sustained contention:
:  Approximately 9% of expected deployments.  Files with multiple
   concurrent writers where races on the same chunk are rare.
   Examples include shared-directory append-only logs and
   distributed builds.  The chunk_guard4 CAS primitive and per-chunk
   locking cover this case without penalizing the common
   single-writer path.

Multiple writers, disjoint regions:
:  Approximately 1% of expected deployments.  High-performance
   computing (HPC) checkpoint workloads, in which many ranks write
   disjoint regions of the same file in lockstep.  The protocol
   relies on block alignment to keep per-chunk contention rare
   despite overall high writer count.  Contention that does occur
   is resolved via the deterministic tiebreaker rule defined in
   {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

Scale targets include multi-thousand-client deployments (on the
order of tens of thousands of concurrent clients for HPC
checkpointing), parallel-filesystem replacements, and multi-rack
shared-storage clusters.  The repair protocol (see
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) is designed to let such deployments
tolerate data-server failures and concurrent-writer races without
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
envelope of guard, checksum, provenance, and lifecycle state.
Full definition (including chunk_guard4, chunk_owner4, the
PENDING / FINALIZED / COMMITTED chunk state machine, lock
escrow, and the CHUNK_* operations) lives in
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}}, which is authoritative.
A chunk's payload may be a block (mirrored layout) or a shard
(erasure-coded layout); the wire protocol does not distinguish.
The chunk size MAY differ from the size of the block or shard it
carries.

The three terms block / shard / chunk describe the same data at
three different layers.  The encoding transforms blocks into
shards; the wire protocol transmits shards as chunk payloads;
the data server persists chunks.  On read the path reverses.

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

client-side mirroring:

:  a feature in which the client, not the server, is responsible for
updating all of the mirrored copies of a layout segment.

data block:

:  A block (as defined above) in the client's cache for a file.

data file:

:  The data portion of the file, stored on the data server.

replication of data:

:  Data replication is making and storing multiple copies of data in
different locations.

erasure coding:

:  A data protection scheme where a stripe of data is encoded into
shards (k data shards and m parity shards) so that the original
content can be reconstructed from any sufficient subset of the
shards.  Shards are transmitted as the payload of CHUNK operations
and stored on different data servers.

client-side erasure coding:

:  A file based integrity method where copies are maintained in parallel.

compare-and-swap (CAS):

:  an atomic primitive from concurrent programming in which an
update is conditional on a prior observed value.  The FFv2
family's chunk-level CAS mechanism (chunk_guard4 +
NFS4ERR_CHUNK_GUARDED) is defined in
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

(file) data:

:  that part of the file system object that contains the data to be read
or written.  It is the contents of the object rather than the attributes
of the object.

data server (DS):

:  a pNFS server that provides the file's data when the file system
object is accessed over a file-based protocol.

escrow (lock escrow, MDS-escrow):

:  a state in which a chunk lock is held by the metadata server
on behalf of an as-yet-unselected future owner, preserving
lock-continuity across stateid revocation.  Full mechanics
(CHUNK_GUARD_CLIENT_ID_MDS, CHUNK_LOCK_FLAGS_ADOPT,
CB_CHUNK_REPAIR) are defined in
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

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

metadata server (MDS):

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

proxy server (PS):

:  a peer of the metadata server, defined in
{{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}, that admits client
I/O on the metadata server's behalf -- either as a translator for
clients that cannot speak the file's native encoding, or as a
proxy-mediated data path during whole-file move and repair
operations.  A proxy server may additionally act as a data server.

recalling a layout:

:  a graceful recall, via a callback, of a specific layout by the metadata
server to the client.  Graceful here means that the client would have
the opportunity to flush any WRITEs, etc., before returning the layout
to the metadata server.

revoking a layout:

:  an invalidation of a specific layout by the metadata server.
Once revocation occurs, the metadata server will not accept as valid any
reference to the revoked layout, and a storage device will not accept
any client access based on the layout.

resilvering:

:  the act of rebuilding a mirrored copy of a layout segment from a
known good copy of the layout segment.  Note that this can also be done
to create a new mirrored copy of the layout segment.

rsize:

:  the data transfer buffer size used for READs.

stateid:

:  a 128-bit quantity returned by a server that uniquely defines the set
of locking-related state provided by the server.  Stateids may designate
state related to open files, byte-range locks, delegations, or layouts.

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
tight-coupling variant defined by {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}, in which the
control protocol is the TRUST_STATEID family, is referred to as
trusted-stateid tight coupling (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).

trusted-stateid tight coupling:

:  the specific tight-coupling control protocol defined in
{{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}, consisting of the operations TRUST_STATEID, REVOKE_STATEID,
and BULK_REVOKE_STATEID.  Within the FFv2 family,
unqualified references to "tight coupling" or "tightly coupled" refer
to trusted-stateid tight coupling unless the context explicitly
discusses the general concept.  Other tight-coupling control
protocols (proprietary or future Standards Track) may exist but
are not covered by this family.

uid:

:  the user id, a numeric value that identifies which user owns a file.

write hole:

:  a data corruption scenario in erasure-coded systems where a
partial-stripe write leaves the stripe in a non-atomic state
(mixed old and new shards).  The FFv2 family's write-hole
handling (chunk state machine, guard rejection, repair flow)
is defined in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

wsize:

:  the data transfer buffer size used for WRITEs.


# Security Considerations

This document defines no wire-protocol operations and creates
no IANA registries.  Security considerations specific to the
family's operations live in the Standards-Track companion
documents cited in the Introduction.

# IANA Considerations

This document requests no IANA actions.

# Acknowledgments
{:numbered="false"}

The following contributors were instrumental in driving Flexible
File Version 2 Layout Type: David Flynn, Trond Myklebust, Didier
Feron, Jean-Pierre Monchanin, Pierre Evenou, and Brian Pawlowski.

Christoph Hellwig was instrumental in making sure the Flexible File
Version 2 Layout Type was applicable to more than the Mojette
Transformation.

David Black clarified at IETF 124 that the consistency goal of
flexible file v2 layout is RAID consistency across the shards of a stripe
rather than POSIX write ordering across application writes; that
framing is reflected in {{sec-motivation}} and in the System Model
non-goals of {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

The authors thank Dave Noveck, Chuck Lever, Tigran
Mkrtchyan, Rick Macklem, and Christoph Hellwig for their
detailed review of earlier revisions of the parent draft.  Their
comments shaped the system model presentation, the chunk
lifecycle and guard semantics, the trusted-stateid design,
and many smaller choices recorded throughout the family.

Chris Inacio, Brian Pawlowski, and Gorry Fairhurst guided this
process.

Mojette-specific acknowledgments are carried by
{{I-D.haynes-nfsv4-flexfiles-v2-mojette}}.

# Implementation Status {#sec-implementation-status}
{:numbered="false" removeInRFC="true"}

This appendix records the implementation status of this
specification at the time of writing.  The purpose, per
{{RFC7942}}, is to help reviewers evaluate the protocol
against running code and to document which parts have
been validated end-to-end versus specified on paper.
This appendix is reviewer-aid material and is removed
from the final RFC.

##  reffs (metadata server and data server) and ec_demo (Client)
{:numbered="false"}

Organization:
:  Independent / open source.

License:
:  AGPL-3.0-or-later.

Source:
:  <https://github.com/loghyr/reffs>.

Implementation:
:  `reffs` is an NFSv4.2 server written in C that acts as both a
   metadata server (MDS) and a data server (DS) in a flexible file v2 layout
   deployment.  `ec_demo` is a client-side library with a
   demonstration driver that exercises the flexible file v2 layout data path
   over NFSv4.2 with all three erasure coding types defined in the family.

Coverage:

- CHUNK_WRITE, CHUNK_READ, CHUNK_FINALIZE, and CHUNK_COMMIT (the
  happy-path data-plane operations) are implemented end-to-end and
  have been exercised against the three encoding families (Reed-Solomon
  Vandermonde, Mojette systematic, Mojette non-systematic).

- The chunk_guard4 CAS primitive, including the conflict-detection
  and deterministic-tiebreaker rules in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}, is
  implemented on both the client and the data server.

- Per-chunk checksum integrity checking (see
  {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) is implemented end-to-end.

- Per-inode persistent storage of chunk state (PENDING / FINALIZED
  / COMMITTED) is implemented using write-temp / fdatasync / rename
  for crash safety.

- The repair data path (CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT,
  CHUNK_WRITE_REPAIR, CHUNK_REPAIRED, CHUNK_ROLLBACK, and
  CB_CHUNK_REPAIR) is **specified but not yet implemented** in the
  prototype.  The corresponding operations currently return
  NFS4ERR_NOTSUPP.  A fault-injection test harness is in place to
  drive the repair path once it is implemented.

- The tight-coupling control protocol (TRUST_STATEID,
  REVOKE_STATEID, BULK_REVOKE_STATEID) is **specified but not yet
  implemented**.  Data servers advertise loose coupling via
  `ffdv_tightly_coupled = false`, and synthetic AUTH_SYS
  credentials with fencing are used for access control.

Level of maturity:
:  Research-quality prototype.  The implementation demonstrates the
   protocol and has produced the benchmark data summarised below.
   It is not production-ready; in particular, it does not yet
   implement the repair path required to tolerate concurrent-writer
   races or multi-data server failure reconstruction.

Contact:
:  loghyr@gmail.com.

Last update:
:  April 2026.

##  Interoperability and Benchmarks
{:numbered="false"}

The reffs + ec_demo implementation has been benchmarked against
itself (no second flexible file v2 layout implementation is known to the
authors at the time of writing).  The benchmark suite exercises
four I/O strategies -- plain mirroring, pure striping, Reed-Solomon
Vandermonde, Mojette systematic, and Mojette non-systematic -- at
five file sizes (4 KB, 16 KB, 64 KB, 256 KB, and 1 MB), at two
parity geometries (4+2 and 8+2), and on two platforms (an Apple M4
host running macOS with a Rocky Linux 8.10 Docker container, and a
Fedora 43 native Linux host on aarch64).  Each data point is the
mean of five measured runs.  Data servers run as Docker containers
on a single-host bridge network, so absolute latency numbers
reflect encoding and RPC fan-out cost with near-zero network
latency; real deployments will see higher absolute values but
similar overhead ratios.

Selected findings:

Erasure-coded write overhead is modest at small and mid sizes:
:  At 4 KB to 64 KB payloads, all three encodings add 14% to 21%
   write latency relative to plain mirroring.  Above 64 KB the
   encoding cost begins to dominate; at 1 MB Reed-Solomon and Mojette
   systematic reach approximately +54%, Mojette non-systematic
   approximately +62%.

The dominant write cost is encoding, not fan-out:
:  A pure-striping variant (6 data shards, no parity) isolates the two
   costs.  At 1 MB, plain mirroring writes in 64 ms, striping in
   71 ms (+11%), Reed-Solomon in 103 ms (+60%).  Of the 39 ms
   Reed-Solomon penalty, only 7 ms comes from parallel fan-out; the
   remaining 32 ms is encoding plus two additional parity RPCs.

Reconstruction of a missing data shard is essentially free for systematic encodings at 4+2:
:  Reed-Solomon and Mojette systematic
   add 1% to 6% to read latency in degraded-1 mode (one data shard
   missing, reconstructed from the remaining five).  A client that
   discovers a failed data server at read time can reconstruct transparently
   with no user-visible latency impact.

At 8+2, systematic-encoding reconstruction diverges:
:  Mojette
   systematic reconstruction overhead stays at approximately +4% at
   1 MB, while Reed-Solomon grows to approximately +54% due to the
   O(k^2) cost of inverting a k x k matrix in GF(2^8).  Mojette
   systematic's back-projection algorithm scales with m (parity
   count) rather than k (data count), so its reconstruction
   overhead does not exhibit the same growth at wider geometries.

Mojette non-systematic applies a full inverse transform on every read:
:  Regardless of whether any shard is missing.  At
   1 MB this produces approximately 4x read overhead at 4+2 and
   approximately 7x at 8+2.  The read cost is independent of
   failure count, which is the algorithmic trade-off of the
   non-systematic form.

Results are platform-independent:
:  The largest absolute
   latency delta between macOS M4 and Fedora 43 at 1 MB is 20 ms
   on writes.  Encoding ordering, overhead percentages, and
   qualitative scaling behavior are reproducible across operating
   systems and Docker implementations.

The benchmarks confirm that the protocol's central design claims
hold in practice: client-side erasure coding is affordable at
typical payload sizes; systematic encodings reconstruct missing
shards cheaply; and the scaling properties of the three encoding
families follow directly from their published algorithmic
complexities.

The benchmarks quantify the algorithmic trade-offs each encoding
family makes: Mojette non-systematic's constant decode cost comes
at a higher baseline read cost, and Reed-Solomon's matrix-
inversion reconstruction grows as O(k^2) at wider geometries.
The choice of default encoding and geometry in a given deployment
follows from these properties applied to the workload's read /
write mix, fault-tolerance target, and acceptable encoding cost.

A full benchmark report with per-size tables, figures, and the
platform comparison is available alongside the source code.

## Architectural Implication: Cost of Fault Tolerance {#sec-architectural-implication}
{:numbered="false"}

The headline question every storage audience asks of an
erasure-coding protocol is: "what does it cost when something goes
wrong?"  At the systematic-encoding operating points measured
(Mojette systematic at 4+2 and 8+2), the benchmark answer is
**essentially zero**.  Mojette systematic at 4+2 reconstructs a
missing data shard with read-latency overhead within run-to-run
noise of healthy operation.  Mojette systematic at 8+2 holds at
approximately +4%.

This shifts the deployment conversation away from "is erasure
coding cheap enough to enable" and toward "which encoding and
geometry minimise the compromise."  The compromise that remains is
not the cost of fault tolerance; it is the cost of write-time
encoding, which is bounded (under 60% at 1 MB, under 25% at 64 KB),
and the cost of crash-safe durability via the chunk state machine
(see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}), which is +7% to +22% on
writes and +2% to +10% on reads.

Wire-format performance objections raised earlier in the working
group's review of this work are addressed in
{{sec-rejected-alternatives}}: the per-RPC byte-shuffling cost of
the original Mojette-specific projection header has been replaced
with XDR-encoded chunk metadata (see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}), so the
remaining wire-format cost is the XDR-encoded chunk header itself,
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

-  It embedded a specific erasure coding type (Mojette) into the
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
NFSv4.2 (with new ops in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}} and {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), the constraint that
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
   single-writer cases dominate.

##  Server-Side Byte-Range Lock Manager per File
{:numbered="false"}

Another proposal relied on byte-range locks obtained by clients
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

The current design uses CHUNK_LOCK (see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) but
only on the repair path, not on the normal write path.

##  Modified Two-Touch Paxos on Each Chunk
{:numbered="false"}

A fully distributed-consensus proposal placed a lightweight
(modified two-touch) Paxos round on each chunk write, reaching
agreement among the data servers holding the mirror set.  This was
rejected because:

-  The constant-factor cost per write (two or three round trips,
   leader election overhead, majority quorum requirement) was
   unacceptable for workloads where single-writer throughput
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
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) -- but does not require it per
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
disambiguator across clients.  See {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.

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
   {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) and the Proxy Server
   mechanism (see {{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}) together
   handle mid-layout remap without requiring a layout-level
   epoch on the wire.  CB_CHUNK_REPAIR reaches the specific
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
surface is additive rather than a replacement, because
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
   deliberately does not require (see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}).

The current design uses fixed per-file chunk placement decided
at LAYOUTGET time plus chunk_guard4 CAS for writes, which
localises consistency decisions to the chunks being written
rather than to a global mapping table.



--- back
