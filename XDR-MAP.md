# XDR allocation map

Which document declares what, across the flexible file v2 layout draft
family. The three drafts share one NFSv4.2 operation-number space, one
`nfsstat4` space, and one XDR type namespace, but live in three
repositories that can be edited independently. This file is where the
family checks itself for collisions before publication.

| short name | draft |
|---|---|
| base | `draft-haynes-nfsv4-flexfiles-v2` |
| proxy | `draft-haynes-nfsv4-flexfiles-v2-proxy-server` |
| delta | `draft-haynes-nfsv4-flexfiles-v2-delta-writes` |

Regenerate the tables with [`tools/xdr-map.py`](tools/xdr-map.py); it
reads the XDR blocks out of all three drafts and reports collisions.
Run it before publishing any of them.

---

## Operations (`nfs_opnum4`)

Contiguous, 78 through 100, no gaps.

| value | operation | declared in |
|------:|-----------|-------------|
| 78-88 | `OP_CHUNK_COMMIT`, `OP_CHUNK_ERROR`, `OP_CHUNK_FINALIZE`, `OP_CHUNK_HEADER_READ`, `OP_CHUNK_LOCK`, `OP_CHUNK_READ`, `OP_CHUNK_REPAIRED`, `OP_CHUNK_ROLLBACK`, `OP_CHUNK_UNLOCK`, `OP_CHUNK_WRITE`, `OP_CHUNK_WRITE_REPAIR` | base |
| 89-91 | `OP_TRUST_STATEID`, `OP_REVOKE_STATEID`, `OP_BULK_REVOKE_STATEID` | base |
| 92-95 | `OP_CHUNK_ESCROW_INSTALL`, `OP_CHUNK_ESCROW_RELEASE`, `OP_CHUNK_ESCROW_ENUMERATE`, `OP_CHUNK_ESCROW_TAKEOVER` | base |
| 96-99 | `OP_PROXY_REGISTRATION`, `OP_PROXY_PROGRESS`, `OP_PROXY_DONE`, `OP_PROXY_CANCEL` | proxy |
| 100 | `OP_CHUNK_XOR_DELTA` | delta |

**Next free operation number: 101.**

## Callback operations (`nfs_cb_opnum4`)

A separate space; do not confuse it with the above.

| value | operation | declared in |
|------:|-----------|-------------|
| 16 | `OP_CB_CHUNK_REPAIR` | base |

**Next free callback number: 17.**

## Error codes (`nfsstat4`)

| value | error | declared in |
|------:|-------|-------------|
| 10097 | `NFS4ERR_ENCODING_NOT_SUPPORTED` | base |
| 10098 | `NFS4ERR_PAYLOAD_NOT_ATOMIC` | base |
| 10099 | `NFS4ERR_CHUNK_LOCKED` | base |
| 10100 | `NFS4ERR_CHUNK_GUARDED` | base |
| 10101 | `NFS4ERR_PAYLOAD_LOST` | base |
| 10102 | `NFS4ERR_LAYOUT_CHECKSUM_NOT_SUPPORTED` | base |
| 10103 | `NFS4ERR_NO_PREDECESSOR` | base |
| 10104 | `NFS4ERR_NO_ADOPTABLE_LOCK` | base |
| 10105 | `NFS4ERR_STALE_ESCROW` | base |
| 10106 | `NFS4ERR_STALE_MDS_EPOCH` | base |
| 10107 | `NFS4ERR_PARTIAL` | base |
| 10108-10109 | *(reserved — see note)* | — |
| 10110 | `NFS4ERR_DELTA_INCOMPLETE` | delta |
| 10111 | `NFS4ERR_DELTA_LOG_FULL` | delta |

**Next free error code: 10112.**

The 10108-10109 gap is deliberate: delta chose 10110 to sit clear of
base's cluster, leaving room for further CHUNK error codes. A new base
error SHOULD take 10108 or 10109 before extending past 10111.

Every code above is declared in an XDR block, so the generator reads
the whole table natively rather than scraping prose.

## Attributes

| value | attribute | declared in |
|------:|-----------|-------------|
| 89 | `FATTR4_CODING_BLOCK_SIZE` / `fattr4_coding_block_size` | base |
| 90 | `FATTR4_CHUNKED_DATA_FILE` / `fattr4_chunked_data_file` | base |

Attributes take no `ffv2_` infix, even when this family introduces
them; follow the sibling attribute's shape.

## Flag words

| flag family | values | declared in |
|---|---|---|
| `FFV2_FLAGS_*` (layout) | `NO_IO_THRU_MDS`, `NO_LAYOUTCOMMIT`, `NO_READ_IO`, `ONLY_ONE_WRITER`, … | base |
| `FFV2_DS_FLAGS_*` | `ACTIVE`, `PARITY`, `PROXY`, `REPAIR`, … | base |
| `EXCHGID4_FLAG_USE_ERASURE_DS` | `0x00100000` | base |
| `EXCHGID4_FLAG_USE_PROXY_SERVER` | `0x00200000` | proxy |

`FFV2_DS_FLAGS_PROXY` is declared in base but is only meaningful to
proxy — a deliberate split, since the layout XDR belongs to base.

Both `EXCHGID4_FLAG_*` bits are IANA-assigned, not assigned by
publication: each draft requests its bit in its own IANA
Considerations, and IANA may place them elsewhere.

## Registries

| registry | established by | extended by |
|---|---|---|
| Erasure Encoding Type Registry | base | delta (`EC_ENC_FLAGS_XOR_DELTA_CAPABLE` column) |
| Checksum Algorithm Registry | base | delta (`CHECKSUM_FLAGS_XOR_AFFINE` column) |
| Proof-Profile Registry | base | — |

## XDR type namespace

Type and constant names are flat across the family — two documents
declaring the same name is a hard conflict, not a merge.

| document | type/typedef names |
|---|---:|
| base | 84 |
| proxy | 14 |
| delta | 4 |

**No name is declared by more than one document today.** Notable
per-document names: proxy owns `proxy_stateid4`, `proxy_assignment4`,
`proxy_op_kind4`, `open_claim_proxy4`; delta owns
`chunk_xor_delta_entry4`.

Note `proxy_op_kind4`'s values are `PROXY_OP_MOVE` / `PROXY_OP_REPAIR`
/ `PROXY_OP_CANCEL_PRIOR`. They are enum members, not operations, and
share no space with `nfs_opnum4`.

---

## Rules

1. **Take the next free value** from the tables above; never re-use a
   value another document has allocated, even if that document is
   unpublished.
2. **Update this file in the same change** that allocates a value.
3. **Run the generator before publishing** any of the three drafts.
4. A document MAY extend a registry another document established; say
   which document established it, and record the extension here.
5. Prose in a draft SHOULD NOT restate another document's allocations.
   Cite the owning document instead — the allocations move, the
   citation does not. This file is the one place the whole ledger
   lives.
