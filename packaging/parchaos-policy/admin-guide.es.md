# ParchaOS para organizaciones: el archivo de políticas

*English version: [admin-guide.md](admin-guide.md).*

Una escuela o una oficina puede poner los mismos ajustes en todas sus computadoras con ParchaOS,
y bloquear los que la gente no debe cambiar, con **un solo archivo de texto**. No hace falta
servidor ni cuenta: se copia el archivo a cada computadora y se aplica.

## En resumen

1. Parta del ejemplo: `/usr/share/doc/parchaos-policy/policy.example.toml`.
2. Edítelo y compruébelo en cualquier computadora con ParchaOS (no hacen falta permisos de
   administrador):

   ```
   parchaos-policy check policy.toml
   ```

   Muestra cada ajuste que pondría, cuáles quedan bloqueados y, si hay errores, los explica.
3. Cópielo a cada computadora como `/etc/parchaos/policy.toml`:

   ```
   sudo install -m 644 policy.toml /etc/parchaos/policy.toml
   ```

   Se aplica en un segundo (un servicio del sistema vigila ese archivo). Quien entre después ya
   tiene los ajustes; quien ya está dentro recibe casi todos al momento y el resto al volver a
   entrar.
4. Para ver qué está aplicado: `parchaos-policy status`. Para deshacerlo todo: borre el archivo o
   ejecute `sudo parchaos-policy remove`.

Arriba en Ajustes de ParchaOS aparece: *«Esta computadora la administra (su organización).
Algunos ajustes los fija esa organización.»*, con su contacto si lo indica.

## El archivo

Es un archivo [TOML](https://toml.io): secciones entre `[corchetes]` y líneas `nombre = valor`.
El texto va entre comillas; `true`/`false` y los números, sin comillas; las listas entre `[ ]`.
Todas las secciones son opcionales. Los nombres de las secciones y de los ajustes se escriben en
inglés, tal como aparecen aquí.

### Valores por defecto o bloqueados

En cada sección, `lock` decide qué se puede cambiar:

| `lock = …`              | Significado                                              |
|-------------------------|----------------------------------------------------------|
| sin poner o `false`     | son solo valores iniciales; la gente puede cambiarlos    |
| `true`                  | todos los ajustes de la sección quedan fijos             |
| `["wallpaper"]`         | solo quedan fijos los ajustes nombrados                  |

### `[organisation]`

`name` (nombre), `contact` (correo o teléfono de ayuda), `website`.

### `[appearance]` (aspecto)

| Nombre          | Valores                                                                   |
|-----------------|---------------------------------------------------------------------------|
| `style`         | `"glass"` (cristal) o `"classic"` (clásico)                               |
| `colour_scheme` | `"light"` (claro), `"dark"` (oscuro) o `"auto"`                           |
| `accent`        | `"blue"` `"teal"` `"green"` `"yellow"` `"orange"` `"red"` `"pink"` `"purple"` `"slate"` |
| `icon_style`    | `"standard"` `"dark"` `"glass"` `"mono"`                                  |
| `wallpaper`     | la ruta completa de una imagen, p. ej. `"/usr/share/backgrounds/escuela.jpg"` |

### `[screen]` (pantalla)

| Nombre               | Valores                                                     |
|----------------------|-------------------------------------------------------------|
| `lock_after_minutes` | minutos sin uso antes de apagar y bloquear la pantalla (`0` = nunca) |
| `lock_enabled`       | `true` para pedir la contraseña al volver                   |

### `[privacy]` (privacidad)

| Nombre             | Valores                                                     |
|--------------------|-------------------------------------------------------------|
| `location`         | `false` apaga la ubicación                                  |
| `camera`           | `false` apaga la cámara para todas las apps                 |
| `microphone`       | `false` apaga el micrófono para todas las apps              |
| `phone_connection` | `false` apaga la conexión con el teléfono                   |
| `usage_history`    | `false` deja de guardar los archivos usados recientemente   |

### `[extensions]` (extensiones)

| Nombre            | Valores                                                       |
|-------------------|---------------------------------------------------------------|
| `allow_install`   | `false`: no se pueden instalar extensiones nuevas de la web   |
| `user_extensions` | `false`: solo funcionan las extensiones instaladas para todos |
| `enabled`         | la lista de extensiones activas                               |

### `[apps]`

`dock`: las apps del dock, como lista de identificadores `.desktop`, p. ej.
`["es.parchaos.Browser.desktop", "org.gnome.Nautilus.desktop"]`.

### `[updates]` (actualizaciones)

Sin esta sección se avisa a cada persona cuando hay actualizaciones. Con ella, la computadora se
actualiza sola:

| Nombre          | Valores                                                                |
|-----------------|------------------------------------------------------------------------|
| `mode`          | `"notify"` (avisar), `"download"` (descargar; las instala una persona), `"install"` (instalar solas), `"off"` |
| `when`          | cuándo, en el formato de systemd: `"daily"`, `"Sat 03:00"`, `"Mon..Fri 18:30"` |
| `reboot`        | `"never"` (nunca) o `"when-needed"` (reiniciar si hace falta)          |
| `security_only` | `true` instala solo los arreglos de seguridad                          |

### `[browser]` (Parcha Browser)

Parcha Browser se basa en Chromium y acepta sus políticas: `NombreDePolítica = valor`. La lista
completa está en [chromeenterprise.google/policies](https://chromeenterprise.google/policies/).

```toml
[browser]
HomepageLocation = "https://escuela.example"
PasswordManagerEnabled = false
URLBlocklist = ["juegos.example"]
ForceGoogleSafeSearch = true
```

### `[settings]`: cualquier otro ajuste

Cualquier otro ajuste de GNOME o ParchaOS, por su ruta de dconf:

```toml
[settings]
"org/gnome/desktop/interface/clock-format" = "24h"
lock = ["org/gnome/desktop/interface/clock-format"]
```

## Muchas computadoras

Basta con copiar el archivo: a mano o desde una memoria USB (la línea `sudo install` de arriba),
con Ansible (`ansible.builtin.copy` a `/etc/parchaos/policy.toml`), o con un paquete RPM propio
que instale ese archivo.

## Qué cambia en la computadora

Lo mismo que en la [versión en inglés](admin-guide.md#what-it-changes-on-the-computer): archivos
estándar de Fedora (dconf, políticas de Chromium, `dnf5-automatic`), y al quitar la política se
borran exactamente esos archivos.
