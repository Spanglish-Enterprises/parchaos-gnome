# Security

## Reporting a problem

Please report security issues privately rather than in a public issue:
use GitHub's **Report a vulnerability** button on this repository's
Security tab. You'll get a reply within a few days.

## Known issue: keyboard remap and the `input` group

ParchaOS maps Super to Ctrl (macOS-style shortcuts) with a remapper that
currently runs as the logged-in user. To do that, the installer adds
accounts to the `input` group and allows access to `/dev/uinput`. Any
program running as that user can therefore read keyboard input and
send keystrokes.

A redesign that moves the remapper into a sandboxed system service is
in progress. Until it ships, if you don't use Super as Ctrl you can
turn off **Super as Ctrl** in Settings and leave the group:

    sudo gpasswd -d $USER input

then log out and back in.
