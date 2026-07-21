---
title: Chunk Substrate and CHUNK Operations for the Flexible File Version 2 Layout Type
abbrev: FFv2 Chunks
docname: draft-haynes-nfsv4-flexfiles-v2-chunks-latest
category: std
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: [pNFS, flexfiles, erasure coding, chunks]

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping, comments]

author:
 -
    ins: T. Haynes
    name: Thomas Haynes
    organization: Hammerspace
    email: loghyr@gmail.com

normative:
  RFC4121:
  RFC4506:
  RFC5531:
  RFC5661:
  RFC5662:
  RFC7530:
  RFC7861:
  RFC7862:
  RFC8178:
  RFC8881:
  RFC9289:
  RFC1813:
  RFC7863:
  RFC8126:
  RFC8434:
  RFC8435:
  I-D.haynes-nfsv4-flexfiles-v2-requirements:
  I-D.haynes-nfsv4-flexfiles-v2-layout:
  I-D.haynes-nfsv4-flexfiles-v2-encoding-registry:
  I-D.haynes-nfsv4-flexfiles-v2-trust-stateid:

informative:
  I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde:
  I-D.haynes-nfsv4-flexfiles-v2-mojette:
  RFC1950:
  RFC2083:
  RFC3720:
  RFC4960:
  RFC5905:
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

--- abstract

This document specifies the chunk substrate for the Flexible
File Version 2 Layout Type: the per-block state machine
(PENDING / FINALIZED / COMMITTED) that underpins client-driven
erasure coding, the guards and checksums that carry chunk
identity across Data Servers, the correctness model that
grounds the wire operations in a formal specification, and the
11 CHUNK operations plus the CB_CHUNK_REPAIR callback that the
Metadata Server, Data Servers, and encoding-capable clients use
to manipulate chunk state.  This document also establishes the
Flexible File Version 2 Layout Type Checksum Algorithm
Registry.

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
encoding-method-agnostic protocol surface for pNFS layouts that
support client-driven erasure coding.  The
{{I-D.haynes-nfsv4-flexfiles-v2-layout}} document specifies the
layout XDR and control-plane operations.  This document
specifies the chunk substrate on which the layout operates:

- The per-(inode, block-offset) chunk state machine (PENDING,
  FINALIZED, COMMITTED) that provides defined crash semantics
  and the "never a mixed stripe" property.
- The chunk_guard4 and chunk_owner4 identifiers that carry
  write-transaction identity across Data Servers.
- The checksum4 mechanism for per-block integrity, with a
  registry of algorithms established in this document.
- The formal correctness model (System Model) that grounds
  the wire operations in per-chunk linearizability on
  COMMITTED state with bounded repair termination.
- The 11 CHUNK_* operations (78-88) that encoding-capable
  clients invoke on Data Servers to manipulate chunk state.
- The CB_CHUNK_REPAIR callback that the Metadata Server sends
  to clients to initiate distributed repair.

The trust-stateid control-plane operations (TRUST_STATEID,
REVOKE_STATEID, BULK_REVOKE_STATEID) and their security
considerations live in a separate document.

# Requirements Language

{::boilerplate bcp14-tagged}

# Definitions

The following terms are used with meanings defined in
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}:

- data server (DS), metadata server (MDS)
- encoding, stripe, shard, mirror, layout
- k (number of data shards), m (number of parity shards)
- `ffv2_layout4`, `ffv2_mirror4`, `ffv2_coding_type4` -- the
  layout XDR types defined in {{I-D.haynes-nfsv4-flexfiles-v2-layout}}

Local terms defined in this document:

Chunk:
:  The unit of client-driven erasure-coded write and read.  A
   chunk is per-(inode, block-offset) on the DS, distinct from
   the file-system-level block.

Chunk state machine:
:  The three-state life cycle of a chunk (PENDING, FINALIZED,
   COMMITTED) that governs when writers may modify a chunk and
   when readers may observe it.

PENDING:
:  Chunk state indicating an in-progress write; not visible to
   readers.

FINALIZED:
:  Chunk state indicating the write has stopped mutating but
   is not yet committed.

COMMITTED:
:  Chunk state indicating the write is durable and visible to
   readers.

chunk_guard4:
:  A 32-bit-plus-payload identifier scoped to a write
   transaction, used to detect concurrent writers on the same
   chunk range.

chunk_owner4:
:  Identifier for the client owning a chunk lock.

checksum4:
:  Per-block integrity value; algorithm is registered in the
   Flexible File Version 2 Layout Type Checksum Algorithm
   Registry established by this document.

# Erasure Coding

Erasure coding takes a data block and transforms it to a payload
to send to the data servers (see {{fig-encoding-data-block}}).  It
generates a metadata header and transformed block per data server.
The header is metadata information for the transformed block.  From
now on, the metadata is simply referred to as the header and the
transformed block as the chunk.  The payload of a data block is the
set of generated headers and chunks for that data block.

The guard is an unique identifier generated by the client to describe
the current write transaction (see {{sec-chunk_guard4}}).  The
intent is to have a unique and non-opaque value for comparison.
The payload_id describes the position within the payload.  Finally,
the checksum carries a 32-bit CRC computed over the header and the
chunk.  Because the checksum field is itself part of the header, the
computation treats the bytes of that field as zero so that the
result is independent of the field's wire value; the writer then
stores the computed CRC into the checksum field for transmission.
To validate on the read path, the receiver saves the received
checksum, treats those bytes as zero, recomputes the CRC over the
header and chunk, and compares against the saved value.  By
combining the two parts of the payload in the CRC, integrity is
ensured for both parts.

While the data block might have a length of 4kB, that does not
necessarily mean that the length of the chunk is 4kB.  That length
is determined by the erasure coding type algorithm.  For example,
Reed Solomon might have 4kB chunks with the data integrity being
compromised by parity chunks.  Another example would be the Mojette
Transformation, which might have 1kB chunk lengths.

The payload contains redundancy which will allow the erasure
coding type algorithm to repair chunks in the payload as it is
transformed back to a data block (see {{fig-decoding-db}}).

The protocol provides two levels of payload integrity, consumed at
different points in the read path:

Atomicity:
:  A payload is **atomic** when all of the chunks that belong
   to it carry the same chunk_guard4 value (see
   {{sec-chunk_guard4}}).  Atomicity alone does NOT imply the
   bytes are free of corruption; it means only that every chunk in
   the payload came from one write transaction.  A reader detects
   a non-atomic payload (a torn read across writes) when it
   assembles a payload and finds differing chunk_guard4 values
   across chunks.

Integrity:
:  A payload has **integrity** when it is atomic AND every
   contained chunk passes its checksum check.  Integrity is the
   precondition for returning the payload's data block to the
   application.

The separation matters because the two checks detect different
failure modes.  Atomicity detects protocol-level failures (racing
writers, partial writes, rollback windows); the checksum detects
byte-level corruption (network errors, media errors, software bugs
in the erasure transform).  Neither subsumes the other.

The two-level integrity model also reflects a deeper property of
distributed writes: **last-writer-wins does not apply to a payload
spread across independent data servers.**  The ordering of writes
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

## Encoding a Data Block

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
   +---+------------+     +---+------------+     +--+-------------+
   | HEADER         | ... | HEADER         | ... | HEADER         |
   +----------------+     +----------------+     +----------------+
   | guard:         | ... | guard:         | ... | guard:         |
   |   gen_id   : 3 | ... |   gen_id   : 3 | ... |   gen_id   : 3 |
   |   client_id: 6 | ... |   client_id: 6 | ... |   client_id: 6 |
   | payload_id : 0 | ... | payload_id : M | ... | payload_id : 5 |
   | checksum   :      | ... | checksum   :      | ... | checksum   :      |
   +----------------+     +----------------+     +----------------+
   | CHUNK          | ... | CHUNK          | ... | CHUNK          |
   +----------------+     +----------------+     +----------------+
   | data: ....     | ... | data: ....     | ... | data: ....     |
   +----------------+     +----------------+     +----------------+
     Data Server 1          Data Server N          Data Server 6
