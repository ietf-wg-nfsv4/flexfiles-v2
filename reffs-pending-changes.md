# reffs follow-up changes from this draft

This document records spec changes in
`draft-haynes-nfsv4-flexfiles-v2.md` that require corresponding
changes in the reffs implementation (`/Volumes/Sensitive/reffs`).
The list is kept here in the flexfiles-v2 repo rather than in the
reffs repo so that another Claude agent working in reffs does not
delete it as an unfamiliar file.

When a slice of these changes is picked up, the agent working in
reffs can be pointed at this document and instructed to apply the
corresponding edits.

The reffs repo's XDR file is at
`/Volumes/Sensitive/reffs/lib/xdr/nfsv42_xdr.x`.

## Pending change 2: normalize FFv2 field prefixes to ffv2*_

**Status: DEFERRED.  Spec change applied on flexfiles-v2.
reffs side not yet attempted; the rename is bigger and more
hazardous than the original estimate -- see Hazard note below.**

### Hazard note (discovered 2026-05-25)

The original estimate assumed the FFv1 reused structs were
cited but not full struct definitions in the reffs XDR.  In
fact reffs has its own full XDR definitions of all the FFv1
structs (ff_layout4, ff_mirror4, ff_ioerr4, ff_io_latency4,
ff_iostats4, ff_layoutreturn4, ff_layoutupdate4, etc.), and
those FFv1 struct definitions use the SAME short prefixes
(ffl_, ffm_, ffie_, ffil_, ffis_, fflr_) that the rename
intends to move on the FFv2 side.

Concretely, the FFv1 ff_layout4 and the FFv2 ffv2_layout4
both have fields ffl_mirrors / ffl_flags / ffl_stats_collect_hint.
A blanket s/ffl_/ffv2l_/g would silently break the FFv1 code
path.

C code in lib/nfs4/server/layout.c and lib/nfs4/client/
mds_layout.c handles BOTH wire formats and mixes the prefixes
inside the same file (e.g. layoutget_build_v1 vs
layoutget_build_v2 in layout.c).  The rename has to be
function-aware, sometimes line-aware.

### What the rename actually requires

1. XDR: rename only the FFv2 struct field declarations
   (lines roughly 4790-4905 in nfsv42_xdr.x), leaving the
   FFv1 struct field declarations untouched.

2. C code: for each file that references the renamed
   prefixes (lib/nfs4/server/layout.c ~45 hits, lib/nfs4/
   client/mds_layout.c ~15 hits, plus ~3 hits across
   lib/nfs4/ps/tests/ec_pipeline_stripe_test.c,
   lib/nfs4/client/ec_client.h, lib/include/reffs/super_block.h),
   read each usage and determine whether the typed object is
   ff_layout4 (keep) or ffv2_layout4 (rename).  No reliable
   automation; this is per-line inspection.

3. Generated XDR: regenerate.

4. Build verification via 'make -f Makefile.reffs ci-check'
   in Docker, iterating on compile errors -- this is the only
   safety net for the per-line judgments above.

Estimated effort: a focused half-day with Docker build
iteration.  Not appropriate for a fast-cadence spec-review
session.

### Prefix mapping (for the eventual rename)

Two categories of structs:

**FFv1 structs reused from RFC 8435** -- prefixes stay as-is:

| Struct          | Field prefix | Source            |
|-----------------|--------------|-------------------|
| `ff_device_addr4`     | `ffda_*`  | RFC 8435 |
| `ff_device_versions4` | `ffdv_*`  | RFC 8435 |
| `ff_layout4`          | `ffl_*`   | RFC 8435 (in reffs XDR; keep) |
| `ff_mirror4`          | `ffm_*`   | RFC 8435 (in reffs XDR; keep) |
| `ff_ioerr4`           | `ffie_*`  | RFC 8435 (in reffs XDR; keep) |
| `ff_io_latency4`      | `ffil_*`  | RFC 8435 (in reffs XDR; keep) |
| `ff_iostats4`         | `ffis_*`  | RFC 8435 (in reffs XDR; keep) |
| `ff_layoutreturn4`    | `fflr_*`  | RFC 8435 (in reffs XDR; keep) |
| `ff_layoutupdate4`    | `ffl_*`   | RFC 8435 (in reffs XDR; keep -- note: shares prefix with ff_layout4) |
| `ff_layouthint4`      | `fflh_mirrors_hint` (only that field) | RFC 8435 |
| `ff_mirrors_hint`     | `ffmc_*`  | RFC 8435 |

