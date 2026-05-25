# Layout Affinity: Detecting Client / Data-Server Colocation

## Background

When a pNFS client (which in flexible file v2 may be a Proxy Server) is
running on the same physical machine -- more precisely, the same
kernel instance -- as a data server it is about to do I/O against,
the network stack is pure overhead.  AF_UNIX sockets, shared memory,
splice / sendfile zero-copy, and other local-IPC mechanisms can move
the bytes without the TCP / TLS / RPC machinery.  At Hammerspace's
deployment scale this is load-bearing: clients, Proxy Servers, and
data servers routinely share physical infrastructure, and skipping
the network stack saves both bandwidth and latency in a way the cost
model depends on.

The protocol gap: there is no standard mechanism in NFSv4.2 to detect
this colocation.  The current Hammerspace approach embeds a sentinel
value in `eir_server_owner` / `eia_client_owner` at EXCHANGE_ID, which
overloads NFSv4.1 identity fields with locality-routing information.
It works but is fragile -- those fields have their own RFC 8881
semantics (client / server identity matching for state recovery),
and locality routing is not what they are for.

This note records the design of a clean alternative.  It is parked,
not implemented.  Pick it up when the v2 layout type is closer to
adoption and we have implementation experience from at least the
reffs prototype.

## Granularity

"Same machine" has three plausible meanings:

| Granularity | Containers (shared host kernel) | VMs (same host, different kernels) | What bypass it enables |
|-------------|---------------------------------|------------------------------------|------------------------|
| Same kernel | yes | no | AF_UNIX, shared memory, splice / sendfile, kernel-direct |
| Same physical host | yes | yes | Loopback RDMA, NUMA-aware placement |
| Same cluster / rack | yes | yes | Topology hints only |

For NFS byte-level data-path bypass, **same kernel** is the correct
granularity.  Shared-memory IPC and AF_UNIX require shared kernel;
same-host-but-different-VM gives you nothing for byte-level bypass.

On Linux that maps to `/etc/machine-id` (kernel-instance-stable,
shared by all containers running on that kernel, not shared across
VMs).  Equivalent identifiers exist on FreeBSD (`kern.hostuuid`),
Solaris (hostid), etc.  The wire form is opaque; comparators do
byte-equality.

## Why ffv2_key4 doesn't fit

