# Known issues and validation limits

Baseline date: 2026-10-25. These are source-development status notes. The latest
unified image build succeeded, but its AOD/swap/wakeup/NFC-SE candidate changes
have not completed that round's on-device acceptance. Public-source cleanup and
payload exclusion are additional changes, not already-tested ROM releases.

| Area | Status |
| --- | --- |
| Boot, display/touch/battery, Wi-Fi, ordinary storage, gesture/button navigation | Validated on earlier image baselines; regress after integration changes |
| Fingerprint | Enroll, wrong-finger rejection, lockscreen/AOD/off-screen pulse unlock previously validated; new AOD lifecycle candidate still needs regression |
| Face | Enrollment and lockscreen authentication validated on earlier baseline; source changes and preview/lifecycle cleanup need regression |
| Bluetooth media | Software A2DP continuous playback validated; default disables hardware offload; hardware-offload repair deferred |
| Bluetooth headset microphone/profiles/codecs | Do not infer complete support from media playback; further profile tests needed |
| Telephony | Local two-way calls validated with available card; China Telecom calls/SMS failures reported, no tester trace available; unresolved |
| SIM toggle / hotspot 5 GHz and selectable security | User validation passed on an earlier baseline; full combinations not claimed |
| AOD | Intermittent black-screen lifecycle fix is a new candidate; host/draw comparison evidence exists, full idle/suspend/notification/runtime acceptance pending |
| AOD physical 30 Hz | Unresolved/unverified; neither overlay numbers nor draw lease prove panel 30 Hz |
| Camera JPEG_R / Ultra HDR | Deferred; prior enabled capture hung; public development configuration still selects IDs 0,1 for the framework route, subject to metadata checks |
| Ordinary camera detail/sharpness | Reported below preview quality; unresolved; do not call it fixed because preview/photo capture works |
| Display colors/HDR/automatic brightness | Earlier user tests verified color switching, HDR boost/restoration and automatic brightness; complete factory parity/thermal/HBM/OPR scenarios not established |
| Thermal / charging | Full factory policy/protocol equivalence not validated; extra charging-control feature was cancelled and its SDK/UI changes reverted |
| GPS | Outdoor satellite acquisition and position validated on an earlier baseline |
| Accelerometer/light/proximity/vibration/audio recording | Earlier user validation passed; current-round regression still required |
| zRAM / double-tap / pickup / NFC secure element | Source and/or limited host/stock-control checks; latest unified candidate runtime acceptance pending |
| 32-bit applications | Product is 64-bit-only; do not advertise 32-bit compatibility |
| Kernel and modules | Stock prebuilts are reconstructed locally; corresponding source/build route and official requirements remain unresolved |

File a result against an exact source/image revision and firmware. Separate UI
options being visible, service registration, protocol success and real hardware
behavior. Do not post IMEI or other private identifiers when reporting carrier
issues. Camera HDR and display HDR are different pipelines.
