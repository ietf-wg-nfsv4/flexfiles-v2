# TRUST_STATEID / REVOKE_STATEID: Tight Coupling for NFSv4.2 DSes

## Background

Flex Files (both v1 and v2) has two coupling models for DS access:

**Loosely coupled**: the client uses the anonymous stateid for all I/O,
presenting `ffds_user`/`ffds_group` via AUTH_SYS.  The DS validates
AUTH_SYS credentials against the DS file's owner.  Fencing (rotating
uid/gid on the DS file) is the only revocation mechanism.  This works
with any NFSv3 or NFSv4.2 DS.

**Tightly coupled**: the client uses a registered stateid for all I/O.
The DS validates the stateid against a per-file trust table populated
by the MDS via a control-plane op.  `ffdv_tightly_coupled = true` in
the device address signals to the client that tight coupling is in use.
This is the model TRUST_STATEID implements.

For v1, the DSes are off-the-shelf NFSv3 servers with no stateid
support; only loose coupling is possible.  For v2, the DSes are
NFSv4.2 servers and either model is available.  TRUST_STATEID is the
mechanism that makes tight coupling practical for v2.

## Kerberos Gap in Flex Files v1

Flex files v1 layouts carry only `ffds_user`/`ffds_group` (POSIX
uid/gid for AUTH_SYS).  If a DS export requires Kerberos, the client
cannot present the synthetic credentials -- AUTH_SYS is refused.
There is no mechanism in v1 for the MDS to convey "I have already
authenticated this client as `alice@REALM`; trust her" to the DS.

The common workaround is to configure the DS export to accept AUTH_SYS
from the MDS subnet for data access, with Kerberos only for the control
plane.  This is not Kerberos-secured I/O -- it is network-level trust.
A strict Kerberos environment (no AUTH_SYS permitted) cannot use flex
files v1 for the data path.

Flex files v2 with TRUST_STATEID and `tsa_principal` closes this gap.

## Problem

With loose coupling (anonymous stateid + AUTH_SYS), the authorization
chain is:

```
client I/O --> anonymous stateid (bypasses DS stateid check)
           --> AUTH_SYS(ffds_user, ffds_group) --> file mode check
```

The DS has no way to verify independently that the client's layout is
still valid.  Revocation requires the MDS to fence the DS file
out-of-band (uid/gid rotation + chmod).  This is operationally fragile:
if fencing fails (DS unreachable), the client retains access
indefinitely until the DS file is corrected manually.

## Proposal: TRUST_STATEID

TRUST_STATEID is a new MDS-to-DS control-plane op that registers a
layout stateid with the DS, enabling tight coupling.  It is sent by the
MDS on its own DS control session; the DS MUST reject TRUST_STATEID
from any connection that did not present `EXCHGID4_FLAG_USE_PNFS_MDS`
at EXCHANGE_ID time.

TRUST_STATEID operates on the current filehandle (set by PUTFH in the
compound).

```
TRUST_STATEID4args {
    stateid4      tsa_layout_stateid;  /* layout stateid granted by MDS */
    layoutiomode4 tsa_iomode;          /* LAYOUTIOMODE4_READ or _RW */
    nfstime4      tsa_expire;          /* expiry time -- see Lease section */
    utf8str_cs    tsa_principal;       /* client's authenticated identity;
                                        * "" for AUTH_SYS or TLS clients */
};

TRUST_STATEID4res {
    nfsstat4  tsr_status;
};
```

`tsa_principal` is the client's GSS display name as authenticated to
the MDS at LAYOUTGET time (e.g., `alice@REALM` for Kerberos).  The
empty string means no principal binding: the DS validates the stateid
but does not check the caller's identity.  For AUTH_SYS and TLS
clients this is appropriate -- AUTH_SYS provides uid/gid, and TLS
provides machine-level authentication at the transport layer.

### Capability discovery

The MDS probes whether the DS supports TRUST_STATEID during session
setup, before any runway or layout work:

```
SEQUENCE + PUTROOTFH + TRUST_STATEID(anon_stid, LAYOUTIOMODE4_READ,
                                     expire=0, principal="")
```

The anonymous stateid (`{seqid=0, other=all-zeros}`) is a special
stateid.  The root filehandle is a directory; directories never have
layout stateids.  A correctly implemented DS returns:

