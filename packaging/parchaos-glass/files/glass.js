// SPDX-License-Identifier: GPL-3.0-or-later
// ParchaOS glass: a pane that shows a refracted, lightly blurred, tinted copy of the
// desktop behind it, with a bright rim, like liquid glass. Original code for ParchaOS.
import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

// The pane is drawn into a texture a little larger than the pane (PAD each side) so the lens
// can pull in pixels from beyond the edge. Everything below is in texture pixels.
const FRAG = `
uniform sampler2D tex;
uniform float u_w;        // pane width
uniform float u_h;        // pane height
uniform float u_pad;      // padding around the pane in the texture
uniform float u_radius;   // corner radius
uniform float u_bezel;    // width of the curved edge (where light bends)
uniform float u_refract;  // how far the edge pulls the picture, px
uniform float u_blur;     // blur radius, px
uniform float u_tint;     // 0..1 tint strength
uniform float u_sat;      // saturation
uniform float u_rim;      // rim light strength
uniform float u_disp;     // colour fringing, px
uniform float u_light;    // light direction, radians
uniform float u_dark;     // 1 for a dark pane, 0 light

float sdRoundBox(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + r;
    return length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;
}

vec3 sampleAt(vec2 px) {
    vec2 uv = (px) / vec2(u_w + 2.0 * u_pad, u_h + 2.0 * u_pad);
    return texture2D(tex, uv).rgb;
}

vec3 blurAt(vec2 px, float r) {
    if (r < 0.5)
        return sampleAt(px);
    vec3 acc = sampleAt(px) * 0.2;
    float wsum = 0.2;
    for (int i = 0; i < 12; i++) {
        float a = float(i) * 2.399963;          // golden angle
        float rr = r * sqrt((float(i) + 0.5) / 12.0);
        vec2 o = vec2(cos(a), sin(a)) * rr;
        acc += sampleAt(px + o) * 0.8 / 12.0 * 1.0;
        wsum += 0.8 / 12.0;
    }
    return acc / wsum;
}

void main() {
    vec2 size = vec2(u_w, u_h);
    vec2 px = cogl_tex_coord_in[0].xy * (size + 2.0 * u_pad);
    vec2 p = px - u_pad - size * 0.5;                  // from the pane centre
    float sd = sdRoundBox(p, size * 0.5, u_radius);    // < 0 inside
    if (sd > 1.0) {
        cogl_color_out = vec4(0.0);
        return;
    }
    float inside = clamp(0.5 - sd, 0.0, 1.0);          // anti-aliased mask
    float depth = clamp(-sd / u_bezel, 0.0, 1.0);      // 0 at the edge, 1 where flat

    // outward normal from the signed distance field
    float e = 1.0;
    vec2 n = normalize(vec2(
        sdRoundBox(p + vec2(e, 0.0), size * 0.5, u_radius) - sdRoundBox(p - vec2(e, 0.0), size * 0.5, u_radius),
        sdRoundBox(p + vec2(0.0, e), size * 0.5, u_radius) - sdRoundBox(p - vec2(0.0, e), size * 0.5, u_radius)) + 1e-5);

    // a convex lens: slope is steep at the edge and zero in the middle
    float slope = 1.0 - sqrt(1.0 - (1.0 - depth) * (1.0 - depth));
    float bend = (1.0 - depth) > 0.0 ? pow(1.0 - depth, 2.0) : 0.0;
    vec2 shift = -n * u_refract * bend * (0.35 + 0.65 * slope);

    vec3 col;
    col.r = blurAt(px + shift * (1.0 + u_disp * 0.04), u_blur).r;
    col.g = blurAt(px + shift, u_blur).g;
    col.b = blurAt(px + shift * (1.0 - u_disp * 0.04), u_blur).b;

    // saturation and a smoky tint (dark panes tint toward black, light ones toward white)
    float lum = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(lum), col, u_sat);
    vec3 tint = mix(vec3(0.97), vec3(0.04), u_dark);
    col = mix(col, tint, u_tint);

    // the curved edge darkens a little, like thick glass seen through its side
    float shade = smoothstep(1.0, 0.0, depth);
    col *= 1.0 - 0.22 * shade * shade;

    // rim light: a thin grey line, brighter where the edge faces the light (top-left)
    // and weaker on the opposite side (bottom-right)
    vec2 L = vec2(cos(u_light), sin(u_light));
    float facing = dot(n, L);
    float line = smoothstep(2.4, 0.0, -sd);               // ~2px band along the edge
    float spec = 0.28 + 0.72 * pow(max(facing, 0.0), 2.0) + 0.38 * pow(max(-facing, 0.0), 2.0);
    float glowBand = pow(1.0 - depth, 6.0);               // faint inner glow
    col += vec3(0.86, 0.88, 0.92) * (line * spec * u_rim + glowBand * spec * u_rim * 0.35);

    cogl_color_out = vec4(clamp(col, 0.0, 1.0) * inside, inside);
}
`;

export const GlassPane = GObject.registerClass(
class GlassPane extends St.Widget {
    _init(params = {}) {
        super._init({reactive: false, clip_to_allocation: false});
        this._p = Object.assign({
            radius: 34, bezel: 22, refract: 34, blur: 2.5, tint: 0.22, sat: 1.15,
            rim: 0.9, disp: 1.0, light: -2.35, dark: 1, pad: 48,
        }, params);
        this._inner = new Clutter.Actor();
        this._clone = new Clutter.Clone({source: Main.layoutManager._backgroundGroup});
        this._inner.add_child(this._clone);
        this.add_child(this._inner);
        this._effect = new Clutter.ShaderEffect();
        this._effect.set_shader_source(FRAG);
        this._inner.add_effect(this._effect);
        this.connect('notify::allocation', () => this._sync());
        this.connect('notify::mapped', () => this._sync());
        this.connect('destroy', () => { if (this._retry) GLib.source_remove(this._retry); this._retry = 0; });
    }

    // Place the clone so the part of the desktop under the pane (plus padding) shows in it.
    _sync() {
        const pad = this._p.pad;
        const [w, h] = this.get_size();
        if (w <= 0 || h <= 0)
            return;
        const [ax, ay] = this.get_transformed_position();
        if (!Number.isFinite(ax) || !Number.isFinite(ay)) {
            // Not positioned yet: try again once the layout has settled.
            if (!this._retry) {
                this._retry = GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
                    this._retry = 0;
                    this._sync();
                    return GLib.SOURCE_REMOVE;
                });
            }
            return;
        }
        this._inner.set_position(-pad, -pad);
        this._inner.set_size(w + 2 * pad, h + 2 * pad);
        this._inner.set_clip(0, 0, w + 2 * pad, h + 2 * pad);
        this._clone.set_position(-(ax - pad), -(ay - pad));
        const p = this._p;
        const set = (k, v) => {
            const value = new GObject.Value();
            value.init(GObject.TYPE_FLOAT);
            value.set_float(v);
            this._effect.set_uniform_value(k, value);
        };
        const tex = new GObject.Value();
        tex.init(GObject.TYPE_INT);
        tex.set_int(0);
        this._effect.set_uniform_value('tex', tex);
        set('u_w', w); set('u_h', h); set('u_pad', pad);
        set('u_radius', Math.min(p.radius, Math.min(w, h) / 2));
        set('u_bezel', p.bezel); set('u_refract', p.refract); set('u_blur', p.blur);
        set('u_tint', p.tint); set('u_sat', p.sat); set('u_rim', p.rim); set('u_disp', p.disp);
        set('u_light', p.light); set('u_dark', p.dark);
        this._effect.queue_repaint();
    }
});
