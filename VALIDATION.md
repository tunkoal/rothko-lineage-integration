# Validation of the public collaboration candidate

Date: 2026-10-25. These checks support publishing **source collaboration
development previews**. They do not approve a ROM release or official device.

## Completed

- Three independent, self-contained companion repositories retain all 300
  historical author/committer records; raw identity headers, dates/timezones
  were compared. The original 37 community commits retain their original IDs
  and signatures. No input repository was rewritten.
- Full reachable public histories were mechanically checked for excluded
  payload paths, binary objects/patch blocks, known host/device identifiers and
  listed credential patterns. No reported issues remained. This is not a
  licensing or security certification.
- Clean companion clones recreated 778 device, 2975 vendor/ODM and 581 kernel
  artifacts from the reviewed unpacked stock inputs: **4334 payloads**. All
  hashes and four generated vendor build metadata files matched. Existing
  maintained vendor payloads were not inputs. Existing Android host-tool
  checkouts were reused; this was not a full new Android checkout.
- All 4334 payload paths were verified Git-ignored; the populated source
  checkouts remained tracked-clean. Later publication-only metadata changes
  were compared to ensure runtime/extraction source files did not change.
- The public patch entrypoint actually applied **66 commits in 12 repositories**
  on isolated exact bases; all final trees matched. Repeating it reported zero
  pending series. Local-work, in-progress Git-operation and hash-drift rejection
  were tested. Custom first-stage probe additions are omitted.
- Real `repo init`, `repo manifest`, and `repo list --all --groups all -p` accepted
  the full pinned manifest: **1167 unique projects**. No full source sync ran.
- The 13 modified/core upstream bases were checked through the public GitHub
  commit API. Six critical extraction/runtime dependency commits were checked
  using the appropriate public Git transport or AOSP Gitiles source.
- Seven private-input helper fixture cases passed with normal and optimized
  Python. Public-history checker fixtures rejected a payload/token even after
  it was deleted from the newest commit. Tests use synthetic data.
- Existing portable production-Java host fixtures passed 11 AOD draw scenarios
  and 8 pickup groups against Android fakes. They do not validate real graphics,
  Android resources, Dagger, HALs, panel behavior or sensor delivery.

Evidence is in `validation/` and `snapshots/20261025/`. The reports contain hashes
and scope, not raw firmware, phone logs or credentials. CI checks source-only
history and the small input-helper fixtures, with read-only permissions and a
commit-pinned checkout action; it does not build Android or access a phone.

## Not completed or not claimed

- Fetching all 1167 pinned projects again and a clean full-ROM build.
- Unpacking arbitrary firmware archives/images, installed-phone extraction,
  different APK signatures, arbitrary firmware or different patchelf output.
- New phone regression of the cleaned public-source baseline, OTA/upgrades,
  complete hardware/security acceptance or physical AOD 30 Hz/power parity.
- Full original thermal/charging/brightness equivalence, camera JPEG_R repair,
  China Telecom IMS repair or resolution of every item in KNOWN_ISSUES.md.
- Proprietary payload redistribution permission, corresponding source-built
  kernel/module delivery, or LineageOS official acceptance.

Existing ROM test results remain tied to their actual tested image baselines.
Do not silently transfer them to this source-cleanup candidate. A collaborator
can review, reproduce declared extraction/patches and submit fixes while these
development acceptance items remain open.
