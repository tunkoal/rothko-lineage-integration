# Build and extraction workflow

The supported helper environment is Linux x86-64 with Python 3 and the matching
LineageOS checkout's host tools/JDK21. Provision the ordinary LineageOS build
environment separately. Stock extraction, compiling Android and flashing are
different steps; none of these helpers contacts a phone.

## 1. Clone the four real repositories

Clone this integration repository and its three companion repositories beside
one another, using the actual URLs chosen by the maintainer. No fictitious owner
or implicit private remote is embedded. Set `INTEGRATION` to this local checkout
and `SOURCE` to a new Android source directory. Keep the repository names from
README.md, or pass `--repositories-parent` to the staging helper.

Read `baseline.json` and check out its recorded companion revisions before
continuing. Do not use an unrelated vendor, kernel or device branch.

## 2. Synchronize the pinned Android base

```sh
mkdir -p "$SOURCE"
cd "$SOURCE"
repo init -u "$INTEGRATION" -b lineage-23.2 -m manifests/pinned.xml --git-lfs
repo sync -j4
python3 "$INTEGRATION/scripts/stage-sources.py" --source-root "$SOURCE"
```

`manifests/pinned.xml` is a complete manifest, **not** a local-manifest overlay.
It uses public fetch URLs and upstream bases for locally patched repositories.
The 1167-project snapshot is pinned; this does not claim that every remote SHA
has been fetched anew during preparation. A missing upstream object must be
reported with its project and SHA, not replaced by an arbitrary newer branch.
Three companion checkouts are intentionally staged separately; no unpublished
maintainer commit is requested from an unrelated upstream remote.

## 3. Apply the platform series

```sh
python3 "$INTEGRATION/scripts/apply-platform-patches.py" --source-root "$SOURCE" --check-only
python3 "$INTEGRATION/scripts/apply-platform-patches.py" --source-root "$SOURCE"
```

This requires clean repositories at exact bases and verifies final trees. It
never resets local work; an interrupted `git am` is left for inspection. Configure
your Git committer identity first. Original patch authors/messages remain intact.
Source patches include host support for external OUT_DIR and optional Soong
memory limits; `--without-host-support` skips that group if intentionally desired.
The host group is not a hardware requirement. First-stage probe patches are not
included; `system/core` remains at its unmodified upstream base.

## 4. Prepare the exact stock inputs

Unpack your own OS3.0.307.0.WNNCNXM fastboot package using trusted Android tools.
The helpers below accept **already unpacked** inputs; archive/image unpacking is
not implemented or validated by these scripts. Preserve bytes and case. The
required layout is:

| Variable | Required contents |
| --- | --- |
| STOCK_DUMP | Partition filesystem roots: system, system_ext, vendor, odm, vendor_dlkm, system_dlkm and required other selected paths |
| STOCK_DUMP/apex | Prepared com.android.vndk.v34 filesystem, including lib64; it is not the compressed .apex archive |
| STOCK_ARTIFACTS | boot/kernel, vendor_boot/dtb, vendor_boot/vendor_ramdisk00-files/lib/modules, kernel-config.txt |
| STOCK_IMAGES | Original images directory containing dtbo.img |

`boot/kernel` is the original compressed kernel returned by Android unpack_bootimg;
retain the DT table wrapper in vendor_boot/dtb. Unpack the first vendor ramdisk
without flattening its module directory. Extract IKCONFIG from that same kernel
as kernel-config.txt; it is evidence, not a kernel build input override. Extract
dynamic partitions before reading filesystem contents; do not feed super.img or
sparse images to the file-copy helpers. Hash locks reject other firmware or
incorrect extraction. No LK/preloader image is used.

If STOCK_DUMP/apex is a symlink outside STOCK_DUMP, pass `--apex-input` explicitly
with its exact prepared target. Other external symlink escapes are rejected.
See device `DEVICE_PREBUILTS.md` for the 778 device-local inputs and the kernel
`extraction-recipe.json` for 581 precise stock artifacts.

```sh
python3 "$INTEGRATION/scripts/prepare-local-inputs.py" \
  --source-root "$SOURCE" --stock-dump "$STOCK_DUMP" \
  --stock-artifacts "$STOCK_ARTIFACTS" --stock-images "$STOCK_IMAGES" \
  --staging-output "$NEW_PRIVATE_STAGING"
# Add --apex-input "$PREPARED_APEX" only for the documented external APEX layout.
```

Staging must be new and outside source/stock directories. The workflow verifies
778 device payloads, 2975 vendor/ODM payloads and four generated metadata files,
and 581 kernel artifacts before population. Conflicting target files are rejected;
existing byte-identical payloads are retained. All extracted payload paths are
Git-ignored. Do not `git add -f` them. The reviewed patchelf binary from
prebuilts/extract-tools is mandatory for exact device audio transforms.

The extraction contract is stock-dump based. Installed-phone extraction, arbitrary
APK signatures, OTA parsing and a source-built kernel remain separate work.

## 5. Build a development candidate

```sh
cd "$SOURCE"
export OUT_DIR=/absolute/path/to/new-output
export SOONG_GOMEMLIMIT=14GiB
export NINJA_HIGHMEM_NUM_JOBS=1
source build/envsetup.sh
lunch lineage_rothko-bp4a-userdebug
m -j4 bootimage initbootimage vendorbootimage systemimage systemextimage \
  productimage vendorimage odmimage system_dlkmimage vendor_dlkmimage odm_dlkmimage \
  vbmetasystemimage vbmetavendorimage vbmetaimage check-vintf-all sepolicy_test
```

These host resource values describe the working development host, not device
requirements. Use appropriate resources on another machine. This is the recorded
image-oriented bring-up route; Recovery/OTA distribution, signing and installation
must be validated separately. Do not use it to overwrite a trusted release build.
The cleaned public-source candidate has not undergone a new clean full-ROM build
and phone regression. A successful extraction or host fixture does not imply that
those steps passed. See VALIDATION.md before proposing a release.