**FFv2 structs** -- field prefixes normalize to `ffv2*_`:

| Old prefix | New prefix | Struct              |
|------------|------------|---------------------|
| `fffi_`    | `ffv2fi_`  | `ffv2_file_info4`   |
| `ffie_`    | `ffv2ie_`  | `ffv2_ioerr4`       |
| `ffil_`    | `ffv2il_`  | `ffv2_io_latency4`  |
| `ffis_`    | `ffv2is_`  | `ffv2_iostats4`     |
| `ffl_`     | `ffv2l_`   | `ffv2_layout4` and `ffv2_layoutupdate4` |
| `fflh_`    | `ffv2lh_`  | `ffv2_layouthint4` (NOT `ff_layouthint4`; `fflh_mirrors_hint` in the v1 struct stays unchanged) |
| `fflr_`    | `ffv2lr_`  | `ffv2_layoutreturn4` |
| `ffm_`     | `ffv2m_`   | `ffv2_mirror4`      |
| `ffs_`     | `ffv2s_`   | `ffv2_stripes4`     |
| `ffv2ds_`  | `ffv2ds_`  | `ffv2_data_server4` (already in v2 form) |

### Sequence (when the rename is finally done)

1. Rename in `lib/xdr/nfsv42_xdr.x`, FFv2 struct definitions
   only (lines ~4790-4905).
2. Regenerate XDR code.
3. Compile.  For each error, inspect the line's typed-object
   context to decide whether the access is on an FFv1 struct
   (revert) or FFv2 struct (rename).  Iterate until clean.
4. Run `make check` and `make -f Makefile.reffs ci-check`.
5. Commit on a topic branch (`ffv2-prefix-normalize`).  Review
   and merge per reffs's normal workflow.

### Sanity checks during the rename

- The `(MDS)` acronym in "Maximum Distance Separable (MDS) codes"
  is unrelated and unaffected.
- Constants like `FFV2_ENCODING_PASSTHROUGH` use `FFV2_` as an
  all-caps prefix; these are not field-prefix renames.

## Pending change 4 (deferred): MACHINE_ID_ANNOUNCE op

**Status: spec discussion recorded in `layout-affinity.md`; not
yet added to the draft.**

If/when the MACHINE_ID_ANNOUNCE op described in
`layout-affinity.md` is added to the draft, reffs will need:

1. XDR additions: new op definition, args/result structs.
2. Server-side handler in `lib/nfs4/server/`.
3. Client-side caller in `lib/nfs4/client/`.
4. Configuration plumbing for the machine_id source
   (`/etc/machine-id` on Linux; equivalents on other platforms).
5. MDS-side bookkeeping for the (client, ds) colocation matrix
   and layout-ordering bias for read-iomode LAYOUTGET.

Defer until the wire mechanism is actually added to the draft.

## Closed entries (breadcrumbs)

Applied entries are removed from the main body per the doc's
convention; this trailer keeps the commit references findable
for future archaeology.

| # | Title                                                | reffs commit  | spec commit  |
|---|------------------------------------------------------|---------------|--------------|
| 1 | drop commented-out ffv2_key4 / ffm_key                | 10c31b98e8cc  | c080d06afe5c |
| 3 | NFS4ERR_PAYLOAD_NOT_CONSISTENT -> _NOT_ATOMIC         | c0759f9ace76  | (in-session) |
| 5 | CHUNK_GUARD_CLIENT_ID_NONE + _MDS sentinels + reject  | e8c4ea8896d6  | d23247b52184 |

All three landed on reffs topic branch `xdr-op-renumber`
(worktree `../reffs-xdr-renumber`) alongside the op-number
renumber commit `f49a21ded11d`.  Topic branch is ready for
ff-merge to main after a Docker `ci-check` pass.

## How to use this document

When picking up a pending change:

1. Read the relevant section above.
2. Make the corresponding reffs edits.
3. Run reffs's CI (`make -f Makefile.reffs ci-check`).
4. Once the change is shipped in reffs, either update its
   status to "applied" with the commit hash, or move the entry
   to the "Closed entries" trailer (preferred for short
   entries) and remove the body.

Do not delete this file even if all current entries are
applied -- future spec changes will add new entries here.