~~~
{: #fig-encoding-data-block title="Encoding a Data Block" }

Each data block of the file resident in the client's cache of the
file will be encoded into N different payloads to be sent to the
data servers as shown in {{fig-encoding-data-block}}.  As CHUNK_WRITE
(see {{sec-CHUNK_WRITE}}) can encode multiple write_chunk4 into a
single transaction, a more accurate description of a CHUNK_WRITE
is in {{fig-example-chunk-write-args}}.

~~~
  +------------------------------------+
  | CHUNK_WRITEargs                    |
  +------------------------------------+
  | cwa_stateid: 0                     |
  | cwa_offset: 1                      |
  | cwa_stable: FILE_SYNC4             |
  | cwa_payload_id: 0                  |
  | cwa_owner:                         |
  |            co_guard:               |
  |                cg_gen_id   : 3     |
  |                cg_client_id: 6     |
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
in the file.  As each block shares the cwa_owner, it is only presented
once.  I.e., the data server will be able to construct the header
for the i'th chunk from the cwa_chunks from the cwa_payload_id, the
cwa_owner, and the i'th checksum from the cwa_checksums.  The cwa_chunks
are sent together as a byte stream to increase performance.

Assuming that there were no issues, {{fig-example-chunk-write-res}}
illustrates the results.  The payload sequence id is implicit in
the CHUNK_WRITEargs.

~~~
  +-------------------------------+
  | CHUNK_WRITEresok              |
  +-------------------------------+
  | cwr_count: 3                  |
  | cwr_committed: FILE_SYNC4     |
  | cwr_writeverf: 0xf1234abc     |
  | cwr_owners[0]:                |
  |        co_chunk_id: 1         |
  |        co_guard:              |
  |            cg_gen_id   : 3    |
  |            cg_client_id: 6    |
  | cwr_owners[1]:                |
  |        co_chunk_id: 2         |
  |        co_guard:              |
  |            cg_gen_id   : 3    |
  |            cg_client_id: 6    |
  | cwr_owners[2]:                |
  |        co_chunk_id: 3         |
  |        co_guard:              |
  |            cg_gen_id   : 3    |
  |            cg_client_id: 6    |
  +-------------------------------+
~~~
{: #fig-example-chunk-write-res title="Example of CHUNK_WRITE_res" }

### Worked Example: Calculating the CRC32

The examples in this section and in
{{sec-checking-crc32}} illustrate checksum computation
and verification using CHECKSUM_ALG_CRC32 as the worked
algorithm.  Other registered checksum algorithms
(CHECKSUM_ALG_CRC32C, CHECKSUM_ALG_FLETCHER4,
CHECKSUM_ALG_SHA256, CHECKSUM_ALG_SHA512,
CHECKSUM_ALG_BLAKE3; see {{sec-checksum4}}) follow the same
pattern -- the algorithm names a function over the header
and chunk bytes, the writer fills cs_value with the
computed output, and the reader recomputes and compares.
Only the algorithm and the cs_value length differ.

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

~~~
  +------------------------------------+
  | CHUNK_WRITEargs                    |
  +------------------------------------+
  | cwa_stateid: 0                     |
  | cwa_offset: 1                      |
  | cwa_stable: FILE_SYNC4             |
  | cwa_payload_id: 0                  |
  | cwa_owner:                         |
  |            co_guard:               |
  |                cg_gen_id   : 7     |
  |                cg_client_id: 6     |
  | cwa_chunk_size  :  1048            |
  | cwa_checksums:                     |
  |         [0]:  0x21de8              |
  | cwa_chunks  :  ......              |
  +------------------------------------+
~~~
{: #fig-calc-crc-after title="CRC32 After Calculation" }

## Decoding a Data Block

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
erasure coding type.

### Worked Example: Checking the CRC32 {#sec-checking-crc32}

~~~
  +------------------------------------+
  | CHUNK_READresok                    |
  +------------------------------------+
  | crr_eof: false                     |
  | crr_chunks[0]:                     |
  |        cr_checksum: 0x21de8        |
  |        cr_owner:                   |
  |            co_guard:               |
  |                cg_gen_id   : 7     |
  |                cg_client_id: 6     |
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

## Write Modes

There are two basic writing modes for erasure coding and they depend
on the metadata server using FFV2_FLAGS_ONLY_ONE_WRITER in the
ffv2l_flags in the ffv2_layout4 (see {{I-D.haynes-nfsv4-flexfiles-v2-layout}}) to inform
the client whether it is the only writer to the file or not.  If
it is the only writer, then CHUNK_WRITE with the cwa_guard not set
can be used to write chunks.  In this scenario, there is no write
contention, but write holes can occur as the client overwrites old
data.  Thus the client does not need guarded writes, but it does
need the ability to rollback writes.  If it is not the only writer,
then CHUNK_WRITE with the cwa_guard set MUST be used to write chunks.
In this scenario, the write holes can also be caused by multiple
clients writing to the same chunk.  Thus the client needs guarded
writes to prevent over writes and it does need the ability to
rollback writes.

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
No implicit chunk-write lock is acquired by CHUNK_WRITE; the
prior draft's "as if CHUNK_LOCK had been performed" language
is not part of this specification.

If the CHUNK_WRITE results in a atomic data block, then the
client will send a CHUNK_FINALIZE in a subsequent compound to inform
the data server that the chunk is finalized and can be overwritten
by another CHUNK_WRITE.

If the CHUNK_WRITE results in an non-atomic data block, or if the
data server returns NFS4ERR_CHUNK_LOCKED, the client reports the
condition to the metadata server via LAYOUTERROR with an error code
of NFS4ERR_PAYLOAD_NOT_ATOMIC.

## Selecting the Repair Client {#sec-repair-selection}

The repair topology involves three actors communicating along
distinct paths, as shown in {{fig-repair-topology}}.

~~~
     +-------------+      (1)         +-----------------+
     |  Reporting  | ---------------> |                 |
     |  client     |   LAYOUTERROR    |       MDS       |
     |  (detects   |                  |                 |
     |  error)     |                  |                 |
     +-------------+                  +--------+--------+
                                               |
                                               | (2b)
                                               | CB_CHUNK_REPAIR
                                               | (RACE or SCRUB)
                                               v
     +-------------+      (4)         +-----------------+
     |  Repair     | ---------------> |      DSes       |
     |  client     |    CHUNK_*       |  (mirror set    |
     |  (selected  |                  |  for affected   |
     |  per (2a),  |                  |  ranges)        |
     |  adopts     |                  |                 |
     |  lock (3))  |                  |                 |
     +-------------+                  +-----------------+

     (1)   Reporting client LAYOUTERRORs the metadata server.
     (2a)  Metadata server selects a repair client (may be same
           as the reporting client).
     (2b)  Metadata server escrows the chunk lock and issues
           CB_CHUNK_REPAIR to the selected repair client.
     (3)   Repair client adopts the lock and drives the repair.
     (4)   Repair client issues CHUNK_LOCK_ADOPT, CHUNK_WRITE_REPAIR,
           CHUNK_FINALIZE, CHUNK_COMMIT, and CHUNK_REPAIRED against
           the mirror set.
~~~
{: #fig-repair-topology title="Repair topology"}

The metadata server is the authority that selects which client
(or, in a tightly coupled deployment, which data server) repairs
an non-atomic payload.  This is analogous to the way the
metadata server assigns per-mirror priority via ffv2ds_efficiency
(see {{I-D.haynes-nfsv4-flexfiles-v2-layout}}): the protocol does not prescribe the
selection algorithm, and each deployment MAY tune its policy.

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
concurrent-writer races or data-server failures.  It is not a
steady-state operation and its frequency is a function of
racing-writer and data-server-failure rates in the deployment
rather than of normal client workload.  Implementations SHOULD
treat the CB_CHUNK_REPAIR handler as rare-path code and avoid
over-optimising it.  Implementations SHOULD, however, provision
enough client-side compute to handle a repair transaction
without stalling their foreground I/O, because foreground
throughput during repair is the externally observable cost of
this callback.

## Repair Protocol: Normative vs. Informative

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
:  The repair client MUST adopt the
   lock on every affected range via CHUNK_LOCK with
   CHUNK_LOCK_FLAGS_ADOPT ({{sec-CHUNK_LOCK}}) before issuing
   any CHUNK_WRITE_REPAIR, CHUNK_ROLLBACK, or CHUNK_WRITE on a
   chunk in that range.  The lock on the affected chunks is
   held continuously from the failure that triggered
   CB_CHUNK_REPAIR through the adoption; at no point is the
   range unlocked.

Clear the errored state:
:  On the reconstruction path,
   the repair client MUST issue CHUNK_REPAIRED
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

## Carrying Out the Repair

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

In both paths, the repair client SHOULD target reconstructed
shards according to the following fallback order: first, any
data server in the layout carrying FFV2_DS_FLAGS_REPAIR; then
the data server that reported the failure (the one carrying the
failing shard at the range identified by ccr_offset and ccr_count
in the CB_CHUNK_REPAIR argument); then, if both of the above are
unreachable, a data server carrying FFV2_DS_FLAGS_SPARE.  If
none of the above are available, the client MUST return
NFS4ERR_PAYLOAD_LOST on the CB_CHUNK_REPAIR response.

### Single Writer Mode

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

### Repairing Single Writer Payloads

In single writer mode, non-atomic blocks arise from a client or data
server failure during a CHUNK_WRITE / CHUNK_FINALIZE sequence.  Because
no other writer is active, the original writer is the typical choice
for repair, but the metadata server MAY designate any client according
to the rules in {{sec-repair-selection}}.  A designated client that
did not originate the writes MUST follow the rollback path of that
section if it cannot reconstruct the payload from surviving shards.

The repair sequence when the selected client is the original writer is:

1. The repair client issues CHUNK_READ to identify which blocks are in a
   failed state (PENDING with a CRC mismatch, or in the errored state
   set by a prior CHUNK_ERROR).

2. For each errored chunk, the repair client reconstructs the correct
   data using the erasure coding algorithm (RS matrix inversion or Mojette
   back-projection) from the surviving atomic chunks (treating each
   chunk's payload as a shard of the stripe).

3. The repair client issues CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}})
   to write the reconstructed data.  CHUNK_WRITE_REPAIR bypasses the guard
   check and applies different data server policies (e.g., allowing writes
   to blocks in the errored state).

4. The repair client issues CHUNK_FINALIZE and CHUNK_COMMIT to persist the
   repaired blocks.

5. The repair client issues CHUNK_REPAIRED ({{sec-CHUNK_REPAIRED}}) to
   clear the errored state and make the blocks available for normal reads.

### Transitioning from Single Writer Mode to Multiple Writer Mode {#sec-swm-to-mwm}

When a second writer requests a write layout for a file currently
covered by a single-writer layout (FFV2_FLAGS_ONLY_ONE_WRITER set),
the metadata server recalls the existing layout before granting
the new request.  The sequence is:

1. The metadata server issues CB_LAYOUTRECALL to the single-writer
   client.

2. The single-writer client drains its outstanding I/O issued
   under the single-writer assumption (CHUNK_WRITE with
   cwa_guard.cwg_check = FALSE).  Operations already underway
   complete under the layout that authorized them: CHUNK_FINALIZE
   and CHUNK_COMMIT proceed normally for blocks already written.

3. Once drained, the single-writer client issues LAYOUTRETURN.

4. The metadata server grants the new writer a layout without
   FFV2_FLAGS_ONLY_ONE_WRITER set.  When the original writer next
   issues LAYOUTGET, it also receives a layout without the flag.
   Both clients then operate in multiple writer mode
   ({{sec-multi-writer}}), supplying cwa_guard.cwg_check = TRUE
   and a chunk_guard4 on every CHUNK_WRITE.

The transition uses standard NFSv4.1 layout recall semantics
(Section 12.5.5 of {{RFC8881}}).  Drained single-writer I/O does
not need to be re-issued under multiple writer rules; it
completed under the layout that authorized it.  If the
single-writer client fails to return the layout within the
recall window, the metadata server escalates to layout
revocation (Section 12.5.5.2.1 of {{RFC8881}}); any single-writer
writes that did not complete before revocation are repaired via
the multiple-writer repair path on subsequent access.

### Multiple Writer Mode {#sec-multi-writer}

In multiple writer mode, the metadata server does not set
FFV2_FLAGS_ONLY_ONE_WRITER, indicating that concurrent writers may hold
write layouts for the file.  The client sends CHUNK_WRITE with
cwa_guard.cwg_check set to TRUE, supplying a chunk_guard4 in cwa_guard.cwg_guard
that uniquely identifies this write transaction across all data servers.

The multiple writer write sequence is:

1. The client selects a unique chunk_guard4 for this transaction.  The
   cg_client_id identifies the client (derived from the client's
   clientid4); the cg_gen_id is a per-client generation counter
   incremented for each new transaction.

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

The guard ensures that the chunks carrying the shards of an atomic
erasure-coded stripe all carry the same chunk_guard4.  A reader that
encounters chunks with different guard values knows the stripe is not
yet atomic and MUST either retry or report NFS4ERR_PAYLOAD_NOT_ATOMIC.

### Repairing Multiple Writer Payloads {#sec-repair-multi-writer}

In multiple writer mode, non-atomic chunks can arise from two sources:
a client failure leaving some chunks in PENDING state, or two clients
writing different data to the same chunk before one has committed.

The metadata server coordinates repair by designating a repair
client according to the rules in {{sec-repair-selection}}.  The
FFV2_DS_FLAGS_REPAIR flag, when present on a data server in the
layout, identifies the target data server into which reconstructed
shards should be written; it does not by itself identify the
repair client.  The repair sequence is:

1. The repair client issues CHUNK_LOCK ({{sec-CHUNK_LOCK}}) on the
   affected block range of each data server.  If any lock attempt returns
   NFS4ERR_CHUNK_LOCKED, the repair client records the existing lock
   holder's chunk_owner4 and proceeds; the lock holder's data is a
   candidate for the winning payload.

2. The repair client issues CHUNK_READ on all data servers to retrieve
   the current payload.  It examines the chunk_owner4 of each shard to
   identify which transaction (if any) produced a atomic set across
   all k data shards.

3. If a atomic set is found (all k data shards carry the same
   chunk_guard4), that payload is the winner.  The repair client issues
   CHUNK_WRITE_REPAIR to copy the winner's data to any data servers whose
   shard is non-atomic, followed by CHUNK_FINALIZE and CHUNK_COMMIT.

4. If no atomic set exists (all available payloads are partial), the
   repair client selects one transaction's payload as authoritative
   (typically the one with the most complete set of shards, or the most
   recent cg_gen_id) and proceeds as above.

5. After all data servers carry atomic, finalized, committed data, the
   repair client issues CHUNK_REPAIRED to clear the errored state and
   CHUNK_UNLOCK to release the locks acquired in step 1.

6. The repair client reports success to the metadata server via
   LAYOUTRETURN.

### Transitioning from Multiple Writer Mode to Single Writer Mode {#sec-mwm-to-swm}

The reverse transition is optional.  When the metadata server
determines that only one writer holds a write layout for a file
(for example, because other writers' layouts have been returned or
their leases have expired), it MAY recall the remaining writer's
layout and grant a fresh layout with FFV2_FLAGS_ONLY_ONE_WRITER
set, restoring the single-writer optimization.  The metadata
server MAY also leave the writer in multiple writer mode
indefinitely; single writer mode is an optimization, not a
correctness requirement.

The metadata server's choice of when to grant
FFV2_FLAGS_ONLY_ONE_WRITER is policy and is implementation-defined.
A metadata server that aggressively grants single writer mode and
then must recall it each time a second writer appears can produce
recall churn under workloads with irregular concurrent access:
each single-writer-to-multiple-writer transition costs a
CB_LAYOUTRECALL round trip and drain time for in-flight I/O.
Strategies to limit churn include withholding
FFV2_FLAGS_ONLY_ONE_WRITER until sustained single-writer behavior
is observed, deferring the single-writer grant after a recent
recall, or never granting single writer mode for files with a
history of concurrent access.

## Reading Chunks {#sec-reading-chunks}

The client reads chunks from the data file via CHUNK_READ.  The
number of chunks in the payload that need to be atomic depend
on both the Erasure Coding Type and the level of protection selected.
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

## Whole File Repair

Whole-file repair is the case in which too many data servers have
failed, or too many chunks have been lost, for the per-range repair
flow defined in {{sec-repair-selection}} to reconstruct the file in
place.  In this case the metadata server MUST either:

1.  Construct a new layout backed by replacement data servers and
    drive the reconstruction via the **Proxy Server** mechanism (a
    designated data server acts as the source of truth for client
    I/O during the transition, pushing reconstructed content to the
    replacement data servers in the background).  The Proxy Server mechanism also covers the non-repair cases where a file's layout
    must change while remaining available to clients -- policy-driven layout transitions, data server maintenance evacuation,
    administrative ingest, TLS coverage transition, and
    filehandle-backend migration.

2.  If the metadata server has no proxy-server-capable data server
    available, or the surviving shards are insufficient to
    reconstruct any portion of the file, terminate the affected
    byte ranges with NFS4ERR_PAYLOAD_LOST (see
    {{sec-NFS4ERR_PAYLOAD_LOST}}).

The Proxy Server mechanism is specified in {{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}.

Implementations that do not support the Proxy Server mechanism can
still perform recovery for cases where per-range repair suffices,
using CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}) and the repair
client selection rules in {{sec-repair-selection}}.  Such
implementations will surface NFS4ERR_PAYLOAD_LOST on any failure
that exceeds per-range repair's reach, including the multi-data-server failure scenarios the Proxy Server mechanism is intended to
handle.

# First-Line Substitution to a Spare {#sec-spare-substitution}

When a client's CHUNK_WRITE to an FFV2_DS_FLAGS_ACTIVE data server
fails with a transport-level error, NFS4ERR_IO, NFS4ERR_NOSPC, or
any other code that indicates the data server cannot accept the
shard, and the layout includes a data server flagged
FFV2_DS_FLAGS_SPARE ({{I-D.haynes-nfsv4-flexfiles-v2-layout}}) that is not already
holding a shard for the affected payload, the client MAY substitute
the spare for the failing active data server for this write.

Substitution avoids the full metadata-server repair flow.  The
client issues CHUNK_WRITE to the spare in place of the failing
ACTIVE and, if successful, proceeds with CHUNK_FINALIZE and
CHUNK_COMMIT against the full set of data servers the payload
now resides on (the k-1 healthy ACTIVE plus the substituted
SPARE).  The spare becomes the i-th shard holder for the
affected payload.

The client MUST inform the metadata server of the substitution
before returning the layout.  This is done via LAYOUTERROR on
the failing ACTIVE (reporting the error code the client
encountered) in the same compound as, or before, any
LAYOUTSTATS reporting of the substitution.  The metadata server
uses the LAYOUTERROR to decide whether to update the layout in
place -- promoting the spare to ACTIVE and demoting the failing
ACTIVE to a stale-or-unreachable state -- or to push new
layouts via CB_RECALL_ANY to other clients so readers do not
continue to consult the failing ACTIVE.

Substitution is optional.  A client that does not implement it,
or does not have a suitable spare in the layout, falls through
to the normal write-hole handling below.  Substitution is also
not available to clients writing with cwa_stable == FILE_SYNC
unless the client is prepared to drive FILE_SYNC semantics on
the spare as well; otherwise the substitution silently
downgrades the durability contract.

Substitution MUST NOT be used when the existing PENDING state
on any shard of the affected payload carries a different
chunk_guard4 than the current transaction (the range has been
adopted by a repair client already -- the normal repair flow
applies and substitution would collide).

# Handling write holes

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

A single-shard CHUNK_WRITE failure MAY also be handled without
CHUNK_ROLLBACK by substituting the failing data server with an
FFV2_DS_FLAGS_SPARE, per {{sec-spare-substitution}}.  This
avoids engaging the metadata server's repair flow and is the
preferred path on transient single-data server failures when the layout
exposes a suitable spare.

In the multiple writer model, a write hole can also arise when two clients
are racing.  The chunk_guard4 value on each chunk identifies which
transaction wrote it.  A reader that finds chunks with different guard
values detects the non-atomicity and either retries (if a concurrent write
is still in progress) or reports NFS4ERR_PAYLOAD_NOT_ATOMIC to the
metadata server to trigger repair.

When substitution and CHUNK_ROLLBACK are both unavailable, and
the payload cannot be reconstructed because too many shards have
been lost (for example, a catastrophic multi-data server failure with no
spares provisioned), the repair flow ultimately terminates with
NFS4ERR_PAYLOAD_LOST; see
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
({{sec-chunk_guard4}}) are the entire surface a peer observes.
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
the addressable unit carried by the CHUNK_* operations, which
has an envelope that blocks do not.

A chunk carries five properties that a block does not:

-  **Atomicity.**  The chunk_guard4 compare-and-swap guard
   ({{sec-chunk_guard4}}) sequences concurrent writers and
   rejects torn-write attempts.  Block I/O has no comparable
   primitive; concurrent block writes either serialize at the
   storage layer or interleave unpredictably.

-  **Integrity.**  The checksum in each chunk header is computed
   over the header and payload and verified end-to-end on the
   read path ({{sec-CHUNK_READ}}).  Block I/O carries no
   integrity tag; data-corruption detection is delegated to
   the underlying storage medium or is absent.

-  **Provenance.**  The chunk_owner4 ({{sec-chunk_owner4}})
   records which transaction produced the chunk.  Block I/O
   carries no per-write provenance; a block's bytes have no
   protocol-visible producer.

-  **Lifecycle state.**  A chunk progresses through PENDING
   -> FINALIZED -> COMMITTED via CHUNK_FINALIZE / CHUNK_COMMIT
   ({{sec-system-model-chunk-state}}).  Block I/O has no
   lifecycle states; a block is either present or absent.

-  **Lock continuity across revocation.**  The chunk's lock
   ({{sec-CHUNK_LOCK}}) is transferred to the metadata server
   in escrow when a holder's stateid is revoked, and adopted
   by a repair client via CHUNK_LOCK_FLAGS_ADOPT.  Block I/O
   has no per-block locking and no continuity mechanism;
   client failure leaves any external lock indeterminate.

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
CHUNK_* operations.  The CHUNK_* operations are not a byte-range
I/O surface with optional integrity bolted on; they are a
chunk-protocol surface in which the envelope is the primitive.

##  Actors and Roles {#sec-system-model-roles}

Three actors participate on behalf of any given file:

pNFS client:
:  Issues CHUNK operations to data servers over the data path;
   issues LAYOUTGET, LAYOUTRETURN, LAYOUTERROR, and SEQUENCE to
   the metadata server on the control path.  Authenticates to the
   metadata server via AUTH_SYS, RPCSEC_GSS, or TLS.  MAY be
   selected as a repair client via CB_CHUNK_REPAIR.

Metadata server (MDS):
:  Is the sole coordinator for the file.  Grants, renews, and
   revokes layouts; issues TRUST_STATEID / REVOKE_STATEID /
   BULK_REVOKE_STATEID to each tight-coupled data server; selects
   the repair client under the rules in
   {{sec-repair-selection}}; owns the reserved
   CHUNK_GUARD_CLIENT_ID_MDS escrow identity for in-flight repair.

Data server (DS):
:  Persists chunks and enforces the per-file trust table, the
   per-chunk guard CAS (chunk_guard4), the per-chunk lock state
   (including the MDS-escrow owner), and the chunk state machine
   (EMPTY / PENDING / FINALIZED / COMMITTED).  Has no
   coordinator role.  Has no knowledge of the erasure coding type
   in use for any file: the erasure transform is performed
   entirely at the client, and the data server stores the
   resulting chunks without interpreting their contents.

An entity MAY simultaneously hold more than one of these roles
with respect to a given data server, with each role bound to a
distinct session.  A metadata server that opens a control
session to a data server (presenting EXCHGID4_FLAG_USE_PNFS_MDS
at EXCHANGE_ID; see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}})
issues TRUST_STATEID, REVOKE_STATEID, and BULK_REVOKE_STATEID on
that session; on a separate client-side session (presenting
EXCHGID4_FLAG_USE_NON_PNFS), the same metadata server MAY also
issue CHUNK_* operations as a data-path client.  A data server
MUST NOT assume that the metadata server is not also one of its
clients; it distinguishes MDS-only operations from client-side
operations by the EXCHANGE_ID flags of the session that carries
the operation, not by the requester's IP address or principal.

