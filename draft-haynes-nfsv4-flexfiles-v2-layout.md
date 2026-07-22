---
title: The Flexible File Version 2 Layout Type
abbrev: FFv2 Layout
docname: draft-haynes-nfsv4-flexfiles-v2-layout-latest
category: std
date: {DATE}
consensus: true
ipr: trust200902
area: General
workgroup: Network File System Version 4
keyword: [pNFS, flexfiles, layout type]

stand_alone: yes
pi: [toc, sortrefs, symrefs, docmapping, comments]

venue:
  group: Network File System Version 4
  type: Working Group
  mail: nfsv4@ietf.org
  arch: https://mailarchive.ietf.org/arch/browse/nfsv4/
  github: ietf-wg-nfsv4/flexfiles-v2
  latest: https://ietf-wg-nfsv4.github.io/flexfiles-v2/draft-haynes-nfsv4-flexfiles-v2-layout.html

author:
 -
    ins: T. Haynes
    name: Thomas Haynes
    organization: Hammerspace
    email: loghyr@gmail.com

normative:
  RFC4506:
  RFC5661:
  RFC5662:
  RFC7530:
  RFC7862:
  RFC8178:
  RFC8434:
  RFC8435:
  RFC8881:
  I-D.haynes-nfsv4-flexfiles-v2-requirements:
  I-D.haynes-nfsv4-flexfiles-v2-trust-stateid:
  I-D.haynes-nfsv4-flexfiles-v2-chunks:
  I-D.haynes-nfsv4-flexfiles-v2-encoding-registry:

informative:
  I-D.haynes-nfsv4-flexfiles-v2-rs-vandermonde:
  I-D.haynes-nfsv4-flexfiles-v2-mojette:
  I-D.haynes-nfsv4-flexfiles-v2-proxy-server:
  RFC1813:
  RFC4519:

--- abstract

This document specifies the Flexible File Version 2 Layout
Type: the layout XDR that carries per-mirror encoding
selection, device addressing, striping, layout-return, layout-
error, layout-stats, layout creation hint, and layout recall.
The layout is the surface over which the trust-stateid control
protocol, the chunk substrate, the erasure-encoding framework,
and the encoding companion documents interoperate.  This
document also specifies Client-Side Mirroring
(FFV2_ENCODING_MIRRORED) and how encodings compare across the
protocol dimensions.

--- note_Note_to_Readers

This is an individual submission and does not reflect Working Group
consensus.  The "About This Document" section above has the current
discussion venue, latest rendering, and source location.

--- middle

# Introduction

The Flexible File Version 2 Layout Type is a pNFS layout type
{{RFC8881}} that extends the Flexible File Layout of {{RFC8435}}
with per-mirror encoding selection, chunk-based erasure coding,
and revoke-now admission control.  This document specifies:

- Device addressing and discovery (`ff_device_addr4`,
  multipathing).
- The layout XDR types (`ffv2_layout4`, `ffv2_mirror4`,
  `ffv2_coding_type4`, `ffv2_data_server4`, and the supporting
  hierarchy).
- Striping.
- Recovering from client I/O errors.
- Client-Side Mirroring (FFV2_ENCODING_MIRRORED) semantics.
- Comparison of encoding types (registered in
  {{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}).
- Layout return, LAYOUTERROR, LAYOUTSTATS, layout creation
  hint, `ff_layouthint4`, and layout recall.
- The `EXCHGID4_FLAG_USE_ERASURE_DS` client identification
  flag.
- The `fattr4_coding_block_size` attribute.

The trust-stateid control protocol, chunk substrate, encoding
registry, and encoding companion specifications live in
separate documents.

# Requirements Language

{::boilerplate bcp14-tagged}

# Definitions

The following terms are used with meanings defined in
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}:

- data server (DS), metadata server (MDS)
- encoding, stripe, shard, k, m

Local terms defined in this document:

Layout:
:  A `ffv2_layout4` structure returned to a client via
   LAYOUTGET, carrying the encoding selection, device
   references, striping information, and mirror set for a
   region of a file.

Mirror:
:  A `ffv2_mirror4` entry within a layout, carrying an
   encoding type, a data-server set, and per-mirror flags.

