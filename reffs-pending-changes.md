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

### Why this needs to happen

The flexfiles-v2 draft normalized FFv2 struct field prefixes
from the short RFC 8435-style names (`ffl_`, `ffm_`, etc.) to
explicit `ffv2*_` forms so an FFv2 reader can tell at a glance
that a field belongs to the new layout type.  The wire bits
are unchanged; only field identifiers in the XDR and the C /
Python source move.  reffs must follow because the wire field
names are derived from the XDR identifiers and the XDR file
in reffs is the canonical source the C and Python sides
include.

### Hazard note (discovered 2026-05-25)

The original estimate assumed reffs's XDR cited the FFv1
reused structs but didn't define them.  In fact reffs has its
own full XDR definitions of all the FFv1 structs (`ff_layout4`,
`ff_mirror4`, `ff_ioerr4`, `ff_io_latency4`, `ff_iostats4`,
`ff_layoutreturn4`, `ff_layoutupdate4`, `ff_data_server_wcc4`,
`ff_mirror_wcc4`, `ff_layout_wcc4`, `ff_layouthint4`,
`ff_mirrors_hint`) at `lib/xdr/nfsv42_xdr.x` lines roughly
4657-4775.  Those FFv1 struct definitions use the SAME short
prefixes (`ffl_`, `ffm_`, `ffie_`, `ffil_`, `ffis_`, `fflr_`)
that the rename intends to move on the FFv2 side.

Concretely, the FFv1 `ff_layout4` and the FFv2 `ffv2_layout4`
both have fields `ffl_mirrors` / `ffl_flags` /
`ffl_stats_collect_hint`.  A blanket
`s/\bffl_/ffv2l_/g` would silently break the FFv1 code path.

C code in `lib/nfs4/server/layout.c` and `lib/nfs4/client/
mds_layout.c` handles BOTH wire formats and mixes the prefixes
inside the same file.  In `layout.c` specifically the FFv1 and
FFv2 paths are in separate static functions
(`layoutget_build_v1` at ~L466 vs `layoutget_build_v2` at
~L577), which gives a usable per-function decision boundary.

### How to identify FFv1 vs FFv2 access in C

The disambiguator is the C type of the object being accessed.
Three reliable signals to look for in or near the line:

1. **Explicit struct type in the declaration**: nearby code
   like `ffv2_mirror4 *mirror = ...` (rename) or
   `ff_mirror4 *mirror = ...` (keep).

2. **sizeof() argument** in a recent calloc / malloc:
   `calloc(1, sizeof(ffv2_mirror4))` (rename) vs
   `calloc(1, sizeof(ff_mirror4))` (keep).

3. **Containing function name**: in `layout.c`,
   `layoutget_build_v1` is FFv1, `layoutget_build_v2` is FFv2.
   Other functions (LAYOUTCOMMIT, LAYOUTRETURN, LAYOUTERROR,
   LAYOUT_WCC handlers) may dispatch on a runtime layout-type
   field; inspect the surrounding switch / if chain.

If a single line is genuinely ambiguous after applying all
three signals, fall back to the build: the Docker compile
will surface the type mismatch on the next iteration.

### Scope inventory (as of 2026-05-25)

Files containing one or more of the renamable prefixes
(`ffl_`, `ffm_`, `ffie_`, `ffil_`, `ffis_`, `fflr_`, `fffi_`,
`fflh_`, `ffs_data_servers`):

| File | Hits | Notes |
|------|------|-------|
| `lib/xdr/nfsv42_xdr.x`                       | many | XDR source; rename only inside FFv2 struct defs (lines ~4790-4905) |
| `lib/nfs4/server/layout.c`                   | ~45  | FFv1 path: `layoutget_build_v1`; FFv2 path: `layoutget_build_v2` + LAYOUT_WCC / LAYOUTSTATS handlers |
| `lib/nfs4/client/mds_layout.c`               | ~15  | mixed v1 + v2 client-side layout handling |
| `lib/nfs4/ps/tests/ec_pipeline_stripe_test.c`| ~1   | small |
| `lib/nfs4/client/ec_client.h`                | ~2   | small |
| `lib/include/reffs/super_block.h`            | ~1   | small |