The `ffv2_key4` typedef and the `ffm_key` field in `ffv2_mirror4`
were initially defined with no concrete protocol semantics ("opaque
64-bit identifier used to associate a mirror instance with its
backing storage key").  reffs has the field commented out.

Salvaging it for the colocation key would put the locality identifier
at the wrong granularity.  `ffm_key` is per-mirror; a mirror's
`ffs_data_servers<>` is a list and a striped mirror can have data
servers on different physical machines.  A single per-mirror key
cannot represent "machine A for stripe 0, machine B for stripe 1".
The locality identifier needs to be per data server.

`ffv2_key4` was removed from the v2 draft pending a real use case
for a per-mirror opaque key.  The colocation use case is per-DS, not
per-mirror.

## Client-side bypass needs no on-wire mechanism

The client can detect colocation locally without any protocol
field.  Three ways, all of which work without spec changes:

1. **IP-is-mine.**  Client resolves the DS address from the layout
   and checks against its own bound interfaces.  Catches loopback,
   shared-net-namespace, and same-host-with-public-IP cases.
2. **Local socket probe.**  Try a well-known Unix-socket path
   keyed by deviceid; if it accepts, you are local.
3. **Operator configuration.**  The deployment declares which
   dstores are local.  reffs's dstore vtable selection
   (`dstore_ops_local` vs `dstore_ops_nfsv3` / `dstore_ops_nfsv4`)
   is exactly this.

For any of those, the client's OS already knows the answer.
Publishing the DS machine_id to the client via the layout or
deviceinfo would be dead weight.

## The use case that does need a wire mechanism: MDS layout optimization

The MDS, when granting a read layout, can prefer mirrors whose data
servers are colocated with the requesting client.  For erasure-coded
layouts the optimization is particularly valuable: a client reads K
of K+M shards, and routing K shard reads through local IPC instead
of TCP saves the network cost of K paths.

For this the MDS needs the (client_machine_id, ds_machine_id) matrix.
The MDS learns each by being told.

The optimization is **reads only**.  Writes to a mirror set must
reach every mirror regardless of locality, so there is nothing to
optimize.  Pure-write layouts use the matrix not at all.

## Proposed wire mechanism: MACHINE_ID_ANNOUNCE

One new minor op, used in both directions:

~~~ xdr
struct MACHINE_ID_ANNOUNCE4args {
    opaque  mia_machine_id<MACHINE_ID_MAXLEN>;
};
~~~

`MACHINE_ID_MAXLEN` is something modest, on the order of 64 bytes:
room for a raw /etc/machine-id (32 hex chars), a SHA-256 hash, or a
deployment-scoped randomized identifier, plus some headroom.

**Sentinel for opt-out**: `mia_machine_id<>` of length zero.  Means
"I am not publishing a machine_id; do not include me in colocation
optimization."  Both client and DS independently choose to
participate; a participant that never calls MACHINE_ID_ANNOUNCE, or
calls it with the sentinel, opts out.

**Where each direction lives**:

- **DS → MDS**: on the tight-coupling control session (the session
  the DS opens to the MDS at registration, per
  `sec-tight-coupling-control-session` in the v2 draft).
- **Client → MDS**: on the fore-channel session, any time after
  EXCHANGE_ID.

The receiving end records the most recent announcement per session.
Re-announcing with the sentinel withdraws.

## Where the MDS uses it

At LAYOUTGET time for LAYOUTIOMODE4_READ (and the read portion of
LAYOUTIOMODE4_RW where the MDS can express ordering):

- For mirrored layouts: prefer the mirror whose data servers'
  machine_ids match the requesting client's machine_id.  If
  multiple mirrors qualify, pick by other policy (load, recent
  health, etc.); ties broken arbitrarily.
- For striped layouts (RS / Mojette): if there are multiple
  candidate data server sets that can satisfy the K-of-K+M read,
  prefer the set with the most matches against the client's
  machine_id.

For LAYOUTIOMODE4_RW the matrix is consulted only for the read
shape of the layout; write semantics are unchanged.

## Reads-only and writes-not

Mirror writes hit every mirror.  EC writes hit every shard.  There
is no read-time choice to optimize on the write path.  This is a
clean scope boundary: the mechanism affects mirror ordering at
LAYOUTGET only.

## Security considerations

Five points the spec text would need to address:

**Privacy.**  machine_id is a fingerprinting identifier.  The wire
form is opaque; implementations MAY publish raw `/etc/machine-id`,
a stable hash of it, a deployment-scoped randomly-generated
identifier, or any other byte string.  Operators concerned about
cross-deployment fingerprinting SHOULD use a deployment-scoped
scheme.  The protocol's only requirement is stability across the
lifetime of the announcing entity and byte-wise comparability
between participants in the same deployment.

**Opt-in.**  Both client and DS choose to participate.  A
participant that does not call MACHINE_ID_ANNOUNCE, or calls it
with the sentinel, opts out.  The MDS treats opt-out participants
as non-colocatable for optimization purposes.  No protocol penalty
for opting out; the only effect is loss of read-layout
optimization for that participant.

**Spoofing.**  A malicious DS could announce a machine_id matching
a target client's machine_id, hoping to be selected as the
preferred read mirror.  The client then takes a bypass path
expecting local IPC.  The client's defense is the local-detection
check itself: before depending on a bypass path the client MUST
verify the path is locally reachable (the IP is on a local
interface, the Unix socket path exists and accepts, etc.).  If
verification fails, fall back to network I/O.  The DS's
announcement biases MDS mirror ordering only; it does not commit
the client to anything.

The reverse spoof (client announces a fake machine_id) costs the
attacker nothing they could not already obtain by reading from any
mirror at network speed.

**Granularity mismatch.**  If client and DS use different
machine_id derivations (e.g., client publishes raw `/etc/machine-id`,
DS publishes a hash of it), the MDS sees no match and produces no
optimization.  Behavior degrades gracefully; no correctness risk.
Deployments concerned about consistency SHOULD standardize on one
derivation across all participants.

**Stability.**  machine_id is stable across DS process restart
(same kernel instance), across container restart (assuming the
container's `/etc/machine-id` is sourced from the host), and
typically across kernel reboot (`/etc/machine-id` is persisted to
disk).  machine_id changes when the underlying kernel instance is
re-imaged or replaced.  The MDS does not need to invalidate state
on machine_id change; the next MACHINE_ID_ANNOUNCE supersedes the
previous record.

## How reffs's existing local detection fits

reffs already distinguishes local from remote dstores via operator
configuration: TOML declares each `[[data_server]]` as either local
(uses `dstore_ops_local` vtable, direct VFS access) or remote (uses
`dstore_ops_nfsv3` or `dstore_ops_nfsv4` vtable, RPC).  The selection
happens at startup.  See `.claude/design/mds.md` and
`.claude/design/dstore-vtable-v2.md` in the reffs repository.

That configuration approach is the client-side bypass mechanism --
it requires no protocol surface.  MACHINE_ID_ANNOUNCE coexists
without conflict: reffs's per-deployment configuration handles the
"I am the client, am I local to this DS" question; the new op
handles the "MDS, please prefer co-located mirrors for this client
in future layout grants" question.  The two solve different
problems.

A future reffs implementation could implement MACHINE_ID_ANNOUNCE
by reading the OS-provided machine identifier
(`/etc/machine-id` on Linux) and announcing it on session
setup.  No additional configuration would be required from the
operator; the operator's existing dstore-vtable choice remains the
authoritative local-vs-remote decision.

## Action plan (deferred)

When this is picked up:

1. Done.  `ffv2_key4` and `ffm_key` removed from the v2 draft.
2. Define `MACHINE_ID_ANNOUNCE` op (op number TBD, somewhere in the
   FFv2 range or alongside the TRUST_STATEID family).
3. Add a paragraph in the v2 draft describing the MDS
   read-layout-optimization use, opt-in semantics, and sentinel.
4. Add the five security paragraphs above to the Security
   Considerations section.
5. Add a sub-section to the implementation status notes about
   reffs's existing operator-config local detection and how
   MACHINE_ID_ANNOUNCE would compose with it.

Not for the v2 draft right now: the wire mechanism, until the
v1 / v2 / ECv1 layout-type split is settled and the MDS-side
layout-optimization code has a place to land.

## Related work

- RFC 8881 `eir_server_owner` / `eia_client_owner` -- what the
  current Hammerspace approach overloads.  Not modified by this
  proposal.
- `eir_server_impl_id` / `eia_client_impl_id` -- could carry
  machine_id if a new op is unacceptable, but overloads the
  implementation-id slot.  Less clean than a dedicated op.
- pNFS layout-iomode-aware mirror selection -- existing
  per-iomode behavior on the MDS side.  MACHINE_ID_ANNOUNCE is a
  new input to that selection, not a replacement.
- Linux's `IPPROTO_TCP` `TCP_REPAIR` and similar same-host
  optimizations -- the local IPC mechanisms a bypass would use,
  none of which require NFS protocol participation.