A data server MAY likewise act as a client of another data
server -- for example, when selected as the repair client by an
MDS-directed CB_CHUNK_REPAIR.  Independent of the actor role,
any entity may operate as encoding-aware (issuing CHUNK_*
operations directly against data servers) or encoding-unaware
(operating through the proxy-server-mediated READ / WRITE path
described in {{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}).
Proxy-server registration carries the encoding capability
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

Each file is owned by exactly one metadata server at any given
instant.  Ownership transfer between metadata servers (for
example, during metadata server failover) is implementation-defined and out
of scope for this document; see {{sec-system-model-consensus}}.

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
   layout (possibly against a spare, see
   {{sec-spare-substitution}}).  An metadata server partitioned from a data
   server eventually renews trust entries on reconnection; in
   the interim, the data server returns NFS4ERR_DELAY for
   affected stateids (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).
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
   {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).  An orphaned entry will
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
with a newer COMMITTED generation chosen by the repair client,
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
             |                                   |  (MDS invalidates
             |                                   |   writer stateid;
             |                                   |   lock transfers
             |                                   |   to MDS escrow)
             |                                   v
             |        CHUNK_UNLOCK     +-------------------+
             |       or CHUNK_REPAIRED |   LOCKED by MDS   |
             |      (repair client     |       escrow      |
             |       releases after    +-------------------+
             |       repair completes)           |
             |                                   | CHUNK_LOCK with
             |                                   | CHUNK_LOCK_FLAGS_ADOPT
             |                                   |  (repair client
             |                                   |   adopts MDS-escrow
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

##  Consistency Guarantees {#sec-system-model-consistency}

The protocol provides **per-chunk linearizability on COMMITTED
state**:

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
    by the original writer, then transferred to the MDS-escrow
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

**The chunk is the unit of atomicity.**  Two properties follow:

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
example via NFSv4 byte-range locks ({{RFC8881}}, Section 12).
The chunk size that bounds the atomicity unit for a given file
is the product of ffv2m_striping_unit_size and the stripe width
W in {{I-D.haynes-nfsv4-flexfiles-v2-layout}}; applications can query
fattr4_coding_block_size (see {{I-D.haynes-nfsv4-flexfiles-v2-layout}})
to learn the effective chunk size and align their writes
accordingly.

This choice -- chunk-boundary atomicity rather than stripe- or
block-boundary atomicity -- is load-bearing for the rest of the
consistency story: the chunk_guard4 CAS evaluates at the chunk
level, the PENDING / FINALIZED / COMMITTED state machine is per
chunk, CHUNK_LOCK is per chunk, and repair via CB_CHUNK_REPAIR
operates on chunks.  A different atomicity boundary would
require redefining those primitives, which this revision does
not.

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
   content of a chunk while any successor PENDING chunk exists.
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
COMMITTED content of a chunk while any successor PENDING chunk
exists.  That retained content -- sometimes informally called
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
   selected as the repair client either:

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
   TRUST_STATEID (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).

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
       an MDS-defined grace period.  The grace period exists to
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
   for layout grants, stateid registration, repair client
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
:  Single-MDS-per-file is the protocol model.  Metadata server
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
-  LOOKUP ({{RFC8881}} Section 18.15): runway pool directory
   traversal.
-  GETATTR ({{RFC8881}} Section 18.7): reflected GETATTR after a
   write layout is returned, and any other attribute queries the
   metadata server needs to reconcile its cached view.
-  SETATTR ({{RFC8881}} Section 18.30): data file truncate for
   MDS-level SETATTR(size) fan-out, synthetic uid/gid rotation
   for fencing, and mode-bit initialisation on runway assignment.
-  CREATE ({{RFC8881}} Section 18.4): runway pool file creation.
-  REMOVE ({{RFC8881}} Section 18.25): cleanup on metadata server file
   unlink.
-  OPEN, CLOSE ({{RFC8881}} Sections 18.16, 18.2): used by the
   metadata server when it acts as a client to the data server
   for InBand or proxy I/O.
-  EXCHANGE_ID, CREATE_SESSION, DESTROY_SESSION,
   BIND_CONN_TO_SESSION, DESTROY_CLIENTID ({{RFC8881}} Sections
   18.35, 18.36, 18.37, 18.34, 18.50): control-session
   management.  The metadata server sets
   EXCHGID4_FLAG_USE_PNFS_MDS in its EXCHANGE_ID.  A data
   server that supports the tight-coupling control protocol
   (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}) identifies the
   metadata server's session by EXCHGID4_FLAG_USE_PNFS_MDS and
   accepts TRUST_STATEID, REVOKE_STATEID, and
   BULK_REVOKE_STATEID on that session.
-  TRUST_STATEID ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), REVOKE_STATEID
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), BULK_REVOKE_STATEID
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}): the MDS-to-DS tight-coupling
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
defined below.  A data server MUST reject any other operation on
a data file with NFS4ERR_NOTSUPP.

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

