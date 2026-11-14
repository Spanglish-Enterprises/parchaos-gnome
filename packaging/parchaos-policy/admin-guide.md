# ParchaOS for organisations: the policy file

*Versión en español: [admin-guide.es.md](admin-guide.es.md).*

A school or an office can set the same defaults on every ParchaOS computer, and lock the ones
people should not change, with **one text file**. There is no server and no account: you copy
the file to each computer and it takes effect.

## In short

1. Start from the example: `/usr/share/doc/parchaos-policy/policy.example.toml`.
2. Edit it, then check it on any ParchaOS computer (no admin rights needed):

   ```
   parchaos-policy check policy.toml
   ```

   It lists every setting it would set, which ones are locked, and any mistakes in plain words.
3. Copy it to each computer as `/etc/parchaos/policy.toml`:

   ```
   sudo install -m 644 policy.toml /etc/parchaos/policy.toml
   ```

   It applies within a second (a system service watches that file). New sign-ins get the
   settings; people already signed in get most of them at once and all of them at their next
   sign-in.
4. To see what is applied: `parchaos-policy status`. To undo everything: delete the file, or run
   `sudo parchaos-policy remove`.

People see a line at the top of ParchaOS Settings: *"This computer is managed by (your
organisation). Some settings are set by them."*, with your contact if you give one.

## The file

It is a [TOML](https://toml.io) file: sections in `[brackets]`, then `name = value` lines. Text
goes in quotes, `true`/`false` and numbers do not, lists go in `[ ]`. Every section is optional.

### Defaults or locks

In each section, `lock` decides what people may change:

| `lock = …`          | Meaning                                                   |
|---------------------|-----------------------------------------------------------|
| left out or `false` | the values are only defaults; people can change them      |
| `true`              | every setting of the section is fixed                     |
| `["wallpaper"]`     | only the settings named are fixed                         |

### `[organisation]`

| Name      | Example                       |
|-----------|-------------------------------|
| `name`    | `"Escuela Ejemplo"`           |
| `contact` | `"soporte@escuela.example"`   |
| `website` | `"https://escuela.example"`   |

### `[appearance]`

| Name            | Values                                                                    |
|-----------------|---------------------------------------------------------------------------|
| `style`         | `"glass"` or `"classic"`                                                  |
| `colour_scheme` | `"light"`, `"dark"` or `"auto"`                                           |
| `accent`        | `"blue"` `"teal"` `"green"` `"yellow"` `"orange"` `"red"` `"pink"` `"purple"` `"slate"` |
| `icon_style`    | `"standard"` `"dark"` `"glass"` `"mono"`                                  |
| `wallpaper`     | a full path to a picture on the computer, e.g. `"/usr/share/backgrounds/school.jpg"` |

### `[screen]`

| Name                 | Values                                            |
|----------------------|---------------------------------------------------|
| `lock_after_minutes` | minutes without use before the screen turns off and locks (`0` = never) |
| `lock_enabled`       | `true` to ask for the password when it wakes      |

### `[privacy]`

| Name               | Values                                                      |
|--------------------|-------------------------------------------------------------|
| `location`         | `false` turns location services off                         |
| `camera`           | `false` turns the camera off for every app                  |
| `microphone`       | `false` turns the microphone off for every app              |
| `phone_connection` | `false` turns phone pairing (Phone Connection) off          |
| `usage_history`    | `false` stops the list of recently used files               |

### `[extensions]`

| Name              | Values                                                         |
|-------------------|----------------------------------------------------------------|
| `allow_install`   | `false`: no new extensions can be installed from the web      |
| `user_extensions` | `false`: only the extensions installed for everyone run        |
| `enabled`         | the list of extension ids to turn on                           |

### `[apps]`

| Name   | Values                                                                   |
|--------|--------------------------------------------------------------------------|
| `dock` | the apps in the dock, as a list of `.desktop` ids, e.g. `["es.parchaos.Browser.desktop", "org.gnome.Nautilus.desktop"]` |

### `[updates]`

Without this section each person is told when updates are ready and installs them. With it,
the computer updates itself:

| Name            | Values                                                                 |
|-----------------|------------------------------------------------------------------------|
| `mode`          | `"notify"` (default), `"download"` (downloaded, installed by a person), `"install"` (installed by itself), `"off"` |
| `when`          | when to check, in systemd's words: `"daily"`, `"Sat 03:00"`, `"Mon..Fri 18:30"` |
| `reboot`        | `"never"` or `"when-needed"` (restarts if an update needs it)          |
| `security_only` | `true` installs only security fixes                                    |

Automatic updates use Fedora's `dnf5-automatic`.

### `[browser]`

Parcha Browser is built on Chromium, so it takes Chromium's own policies. Write them as
`PolicyName = value`; the full list is at
[chromeenterprise.google/policies](https://chromeenterprise.google/policies/). Examples:

```toml
[browser]
HomepageLocation = "https://escuela.example"
PasswordManagerEnabled = false
URLBlocklist = ["example-games.com"]
ForceGoogleSafeSearch = true
```

Browser policies are always fixed (Chromium shows "Managed by your organisation" in its menu).

### `[settings]`: anything else

Any other GNOME or ParchaOS setting, by its dconf path (as `dconf-editor` or
`gsettings list-recursively` show it):

```toml
[settings]
"org/gnome/desktop/interface/clock-format" = "24h"
"org/gnome/desktop/peripherals/touchpad/tap-to-click" = true
lock = ["org/gnome/desktop/interface/clock-format"]
```

`parchaos-policy check` tells you if a name is not a known setting.

## Many computers

The file is all there is, so use whatever you already have to copy it:

- **By hand or from a USB stick**: the `sudo install` line above.
- **Ansible**:

  ```yaml
  - name: ParchaOS policy
    ansible.builtin.copy:
      src: policy.toml
      dest: /etc/parchaos/policy.toml
      mode: "0644"
  ```

- **Your own package**: an RPM that installs `/etc/parchaos/policy.toml` (mark it `%config`).
  Updating the package updates every computer.

## What it changes on the computer

For anyone who wants to look underneath: the policy is turned into Fedora's standard files, so
the usual tools see it.

| What                | Where                                                     |
|---------------------|-----------------------------------------------------------|
| settings            | `/etc/dconf/db/local.d/60-parchaos-policy`, then `dconf update` |
| locks               | `/etc/dconf/db/local.d/locks/60-parchaos-policy`          |
| Parcha Browser      | `/etc/chromium/policies/managed/parchaos-policy.json`     |
| automatic updates   | `/etc/dnf/dnf5-plugins/automatic.conf`, `/etc/systemd/system/dnf5-automatic.timer.d/60-parchaos-policy.conf` |
| organisation name   | `/etc/parchaos/managed.json`                              |
| what it wrote       | `/var/lib/parchaos-policy/applied.json`                   |

Removing the policy deletes exactly these files (an `automatic.conf` you had before is put back).
