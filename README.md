# rothko LineageOS 23.2 collaboration sources

[中文入口](README.zh-CN.md)

**Unofficial development sources for Redmi K70 Ultra (`rothko`).** This is a
collaboration baseline, not an official LineageOS device submission or a tested
ROM release. The system framework is Android 16; the selected stock vendor is
Android 14 / API 34 from **OS3.0.307.0.WNNCNXM**.

This integration repository accompanies three source-only repositories:

| Repository | Android checkout path | Contents |
| --- | --- | --- |
| android_device_xiaomi_rothko | device/xiaomi/rothko | Device configuration, services, overlays, policy, extraction/fixup code |
| proprietary_vendor_xiaomi_rothko | vendor/xiaomi/rothko | Generated build rules and portable content ledger; **no proprietary payloads** |
| android_device_xiaomi_rothko-kernel | device/xiaomi/rothko-kernel | Stock kernel extraction recipe; **no kernel/module binaries or kernel source** |

The device tree alone is insufficient. See [BUILD.md](BUILD.md) for the pinned
manifest, platform patch series, exact stock inputs and source placement.
`baseline.json` records the required source revisions and validation limits.

The public device history keeps the original community base and its signed
commits. Later history was filtered in an independent copy to omit imported
payloads and host paths while retaining authors, committers and commit count.
`history/` records the mapping. Original repositories were not rewritten.
See [HISTORY.md](HISTORY.md) and [LICENSING.md](LICENSING.md).

Start with [KNOWN_ISSUES.md](KNOWN_ISSUES.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
Changes to Android platform repositories remain independent patches with their
original authors and Change-Ids. The obsolete first-stage boot probe is omitted
from the public integration manifest/series. Camera JPEG_R remains an explicitly
documented, unverified development path; display HDR is a separate feature.

No firmware archive, factory calibration, modem NV, device identity, biometric
template, signing private key or phone log is included. Obtain the matching stock
firmware yourself and reconstruct the declared private inputs locally. Do not
commit them. There is no flash command or bootloader manipulation in these tools.

Opening these sources for collaboration does not claim clean full-ROM build,
runtime, security, licensing of stock payloads, or official-device acceptance.
Completed checks and remaining acceptance items are listed in `VALIDATION.md`.
