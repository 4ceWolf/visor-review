# Visor BootManager review

Reviewed 2026-09-29, source revision a90906017375a296343e8445a72b1e596e61fc47.
Checkout: /home/user/Projects/Visor-BootManager.
Scope: architectural survey and targeted source review of media playback,
configuration, LUKS password handoff, boot routing, build profiles, installer/CLI,
and relevant public issue/discussion threads. Not an exhaustive security audit
or hardware validation. Nothing built, installed, converted, or activated.

## Existing video support

- Animated GIF: src/decoders/gif_decoder.c.
- MJPEG inside MP4/MOV/M4V: src/decoders/mp4_decoder.c and mjpeg_decoder.c.
  Ordinary H.264/H.265 MP4 is explicitly rejected; conversion is needed.
- VBG: src/decoders/vbg_decoder.c, using keyframes, delta tiles and optional
  motion compensation. tools/vbg_encode.py provides the host encoder.
- gui_image.c dispatches formats; gui_background.c paints and advances frames.
  Compressed animation files are read into memory, so file size still matters.
  Decode buffers are reused rather than pre-decoding every frame into a giant
  image array. No performance claims have been measured on this laptop.
- The make default is full. Ricer includes animation; standard and hardened
  omit animated decoders. Compiled-out features cannot be enabled with config.

Relevant configuration: background=\\EFI\\visor\\backgrounds\\example.vbg.
The CLI supports `visor convert INPUT --vbg --scale 1280x720 --fps 12 --out OUTPUT`.
This is an example, not executed. Conversion needs ffmpeg and Python/NumPy.
The encoder creates up to 16 workers from os.cpu_count(); cap its resources before
running on this laptop. CLI --fps applies to VBG, not the MJPEG path.
Minor confirmed interface mismatch: help advertises --no-motion, but the CLI
parser rejects it; use --mv-range 0 instead.

## Configuration structure

boot.conf lives at EFI/visor/boot.conf on the ESP. Entry blocks define names,
icons, kernel/EFI paths, optional initrd/cmdline and partition pinning. For UKIs,
preserve their embedded command line rather than copying generic LUKS examples.

Appearance controls include resolution, title/logo, icon sizes, pagination,
mouse_speed, colors, blur/blur_title, animation speed, clock, screensaver,
Material You wallpaper accents and theme selection. Named theme files override
UI keys in boot.conf; theme=random/cycle are supported. Boot entries stay in the
main configuration. docs/boot.conf.schema.json is the machine-readable schema.
Visor Studio provides a companion visual configurator, not a replacement loader.

Boot machinery includes graphical/text menus, UEFI executable/UKI handoff,
raw Linux handover, discovery/BLS, optional filesystem drivers, snapshot listings,
Secure Boot/shim integration, TPM measurements, and boot-entry self-healing.
These are implementation paths reviewed/surveyed, not guarantees of correctness.

## LUKS: the exact distinction

Discussion #11, author reply dated August 1, 2026, explicitly says native LUKS
support would be needed for wrong-password rejection before handoff:
https://github.com/IO-ZetZor/Visor-BootManager/discussions/11

Current code agrees. main.c captures the passphrase; luks_keyfile.c creates an
in-memory CPIO keyfile; linux_boot.c registers the initrd (or supplemental initrd
for UKIs). config_luks.c chooses cryptkey=rootfs: for mkinitcpio/arch or
rd.luks.key= for dracut/systemd. Linux cryptsetup actually verifies/unlocks it.
The password is not a literal kernel command-line parameter.

luks_confirm=1 detects differences between two typed strings, not whether either
is correct for the disk. luks_verbose=1 drops quiet/splash to expose retry output.
F2 reveals typed characters for keyboard-layout checking. The source contains
password-buffer wiping paths; this is not proof that every copy is erased.

Visor's separate VISORENC boot-file encryption is NOT native LUKS support.
Checking a LUKS password before Linux needs the relevant header/keyslot handling,
key derivation, decryption and validation logic, including supported LUKS2 KDFs.
It need not implement a complete filesystem or general-purpose Linux device-mapper
stack merely to validate a keyslot, but it is substantial security-sensitive work.
Do not weaken disk key derivation just to fit a boot manager.

## Public reports checked

Reviewed the all-state issue/PR index and relevant bodies/comments; checked the
discussion listing and discussions #11, #13 and #15. Not every hidden discussion
reply was available in GitHub's rendered pages.

- #11: password handoff failures, keyboard visibility, snapshots filename/V key,
  initial USB detection, mouse speed; includes the native-LUKS explanation.
- #13: mapper-name consistency documentation.
- #15: Visor Studio visual configuration/preview work.
- Issue #22 OPEN: delays before Linux handoff, especially non-FAT filesystem access.
- Issue #8 OPEN: pre-menu freezes on a specific Gigabyte motherboard.
- Issue #18 OPEN: USB Setup.
- Issue #14 CLOSED: non-FAT/ext4 loading regression.
- Issue #25 CLOSED: BLS/loader-interface interoperability.
- Issue #32 CLOSED: malformed firmware boot entries after BIOS update and repair.

Issue index: https://github.com/IO-ZetZor/Visor-BootManager/issues
Closure is not a hardware test on this laptop. No exact current video feature
request was needed: executable decoder paths already exist in the source.

## Recommended arrangement for this machine

Firmware -> systemd-boot (retained) -> optional Visor entry -> existing Zen or LTS UKI.
Zen then presents Miku/Plymouth and cryptsetup unlocks root as it already does.
LTS retains its Plymouth-free command line. Do not enable Visor luks=1 initially;
that adds a second password-handling path with no benefit to the working setup.

A future trial should preserve systemd-boot and disable Visor self-healing/fallback
replacement (selfheal=0, restore_fallback=0) so an experiment does not take over
EFI fallback paths. The installer itself must also be reviewed for deployment
flags before running it. Keep videos short and start with modest resolution/fps.

Sources:
https://github.com/IO-ZetZor/Visor-BootManager/blob/a90906017375a296343e8445a72b1e596e61fc47/boot.conf.example
https://github.com/IO-ZetZor/Visor-BootManager/blob/a90906017375a296343e8445a72b1e596e61fc47/features/features.mk
https://github.com/IO-ZetZor/Visor-BootManager/blob/a90906017375a296343e8445a72b1e596e61fc47/src/decoders/mp4_decoder.c
https://github.com/IO-ZetZor/Visor-BootManager/blob/a90906017375a296343e8445a72b1e596e61fc47/src/security/luks_keyfile.c
https://gitlab.com/cryptsetup/cryptsetup/-/blob/main/FAQ.md