Layout hint:
:  A `ff_layouthint4` structure passed by a client to influence
   the layout the MDS assigns to a newly-created file.

#  Device Addressing and Discovery

Data operations to a storage device require the client to know the
network address of the storage device.  The NFSv4.1+ GETDEVICEINFO
operation (Section 18.40 of {{RFC8881}}) is used by the client to
retrieve that information.

##  ff_device_addr4 {#sec-ff_device_addr4}

The ff_device_addr4 data structure (see {{fig-ff_device_addr4}})
is returned by the server as the layout-type-specific opaque field
da_addr_body in the device_addr4 structure by a successful GETDEVICEINFO
operation.

The ff_device_versions4 and ff_device_addr4 structures are
reused unchanged from {{RFC8435}}; they are reproduced here for
reader convenience and are not part of the XDR extracted from
this document.

~~~ xdr
   struct ff_device_versions4 {
           uint32_t        ffdv_version;
           uint32_t        ffdv_minorversion;
           uint32_t        ffdv_rsize;
           uint32_t        ffdv_wsize;
           bool            ffdv_tightly_coupled;
   };
~~~
{: #fig-ff_device_versions4 title="ff_device_versions4 (reused from RFC 8435)"}

~~~ xdr
   struct ff_device_addr4 {
           multipath_list4     ffda_netaddrs;
           ff_device_versions4 ffda_versions<>;
   };
~~~
{: #fig-ff_device_addr4 title="ff_device_addr4 (reused from RFC 8435)"}

The ffda_netaddrs field is used to locate the storage device.  It
MUST be set by the server to a list holding one or more of the device
network addresses.

The ffda_versions array allows the metadata server to present choices
as to NFS version, minor version, and coupling strength to the
client.  The ffdv_version and ffdv_minorversion represent the NFS
protocol to be used to access the storage device.  This layout
specification defines the semantics for ffdv_versions 3 and 4.  If
ffdv_version equals 3, then the server MUST set ffdv_minorversion to
0 and ffdv_tightly_coupled to false.  The client MUST then access the
storage device using the NFSv3 protocol {{RFC1813}}.  If ffdv_version
equals 4, then the server MUST set ffdv_minorversion to 1 or 2, and
the client MUST access the storage device using NFSv4 with the
specified minor version.

Two additional constraints narrow the valid set of
(ffdv_version, ffdv_minorversion) tuples in specific cases:

-  When a mirror's encoding type uses CHUNK_* operations (that
   is, any FFV2_ENCODING_* value other than
   FFV2_ENCODING_PASSTHROUGH), the corresponding storage device
   MUST be advertised with ffdv_version = 4 and
   ffdv_minorversion = 2.  CHUNK_* operations are NFSv4.2 ops
   defined in this document; NFSv3 and NFSv4.1 storage devices
   cannot serve a non-PASSTHROUGH mirror.

-  When ffdv_tightly_coupled is true (indicating trusted-stateid
   tight coupling), the storage device MUST be advertised with
   ffdv_version = 4 and ffdv_minorversion = 2.  The TRUST_STATEID
   family of operations is defined as NFSv4.2; NFSv4.1 storage
   devices cannot participate in trusted-stateid tight coupling.

PASSTHROUGH mirrors with loose coupling are the only configuration
for which (3, 0) or (4, 1) remain valid; for all other
configurations the storage device MUST be NFSv4.2.

Note that while the client might determine that it cannot use any of
the configured combinations of ffdv_version, ffdv_minorversion, and
ffdv_tightly_coupled, when it gets the device list from the metadata
server, there is no way to indicate to the metadata server as to
which device it is version incompatible.  However, if the client
waits until it retrieves the layout from the metadata server, it can
at that time clearly identify the storage device in question (see
{{sec-version-errors}}).

The ffdv_rsize and ffdv_wsize are used to communicate the maximum
rsize and wsize supported by the storage device.  As the storage
device can have a different rsize or wsize than the metadata server,
the ffdv_rsize and ffdv_wsize allow the metadata server to
communicate that information on behalf of the storage device.

ffdv_tightly_coupled informs the client as to whether the
metadata server is tightly coupled with this storage device.  The
flag was defined by {{RFC8435}} as a general tight-coupling
indicator; in flexible file v2 layouts the flag specifically
indicates trusted-stateid tight coupling
({{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}).  Note that even if the data
protocol is at least NFSv4.1, it may still be the case that there
is loose coupling in effect.  For an NFSv4.2 storage device, the
metadata server sets ffdv_tightly_coupled to true only after
confirming the storage device implements the TRUST_STATEID control
protocol via the capability probe described in
{{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}.  An NFSv4.2 storage device that does
not implement TRUST_STATEID (returning NFS4ERR_NOTSUPP to the
probe) MUST be advertised with ffdv_tightly_coupled set to false,
regardless of whether it implements some other (non-TRUST_STATEID)
tight-coupling control protocol; from this specification's
perspective, only trusted-stateid tight coupling is interoperable.

If ffdv_tightly_coupled is not set, then the client MUST commit
writes to the storage devices for the file before sending a
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

To support storage device multipathing, ffda_netaddrs contains an
array of one or more storage device network addresses.  This array
(data type multipath_list4) represents a list of storage devices
(each identified by a network address), with the possibility that
some storage device will appear in the list multiple times.

The client is free to use any of the network addresses as a
destination to send storage device requests.  If some network
addresses are less desirable paths to the data than others, then the
metadata server SHOULD NOT include those network addresses in
ffda_netaddrs.  If less desirable network addresses exist to provide
failover, the RECOMMENDED method to offer the addresses is to provide
them in a replacement device-ID-to-device-address mapping or a
replacement device ID.  When a client finds no response from the
storage device using all addresses available in ffda_netaddrs, it
SHOULD send a GETDEVICEINFO to attempt to replace the existing
device-ID-to-device-address mappings.  If the metadata server detects
that all network paths represented by ffda_netaddrs are unavailable,
the metadata server SHOULD send a CB_NOTIFY_DEVICEID (if the client
has indicated it wants device ID notifications for changed device
IDs) to change the device-ID-to-device-address mappings to the
available addresses.  If the device ID itself will be replaced, the
metadata server SHOULD recall all layouts with the device ID and thus
force the client to get new layouts and device ID mappings via
LAYOUTGET and GETDEVICEINFO.

Generally, if two network addresses appear in ffda_netaddrs, they
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

## ffv2_coding_type4

~~~ xdr
   /// enum ffv2_coding_type4 {
   ///     FFV2_ENCODING_PASSTHROUGH             = 1,
   ///     FFV2_ENCODING_MOJETTE_SYSTEMATIC      = 2,
   ///     FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC  = 3,
   ///     FFV2_ENCODING_RS_VANDERMONDE          = 4,
   ///     FFV2_ENCODING_MIRRORED                = 5
   /// };
~~~
{: #fig-ffv2_coding_type4 title="The coding type"}

The ffv2_coding_type4 (see {{fig-ffv2_coding_type4}}) encompasses
a new IANA registry for 'Flexible File Version 2 Layout Type Erasure Coding
Type Registry'.  I.e., instead of defining a new Layout Type for
each erasure coding, we define a new Erasure Coding Type.  The
encoding types this document defines fall into two groups:

-  FFV2_ENCODING_PASSTHROUGH is the non-chunked, non-integrity
   on-ramp from flexible file v1 layout.  It uses NFSv3 WRITE / READ directly
   against each replica's data server.  No CHUNK_WRITE, no
   CHUNK_READ, no per-chunk CRC.  See {{sec-encoding-passthrough}}.

-  FFV2_ENCODING_MIRRORED, FFV2_ENCODING_MOJETTE_SYSTEMATIC,
   FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC, and
   FFV2_ENCODING_RS_VANDERMONDE all use the new operations
   defined here: in particular CHUNK_WRITE
   ({{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) and CHUNK_READ ({{I-D.haynes-nfsv4-flexfiles-v2-chunks}}),
   which carry the per-chunk checksum this version of the layout
   type relies on for end-to-end integrity.  The encoding type
   selects how chunks are produced from application data
   (mirrored verbatim, Reed-Solomon shards, Mojette
   projections); the wire and the storage device are the same
   in every case.

The 32-bit ffv2_coding_type4 value space is partitioned by
intended scope -- Standards Track, Experimental, Vendor (open),
and Private / proprietary -- with different allocation policies
per range, so that vendors can assign encoding values without
consuming standards-track codepoints.  See
{{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}} and the accompanying prose in
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
in the proxy-server draft
({{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}), in the
sections "Layout Shape During a Proxy Operation" and "Atomic
commit on PROXY_DONE".  This document specifies the per-mirror
encoding naming primitive; the proxy-server document specifies
the transactional machinery that uses it.

### FFV2_ENCODING_PASSTHROUGH {#sec-encoding-passthrough}

FFV2_ENCODING_PASSTHROUGH is the on-ramp from flexible file v1 layout ({{RFC8435}})
into the flexible file v2 layout type.  A PASSTHROUGH mirror points at the
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
-  The concurrent-writer disambiguation that chunk_guard4
   provides for encoded types.

PASSTHROUGH is RECOMMENDED for the assimilation, migration, and
heterogeneous-mirror use cases described in
{{sec-heterogeneous-mirrors}}.  New deployments that do not
need a flexible file v1 layout on-ramp SHOULD use FFV2_ENCODING_MIRRORED for
the integrity guarantees described in
{{sec-encoding-mirrored}}.

### FFV2_ENCODING_MIRRORED {#sec-encoding-mirrored}

FFV2_ENCODING_MIRRORED is the chunked-with-integrity peer of
PASSTHROUGH.  The chunk produced for each replica is the
application data verbatim -- no transform, no parity shards --
but it travels on the wire and is stored on the data server
through CHUNK_WRITE / CHUNK_READ and so carries every integrity
property the encoded coding types carry.

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
   by the client over the chunk payload, sent on the wire with
   the chunk, recomputed by the data server before storing,
   and recomputed again from disk by the data server on every
   CHUNK_READ.  Wire-level bit flips are caught before the
   chunk is stored; on-disk bit rot is caught the next time
   the chunk is read.
-  Per-chunk repair granularity.  When one replica's CRC fails
   to verify and another replica's verifies, the repair unit
   is the chunk, not the file: CHUNK_READ the good replica,
   CHUNK_WRITE to the bad replica, done.  No whole-file
   resilvering is required.
-  Per-chunk concurrent-writer disambiguation.  Mirrored
   writes carry the same chunk_guard4 ({{I-D.haynes-nfsv4-flexfiles-v2-chunks}})
   the erasure coding types do.  Two clients racing to write
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
layout segment (see {{sec-CSM}}) and rely on the metadata
server or a peer data server to propagate the update to the
remaining mirrors.  When unset, the client MUST update all
mirrors.

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

The ffv2_file_info4 is a new structure to help with the stateid
issue discussed in Section 5.1 of {{RFC8435}}.  I.e., in version 1
of the Flexible File Version 2 Layout Type, there was the singleton ffv2ds_stateid
combined with the ffv2ds_fh_vers array.  I.e., each NFSv4 version
has its own stateid.  In {{fig-ffv2_file_info4}}, each NFSv4
filehandle has a one-to-one correspondence to a stateid.

## ffv2_ds_flags4 {#sec-ffv2_ds_flags4}

~~~ xdr
   /// const FFV2_DS_FLAGS_ACTIVE        = 0x00000001;
   /// const FFV2_DS_FLAGS_SPARE         = 0x00000002;
   /// const FFV2_DS_FLAGS_PARITY        = 0x00000004;
   /// const FFV2_DS_FLAGS_REPAIR        = 0x00000008;
   /// const FFV2_DS_FLAGS_PROXY         = 0x00000010;
   /// typedef uint32_t            ffv2_ds_flags4;
~~~
{: #fig-ffv2_ds_flags4 title="The ffv2_ds_flags4" }

The ffv2_ds_flags4 (in {{fig-ffv2_ds_flags4}}) flags details the
state of the data servers.  With erasure coding algorithms, there
are both Systematic and Non-Systematic approaches.  In the Systematic,
the bits for integrity are placed amongst the resulting transformed
chunk.  Such an implementation would typically see FFV2_DS_FLAGS_ACTIVE
and FFV2_DS_FLAGS_SPARE data servers.  The FFV2_DS_FLAGS_SPARE ones
allow the client to repair a payload without engaging the metadata
server.  I.e., if one of the FFV2_DS_FLAGS_ACTIVE did not respond
to a CHUNK_WRITE, the client could fail the chunk to the
FFV2_DS_FLAGS_SPARE data server.

With the Non-Systematic approach, the data and integrity live on
different data servers.  Such an implementation would typically see
FFV2_DS_FLAGS_ACTIVE and FFV2_DS_FLAGS_PARITY data servers.  If the
implementation wanted to allow for local repair, it would also use
FFV2_DS_FLAGS_SPARE.

The FFV2_DS_FLAGS_REPAIR flag informs the client that the
indicated data server is a replacement for a previously failed
ACTIVE data server, whose content has been (or is being)
reconstructed from the surviving shards of the mirror set.  A
REPAIR data server differs from a SPARE in two ways:

-  A SPARE is standing by with no payload; the client MAY fail
   over to it at write time without metadata-server coordination.
-  A REPAIR has been promoted by the metadata server to replace a
   failed ACTIVE, and its payload was placed there by a repair
   client executing the flow in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}} rather
   than directly by the original writer.  The flag is the
   client's indication that reads from this data server return
   erasure-decoded content rather than content produced by the
   original write.

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

The FFV2_DS_FLAGS_PROXY flag identifies a data-server entry
that names a Proxy Server rather than a real storage device.
A client whose local encoding capabilities cannot cover the
file's mirror set receives a layout in which one or more
mirror entries have FFV2_DS_FLAGS_PROXY set on their
ffv2_data_server4; the client directs I/O for that mirror
to the proxy, which translates on behalf of the client.  The
Proxy Server protocol itself is specified in
{{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}; this
document defines only the layout-flag surface (this bit) that
lets the metadata server mark a data-server entry as
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
uniformly to all coding types:

| Protection Mode | fdp_data | fdp_parity | Total DSes | Description |
|---
| Mirroring (3-way) | 1 | 2 | 3 | 3 copies, no encoding |
| Striping (6-way) | 6 | 0 | 6 | Parallel I/O, no redundancy |
| RS Vandermonde 4+2 | 4 | 2 | 6 | Tolerates 2 DS failures |
| Mojette-sys 8+2 | 8 | 2 | 10 | Tolerates 2 DS failures |
{: #fig-protection-examples title="Example data protection configurations" }

By expressing all protection modes as (fdp_data, fdp_parity) pairs,
a single structure serves mirroring, striping, and all erasure
coding types.  The coding type ({{fig-ffv2_coding_type4}}) determines
how the shards are encoded; the protection structure determines
how many shards there are.

The total number of data servers required is fdp_data + fdp_parity.
The storage overhead is fdp_parity / fdp_data (e.g., 50% for 4+2,
25% for 8+2).

## ffv2_coding_type_data4

~~~ xdr
   /// union ffv2_coding_type_data4 switch
   ///         (ffv2_coding_type4 fctd_coding) {
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
the data protection geometry for the layout.  All coding types carry an
ffv2_data_protection4 ({{fig-ffv2_data_protection4}}) specifying the
number of data and parity shards.  The coding type enum determines how
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

-  Erasure coding types (FFV2_ENCODING_RS_VANDERMONDE,
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

## ffv2_mirror4 {#sec-ffv2-mirror4}

~~~ xdr
   /// /* Shadow typedef; canonical definition and semantics live
   ///  * in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.  Duplicated
   ///  * here so this document's XDR extract is self-contained. */
   /// typedef uint32_t   checksum_algorithm4;
   ///
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

The ffv2_mirror4 (in {{fig-ffv2_mirror4}}) describes the Flexible
File Layout Version 2 specific fields.

The ffv2m_checksum_algorithm field names the checksum
algorithm the client MUST use when computing
cwa_checksums on CHUNK_WRITE and cwra_checksums on
CHUNK_WRITE_REPAIR, and the algorithm the client MUST
expect in cr_checksum on CHUNK_READ responses, for chunks
in this mirror.  The metadata server picks the algorithm
at LAYOUTGET time; the value is one of the registered
checksum_algorithm4 codes (see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}).
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
cg_client_id field of chunk_guard4 (see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}) in
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
   tiebreaker for racing writers (see {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}),
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
{: #fig-parallel-filesystem title="The Relationship between MDS and DSes"}

As shown in {{fig-parallel-filesystem}} if the ffv2m_coding_type_data
is FFV2_ENCODING_PASSTHROUGH or FFV2_ENCODING_MIRRORED, then
each of the stripes MUST only have 1 storage device.  I.e.,
the length of ffv2s_data_servers MUST be 1.  The erasure-coding
encoding types (FFV2_ENCODING_MOJETTE_SYSTEMATIC,
FFV2_ENCODING_MOJETTE_NON_SYSTEMATIC,
FFV2_ENCODING_RS_VANDERMONDE) distribute shards across multiple
storage devices and so carry multiple entries in
ffv2s_data_servers.

The abstraction here is that for FFV2_ENCODING_PASSTHROUGH and
FFV2_ENCODING_MIRRORED, each stripe describes exactly one data
server.  And for the erasure-coded encoding types, each of the
stripes describes a set of data servers to which the shards are
distributed.  Further, the payload length can be different per
stripe.

## ffv2_layouthint4 {#sec-ffv2-layouthint}

~~~ xdr
   /// struct ffv2_layouthint4 {
   ///     ffv2_coding_type4       ffv2lh_supported_types<>;
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
metadata server MAY honour any subset and MAY override any of
them per administrative policy.

ffv2lh_supported_types

:  An ordered list of coding types the client supports,
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
(fdp_data=1, fdp_parity=2) for 3-way flexible file v1 layout-
compatible mirroring without per-chunk integrity.

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

Because the coding-type registry is expected to grow over time
(new erasure coding types are added, older ones fall out of favour,
vendors register private codes; see {{iana-considerations}}),
neither clients nor metadata servers are required to implement
every registered encoding.  The protocol uses ffv2_layouthint4 as
the negotiation surface:

Client-side advertisement:
:  A client that wishes to influence encoding selection SHOULD
   send the set of encodings it actually implements in
   ffv2lh_supported_types.  A client MUST NOT claim support for
   an encoding it cannot encode or decode: a false advertisement
   produces silent data unavailability when the resulting layout
   is issued.

Metadata-server selection:
:  The metadata server SHOULD select an encoding from the client's
   ffv2lh_supported_types list when the server's policy permits.
   The server MAY override the hint when its policy dictates a
   specific encoding (for example, per-export objectives); in that
   case the server issues a layout with the policy-dictated
   encoding and the client MUST either honour it or fail its I/O
   with NFS4ERR_CODING_NOT_SUPPORTED.

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
       behalf (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}} for the MDS-I/O
       fallback).  This is correct but serializes all I/O for
       the encoding-ignorant client through a single actor.

   3.  Route the client through a **translating proxy** that
       understands both the file's native encoding and an encoding
       the client does support.  The metadata server issues a layout with
       the proxy's data-server entry carrying
       FFV2_DS_FLAGS_PROXY and a coding_type the client does
       support (typically FFV2_ENCODING_MIRRORED for a minimal
       NFSv4.2 client, or FFV2_ENCODING_PASSTHROUGH / a flat
       NFSv3 surface for an NFSv3 client).  The proxy encodes
       and decodes on the fly
       against the real data servers.  This preserves parallel I/O
       for the encoding-ignorant client that the MDS-I/O
       fallback loses.  The proxy registration, directive, and
       credential-forwarding rules are defined in the
       {{?I-D.haynes-nfsv4-flexfiles-v2-proxy-server}}; this draft defines only
       the layout-flag surface (FFV2_DS_FLAGS_PROXY in
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
per-request negotiation surface; adding a session-level
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
are in ffda_versions.  Each element of the array corresponds to a
particular combination of ffdv_version, ffdv_minorversion, and
ffdv_tightly_coupled provided for the device.  The array allows for
server implementations that have different filehandles and stateids
for different combinations of version, minor version, and coupling
strength.  See {{sec-version-errors}} for how to handle versioning
issues between the client and storage devices.

For tight coupling, ffv2fi_stateid provides the stateid to be used
by the client to access the file.  The metadata server registers
ffv2fi_stateid with each tight-coupling-capable storage device via
TRUST_STATEID (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}}) before returning
the layout; the storage device validates subsequent CHUNK operations
against its trust table.

For loose coupling and an NFSv4 storage device, the client MUST use
the anonymous stateid to perform I/O on the storage device, because
the metadata server stateid has no meaning to a storage device that
is not participating in the control protocol.  In this case the
metadata server MUST set ffv2fi_stateid to the anonymous stateid.

For an NFSv3 storage device (ffdv_version = 3), the tight-coupling
model does not apply: {{sec-ff_device_addr4}} requires
ffdv_tightly_coupled to be FALSE whenever ffdv_version equals 3,
because NFSv3 has no wire encoding for stateids.  The corresponding
ffv2fi_stateid element in the ffv2ds_file_info array MUST therefore
be the anonymous stateid and is unused; an NFSv3 data server uses
the synthetic-uid fencing model (see {{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}})
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
is, if ffdv_tightly_coupled (see {{sec-ff_device_addr4}}) is set,
then the client MUST ignore both ffv2ds_user and ffv2ds_group.

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

The prior draft's "the flag functions as a hint" language is
withdrawn; the encoding-negotiation fallback path that requires
MDS I/O to be possible is served by the metadata server clearing
NO_IO_THRU_MDS on the fallback layout, not by clients ignoring
the flag on a NO_IO_THRU_MDS layout.

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
multiple mirrored instances, each with a different ff_device_addr4.
The client can then determine that, since each of the ffv2fi_fh_vers
values within ffv2ds_file_info are different, there are multiple
copies of the file for the current layout segment available.

##  Handling Version Errors {#sec-version-errors}

When the metadata server provides the ffda_versions array in the
ff_device_addr4 (see {{sec-ff_device_addr4}}), the client is able
to determine whether or not it can access a storage device with any
of the supplied combinations of ffdv_version, ffdv_minorversion,
and ffdv_tightly_coupled.  However, due to the limitations of
reporting errors in GETDEVICEINFO (see Section 18.40 in {{RFC8881}}),
the client is not able to specify which specific device it cannot
communicate with over one of the provided ffdv_version and
ffdv_minorversion combinations.  Using ffv2_ioerr4 ({{sec-ffv2_ioerr4}})
inside either the LAYOUTRETURN (see Section 18.44 of {{RFC8881}})
or the LAYOUTERROR (see Section 15.6 of {{RFC7862}} and {{sec-LAYOUTERROR}}
of this document), the client can isolate the problematic storage
device.

The error code to return for LAYOUTRETURN and/or LAYOUTERROR is
NFS4ERR_MINOR_VERS_MISMATCH.  It does not matter whether the mismatch
is a major version (e.g., client can use NFSv3 but not NFSv4) or
minor version (e.g., client can use NFSv4.1 but not NFSv4.2), the
error indicates that for all the supplied combinations for ffdv_version
and ffdv_minorversion, the client cannot communicate with the storage
device.  The client can retry the GETDEVICEINFO to see if the
metadata server can provide a different combination, or it can fall
back to doing the I/O through the metadata server.

#  Striping {#sec-striping}

The flexible file v2 layout version 2 inherits the dense and
sparse striping dispositions defined by the file layout type in
Section 13.4 of {{RFC8881}}.  The disposition for a given
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

Although the client implementation has the option to propagate a
corresponding error to the application that initiated the I/O
operation and drop any unwritten data, the client should attempt
to retry the original I/O operation by either requesting a new
layout or sending the I/O via regular NFSv4.1+ READ or WRITE
operations to the metadata server.  The client SHOULD attempt to
retrieve a new layout and retry the I/O operation using the storage
device first and only retry the I/O operation via the metadata
server if the error persists.

#  Client-Side Mirroring {#sec-CSM}

The flexible file v2 layout has a simple model in place for the
mirroring of the file data constrained by a layout segment.  There
is no assumption that each copy of the mirror is stored identically
on the storage devices.  For example, one device might employ
compression or deduplication on the data.  However, the over-the-wire
transfer of the file contents MUST appear identical.  Note, this
is a constraint of the selected XDR representation in which each
mirrored copy of the layout segment has the same striping pattern
(see {{fig-parallel-filesystem}}).

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
the layout.  Thus, the metadata server MUST update that copy until
the client is presented it in a layout.  If the FF_FLAGS_WRITE_ONE_MIRROR
is set in ffv2l_flags, the client need only update one of the mirrors
(see {{sec-write-mirrors}}).  If the client is writing to the layout
segments via the metadata server, then the metadata server MUST
update all copies of the mirror.  As seen in {{sec-mds-resilvering}},
during the resilvering, the layout is recalled, and the client has
to make modifications via the metadata server.

##  Selecting a Mirror {#sec-select-mirror}

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

##  Writing to Mirrors {#sec-write-mirrors}

###  Single Storage Device Updates Mirrors

If the FF_FLAGS_WRITE_ONE_MIRROR flag in ffv2l_flags is set, the
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

###  Client Updates All Mirrors

If the FF_FLAGS_WRITE_ONE_MIRROR flag in ffv2l_flags is not set, the
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

###  Handling Write Errors {#sec-write-errors}

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

###  Handling Write COMMITs {#sec-write-commits}

When stable writes are done to the metadata server or to a single
replica (if allowed by the use of FF_FLAGS_WRITE_ONE_MIRROR), it
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

##  Metadata Server Resilvering of the File {#sec-mds-resilvering}

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
request with an NFS4ERR_LAYOUTUNAVAILABLE.  The client would then
have to perform the I/O through the metadata server.

# Comparison of Encoding Types

| Property | Reed-Solomon | Mojette Systematic | Mojette Non-Systematic |
|---
| MDS guarantee | Yes | Yes (Katz) | Yes (Katz) |
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

#  Flexible File Version 2 Layout Type Return

layoutreturn_file4 is used in the LAYOUTRETURN operation to convey
layout-type-specific information to the server.  It is defined in
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
suggested.  For example, a client can define the default byte-range
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
which provides coding type selection and data protection geometry
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
in {{I-D.haynes-nfsv4-flexfiles-v2-chunks}}.  Further, this support is orthogonal to the
Erasure Coding Type selected.  The data server is unaware of which type
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


# IANA Considerations

This document registers the following in the "pNFS Layout Types"
registry established by {{RFC8881}}:

 | Layout Type Name      | Value | RFC      | How | Minor Versions |
 |---
 | LAYOUT4_FLEX_FILES_V2 | 0x6   | RFCTBD10 | L   | 1              |
{: #tbl_layout_types title="Layout Type Assignments"}

This document registers the following in the "NFSv4 Recallable
Object Types" registry established by {{RFC8881}}:

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

NFSv4 attribute numbers are governed by the publishing
standards-track document ({{RFC7862}} assigned attributes 77-84;
subsequent extensions have assigned above 84 by publishing
document, not by IANA action; no "NFSv4.2 Attributes" IANA
registry exists to assign attribute numbers).  This document
therefore assigns -- rather than requests IANA to assign -- the
following new NFSv4.2 attribute:

- Attribute 89: fattr4_coding_block_size

The reference is this document.  No IANA action is required for
this assignment.

This document registers the following in the "Flexible File
Version 2 Layout Type Erasure Coding Type Registry" established
by {{I-D.haynes-nfsv4-flexfiles-v2-encoding-registry}}:

| Encoding Type Name | Value | RFC | How | Minor Versions |
| ---
| FFV2_ENCODING_PASSTHROUGH | 1 | RFCTBD10 | L | 2 |
| FFV2_ENCODING_MIRRORED    | 5 | RFCTBD10 | L | 2 |

# Security Considerations

The trust-stateid security considerations of
{{I-D.haynes-nfsv4-flexfiles-v2-trust-stateid}} and the
chunk-level security considerations of
{{I-D.haynes-nfsv4-flexfiles-v2-chunks}} apply to any
deployment using this layout type.

# Acknowledgments
{:numbered="false"}

See the Acknowledgments section of
{{I-D.haynes-nfsv4-flexfiles-v2-requirements}}.

--- back
