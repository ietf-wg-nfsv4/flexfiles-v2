# Data Mover design (moved)

The Data Mover design has moved to its own repository and
Internet-Draft:

https://github.com/ietf-wg-nfsv4/flexfiles-v2-data-mover

Working draft source:
[`draft-haynes-nfsv4-flexfiles-v2-data-mover.md`](https://github.com/ietf-wg-nfsv4/flexfiles-v2-data-mover/blob/main/draft-haynes-nfsv4-flexfiles-v2-data-mover.md)

The whole-file / migration / repair mechanisms, the proxy
role, codec translation for codec-ignorant clients (including
NFSv3), credential-forwarding security rules, and the
PROXY_* operation surface all live in that repository.

Per-chunk repair via `CB_CHUNK_REPAIR` stays in this
(flexfiles-v2) draft.  The section on repair-client selection
contains a forward reference to the data-mover draft for the
whole-file case.
