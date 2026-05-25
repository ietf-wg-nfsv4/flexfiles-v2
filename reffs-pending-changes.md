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

## Pending change 1: remove ffv2_key4 and ffm_key

**Status: spec change applied (commit c080d06afe5c on
flexfiles-v2).  reffs side not yet updated.**

`ffv2_key4` typedef and the `ffm_key` field in `ffv2_mirror4` were
removed from the draft because the field had no protocol semantics
and no use case.  See `layout-affinity.md` for the design
discussion (the colocation-detection use case the field was
considered for was the wrong granularity; per-DS, not per-mirror).

### What reffs has today

The reffs XDR has the field commented out:

```
struct ffv2_mirror4 {
        ffv2_coding_type4       ffm_coding_type;
        ffv2_data_protection4   ffm_protection;
        /* ffv2_key4               ffm_key; */    <-- commented out
        ffv2_striping           ffm_striping;
        uint32_t                ffm_striping_unit_size;
        uint32_t                ffm_client_id;
        ffv2_stripes4           ffm_stripes<>;
};
```

at `lib/xdr/nfsv42_xdr.x:4828-4836`.

### What reffs needs to change

Remove the commented-out `ffv2_key4` field entirely.  No
`ffv2_key4` typedef exists in reffs to remove; just the field
comment.

The diff is one line.  No semantic change.

## Pending change 2: normalize FFv2 field prefixes to ffv2*_

**Status: spec change in progress on flexfiles-v2 (Option A from
the prefix-consistency discussion).  reffs side not yet updated.**

The draft inconsistently used the short `ff[a-z]+_` field prefix
inherited from RFC 8435 (FFv1) for most FFv2 structs, with
`ffv2ds_*` as the one exception (for `ffv2_data_server4`).  The
inconsistency was identified during review.  Option A: normalize
all FFv2 fields to `ffv2*_` prefix.

### Prefix mapping

Two categories of structs in the draft:

**FFv1 structs reused unchanged from RFC 8435** -- prefixes stay
as-is.  The draft explicitly says these are "reproduced here for
reader convenience and are not part of the XDR extracted from
this document":

| Struct          | Field prefix | Source            |
|-----------------|--------------|-------------------|
| `ff_device_addr4`     | `ffda_*`  | RFC 8435 |
| `ff_device_versions4` | `ffdv_*`  | RFC 8435 |
| `ff_layouthint4`      | `fflh_mirrors_hint` (only that field) | RFC 8435 |
| `ff_mirrors_hint`     | `ffmc_*`  | RFC 8435 |

**FFv2 structs** -- field prefixes normalize to `ffv2*_`:

| Old prefix | New prefix | Struct              |
|------------|------------|---------------------|
| `fffi_`    | `ffv2fi_`  | `ffv2_file_info4`   |
| `ffie_`    | `ffv2ie_`  | `ffv2_ioerr4` (note: section heading and figure title say `ff_ioerr4`; the actual struct definition is `ffv2_ioerr4`, fix prose to match) |
| `ffil_`    | `ffv2il_`  | `ffv2_io_latency4`  |
| `ffis_`    | `ffv2is_`  | `ffv2_iostats4`     |
| `ffl_`     | `ffv2l_`   | `ffv2_layout4`      |
| `fflh_`    | `ffv2lh_`  | `ffv2_layouthint4` (NOT `ff_layouthint4`; `fflh_mirrors_hint` in the v1 struct stays unchanged) |
| `fflr_`    | `ffv2lr_`  | `ffv2_layoutreturn4` (note: section heading says `ff_layoutreturn4`; struct is `ffv2_layoutreturn4`, fix prose) |
| `ffm_`     | `ffv2m_`   | `ffv2_mirror4`      |
| `ffs_`     | `ffv2s_`   | `ffv2_stripes4`     |
| `ffv2ds_`  | `ffv2ds_`  | `ffv2_data_server4` (already in v2 form) |
| `ffds_`    | `ffds_`    | only FFv1 prose references (RFC 8435) |

The struct-name corrections (`ff_ioerr4` -> `ffv2_ioerr4` in
prose; `ff_layoutreturn4` -> `ffv2_layoutreturn4` in prose) are
part of the same normalization.  In the XDR they were already
`ffv2_*`; only the surrounding documentation drifted.

### What reffs has today

All FFv2 struct fields in reffs's XDR use the old prefixes
(`ffm_*`, `ffl_*`, `ffs_*`, `fffi_*`, etc., matching the
unrenamed draft).  Every C / Python file in reffs that touches
the FFv2 wire format references these old prefixes.

### What reffs needs to change

1. **XDR rename** at `lib/xdr/nfsv42_xdr.x`: substitute every old
   prefix with its `ffv2*_` form.
2. **Generated code**: re-run `xdr-parser` (or whatever generator
   reffs uses) to regenerate `nfsv42_xdr_const.py`,
   `nfsv42_xdr_type.py`, `nfsv42_xdr_pack.py`, `nfsv42_xdr.h`,
   `nfsv42_xdr.c`.
3. **C sources**: substitute every reference to FFv2 field names.
   Likely paths: `lib/nfs4/server/layout.c`, `lib/nfs4/client/`,
   `lib/nfs4/dstore/`, anything touching `ffv2_layout4`,
   `ffv2_mirror4`, etc.  Use a careful regex; preserve any
   FFv1 references that legitimately use `ffds_*` etc.
4. **Python sources**: same substitution in `scripts/reffs/*.py`
   wherever FFv2 fields are referenced.
5. **Tests**: same substitution in `lib/nfs4/tests/*.c`,
   `scripts/test_*.py`, etc.
6. **Build verification**: `make -f Makefile.reffs ci-check`
   must pass.

### Estimated scope

The XDR file is the bounded part: ~5 lines per struct, ~15
structs that use these prefixes, so ~75 line touches in the XDR.
The generated code regenerates from that automatically.

The C / Python source impact depends on how many call sites
reference FFv2 wire fields.  Likely 100-300 lines across the
reffs source tree, mostly in the NFSv4 server layout code, the
NFSv4 client code, and the dstore vtables.

### Sequence

1. Rename in `lib/xdr/nfsv42_xdr.x`.
2. Regenerate XDR code.
3. Compile.  Fix every reported error by renaming the C-side
   reference.  Iterate until clean.
4. Run `make check` (unit tests) and `make -f Makefile.reffs
   ci-check` (full CI).  Fix any test that hard-codes old field
   names.
5. Commit on a topic branch (`ffv2-prefix-normalize`).  Review
   and merge per reffs's normal workflow.

### Sanity checks during the rename

- Don't touch `ffds_*` references that are FFv1 references (in
  prose comments or RFC 8435 cross-references).  reffs's source
  may not have many of these but check anyway.
- The `(MDS)` acronym in "Maximum Distance Separable (MDS) codes"
  is unrelated and unaffected.
- Some constants like `FFV2_ENCODING_PASSTHROUGH` use `FFV2_` as
  an all-caps prefix; these are not field-prefix renames.

## Pending change 3 (deferred): MACHINE_ID_ANNOUNCE op

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

## How to use this document

When picking up a pending change:

1. Read the relevant section above.
2. Make the corresponding reffs edits.
3. Run reffs's CI (`make -f Makefile.reffs ci-check`).
4. Once the change is shipped in reffs, update the status field
   in this document to "applied" (or remove the section if the
   draft and reffs are now in sync and no further action is
   pending).

Do not delete this file even if all current entries are
applied -- future spec changes will add new entries here.
