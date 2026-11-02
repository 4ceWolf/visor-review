# Animated intro (local contribution)

Optional skippable intro before Visor's menu or default-entry boot. Disabled
unless a media path is set. No firmware or encryption changes are involved.

## Configuration

```ini
autoboot=0
timeout=-1
default=0
remember_last=0
intro_media=\EFI\visor\backgrounds\kawaii.gif
intro_duration=5000
intro_loop=1
intro_auto_continue=1
intro_action=menu
animation=1
```

- `intro_media`: PNG/BMP/GIF/MJPEG MP4/MOV/M4V/VBG. `intro_image` is an alias.
- `intro_duration`: automatic deadline in milliseconds, default 2000, capped at
  5000, excluding synchronous loading/decoding. Zero disables all intro modes.
- `intro_loop=0`: play once, then automatically continue after the final frame's
  delay or deadline, whichever comes first. In manual mode, hold the final frame.
- `intro_loop=1`: repeat regardless of embedded GIF loop counts; automatic mode
  still ends at the deadline.
- `intro_auto_continue=1`: perform `intro_action` automatically.
- `intro_auto_continue=0`: wait for a key, repeating or holding the final frame.
  The duration is not a deadline in this explicit manual mode.
- `intro_action=menu`: open the existing chooser. Its normal timeout still
  applies; use `timeout=-1` to wait indefinitely at the menu.
- `intro_action=boot`: boot the existing preselected entry after successful
  automatic completion.
- `animation=0`: no fade or motion; show the first frame until deadline or key.

**Any key opens the menu and cancels its countdown**, even with action=boot.
Missing/unsupported media, decode failure and timer failure skip to the normal
menu, not the intro's direct-boot action. The normal menu timeout still applies.
Existing `autoboot=1` or `timeout=0` bypasses the intro entirely, as does text
mode. There is no mouse skip or audio. Failed boots do not replay the intro.

## Entry ordering and default

Visor already has a boot-entry chooser. Explicit `entry { ... }` blocks appear
in configuration order. Put the preferred OS first with `default=0`, or select
the second with `default=1`. Indices are zero-based. `remember_last=1` overrides
this default; existing systemd loader variables may override selection too.
Inspect discovered entries before choosing an index. Use explicit entries and
the existing discovery controls for deterministic ordering. The existing
`boot_order` self-heal setting controls firmware NVRAM, NOT menu ordering.

## Media and profiles

Reuses Visor's existing decoders; no GRUB code or multimedia framework is added.
Full/ricer include GIF/MP4; other profiles need `anim_gif` / `anim_mp4`.
Unavailable decoders safely bypass the intro. Fades honor the `fade` feature.
Media is aspect-fitted against black, never stretched or cropped.

**MP4 means MJPEG, not arbitrary H.264/H.265/AV1.** Convert outside firmware:

```sh
ffmpeg -threads 1 -i input.mp4 -an -vf 'scale=960:-2,fps=15' \
  -c:v mjpeg -threads 1 -q:v 4 -pix_fmt yuvj420p -movflags +faststart intro.mp4
```

Keep clips small and trusted. Compressed data and working buffers reside in RAM;
frames are decoded on demand, not all in advance. There is no new media-size
hardening layer. Loading/decoding is synchronous and not interruptible mid-frame.
Slow decoding may stretch playback; there is no audio synchronization.

## Personal example and rights

`assets/kawaii-intro/kawaii.gif` is the user's unchanged 500x289, nine-frame,
approximately 1.17-second GIF. `kawaii-mjpeg.mp4` is a single-worker conversion
for decoder tests. The theme fragment chooses a five-second looping GIF followed
by the menu. Merge it with a reviewed config, not as a replacement boot.conf.

This supplied pink-haired character replaces the earlier Rem choice. Its original
publisher and redistribution rights are unverified. These are personal test
assets, not BSD-licensed character artwork; replace with rights-cleared media
before a public release. The source-only patch excludes artwork. The older
`assets/rem-intro/` is retained as an optional AI-generated still-image example.

## Validation and deployment

`intro_duration=0` disables the feature; check theme overrides. No installer ran.
The review bundle contains complete working source, source-only patch, examples,
binaries, build logs and VM screenshots. Keep installed systemd-boot, LTS and
Plymouth unchanged until separately reviewed deployment.

`tools/preview_intro.py` uses QEMU/KVM, 256 MiB RAM, one CPU, no networking and a
synthetic ESP with a disposable write overlay. No host OS disks are attached.
Its missing-file entries deliberately test selection/boot attempt, not a real
OS boot. Capturing screenshots is not an automated behavioral assertion; inspect
them. See the bundle's validation report for actual observed results.
