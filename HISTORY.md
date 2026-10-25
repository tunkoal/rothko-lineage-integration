# History and attribution

The original community device base is
`059ac72366d7ca095f2341e635145f611349e0de` from the public
[Xiaomi-Rothko-development device repository](https://github.com/Xiaomi-Rothko-development/android_device_xiaomi_rothko).
Its 37 commits, including signatures and SHAs, are retained without filtering.

Later device history was filtered only in a separate publication copy to remove
the imported prebuilts and known host paths. Vendor history was filtered to
build metadata/portable provenance; the original absolute-path ledger and all
proprietary payloads are omitted. The kernel repository retains historical
authorship plus a new extraction recipe instead of distributing stock binaries.

Original input histories remain unchanged locally. For retained historical
commits the author/committer names, emails and dates were checked for equality;
empty commits are retained. `history/*-commit-map.txt` maps input IDs to the
filtered IDs. Changed commits cannot retain valid old signatures; the untouched
community base avoids that change. New publication commits are separate.

Platform mbox series retain original authors, messages and Change-Ids. Recreated
commits may have new committer identity/IDs; the scripts compare final trees.
The source-only copy is not a claim that all code was written by this project.
Per-file copyright and licenses remain authoritative. No original remote is set
for automatic pushing; choose the real publication URLs separately.
