# parchaos-ambient

Ambient Sounds for ParchaOS (ticket #183): rain, ocean, stream, night, and white, pink and brown
noise, with a volume, a tone control and a timer (15 minutes to 8 hours).

## Where the sounds come from

Every sound is generated while it plays. GStreamer's test source makes the noise (white, pink,
brown) and the tones; filters shape it (high-, low- and band-pass); slow random level changes make
the waves, the moving water, the rain drops and the insect calls. There are no recordings in this
package, so it carries no third-party sound licences, and nothing is taken from any other desktop.

## Controls

- Parcha Controls: "Ambient Sounds" in Sound and Media (hidden until added in Edit Controls).
- ParchaOS Settings > Sound: sound, volume, tone, timer, Play/Stop.
- Command line: `parchaos-ambient play [rain|ocean|stream|night|white|pink|brown]`, `stop`,
  `toggle`, `status`.

The player is the D-Bus service `org.parchaos.Ambient` and only runs while a sound plays. Its
settings are the `ambient-*` keys of `org.parchaos.desktop`.
