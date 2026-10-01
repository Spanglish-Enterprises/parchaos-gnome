# parchaos-glass

ParchaOS's own liquid glass (ticket #135). A `GlassPane` actor draws a refracted, lightly blurred, tinted copy of the
desktop behind it (a Clutter.Clone of the background through a Clutter.ShaderEffect), with a curved-edge lens, a thin
rim light and chromatic fringing. Rounded corners come from a signed-distance field in the shader, so no square halo.

Develop with a real GPU: `sudo dnf install mutter-devkit`, then
`DEVKIT=1 EXTS="parchaos-glass@parchaos.org" scripts/devshot/run.sh plan.json` opens a nested shell window and writes
screenshots. Status: prototype (demo panes only). Next: apply to Control Center tiles, menus, dock; clone windows too.
