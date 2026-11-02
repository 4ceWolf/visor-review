# Visor animated-intro contribution

Prepared 2026-09-30 for maintainer review. No commit, push, installer, firmware
write or live ESP change was performed. This is a prototype contribution.

## Included

- `Visor-BootManager/`: complete working source snapshot, including unchanged
  upstream files, examples and personal media; excludes Git history and caches.
- `intro-source.patch`: code/config/docs/tools changes against the base revision
  recorded in `BASE-REVISION.txt`. No binary artwork or EFI binaries in the patch.
- `binaries/`: unsigned x86_64 full and minimal build artifacts, for review only.
- `logs/`: task-specific build/check/capture logs, with local home paths redacted.
- `screenshots/`: final isolated VM captures for all 12 scenarios.
- `SHA256SUMS`: hashes of every other bundled file.

## Behavior

GIF and MJPEG MP4 intros use the existing decoders. Still images and VBG remain
usable. No H.264/H.265 decoding or sound is added. Looping, automatic continuation,
manual waiting, and menu-versus-default-boot actions are independently configured.
Any key opens the existing chooser and cancels its countdown. Existing default
index, remember-last and entry ordering are reused, not replaced by another UI.
See `Visor-BootManager/docs/intro.md` for all options and limitations.

## Build and checks

Build with GNU-EFI headers/libraries installed:

```sh
make -j1 PROFILE=full
make -j1 PROFILE=minimal BUILD_DIR=build-minimal TARGET=visor_minimal.efi
python3 tools/check_features.py
```

Use fresh build directories when changing paths; relocated old object/dependency
files caused an initial black-screen test. Clean builds resolved it. Packaged
binaries and final screenshots come from clean-build directories.

The upstream `tools/check_config_keys.py` still references old `src/` paths.
Validation overrode its two path constants in memory to `src/config/`, without
changing that unrelated upstream script. Both config and feature checks passed.

## Validation observations

QEMU/KVM + OVMF; one CPU, 256 MiB RAM, 1280x720, no network, synthetic test ESP,
disposable disk overlay and no host OS disks. Full and minimal/text-only x86_64
builds completed and passed relocation checks. No compiler warnings were found.

The final 12-case run captured these behaviors:

- GIF loops through multiple cycles, then opens the menu at the deadline.
- Non-looping GIF opens the menu after one playback.
- Manual looping remains active past the automatic deadline.
- Manual non-looping holds the final frame (last four captures identical).
- Keyboard skip opens the menu and cancels the countdown.
- Missing media and a disabled intro fall through to the menu.
- Reduced motion holds a still frame before proceeding.
- Converted MJPEG MP4 renders changing video frames and reaches the menu.
- `intro_action=boot`, `default=1` attempts the SECOND configured entry.
- Keyboard skip with action=boot opens the menu instead, without a countdown.
- Missing media with action=boot opens the normal menu rather than direct boot.

The boot test deliberately points to nonexistent EFI files. Its rescue screen
shows SECOND was selected; this verifies selection/attempt, NOT an actual OS boot.
Early keyboard tests sent Escape before firmware handoff. The final harness waits
for recognizable intro pixels before sending it; those final runs verify skipping.
Capture completion is not an automated behavioral assertion; screenshots were
reviewed and frame fingerprints checked for motion versus held frames.

Not tested: physical firmware, ARM builds, adversarial media, allocation/timer
failure injection, all codec variations, Secure Boot signing, or real OS booting.
Keep normal recovery boot paths. No production-readiness/security certification
is claimed. Compressed media is resident and decoding remains synchronous.

## Media rights

The supplied pink-haired GIF is copied unchanged; its original publisher and
redistribution license are unknown. The MP4 derives from it. Personal test media
is included at the user's request, not declared BSD-licensed. Replace it with
rights-cleared assets before public distribution. Generic code can be reviewed
and applied without the artwork. The previous AI-generated Rem image remains
only as an optional example. No GRUB source was copied.
