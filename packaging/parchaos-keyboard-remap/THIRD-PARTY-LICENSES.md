# Third-party components in parchaos-keyboard-remap

- **xremap** (`/usr/bin/xremap`, prebuilt release binary v0.15.13 from
  https://github.com/xremap/xremap): MIT License, Copyright (c) 2021
  Takashi Kokubun. Full text: `xremap-LICENSE`. The binary statically
  links Rust crates under their own permissive licenses (MIT, Apache-2.0
  and similar); see xremap's `Cargo.lock` at that tag.
- **xremap-gnome** (`xremap@k0kubun.com` GNOME Shell extension, from
  https://github.com/xremap/xremap-gnome): GPL-2.0-or-later, as stated in
  its source file header (the repository has no separate license file).
  Full text: `GPL-2.0.txt`.

ParchaOS's own files in this package (the remap configuration, the
keyboard-style helper, the service and udev files) are GPL-3.0-or-later.
Full text: `LICENSE`.