The stateid presented on a CHUNK_* operation is a **layout
stateid** returned by a prior LAYOUTGET against the metadata
server (see Section 18.43 of {{RFC8881}}), NOT an open
stateid, byte-range lock stateid, or delegation stateid.  A
pNFS client does NOT issue OPEN against the data server.
This is a meaningful departure from the stateid model in
Section 18.32 of {{RFC8881}} (which states that the WRITE
stateid "represents a value returned from a previous
byte-range LOCK or OPEN request or the stateid associated
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
   path is chunk-range rather than byte-range, expressed
   via CHUNK_LOCK ({{sec-CHUNK_LOCK}}), and the lock holder
   is identified by chunk_owner4 (the {cg_client_id,
   cg_gen_id} pair) rather than by a lock stateid.  A
   client wanting byte-range locks on a file MUST acquire
   them on the metadata-server filehandle, where standard
   {{RFC8881}} Section 12 byte-range locking applies.

I/O authorization on the data server:
:  The layout stateid carried on CHUNK_* operations.  Under
   tight coupling ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), the
   metadata server registers each issued layout stateid
   with the data server via TRUST_STATEID
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}) and the data server validates
   subsequent CHUNK_* stateids against the trust table.
   Under loose coupling, the data server treats the layout
   stateid as an opaque per-client token and authorizes by
   the synthetic uid/gid the layout carries (see
   {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).

Because the layout stateid does authorization but does not
identify a per-open or per-lock owner, a single client may
present the same layout stateid on many CHUNK_* operations
across many parallel writers within the client, without any
of the open-owner ordering constraints {{RFC8881}}
Section 8.2.2 imposes on regular NFSv4 stateids.  Chunk-
level write ordering and contention are resolved by the
per-chunk chunk_guard4 CAS ({{sec-chunk_guard4}}) and the
chunk-range CHUNK_LOCK, not by stateid-owner sequencing.

### GETATTR on a Data File

GETATTR MAY be issued by a client against a data file.  The
primary use case is repair: a repair client selected by
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
MUST reject a client SETATTR with NFS4ERR_NOTSUPP.

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
truncate on erasure-coded files.  Similarly, a client MUST NOT
issue DEALLOCATE against a data file; see the next subsection.

### MDS-Driven Truncate on Erasure-Coded Files {#sec-mds-truncate-ec}

A client that wants to truncate an erasure-coded file MUST
issue SETATTR(FATTR4_SIZE) to the metadata-server filehandle
(see {{sec-setattr-on-data-file}}).  The metadata server
translates the logical truncate into per-shard size changes
across the data servers in each mirror.

Stripe-aligned truncate:
:  When the new size lies on a stripe boundary (including
   zero), no chunk re-encoding is required.  The metadata
   server computes per-shard sizes from the encoding geometry it
   issued in the layout (k, m, and the projection parameters
   for Mojette; see {{I-D.haynes-nfsv4-flexfiles-v2-mojette}}) and issues
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
   actor: either a Proxy Server
   ({{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}) for
   proxy-mediated truncate, or an encoding-aware client selected
   per {{sec-repair-selection}} via CB_CHUNK_REPAIR with the
   affected partial-stripe chunks as the repair target.  If
   neither path is available, the metadata server MUST return
   NFS4ERR_NOTSUPP to the originating SETATTR.

The metadata server knows encoding geometry from the layout but
is not required to include an encoding implementation.  The
delegation rule above accommodates a metadata server that has
geometry knowledge only.

### PASSTHROUGH Data Files (FFV2_ENCODING_PASSTHROUGH)

For a mirror whose ffv2m_coding_type_data is
FFV2_ENCODING_PASSTHROUGH (see {{I-D.haynes-nfsv4-flexfiles-v2-layout}}),
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

### Chunked Data Files (FFV2_ENCODING_MIRRORED, FFV2_ENCODING_MOJETTE_*, FFV2_ENCODING_RS_VANDERMONDE)

For a mirror whose ffv2m_coding_type_data is any of the chunked
coding types defined in this document
(FFV2_ENCODING_MIRRORED, FFV2_ENCODING_MOJETTE_SYSTEMATIC,
FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC,
FFV2_ENCODING_RS_VANDERMONDE), client operations use the CHUNK_*
operations rather than READ / WRITE / COMMIT.

Required for all erasure-coded clients:

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

-  READ, WRITE, COMMIT against an erasure-coded data file.  A
   data server MUST reject these with NFS4ERR_NOTSUPP and MAY
   log the client for operator attention; this case is almost
   always a client bug in which the client did not inspect the
   mirror's ffv2m_coding_type_data before issuing I/O.
-  READ_PLUS, SEEK, ALLOCATE, DEALLOCATE against an erasure-coded data file.  Chunk-level allocation is a
   metadata-server responsibility.
-  SETATTR against an erasure-coded data file (the general
   prohibition in {{sec-setattr-on-data-file}} applies to all
   data files; truncate in particular is handled by the
   metadata server per {{sec-mds-truncate-ec}}).

### Operations That MUST NOT Be Sent to a Data File

Clients MUST NOT send the following operations to a data server
on a data file, regardless of protection mode.  A data server
MUST return NFS4ERR_NOTSUPP:

-  OPEN, CLOSE, OPEN_DOWNGRADE, OPEN_CONFIRM ({{RFC8881}}
   Sections 18.16, 18.2, 18.18, 18.20).  Opens occur on the
   metadata server; the stateid obtained there is used on the
   data path.
-  LOCK, LOCKU, LOCKT, RELEASE_LOCKOWNER ({{RFC8881}} Sections
   18.10, 18.11, 18.13, 18.24).  Byte-range locks on data files
   are not supported; erasure-coded files use CHUNK_LOCK, and
   mirrored files rely on metadata-server coordination.
-  DELEGPURGE, DELEGRETURN, WANT_DELEGATION ({{RFC8881}} Sections
   18.5, 18.6 and {{RFC7862}} Section 15.3).  Delegations are
   issued by the metadata server.
-  Any operation whose purpose is to manipulate the file's
   namespace: RENAME, LINK, SYMLINK, CREATE (at the file-creation use, not metadata server runway creation), REMOVE.  Namespace
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
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}, {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}},
   {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).  These are MDS-to-DS
   control-plane operations; a data server rejects them with
   NFS4ERR_PERM when received on a client session (see
   {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).

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
   {{RFC8881}} Section 17; specific to the metadata-server-to-
   data-server path in this document.

 | Operation                        | Client -> data server                | metadata server -> data server          |
 | ---
 | SEQUENCE, PUTFH, GETFH, PUTROOTFH | REQUIRED                   | REQUIRED           |
 | EXCHANGE_ID, CREATE_SESSION, DESTROY_SESSION, BIND_CONN_TO_SESSION, DESTROY_CLIENTID | REQUIRED | REQUIRED  |
 | RECLAIM_COMPLETE                  | REQUIRED                   | REQUIRED           |
 | SECINFO, SECINFO_NO_NAME          | REQUIRED                   | MAY                |
 | GETATTR                           | OPTIONAL (non-authoritative) | REQUIRED         |
 | SETATTR                           | MUST NOT                   | REQUIRED           |
 | LOOKUP, CREATE, REMOVE            | MUST NOT                   | REQUIRED           |
 | READ, WRITE, COMMIT               | REQUIRED (mirrored); MUST NOT (erasure-coded) | MAY |
 | READ_PLUS, SEEK, ALLOCATE         | OPTIONAL (mirrored); MUST NOT (erasure-coded) | MAY |
 | DEALLOCATE                        | MUST NOT                   | MAY                |
 | CHUNK_WRITE, CHUNK_READ, CHUNK_FINALIZE, CHUNK_COMMIT, CHUNK_HEADER_READ, CHUNK_LOCK, CHUNK_UNLOCK, CHUNK_ROLLBACK | REQUIRED (erasure-coded); MUST NOT (mirrored) | not used |
 | CHUNK_ERROR, CHUNK_REPAIRED, CHUNK_WRITE_REPAIR | REQUIRED (erasure-coded repair clients); MUST NOT (mirrored) | not used |
 | OPEN, CLOSE, OPEN_DOWNGRADE, OPEN_CONFIRM | MUST NOT           | OPTIONAL (proxy I/O) |
 | LOCK, LOCKU, LOCKT, RELEASE_LOCKOWNER | MUST NOT               | MUST NOT           |
 | DELEGPURGE, DELEGRETURN, WANT_DELEGATION | MUST NOT            | MUST NOT           |
 | RENAME, LINK, SYMLINK             | MUST NOT                   | MUST NOT           |
 | CLONE, COPY, COPY_NOTIFY, OFFLOAD_CANCEL, OFFLOAD_STATUS | MUST NOT | MAY (data migration) |
 | LAYOUTGET, LAYOUTCOMMIT, LAYOUTRETURN, LAYOUTSTATS, LAYOUTERROR, GETDEVICEINFO, GETDEVICELIST | MUST NOT | MUST NOT |
 | ACL-scoped GETATTR/SETATTR bits   | MUST NOT                   | MAY                |
 | TRUST_STATEID, REVOKE_STATEID, BULK_REVOKE_STATEID | MUST NOT  | REQUIRED (tight coupling) |
{: #tbl-ops-allowed title="NFSv4.2 operations allowed on data files"}


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
{: #tbl-protocol-errors title="Error Definitions"}

### NFS4ERR_CODING_NOT_SUPPORTED (Error Code 10097) {#sec-NFS4ERR_CODING_NOT_SUPPORTED}

The client requested a ffv2_coding_type4 which the metadata server
does not support.  I.e., if the client sends a layout_hint requesting
an erasure coding type that the metadata server does not support,
this error code can be returned.  The client might have to send the
layout_hint several times to determine the overlapping set of
supported erasure coding types.

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

Returned by a repair client on the CB_CHUNK_REPAIR response
(ccrr_status) to indicate that the identified ranges cannot be
repaired and the underlying data is no longer recoverable.
Causes include: too few surviving shards to meet the
reconstruction threshold (Katz criterion for Mojette, any
k-of-(k+m) subset for Reed-Solomon Vandermonde), inability to
roll back to a previously committed payload because that payload
is also lost, or exhaustion of all FFV2_DS_FLAGS_SPARE and
FFV2_DS_FLAGS_REPAIR data servers available in the layout.

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
({{I-D.haynes-nfsv4-flexfiles-v2-layout}}) names a checksum_algorithm4
({{sec-checksum4}}) that the client does not implement.
The client returns the layout with this error code rather
than attempting CHUNK_* operations it cannot validate.

On receipt, the metadata server MAY:

-  issue a new layout for the same file naming a different
   checksum_algorithm4 that the client supports (if the
   file's policy permits any of the algorithms the client
   does support); or

-  deny the layout request, in which case the client MUST
   either fall back to MDS-mediated I/O or report an I/O
   error to the application.

NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED is distinct from
NFS4ERR_BADLAYOUT (generic "this layout shape is unusable"):
the explicit per-checksum-algorithm signal lets the metadata
server discriminate "client can't read this layout because
of the checksum algorithm" from "client can't read this
layout for some other reason" and respond accordingly.

## Operations and Their Valid Errors

The operations and their valid errors are presented in
{{tbl-ops-and-errors}}.  All error codes not defined in this document
are defined in Section 15 of {{RFC8881}} and Section 11 of {{RFC7862}}.

 | Operation          | Errors |
 | ---
 | CHUNK_COMMIT       | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_ERROR        | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_FINALIZE     | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_HEADER_READ  | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_LOCK         | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_CHUNK_LOCKED, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_READ         | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOTSUPP, NFS4ERR_PAYLOAD_NOT_ATOMIC, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_REPAIRED     | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_ROLLBACK     | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_UNLOCK       | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_INVAL, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT |
 | CHUNK_WRITE        | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_CHUNK_GUARDED, NFS4ERR_CHUNK_LOCKED, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOSPC, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
 | CHUNK_WRITE_REPAIR | NFS4_OK, NFS4ERR_ACCESS, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DELAY, NFS4ERR_FHEXPIRED, NFS4ERR_IO, NFS4ERR_NOSPC, NFS4ERR_NOTSUPP, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
{: #tbl-ops-and-errors title="Operations and Their Valid Errors (CHUNK_* only; TRUST/REVOKE/BULK_REVOKE errors live in [I-D.haynes-nfsv4-flexfiles-v2-trust-stateid])"}

## Callback Operations and Their Valid Errors

The callback operations and their valid errors are presented in
{{tbl-cb-ops-and-errors}}.  All error codes not defined in this document
are defined in Section 15 of {{RFC8881}} and Section 11 of {{RFC7862}}.

 | Callback Operation| Errors                                       |
 | ---
 | CB_CHUNK_REPAIR | NFS4_OK, NFS4ERR_BADXDR, NFS4ERR_BAD_STATEID, NFS4ERR_DEADSESSION, NFS4ERR_DELAY, NFS4ERR_CODING_NOT_SUPPORTED, NFS4ERR_INVAL, NFS4ERR_IO, NFS4ERR_ISDIR, NFS4ERR_LOCKED, NFS4ERR_NOTSUPP, NFS4ERR_OLD_STATEID, NFS4ERR_PAYLOAD_LOST, NFS4ERR_SERVERFAULT, NFS4ERR_STALE |
{: #tbl-cb-ops-and-errors title="Callback Operations and Their Valid Errors"}

## Errors and the Operations That Use Them

The operations and their valid errors are presented in
{{tbl-errors-and-ops}}.  All operations not defined in this document
are defined in Section 18 of {{RFC8881}} and Section 15 of {{RFC7862}}.

 | Error                            | Operations                  |
 | ---
 | NFS4ERR_CODING_NOT_SUPPORTED     | CB_CHUNK_REPAIR, LAYOUTGET  |
 | NFS4ERR_PAYLOAD_LOST             | CB_CHUNK_REPAIR             |
{: #tbl-errors-and-ops title="Errors and the Operations That Use Them"}

# New NFSv4.2 Common Data Structures

## chunk_guard4 {#sec-chunk_guard4}

~~~ xdr
   /// const CHUNK_GUARD_CLIENT_ID_NONE = 0x00000000;
   /// const CHUNK_GUARD_CLIENT_ID_MDS  = 0xFFFFFFFF;
   ///
   /// struct chunk_guard4 {
   ///     uint32_t   cg_gen_id;
   ///     uint32_t   cg_client_id;
   /// };
~~~
{: #fig-chunk_guard4 title="XDR for chunk_guard4" }

On the wire, a single CHUNK_WRITE carries the 8-byte
chunk_guard4 header followed by the tagged checksum4 and
then the opaque payload, as shown in
{{fig-chunk-wire-layout}}.  The payload length is carried
separately in the CHUNK_WRITE4args cwa_chunks<> slot; the
diagram shows the per-chunk framing only.

~~~
    0                   1                   2                   3
    0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                          cg_gen_id                            |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                         cg_client_id                          |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                       cs_algorithm                            |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                        cs_value_len                           |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    cs_value ... (variable)                    |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+
   |                    opaque payload ...                         |
   +-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+-+

   Bytes 0-3:    cg_gen_id      (per-chunk generation counter)
   Bytes 4-7:    cg_client_id   (owning-client short id)
   Bytes 8-11:   cs_algorithm   (checksum_algorithm4)
   Bytes 12-15:  cs_value_len   (XDR opaque length prefix)
   Bytes 16-N:   cs_value       (checksum bytes; length per
                                 cs_algorithm's registered output)
   Bytes N+1-M:  opaque payload (encoded shard; variable length)

   The checksum block (cs_algorithm + cs_value_len + cs_value)
   is the XDR encoding of one checksum4 ({{fig-checksum4}}).
   For CHECKSUM_ALG_NONE the cs_value_len is zero and the
   payload follows immediately after byte 15.
~~~
{: #fig-chunk-wire-layout title="Per-chunk wire layout"}

The chunk_guard4 (see {{fig-chunk_guard4}}) is effectively a 64-bit
value identifying a specific write transaction on a specific chunk.
It has two fields:

cg_gen_id:
:  A per-chunk monotonic generation counter.  Each chunk's gen_id
   starts at 0 when the chunk is first written and is incremented
   on each successful write by any client.  cg_gen_id is NOT a
   timestamp -- the protocol does not rely on a global clock,
   and no interpretation of cg_gen_id as a wall-clock value is
   supported.  cg_gen_id values are NOT comparable across distinct
   chunks; a given cg_gen_id is only meaningful within the scope
   of a single chunk on a single file.

cg_client_id:
:  A 32-bit value established by the metadata server at the time
   the client's layout is granted (see {{I-D.haynes-nfsv4-flexfiles-v2-layout}} and
   ffv2m_client_id).  The metadata server MUST assign distinct
   cg_client_id values to distinct clients that hold concurrent
   write layouts on the same file.  cg_client_id is opaque with
   respect to client identity -- a data server MUST NOT
   interpret its bits as naming or ordering clients in any
   external sense.  The value supports two operations only:
   equality comparison (to detect whether two chunks were written
   by the same transaction) and numeric comparison (to implement
   the tiebreaker rule below).

Uniqueness contract:
:  The pair (cg_gen_id, cg_client_id) uniquely identifies a write
   transaction on a chunk.  Neither field alone is globally
   unique; two clients MAY independently write with the same
   cg_gen_id on the same chunk (in particular, both may write
   with cg_gen_id equal to some prior value + 1), and the
   cg_client_id is what makes the resulting transactions
   distinguishable.

Deterministic tiebreaker for concurrent writers:
:  When two or more clients race on the same chunk in the
   multi-writer mode, the client whose cg_client_id compares
   numerically lowest MUST ultimately be the one whose write
   reaches COMMITTED on the affected data servers.  The rule is
   enforced in two stages:

    - **At CHUNK_WRITE** (per data server, arrival-order): a
      data server accepts the first CHUNK_WRITE whose
      chunk_guard4 CAS check succeeds against its current
      chunk_guard4 value.  Later writers whose CAS fails receive
      NFS4ERR_CHUNK_GUARDED.  Because arrival order can differ
      between data servers, different subsets of the mirror set
      may accept different clients' writes in this stage; that
      is expected transient divergence, not a violation of the
      tiebreaker rule.

    - **At CHUNK_FINALIZE** (numeric comparison, mirror-set
      convergence): CHUNK_FINALIZE against a chunk whose current
      PENDING write is owned by cg_client_id C_current MUST
      compare the caller's cg_client_id C_caller numerically
      against C_current.  If C_caller < C_current, the data
      server accepts the FINALIZE against the caller's PENDING
      write and discards the higher-numbered writer's
      state.  If C_caller > C_current, the data server rejects
      the FINALIZE with NFS4ERR_CHUNK_GUARDED and the caller's
      client MUST re-read the chunk.  If C_caller == C_current
      (same client re-finalizing its own write), FINALIZE
      proceeds normally.  This is where the "lowest cg_client_id
      wins" invariant is enforced globally: after every affected
      data server has processed each racing client's FINALIZE
      attempt, the mirror set converges on the numerically
      lowest cg_client_id's write.

   A client that observes NFS4ERR_CHUNK_GUARDED on either
   CHUNK_WRITE or CHUNK_FINALIZE MUST re-read the chunk and MAY
   retry its write with a refreshed cg_gen_id.  A client that
   detects no forward progress after a bounded number of retries
   MUST escalate via LAYOUTERROR and the repair coordination
   flow in {{sec-repair-selection}}.

The numeric ordering of cg_client_id values is arbitrary with
respect to the clients' external identities -- it is a
deterministic total order over the opaque 32-bit values, not a
preference ordering over the clients themselves.  A deployment
that requires a specific client to win a race MUST arrange
cg_client_id assignment at the metadata server; the protocol does
not provide a preference mechanism at layout-grant time.

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
   client's layout and selecting a repair client under
   {{sec-repair-selection}}.

-  If a client presents CHUNK_GUARD_CLIENT_ID_MDS as
   cg_client_id in any client-originated operation, the data
   server MUST reject the operation with NFS4ERR_INVAL (see
   {{sec-chunk_guard_mds}}).

-  A cg_client_id that does not match any layout the data
   server has been told about (via TRUST_STATEID) MUST be
   rejected.  Unknown cg_client_id values are treated as stale
   layouts; the data server returns the error specified in
   {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}} for unknown stateids.

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
the MDS-escrow owner instead.

The metadata server does not originate CHUNK_LOCK or CHUNK_WRITE
traffic on its own session.  Clients MUST NOT present
CHUNK_GUARD_CLIENT_ID_MDS as the cg_client_id of any
client-originated chunk_guard4 or chunk_owner4.  A data server
that receives such a value from a client MUST reject the
operation with NFS4ERR_INVAL.

The MDS-escrow owner is released only by a CHUNK_LOCK from the
client selected via CB_CHUNK_REPAIR, carrying
CHUNK_LOCK_FLAGS_ADOPT.  See {{sec-CHUNK_LOCK}}.

## chunk_owner4 {#sec-chunk_owner4}

~~~ xdr
   /// struct chunk_owner4 {
   ///     chunk_guard4   co_guard;
   ///     uint32_t       co_chunk_id;
   /// };
~~~
{: #fig-chunk_owner4 title="XDR for chunk_owner4" }

The chunk_owner4 (see {{fig-chunk_owner4}}) is used to determine
when and by whom a block was written.  The co_chunk_id is used
to identify the chunk and MUST be the index of the chunk within
the file.  I.e., it is the offset of the start of the chunk
divided by the chunk length.  The co_guard is a chunk_guard4
(see {{sec-chunk_guard4}}), used to identify a given
transaction.

The co_guard is like the change attribute (see Section 5.8.1.4 of
{{RFC8881}}) in that each chunk write by a given client has to have
an unique co_guard.  I.e., it can be determined which transaction
across all data files that a chunk corresponds.

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

The checksum algorithm for a given file is selected by
the metadata server at LAYOUTGET time and carried in
the layout (see {{I-D.haynes-nfsv4-flexfiles-v2-layout}}).  A client that
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
~~~
{: #fig-ops-xdr title="Operations XDR" }

Note: opnum entries for the tight-coupling control-plane
operations (`OP_TRUST_STATEID = 89`, `OP_REVOKE_STATEID = 90`,
`OP_BULK_REVOKE_STATEID = 91`) live in
{{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}.

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
~~~
{: #fig-nfs_argop4-amend title="nfs_argop4 amendment block (CHUNK operations only; TRUST/REVOKE/BULK_REVOKE amendment arms live in [I-D.haynes-nfsv4-flexfiles-v2-trust-stateid])"}

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
~~~
{: #fig-nfs_resop4-amend title="nfs_resop4 amendment block (CHUNK operations only; TRUST/REVOKE/BULK_REVOKE amendment arms live in [I-D.haynes-nfsv4-flexfiles-v2-trust-stateid])"}

Operations 78 through 88 (the CHUNK_* operations) are sent by
clients to storage devices on the data path.  The complementary
MDS-to-DS control-plane operations (TRUST_STATEID,
REVOKE_STATEID, BULK_REVOKE_STATEID; opnums 89-91) are
specified in {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}
and MUST NOT be sent by pNFS clients.

All CHUNK_* operations MUST be issued under an active flexible
file v2 layout obtained via LAYOUTGET against the metadata
server.  A data server receiving a CHUNK_* operation from a
client that does not hold a current layout stateid for the
target file MUST reject the operation with NFS4ERR_BAD_STATEID.
In trusted-stateid tight coupling, the stateid presented MUST be
present in the data server's trust table; an unknown stateid
MUST be rejected with NFS4ERR_BAD_STATEID per
{{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}.

The chunk envelope's safety properties (atomicity via
chunk_guard4 CAS, integrity via checksum, lock continuity across
revocation) depend on metadata-server coordination of layout
grants, guard generation, and lock escrow.  A client that issues
CHUNK_* operations outside an active layout is operating outside
this specification; the data server's behaviour in that case is
undefined.  See {{sec-system-model-chunk-not-block}} for the
distinction between the CHUNK_* surface and a generic block I/O
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
   | TRUST_STATEID          | 89     | data server (metadata server control)  | {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}} |
   | REVOKE_STATEID         | 90     | data server (metadata server control)  | {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}} |
   | BULK_REVOKE_STATEID    | 91     | data server (metadata server control)  | {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}} |
{: #tbl-protocol-ops title="Protocol OPs"}

## Operation 78: CHUNK_COMMIT - Activate Cached Chunk Data {#sec-CHUNK_COMMIT}

### ARGUMENTS

~~~ xdr
   /// struct CHUNK_COMMIT4args {
   ///     /* CURRENT_FH: file */
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
   cca_offset.  A zero cca_count, or a cca_offset beyond
   the data server's highest chunk, is not an error; the
   data server returns NFS4_OK with an empty ccr_status
   array.

cca_chunks:
:  an array of chunk_owner4 entries
   ({{fig-chunk_owner4}}) naming the specific
   (cg_gen_id, cg_client_id, co_id) generations to
   commit.  Each entry's co_id MUST fall within
   [cca_offset, cca_offset + cca_count); an entry whose
   co_id is outside the range is rejected with
   NFS4ERR_INVAL in the corresponding ccr_status slot.
   The reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   cg_client_id of any cca_chunks entry; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.

cca_offset and cca_count would appear redundant given
cca_chunks contains explicit co_id values, but they exist
because a chunk index MAY have multiple persisted
generations at the moment CHUNK_COMMIT arrives -- an
older COMMITTED generation retained for the rollback
invariant ({{sec-system-model-consistency}}) alongside a
newer FINALIZED successor.  cca_chunks selects which
(cg_gen_id, cg_client_id) generation to advance to
COMMITTED; cca_offset and cca_count bound the work scope
so the data server can reject malformed requests that
name chunks outside the intended commit window.

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

Unlike CHUNK_READ ({{sec-CHUNK_READ}}) and CHUNK_WRITE
({{sec-CHUNK_WRITE}}), CHUNK_COMMIT has no explicit
stateid field in its arguments.  The data server
authorizes CHUNK_COMMIT against the stateid context the
compound has already established, typically the stateid
carried on an immediately preceding PUTFH or an earlier
CHUNK_* operation in the same compound.  Under
trusted-stateid tight coupling ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}),
the data server applies the trust-table check to
whichever layout stateid the compound has presented; if
no layout stateid has been presented or the presented
stateid is not in the trust table, the data server
rejects CHUNK_COMMIT with NFS4ERR_BAD_STATEID.

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
   identified by the cca_chunks entry's cg_gen_id, the
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
(see Section 12.8 of {{RFC8881}}) in single-writer mode, where
no other writer can race the client's per-chunk transitions
and the CHUNK_WRITE per-block status array reports only
local-failure cases (NFS4ERR_NOSPC, NFS4ERR_IO, and so on).

Same-compound pipelining is NOT RECOMMENDED in multiple-writer
mode.  CHUNK_WRITE reports per-block outcomes in cwr_status
({{sec-CHUNK_WRITE}}); a partial-success outcome (some chunks
accepted, others rejected with NFS4ERR_CHUNK_GUARDED on a lost
race) leaves the client without an opportunity to react before
a same-compound CHUNK_FINALIZE / CHUNK_COMMIT proceeds against
whichever chunks happen to be PENDING.  The compound-level
status is NFS4_OK in this case because per-block failures are
reported in the per-op status array rather than as a compound-
level error, so NFSv4 compound short-circuit (Section 2.10.6.4
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

-  During repair, the MDS-escrow owner
   (CHUNK_GUARD_CLIENT_ID_MDS, see {{sec-chunk_guard_mds}})
   holds the lock while the repair client adopts it via
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   this file.  Under trusted-stateid tight coupling
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), this stateid MUST be in the
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
   record which (cg_gen_id, cg_client_id) generation was
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
:  no active layout stateid for this file (or, in trusted-stateid
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
CHUNK_WRITEs for the named (cg_gen_id, cg_client_id)
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
   cfa_offset.  A zero cfa_count, or a cfa_offset beyond
   the data server's highest chunk, is not an error; the
   data server returns NFS4_OK with an empty cfr_status
   array.

cfa_chunks:
:  an array of chunk_owner4 entries
   ({{fig-chunk_owner4}}) naming the specific
   (cg_gen_id, cg_client_id, co_id) generations to
   finalize.  Each entry's co_id MUST fall within
   [cfa_offset, cfa_offset + cfa_count); an entry whose
   co_id is outside the range is rejected with
   NFS4ERR_INVAL in the corresponding cfr_status slot.
   The reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   cg_client_id of any cfa_chunks entry; see
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
      PENDING state at this offset (the chunk is EMPTY,
      FINALIZED at a different generation, or COMMITTED),
      or the entry's co_id is outside the
      [cfa_offset, cfa_offset + cfa_count) range.

   *  NFS4ERR_CHUNK_GUARDED -- the chunk is PENDING but
      at a different (cg_gen_id, cg_client_id) than the
      one named in the cfa_chunks entry.  A client that
      sees this has lost a race; see {{sec-chunk_guard4}}.

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

Like CHUNK_COMMIT, CHUNK_FINALIZE has no explicit stateid
field in its arguments.  The data server authorizes
CHUNK_FINALIZE against the stateid context the compound
has already established, typically the stateid carried on
an immediately preceding PUTFH or an earlier CHUNK_*
operation in the same compound.  Under trusted-stateid
tight coupling ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), the data server
applies the trust-table check to whichever layout stateid
the compound has presented; if no layout stateid has been
presented or the presented stateid is not in the trust
table, the data server rejects CHUNK_FINALIZE with
NFS4ERR_BAD_STATEID.

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
:  no active layout stateid for this file (or, in trusted-stateid
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
   /// struct CHUNK_HEADER_READ4resok {
   ///     bool            chrr_eof;
   ///     nfsstat4        chrr_status<>;
   ///     bool            chrr_locked<>;
   ///     chunk_owner4    chrr_chunks<>;
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
{: #fig-CHUNK_HEADER_READ4res title="XDR for CHUNK_HEADER_READ4resok" }

### DESCRIPTION

CHUNK_HEADER_READ returns the per-chunk metadata
(chunk_owner4, lock state, and per-chunk status) for a
range of chunks in the target data file without returning
the chunk payloads.  The operation enables clients and
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
   this file.  Under trusted-stateid tight coupling
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

chra_offset:
:  starting chunk index of the range to inspect (not a
   byte offset).

chra_count:
:  number of chunks the inspection range covers,
   starting at chra_offset.

The CHUNK_HEADER_READ result returns four co-indexed
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

The operation has several uses:

Whole-file repair scan:
:  A repair client selected via CB_CHUNK_REPAIR
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
   chunk_owner4 reports the writer's own (cg_client_id,
   cg_gen_id) pair are PENDING or FINALIZED and
   recoverable; chunks absent from the response or
   carrying another writer's owner are not.  The writer
   can then re-issue CHUNK_WRITE for the missing chunks
   or CHUNK_ROLLBACK for the abandoned ones without
   reading payloads it has already committed locally.

Read-side atomicity check:
:  Before issuing a multi-chunk CHUNK_READ in
   multiple-writer mode, a client MAY issue
   CHUNK_HEADER_READ to verify that the chunks in the
   target range share a common chunk_guard4 (the
   cohort-atomicity property in
   {{sec-system-model-consistency}}).  If the guards
   diverge, the client knows the read will not be atomic
   and can wait for a writer to commit, retry, or report
   NFS4ERR_PAYLOAD_NOT_ATOMIC via LAYOUTERROR.  This is
   a hint rather than a guarantee: a concurrent writer
   MAY advance a chunk's state between the
   CHUNK_HEADER_READ response and the subsequent
   CHUNK_READ.

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
:  the chunk is PENDING or FINALIZED (a non-globally-
   visible generation is in progress).  The
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   /// const CHUNK_LOCK_FLAGS_ADOPT  = 0x00000001;
   ///
   /// struct CHUNK_LOCK4args {
   ///     /* CURRENT_FH: file */
   ///     stateid4        cla_stateid;
   ///     offset4         cla_offset;
   ///     count4          cla_count;
   ///     uint32_t        cla_flags;
   ///     chunk_owner4    cla_owner;
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
different naming: LOCK is byte-range and stateid-based;
CHUNK_LOCK is chunk-range and chunk_owner4-based.
CHUNK_LOCK is used in multiple-writer mode
({{sec-multi-writer}}) to serialize racing writers on a
common chunk range, and in the repair flow
({{sec-repair-selection}}) to transfer lock ownership
to a repair client via CHUNK_LOCK_FLAGS_ADOPT.

The client provides:

cla_stateid:
:  the layout stateid the metadata server granted for
   this file.  Under trusted-stateid tight coupling
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cla_offset:
:  starting chunk index of the lock range (not a byte
   offset).

cla_count:
:  number of chunks the lock range covers, starting at
   cla_offset.

cla_flags:
:  bitmask of CHUNK_LOCK_FLAGS_* values.  Currently
   defined: CHUNK_LOCK_FLAGS_ADOPT (lock-ownership
   transfer; see "Lock Transfer via
   CHUNK_LOCK_FLAGS_ADOPT" below).  Unknown bits MUST be
   rejected with NFS4ERR_INVAL.

cla_owner:
:  the chunk_owner4 ({{fig-chunk_owner4}}) that will hold
   the lock on success.  The reserved sentinels
   CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   cg_client_id of cla_owner; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.
   (A client requesting CHUNK_LOCK_FLAGS_ADOPT MUST use
   its own cg_client_id, not the MDS-escrow sentinel,
   even when adopting from an MDS-escrow holder.)

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
MDS-escrow owner if the metadata server has revoked
the holder's stateid via REVOKE_STATEID
({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), per the lock-continuity-
across-revocation invariant in
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
selected as the repair client for the range by the metadata server,
typically via CB_CHUNK_REPAIR ({{sec-CB_CHUNK_REPAIR}}).  A data
server that receives CHUNK_LOCK with the ADOPT flag from a client
that has not been so designated MAY reject the operation with
NFS4ERR_ACCESS.  The mechanism by which the data server determines
designation is coupling-model dependent:

- In a tightly coupled deployment, the metadata server notifies the
  data server via the control protocol (e.g., TRUST_STATEID with
  the new client's stateid or a similar facility).

- In a loosely coupled deployment, the data server MAY rely on the
  metadata server's authentication of the client and accept ADOPT
  from any authenticated client holding a current layout that
  includes the range.  The write-hole exposure cost is that a misbehaving
  client can trigger spurious ownership transfers; the write-hole
  exposure is bounded by the chunk_guard4 checks that subsequent
  CHUNK_WRITEs from displaced writers experience.

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

In either case, ADOPT's effect from the repair client's
perspective is the same: after the successful return the caller
holds the lock and may drive the range to consistency.

The data server MUST reject CHUNK_LOCK with
CHUNK_LOCK_FLAGS_ADOPT if cla_owner's cg_client_id equals
CHUNK_GUARD_CLIENT_ID_MDS -- that value is reserved for server
production and MUST NOT be presented by a client.  The operation
returns NFS4ERR_INVAL in that case.

### RESPONSE CODES

NFS4_OK:
:  the requested chunk range has been locked.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to lock chunks on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted-stateid
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
({{I-D.haynes-nfsv4-flexfiles-v2-layout}}).  For encodings whose parity shards
have variable sizes (the Mojette family), the parity-shard
chunks on a given data server may use a smaller per-shard
chunk size; see {{I-D.haynes-nfsv4-flexfiles-v2-mojette}}.  cra_count is a
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
   computed over the chunk payload (cr_chunk) at
   CHUNK_FINALIZE or CHUNK_COMMIT time and persisted with
   the chunk metadata.  The cs_algorithm field matches the
   layout's ffv2m_checksum_algorithm ({{I-D.haynes-nfsv4-flexfiles-v2-layout}});
   the cs_value carries the computed bytes at the length
   registered for that algorithm.  The client uses
   cr_checksum to detect transport corruption between the
   data server and the client; see
   {{sec-security-checksum-scope}} for the scope and limits
   of checksum protection per algorithm class.

cr_effective_len:
:  the byte length of cr_chunk.  This may be smaller than
   the layout's chunk_size when the chunk is the final
   chunk of a file whose size is not chunk-aligned, or
   when the chunk belongs to a variable-size Mojette
   parity shard.

cr_owner:
:  the chunk_owner4 carrying the chunk_guard4 and chunk-id
   of the COMMITTED generation being returned.  A client
   reading from multiple data servers in an erasure-coded
   layout MUST compare cr_owner.co_guard across data
   servers; agreement of the chunk_guard4 across the k
   data shards is the atomicity invariant on which
   reconstruction depends.  See
   {{sec-system-model-consistency}}.

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
chunk_size, cr_owner is set to all-zeros (with cg_client_id
= CHUNK_GUARD_CLIENT_ID_NONE, see {{sec-chunk_guard_none}}),
and cr_checksum is the checksum of the synthetic zero-filled
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
size is reconstructed at the client from the surviving
shards' chunk_owner4 values, not from any single data
server's crr_eof.

Except when special stateids are used, the cra_stateid
value represents a layout stateid returned by a prior
LAYOUTGET against the metadata server (see Section 18.43
of {{RFC8881}}).  The data server uses cra_stateid to
verify that the client holds a valid layout that
authorizes reading this file.  Under trusted-stateid tight
coupling ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), the data server
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
model ({{sec-CHUNK_LOCK}}) rather than the byte-range
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

~~~
        Data Server 2
  +--------------------------------+
  | CHUNK_READ4resok               |
  +--------------------------------+
  | crr_eof: true                  |
  | crr_chunks[0]:                 |
  |     cr_checksum: 0x3faddace    |
  |     cr_owner:                  |
  |         co_chunk_id: 2         |
  |         co_guard:              |
  |             cg_gen_id   : 3    |
  |             cg_client_id: 6    |
  |     cr_payload_id: 1           |
  |     cr_chunk: ....             |
  | crr_chunks[0]:                 |
  |     cr_checksum: 0xdeade4e5    |
  |     cr_owner:                  |
  |         co_chunk_id: 3         |
  |         co_guard:              |
  |             cg_gen_id   : 0    |
  |             cg_client_id: 0    |
  |     cr_payload_id: 1           |
  |     cr_chunk: 0000...00000     |
  | crr_chunks[0]:                 |
  |     cr_checksum: 0x7778abcd    |
  |     cr_owner:                  |
  |         co_chunk_id: 4         |
  |         co_guard:              |
  |             cg_gen_id   : 3    |
  |             cg_client_id: 6    |
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   repair client.  Under trusted-stateid tight coupling
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), this stateid MUST be in the
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
   repair client.  The data server uses this to record
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
repair client that sees NFS4ERR_INVAL SHOULD verify the
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   (cg_gen_id, cg_client_id, co_id) generations to roll
   back.  Each entry's co_id MUST fall within
   [cra_offset, cra_offset + cra_count); entries outside
   the range are rejected with NFS4ERR_INVAL in the
   corresponding crr_status slot (the result struct is
   sized to match cra_chunks).  The reserved sentinels
   CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   cg_client_id of any cra_chunks entry; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.

The CHUNK_ROLLBACK result returns:

crr_writeverf:
:  a verifier identifying the data server's incarnation.
   Semantics match cwr_writeverf in CHUNK_WRITE.

CHUNK_ROLLBACK has two principal scenarios:

1.  A writer in multiple-writer mode that observed
    per-chunk failures in the CHUNK_WRITE response (e.g.,
    NFS4ERR_CHUNK_GUARDED on a subset of chunks) needs to
    abandon the partial write before issuing CHUNK_FINALIZE
    on the chunks that did succeed.  CHUNK_ROLLBACK on the
    abandoned chunks releases their PENDING generation
    cleanly.

2.  A repair client that wrote reconstructed data via
    CHUNK_WRITE_REPAIR ({{sec-CHUNK_WRITE_REPAIR}}) and
    subsequently discovered the reconstruction was wrong
    (for example, a CRC mismatch detected during
    cross-mirror verification) needs to abandon the
    repair before any client commits it.

The data server effects the rollback as follows:

-  Chunks in PENDING with a matching chunk_owner4: the
   data server deletes the PENDING payload and restores
   the chunk to its prior state (EMPTY, or the prior
   COMMITTED generation if the rollback invariant in
   {{sec-system-model-consistency}} required retention).

-  Chunks in FINALIZED with a matching chunk_owner4: the
   data server deletes the FINALIZED payload and the
   persisted finalization metadata, restoring the chunk
   to its prior state.

-  Chunks not in PENDING or FINALIZED at the named
   generation, or whose chunk_owner4 does not match: the
   corresponding crr_status slot reports NFS4ERR_INVAL
   and the chunk is left unchanged.

#### Rollback of COMMITTED Chunks

CHUNK_ROLLBACK against a COMMITTED chunk is permitted
ONLY on the repair path, when a repair client is
restoring a prior COMMITTED generation that another
client incorrectly advanced.  In this case the data
server replaces the current COMMITTED generation with
the chunk_owner4 named in the cra_chunks entry, which
MUST itself name a generation already persisted at the
data server (typically the prior COMMITTED kept under
the rollback invariant).  A non-repair CHUNK_ROLLBACK
against a COMMITTED chunk is rejected with
NFS4ERR_INVAL.

#### Stateid and Authorization

Like CHUNK_COMMIT, CHUNK_ROLLBACK has no explicit
stateid field in its arguments.  The data server
authorizes CHUNK_ROLLBACK against the stateid context
the compound has already established, typically the
stateid carried on an immediately preceding PUTFH or an
earlier CHUNK_* operation.  Under trusted-stateid tight
coupling ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), the data server
applies the trust-table check to whichever layout
stateid the compound has presented; if no layout
stateid has been presented or the presented stateid is
not in the trust table, the data server rejects
CHUNK_ROLLBACK with NFS4ERR_BAD_STATEID.

If the current filehandle is not an ordinary file, an
error MUST be returned (NFS4ERR_ISDIR / NFS4ERR_SYMLINK /
NFS4ERR_WRONG_TYPE).

### RESPONSE CODES

NFS4_OK:
:  the named chunks have been rolled back.

NFS4ERR_ACCESS:
:  the layout stateid or credentials are not
   permitted to roll back chunks on this file.

NFS4ERR_BADXDR:
:  arguments could not be decoded.

NFS4ERR_BAD_STATEID:
:  no active layout stateid for this file (or, in trusted-stateid
   tight coupling, the stateid is not in the trust table).  See
   {{sec-new-ops}}.

NFS4ERR_INVAL:
:  arguments named chunks not eligible for rollback
   or outside the file's mirror set.

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
   this file.  Under trusted-stateid tight coupling
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), this stateid MUST be in the
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
   the lock.  The cg_client_id MUST match the
   chunk_owner4 that was supplied on the CHUNK_LOCK that
   acquired the lock (including the case of a lock
   transferred via CHUNK_LOCK_FLAGS_ADOPT, in which the
   adopter's chunk_owner4 is the current holder).  The
   reserved sentinels CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear as the
   cg_client_id of cua_owner; see
   {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}.
   In particular, a repair client releasing a lock it
   adopted from the MDS-escrow owner uses its own
   cg_client_id in cua_owner, not
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
via REVOKE_STATEID ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}) before the
lease lapses, the lock transitions to the MDS-escrow
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   ///     chunk_owner4       cwa_owner;
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
({{I-D.haynes-nfsv4-flexfiles-v2-mojette}}).  The number of chunks in the
payload is ceil(len(cwa_chunks) / cwa_chunk_size).

cwa_owner ({{fig-chunk_owner4}}) names the writer's
chunk_owner4: cg_gen_id is the writer's per-chunk
generation counter, cg_client_id is the writer's
metadata-server-assigned client identifier (the reserved
sentinels CHUNK_GUARD_CLIENT_ID_NONE and
CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear in cwa_owner;
see {{sec-chunk_guard_none}} and {{sec-chunk_guard_mds}}),
and co_id is the chunk-index identifier of the first
chunk in the payload (redundant with cwa_offset for a
single-chunk write; the data server MUST treat them as
the same value and MAY reject a mismatch with
NFS4ERR_INVAL).

cwa_payload_id is a writer-chosen identifier that lets a
repair coordinator correlate chunks of the same logical
write across data servers.

cwa_checksums, when non-empty, MUST contain one checksum
entry per chunk in the payload.  Each entry's cs_algorithm
MUST match ffv2m_checksum_algorithm of the mirror named in
the layout (see {{I-D.haynes-nfsv4-flexfiles-v2-layout}}); a mismatch is rejected
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

cwa_guard ({{fig-write_chunk_guard4}}) controls the chunk-
guard CAS check (see "Guarding the Write" below).

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
:  per-chunk chunk_owner4 the data server recorded.  In
   normal operation this matches cwa_owner with cg_gen_id
   incremented for each chunk; the field is reported
   explicitly so a client that lost track of its
   per-chunk gen counter can recover the data server's
   view.

Except when special stateids are used, cwa_stateid
represents a layout stateid returned by a prior LAYOUTGET
against the metadata server (see Section 18.43 of
{{RFC8881}}) that authorizes write access to this file.
Under trusted-stateid tight coupling
({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), the data server additionally
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
({{sec-CHUNK_LOCK}}) rather than the byte-range locking
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
data server guarantees before returning:

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

-  Two clients racing on a chunk in multiple-writer mode
   each see chunk_guard4 contention.  One client wins the
   per-chunk CAS; if its CHUNK_WRITE had
   CHUNK_WRITE_FLAGS_ACTIVATE_IF_EMPTY set and stable was
   FILE_SYNC4 or DATA_SYNC4, the winning chunk becomes
   COMMITTED.  The losing client sees NFS4ERR_CHUNK_GUARDED
   in the corresponding cwr_block_status slot.

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
   (storage-space limits, tight-coupling trust-table state,
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   ///     chunk_owner4       cwra_owner;
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
   ///     nfsstat4        cwrr_status<>;
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
the chunk_guard4 CAS check is bypassed (the repair client
is writing a reconstructed value rather than competing in
a multiple-writer race), and the data server MAY log the
repair separately for operator audit.

CHUNK_WRITE_REPAIR has no direct analog in {{RFC8881}}; it
is the chunk-protocol equivalent of writing reconstructed
data into a RAID stripe whose other members are known
healthy.  The reconstructed data is produced by the repair
client from surviving shards via the erasure-coding
algorithm of the file's layout (RS matrix inversion or
Mojette corner-peeling, see {{I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde}} and
{{I-D.haynes-nfsv4-flexfiles-v2-mojette}}).

The repair workflow that invokes CHUNK_WRITE_REPAIR is:

1.  The repair client (selected per
    {{sec-repair-selection}}) reads surviving chunks from
    the remaining data servers via CHUNK_READ
    ({{sec-CHUNK_READ}}).

2.  The repair client reconstructs the missing chunks
    using the erasure-coding algorithm of the file's
    layout.

3.  The repair client acquires a CHUNK_LOCK
    ({{sec-CHUNK_LOCK}}) on the target data server to
    prevent concurrent writes during repair.  For repair
    that adopts an MDS-escrow lock, the CHUNK_LOCK
    carries CHUNK_LOCK_FLAGS_ADOPT
    ({{sec-chunk_guard_mds}}).

4.  The repair client writes the reconstructed data via
    CHUNK_WRITE_REPAIR.

5.  The repair client issues CHUNK_FINALIZE
    ({{sec-CHUNK_FINALIZE}}) and CHUNK_COMMIT
    ({{sec-CHUNK_COMMIT}}) to persist the repair.

6.  The repair client issues CHUNK_REPAIRED
    ({{sec-CHUNK_REPAIRED}}) to clear the errored state.

7.  The repair client releases the lock via CHUNK_UNLOCK
    ({{sec-CHUNK_UNLOCK}}).

The arguments mirror CHUNK_WRITE except that
CHUNK_WRITE_REPAIR has no cwa_flags field (the
activation-shortcut behaviour is not offered on the repair
path) and no cwa_guard field (the guard CAS is bypassed
by construction):

cwra_stateid:
:  the layout stateid the metadata server granted to the
   repair client.  Under trusted-stateid tight coupling
   ({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}), this stateid MUST be in the
   data server's trust table; otherwise the data server
   rejects the operation with NFS4ERR_BAD_STATEID.

cwra_offset:
:  starting chunk index in the file (not a byte offset).

cwra_stable:
:  the stable_how4 durability level the data server MUST
   apply before returning.  Semantics match cwa_stable in
   CHUNK_WRITE (see {{sec-CHUNK_WRITE}} "Stability and
   Activation").

cwra_owner:
:  the chunk_owner4 ({{fig-chunk_owner4}}) the repair
   client uses for the reconstructed payload.  The
   cg_client_id MUST be the repair client's own
   ffv2m_client_id (not CHUNK_GUARD_CLIENT_ID_MDS); the
   cg_gen_id is the repair client's locally chosen
   per-chunk generation counter.  The reserved sentinels
   CHUNK_GUARD_CLIENT_ID_NONE and
   CHUNK_GUARD_CLIENT_ID_MDS MUST NOT appear in
   cwra_owner; see {{sec-chunk_guard_none}} and
   {{sec-chunk_guard_mds}}.

cwra_payload_id:
:  the payload-id the repair client associates with the
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
   ({{I-D.haynes-nfsv4-flexfiles-v2-layout}}), with NFS4ERR_INVAL on mismatch.

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

cwrr_status:
:  per-chunk acceptance status, one entry per chunk in
   the payload, co-indexed.  The top-level
   CHUNK_WRITE_REPAIR status is NFS4_OK as long as the
   data server could evaluate each chunk; per-chunk
   failures are reported in cwrr_status rather than by
   failing the whole operation.

The target chunks SHOULD be in the errored state (set by
a prior CHUNK_ERROR) or EMPTY.  If a target chunk is
COMMITTED with valid data, the data server MAY reject the
repair-write with NFS4ERR_INVAL in the corresponding
cwrr_status slot to prevent overwriting good data; the
repair client SHOULD re-verify the chunk before
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
:  no active layout stateid for this file (or, in trusted-stateid
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
   /// struct CB_CHUNK_REPAIR4args {
   ///     nfs_fh4                     ccra_fh;
   ///     stateid4                    ccra_layout_stateid;
   ///     nfstime4                    ccra_deadline;
   ///     cb_chunk_repair_reason4     ccra_reason;
   ///     cb_chunk_range4             ccra_ranges<>;
   /// };
~~~
{: #fig-CB_CHUNK_REPAIR4args title="XDR for CB_CHUNK_REPAIR4args" }

### RESULTS

~~~ xdr
   /// struct CB_CHUNK_REPAIR4res {
   ///     nfsstat4           ccrr_status;
   /// };
~~~
{: #fig-CB_CHUNK_REPAIR4res title="XDR for CB_CHUNK_REPAIR4res" }

### DESCRIPTION

CB_CHUNK_REPAIR is sent by the metadata server to a
selected pNFS client to request that the client repair one
or more non-atomic chunk ranges on the file's data
servers.  CB_CHUNK_REPAIR is the back-channel companion to
the chunk repair flow: the metadata server selects a
repair client per {{sec-repair-selection}} (those rules
are normative for how the client MUST respond on receipt
of this callback) and uses CB_CHUNK_REPAIR to deliver the
work item.

CB_CHUNK_REPAIR has no analog in {{RFC8881}}.  RFC 8881
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
   acquire one via LAYOUTGET before issuing any CHUNK_*
   operation on the ranges.

ccra_deadline:
:  a wall-clock nfstime4 (seconds and nanoseconds since
   the epoch, as defined in Section 3.3.1 of {{RFC8881}})
   by which the client is expected to have driven every
   range to completion (CHUNK_REPAIRED on the
   reconstruction path, or CHUNK_UNLOCK on the rollback
   path).  The wall-clock representation assumes the
   metadata server and the repair client maintain clock
   synchronization within one metadata-server lease period
   (via NTP {{RFC5905}} or an equivalent mechanism);
   deployments unable to guarantee sub-lease-period
   synchronization SHOULD extend the ccra_deadline budget
   to accommodate the worst-case skew (concretely, set
   `ccra_deadline` to at least
   `current-wall-clock + deadline-budget + expected-skew`).
   Under clock skew, missing the deadline is not
   safety-critical because state cannot be corrupted, but
   spurious deadline expiry SHOULD be avoided by the
   budget above.  Missing the deadline does not corrupt
   state -- the metadata server MAY re-select another
   repair client after the deadline elapses -- but a
   client that has missed the deadline MUST re-verify its
   layout and the chunk lock state before continuing any
   repair-related CHUNK_* operation.

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
   behaviour differs.

ccra_ranges:
:  the list of every chunk range the metadata server
   requests the client to repair.  Each entry carries its
   own ccr_error describing the failure mode the client
   is being asked to remedy.  The repair strategy depends
   on the error code; see {{sec-repair-selection}} for
   the normative and guidance split.

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
established the lock).  The repair client MUST use
CHUNK_LOCK with CHUNK_LOCK_FLAGS_ADOPT
({{sec-CHUNK_LOCK}}) to take ownership of the lock before
issuing CHUNK_WRITE_REPAIR, CHUNK_ROLLBACK, or CHUNK_WRITE
on any chunk in a requested range.

CB_CHUNK_REPAIR returns only a top-level status in
ccrr_status; see "RESPONSE CODES" below for the normative
meanings the metadata server attaches to each returned
nfsstat4.

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

All other error codes listed in {{tbl-cb-ops-and-errors}} are
treated by the metadata server as retriable: the metadata server
MAY issue a subsequent CB_CHUNK_REPAIR to the same or a
different client.  If the client becomes unreachable (no
response within the deadline), the metadata server re-selects
per {{sec-repair-selection}}.

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
({{I-D.haynes-nfsv4-flexfiles-v2-layout}}):

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
have those bytes accepted.  The residual surface differs per
authentication model:

-  Under AUTH_SYS with loose coupling, the residual surface is
   essentially the pre-existing attack surface of NFSv3 writes:
   any host that can reach the data server with a valid uid can
   write nonsense to chunks that uid owns.  This is the Flex
   Files v1 authorization model, which flexible file v2 layout inherits
   without modification for this path.

-  Under RPCSEC_GSS or TLS with mutual authentication, the
   residual surface reduces to: only the authenticated client
   can write nonsense into chunks it owns.  Cross-client
   corruption is prevented because the data server verifies the
   principal before accepting the write.  The remaining attack
   surface is the client's own integrity: any deployment that
   relies on data integrity above the wire MUST apply
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

##  Transport Layer Security {#sec-tls}

RPC-over-TLS {{RFC9289}} MAY be used to protect traffic between the
client and the metadata server and between the client and data servers.
When RPC-over-TLS is in use on the data server path, the synthetic
uid/gid credentials carried in AUTH_SYS remain the access control
mechanism; TLS provides confidentiality and integrity for the transport
but does not replace the fencing model described in {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}.
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


# IANA Considerations

## New NFSv4.2 Operation Assignments

IANA is requested to assign the following new operation values
in the "NFSv4 Operations" registry (extending the assignments of
{{RFC8881}}):

- Value 78: CHUNK_COMMIT
- Value 79: CHUNK_ERROR
- Value 80: CHUNK_FINALIZE
- Value 81: CHUNK_HEADER_READ
- Value 82: CHUNK_LOCK
- Value 83: CHUNK_READ
- Value 84: CHUNK_REPAIRED
- Value 85: CHUNK_ROLLBACK
- Value 86: CHUNK_UNLOCK
- Value 87: CHUNK_WRITE
- Value 88: CHUNK_WRITE_REPAIR

The reference for each is this document.

## New NFSv4.2 Callback Operation Assignment

IANA is requested to assign the following new callback
operation value in the "NFSv4 Callback Operations" registry:

- Value 16: CB_CHUNK_REPAIR

The reference is this document.

##  Checksum Algorithm Registry {#iana-checksum-algorithms}

This document introduces the "Flexible File Version 2
Layout Type Checksum Algorithm Registry".  Values in this
registry name the checksum_algorithm4
({{sec-checksum4}}) carried in checksum4 on the wire and
selected per-mirror via ffv2m_checksum_algorithm
({{I-D.haynes-nfsv4-flexfiles-v2-layout}}).

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
XOR value `0xFFFFFFFF`; input reflected; output reflected;
covered bytes are the shard payload in transmission order
(no length or type prefix).  The 4-byte `cs_value` carries
the CRC as a big-endian integer.  Deployments SHOULD
prefer CHECKSUM_ALG_CRC32C for new files since CRC32C is
hardware-accelerated on every modern CPU.

CHECKSUM_ALG_CRC32C (value 2) is the CRC-32 with the
Castagnoli polynomial specified in {{RFC3720}} Section
12.1 and adopted by {{RFC4960}} Section 6.4 (SCTP), and
also as the SSE4.2 / ARMv8 / RISC-V CRC-32C
hardware-acceleration instructions.  Concrete parameters:
generator polynomial `0x1EDC6F41` (equivalently, the
reflected form `0x82F63B78`); initial register value
`0xFFFFFFFF`; final XOR value `0xFFFFFFFF`; input
reflected; output reflected; covered bytes are the shard
payload in transmission order.  The 4-byte `cs_value`
carries the CRC as a big-endian integer.

CHECKSUM_ALG_FLETCHER4 (value 3) is the ZFS Fletcher4
variant as documented in the OpenZFS on-disk format
specification {{OPENZFS-FLETCHER4}}.  Concrete parameters:
input is processed as a sequence of little-endian 32-bit
words (the shard payload MUST be a multiple of 4 bytes;
implementations that need to checksum non-multiple-of-4
payloads pad with zero bytes and register the padded
variant separately); the four 64-bit accumulators `A`,
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
big-endian).  Covered bytes are the shard payload in
transmission order.

CHECKSUM_ALG_BLAKE3 (value 6) is the BLAKE3 hash algorithm
specified in {{BLAKE3-SPEC}} at its standard 32-byte
output length (BLAKE3 in its default mode, no keyed hash,
no key-derivation context, no XOF output at other
lengths).  Extended-output BLAKE3, keyed BLAKE3, and the
key-derivation mode register as separate algorithms.
Covered bytes are the shard payload in transmission order;
`cs_value` is the 32-byte hash output in the byte order
defined by {{BLAKE3-SPEC}} Section 2.4.

A checksum4 whose cs_value length does not match the
registered cs_value bytes for its cs_algorithm MUST be
rejected with NFS4ERR_INVAL.

The "Class" column in {{tbl-checksum-algorithms}} is
informational and indicates the threat model the algorithm
supports; see {{sec-security-checksum-scope}}.


# Acknowledgments
{:numbered="false"}

See the Acknowledgments section of
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}.

--- back