There are no `*.py` hits today (Python uses the generated
`*_type.py` which will pick up the rename automatically from
the regenerated XDR).  Check again before starting; the
landscape may have changed.

Recompute the hit count with:

```
cd /Volumes/Sensitive/reffs
grep -rlE '\b(ffl_|ffm_|ffie_|ffil_|ffis_|fflr_|fffi_|fflh_|ffs_data_servers)' \
    --include='*.c' --include='*.h' --include='*.x' \
    --include='*.py' --include='*.py.in' \
    lib/ src/ scripts/ tools/
```

### Prefix mapping

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
| `ff_data_server_wcc4` | `ffdsw_*` | RFC 9766 |
| `ff_mirror_wcc4`      | `ffmw_*`  | RFC 9766 |
| `ff_layout_wcc4`      | `fflw_*`  | RFC 9766 |

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

### Sequence for the rename

1. **Branch.**  Following the reffs workflow rule against
   direct commits to `main`, create a topic branch via
   worktree:

   ```
   cd /Volumes/Sensitive/reffs
   git worktree add ../reffs-ffv2-prefix -b ffv2-prefix-normalize
   cd ../reffs-ffv2-prefix
   ```

2. **XDR.**  Rename in `lib/xdr/nfsv42_xdr.x`, FFv2 struct
   definitions ONLY (currently lines ~4790-4905; recheck after
   any intervening edits).  Use the prefix-mapping tables
   above.  Do not touch the FFv1 struct definitions at lines
   ~4657-4775.

3. **C/Python rename.**  For each hit reported by the grep
   above, apply the three-signal disambiguation from "How to
   identify FFv1 vs FFv2 access" and rename only the FFv2
   accesses.  Commit after each file (or each function inside
   layout.c) to keep the topic-branch history bisectable if a
   subtle regression appears.

4. **Build verification.**  reffs does not build natively on
   macOS hosts; use the Docker target:

   ```
   make -f Makefile.reffs ci-check
   ```

   `ci-check` regenerates the XDR (xdr-parser), compiles, runs
   the unit tests, runs the integration tests (NFSv3 + NFSv4.2
   git-clone, identity, TLS, krb5), and verifies SPDX headers
   and clang-format style.

   Iterate: each compile error names the file and line of an
   access that still references the old prefix.  Apply the
   three-signal disambiguation and rename.

5. **Verify zero residual references on the FFv2 side.**
   After the build is green, the residual-check is:

   ```
   # Should match only FFv1 struct definitions and FFv1
   # access patterns.  Inspect each remaining hit by hand.
   grep -rnE '\b(ffl_|ffm_|ffie_|ffil_|ffis_|fflr_)[a-z]' \
       --include='*.c' --include='*.h' lib/ src/ tools/
   ```

6. **Update this document.**  Once `ci-check` is green, move
   this entry to the Closed-entries trailer at the bottom of
   the file with the topic-branch's final commit hash.

### Sanity checks during the rename

- The `(MDS)` acronym in "Maximum Distance Separable (MDS)
  codes" prose comments is unrelated and unaffected.
- Constants like `FFV2_ENCODING_PASSTHROUGH` use `FFV2_` as an
  all-caps prefix; these are not field-prefix renames.
- `ffv2ds_*` field names are already correct (FFv2 form).
- `ffds_*` references in prose comments cite RFC 8435 FFv1
  and stay unchanged.
- The renamed FFv2 const block (`FFV2_FLAGS_*`,
  `FFV2_DS_FLAGS_*`, `FFV2_ENCODING_*`,
  `FFV2_PROTECTION_TYPE_*`, `FFV2_STRIPING_*`) is independent
  of this rename; do not touch.

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