- `NFS4ERR_NOTSUPP` -- op not implemented; MDS uses loose coupling
  (anonymous stateid + fencing) for this DS.
- `NFS4ERR_INVAL` -- op implemented; anonymous stateid or directory
  FH correctly rejected.  MDS uses tight coupling for this DS.

`NFS4_OK` on a probe with an anonymous stateid is a DS bug.  The MDS
SHOULD log the anomaly and treat it as `NFS4ERR_INVAL` (support
confirmed) to avoid degrading to the less secure loose coupling model.

The capability is recorded per-dstore.  The MDS sets
`ffdv_tightly_coupled = true` in the `ff_device_versions4` for this DS
when the probe confirms support.  The client reads `ffdv_tightly_coupled`
from GETDEVICEINFO and knows to present the layout stateid (not the
anonymous stateid) in CHUNK_WRITE and other data-path ops.

### Compound placement

```
SEQUENCE + PUTFH(ds_file_fh) + TRUST_STATEID(layout_stid, iomode, ...)
```

TRUST_STATEID is sent on the MDS-to-DS control session
(`EXCHGID4_FLAG_USE_NON_PNFS` from the MDS's perspective).  It is
not callable by pNFS clients.

### Flow (AUTH_SYS or TLS)

1. At session setup the MDS probes TRUST_STATEID on the root FH.
   If `NFS4ERR_INVAL`, tight coupling is available for this DS.
2. Client calls LAYOUTGET on the MDS.
3. MDS fans out TRUST_STATEID to each DS in the mirror set with
   `tsa_principal = ""`.
4. DS stores the trusted stateid in its per-file trust table.
5. MDS returns the layout with `ffdv_tightly_coupled = true`.
6. Client sends CHUNK_WRITE (or READ/WRITE) to the DS using the
   real layout stateid.
7. DS validates: is this stateid in the trust table and not expired?
   If yes, I/O is authorized.

### Flow (Kerberos / RPCSEC_GSS)

1. Same capability probe at session setup.
2. Client calls LAYOUTGET on the MDS, authenticated as `alice@REALM`.
3. MDS fans out TRUST_STATEID with `tsa_principal = "alice@REALM"`.
4. DS stores the trusted stateid bound to `alice@REALM`.
5. MDS returns the layout with `ffdv_tightly_coupled = true`.
6. Client independently obtains a Kerberos service ticket for
   `nfs/ds-host@REALM` from the KDC.  The KDC must have a keytab
   for each DS service principal before this flow is possible.
7. Client establishes an RPCSEC_GSS session with the DS and sends
   CHUNK_WRITE using the real layout stateid.
8. DS validates two conditions:
   a. The stateid is in the trust table and not expired.
   b. The caller's authenticated identity matches `tsa_principal`.
   Both must hold.  A rogue principal cannot use a stolen stateid,
   and a valid principal cannot access a file without a MDS-issued
   layout.

On principal mismatch the DS returns `NFS4ERR_ACCESS` -- the
identity does not have an authorized layout for this file.  This
matches the error already used for fencing (`NFS4ERR_ACCESS` or
`NFS4ERR_PERM`) and avoids the semantic confusion of `NFS4ERR_WRONGSEC`
("use a different security flavor") or `NFS4ERR_BAD_STATEID` ("invalid
stateid").

This closes the security gap in flex files v1 where Kerberos
authentication on the MDS-client channel provides no protection on the
DS-client channel.

### Client-detected trust gap

A window exists between a successful TRUST_STATEID fan-out and the
client's first I/O: network loss or a transient DS error may prevent
the DS from processing TRUST_STATEID even though the MDS considered
the fan-out complete.  The client's first I/O then receives
`NFS4ERR_BAD_STATEID` from a DS that should have the entry.

The client cannot distinguish this case from a legitimately expired or
revoked entry.  The recovery path:

1. Client sends LAYOUTERROR(layout_stateid, device_id,
   NFS4ERR_BAD_STATEID) to the MDS.
2. MDS retries TRUST_STATEID to the reporting DS.  If the retry
   succeeds, the MDS returns NFS4_OK for LAYOUTERROR.
3. Client retries I/O.  No LAYOUTRETURN is needed if the retry
   succeeds.
4. If the retry fails (DS unreachable or returns a hard error), the
   MDS issues CB_LAYOUTRECALL for that device and the client returns
   the layout segment.

This is the same LAYOUTERROR path used for NFS4ERR_ACCESS / fencing
triggers (see REVOKE_STATEID Triggers, item 2), with the action
being retry-TRUST_STATEID instead of fencing.

### TRUST_STATEID failure at LAYOUTGET time

If TRUST_STATEID fails for a DS during the LAYOUTGET fan-out:

- `NFS4ERR_DELAY` from the DS: MDS retries before completing LAYOUTGET.
- DS unreachable: MDS excludes that DS from the layout (same as
  treating it as offline for runway purposes).  If all DSes in the
  mirror set fail, LAYOUTGET returns `NFS4ERR_LAYOUTTRYLATER`.
- `NFS4ERR_NOTSUPP` (DS changed state): MDS falls back to loose
  coupling for that DS and sets `ffdv_tightly_coupled = false` in the
  device address.

Partial failure (some mirrors support TRUST_STATEID, some do not) is
permitted.  Each mirror's `ffdv_tightly_coupled` flag is set
independently.

### Lease and renewal

`tsa_expire` is set to the current time plus the MDS lease period.
The MDS MUST re-issue TRUST_STATEID for each DS before `tsa_expire`
while the layout is outstanding.  The simplest trigger: renew on each
SEQUENCE from the client that keeps the layout stateid alive, bounded
by a renewal window of `lease_period / 2`.  The MDS maintains a
per-client table of active TRUST_STATEID entries for this purpose.

If the trust entry expires on the DS before renewal (e.g., the MDS
is partitioned from the DS), the DS returns `NFS4ERR_BAD_STATEID`
to the client.  The client returns the layout to the MDS (LAYOUTRETURN)
and re-requests.

### Relationship to `ffv2ds_user` / `ffv2ds_group`

When `ffdv_tightly_coupled = true`, the client MUST ignore both
`ffv2ds_user` and `ffv2ds_group` in the layout body.  The DS file need
not be chowned to match synthetic credentials.  The DS file should be
owned by the MDS service account to prevent unauthorized direct (non-
pNFS) access, but its mode/owner/group do not need to mirror the MDS
file's metadata.

## Proposal: REVOKE_STATEID

REVOKE_STATEID is the explicit counterpart to TRUST_STATEID.  The MDS
calls it to immediately invalidate a client's access without waiting
for `tsa_expire`.  Like TRUST_STATEID, it operates on the current
filehandle and is restricted to MDS control sessions.

```
REVOKE_STATEID4args {
    stateid4  rsa_layout_stateid;  /* stateid to revoke */
};

REVOKE_STATEID4res {
    nfsstat4  rsr_status;
};
```

After a successful REVOKE_STATEID the DS removes the trust table entry.
Subsequent I/O presenting `rsa_layout_stateid` receives
`NFS4ERR_BAD_STATEID`.  In-flight I/O that arrived before the revocation
completes is allowed to finish.

### Triggers

The MDS calls REVOKE_STATEID when:

1. **CB_LAYOUTRECALL timeout** -- the client did not return the layout
   within the recall timeout.  For NFSv4.2 DSes REVOKE_STATEID
   immediately cuts off access; no uid/gid fencing needed.
2. **LAYOUTERROR with NFS4ERR_ACCESS or NFS4ERR_PERM** -- the DS
   rejected the client's I/O.  REVOKE_STATEID cleans up the now-
   invalid trust entry.  (Note: if `ffdv_tightly_coupled = false`
   for this DS, use fencing instead; REVOKE_STATEID only applies
   when tight coupling was negotiated.)
3. **Client lease expiry** -- the MDS expires the client's state.
   REVOKE_STATEID cleans up each DS trust entry immediately.
4. **Explicit LAYOUTRETURN** -- the client returned the layout cleanly.
   The MDS MAY call REVOKE_STATEID or allow the entry to expire via
   `tsa_expire`.

### Fan-out semantics

The MDS fans out REVOKE_STATEID to all DSes in the mirror set in
parallel and does not wait for all to acknowledge before completing the
recall flow.  This mirrors CB_LAYOUTRECALL semantics: the MDS marks the
layout as revoked in its own state machine when REVOKE_STATEID is sent,
not when all DSes confirm.

### Compound placement

```
SEQUENCE + PUTFH(ds_file_fh) + REVOKE_STATEID(layout_stid)
```

### Error handling

- `NFS4ERR_BAD_STATEID` -- no trust entry for this stateid (already
  expired or never registered).  The MDS treats this as success.
- `NFS4ERR_DELAY` -- DS is busy; MDS retries.
- Any other error -- MDS logs the failure.  If the DS is reachable but
  consistently returns errors, the MDS falls back to fencing (uid/gid
  rotation) as a last resort for that DS.

## Proposal: BULK_REVOKE_STATEID

BULK_REVOKE_STATEID revokes all trust entries for a given client in
a single compound, avoiding the N PUTFH + REVOKE_STATEID compounds
that per-file revocation requires when a client holds many layouts.

```
BULK_REVOKE_STATEID4args {
    clientid4  brsa_clientid;  /* revoke all stateids for this client;
                                * the special all-zeros clientid revokes
                                * the entire DS trust table */
};

BULK_REVOKE_STATEID4res {
    nfsstat4  brsr_status;
};
```

BULK_REVOKE_STATEID does not operate on the current filehandle; no
PUTFH is needed.  The compound is:

```
SEQUENCE + BULK_REVOKE_STATEID(clientid4)
```

### Triggers

1. **Client lease expiry** -- the MDS expires a client.  BULK_REVOKE
   replaces the per-file REVOKE_STATEID fan-out with a single op per DS.
2. **CB_LAYOUTRECALL LAYOUTRECALL4_ALL** -- the MDS is recalling all
   layouts for a client.  BULK_REVOKE_STATEID(clientid) is the DS-side
   complement.
3. **MDS reboot cleanup** -- after establishing new DS sessions, the
   MDS sends BULK_REVOKE_STATEID(all-zeros) to each DS to clear stale
   entries, then re-issues TRUST_STATEID as clients reclaim layouts
   during grace.  See MDS Crash Recovery below.

### Error handling

- `NFS4_OK` -- all matching entries removed.
- `NFS4ERR_DELAY` -- DS is busy; MDS retries.
- No error is returned if no entries matched the clientid (the table
  may already have been cleared by expiry or a prior BULK_REVOKE).

## DS Crash Recovery

The trust table is volatile.  After a DS restart (planned or crash),
all trust entries are lost.

The client detects DS restart via `NFS4ERR_BADSESSION` or
`NFS4ERR_STALE_CLIENTID` on its DS session.  The client returns the
affected layout to the MDS (LAYOUTRETURN) and re-requests.  The MDS
re-issues TRUST_STATEID as part of the new LAYOUTGET fan-out.  No
special notification mechanism is needed: the existing client-detected
re-layout path handles recovery.

For planned DS restarts (software upgrade, etc.), the DS SHOULD drain
in-flight CHUNK ops before shutting down.  The trust table need not be
persisted to stable storage; the re-layout path handles restoration.

## MDS Crash Recovery

When the MDS reboots, its control sessions to each DS are lost.
Trust entries on the DSes remain until `tsa_expire` but the MDS is
no longer renewing them.

The MDS SHOULD persist the set of active TRUST_STATEID entries
(clientid, stateid, DS address, expiry) to stable storage so that
on restart it knows which entries exist on each DS.  Without this,
the MDS must wait for clients to reclaim before it can re-issue
TRUST_STATEID; with it, the MDS can optionally re-issue proactively
during grace.

### DS behavior during MDS grace

When the MDS reconnects after a reboot (new EXCHANGE_ID with a new
boot epoch on the DS's client table), the DS SHOULD mark all trust
entries established by the previous MDS session as
`pending-revalidation`.  While in this state:

- I/O presenting a pending entry returns `NFS4ERR_DELAY` rather than
  `NFS4ERR_BAD_STATEID`.
- `NFS4ERR_DELAY` tells the client "retry with the same stateid" --
  the MDS is recovering and may still revalidate this entry.
- `NFS4ERR_BAD_STATEID` would instead cause the client to return the
  layout immediately, creating a thundering-herd against the MDS as
  it comes out of grace.

The client already knows that the MDS was unavailable (its MDS
session was lost and it entered RECLAIM).  `NFS4ERR_DELAY` from the
DS during this window is consistent with the client's expectation
that some operations will stall until the MDS is healthy.

### Re-authorization flow

1. MDS reconnects to each DS; sends BULK_REVOKE_STATEID(all-zeros)
   to clear the prior trust table (optional but cleaner than waiting
   for expiry).
2. MDS enters grace.  Clients reclaim layouts via LAYOUTGET.
3. For each reclaimed layout, MDS fans out TRUST_STATEID to the
   relevant DSes, reusing the same layout stateid where possible or
   issuing a new one.
4. Re-issued entries become valid; the DS clears their
   `pending-revalidation` flag.
5. Entries not re-issued (client gone, lease already expired) expire
   via `tsa_expire`.

If the MDS persisted its TRUST_STATEID table, step 1 can be skipped
and step 3 can be parallelized with grace: the MDS re-issues
TRUST_STATEID for all persisted entries immediately on reconnect,
before any client reclaims.  This minimizes the window during which
DSes return `NFS4ERR_DELAY`.

### Client already holds a stale stateid

A client may hold a layout stateid for which TRUST_STATEID was
issued before the MDS reboot.  If the DS is returning `NFS4ERR_DELAY`
(pending-revalidation), the client retries without returning the
layout.  If the entry expires before the MDS re-issues it (MDS
recovery took longer than the lease period), the DS transitions from
`pending-revalidation` to expired and returns `NFS4ERR_BAD_STATEID`.
The client then returns the layout and re-requests.  This is the
same re-layout path as DS Crash Recovery.

## TLS (RPC-over-TLS, RFC 9289)

TLS is not subject to the Kerberos gap because the trust model is
fundamentally different.  Kerberos is per-user authentication; TLS
(RFC 9289) is per-machine authentication.

With mutual TLS, the TLS handshake authenticates the client host to the
DS at the transport layer.  AUTH_SYS with the synthetic `ffds_user`/
`ffds_group` then rides over that authenticated channel.  The DS knows
the connection came from a legitimate client machine; the stateid check
confirms the MDS authorized that machine's access to this file.  No
per-user identity propagation is needed because TLS does not carry one.

For `tsa_principal`: set to the empty string for TLS clients, the same
as for plain AUTH_SYS.  The machine authentication is handled by the
TLS layer beneath the RPC, not by TRUST_STATEID.

One caveat: this reasoning applies only to mutual TLS (both peers
present and verify certificates).  Opportunistic TLS (STARTTLS without
certificate verification) provides encryption but not machine
authentication.  An opportunistic-TLS deployment has the same
authorization properties as plain AUTH_SYS and the same exposure -- the
stateid check is the only access control in play.

## Backward Compatibility

- **NFSv3 DSes**: unchanged.  Anonymous stateid + fencing (loose
  coupling) still applies.  TRUST_STATEID does not exist on NFSv3
  servers.
- **NFSv4.2 DSes, TRUST_STATEID probe returns NFS4ERR_INVAL**:
  tight coupling.  MDS calls TRUST_STATEID at LAYOUTGET time, sets
  `ffdv_tightly_coupled = true`, client uses real layout stateid.
- **NFSv4.2 DSes, TRUST_STATEID probe returns NFS4ERR_NOTSUPP**:
  loose coupling fallback.  Anonymous stateid + fencing, same as v1.

## Open Questions

1. For Kerberos clients, should the DS reject I/O on principal mismatch
   with `NFS4ERR_ACCESS` (recommended above) or is there a case where
   `NFS4ERR_WRONGSEC` is more appropriate (e.g., the client connected
   with AUTH_SYS but the trust entry has a non-empty `tsa_principal`)?

2. Renewal: should the MDS renew TRUST_STATEID on every client SEQUENCE
   (keeping DS lease in lockstep with MDS lease), or only when the
   entry is within `lease_period / 2` of expiry?  The latter reduces
   MDS-to-DS traffic but requires the MDS to track per-entry expiry
   times.

3. Should TRUST_STATEID and REVOKE_STATEID carry op numbers in the
   CHUNK op range (currently 77-87), or in a separate MDS control-plane
   range?  They are MDS-to-DS only (unlike CHUNK ops which are
   client-to-DS) and should be marked accordingly in the ops table.

4. Should MDS persistence of the TRUST_STATEID table be a MUST, SHOULD,
   or MAY?  Persistence enables proactive re-authorization after MDS
   reboot and shrinks the `NFS4ERR_DELAY` window, but it adds an
   additional crash-safe write on every TRUST_STATEID issuance and
   renewal.  The re-layout path (client returns layout, MDS re-issues)
   is correct without persistence; persistence is a latency optimization.
