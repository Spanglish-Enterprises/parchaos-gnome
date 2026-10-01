// SPDX-License-Identifier: GPL-3.0-or-later
// ParchaOS glass: a pane that shows a refracted, blurred, tinted copy of the desktop behind it,
// with a curved-bezel lens, rim light and a soft shadow, like liquid glass.
//
// The optical model (superellipse bezel height, Snell refraction through its normal, an edge lens
// that builds towards the rim, a rim light that follows the light direction, an inner shadow on the
// side away from the light, a cool drop shadow) follows the approach of the MIT-licensed
// liquid-glass GNOME extension by Ryosuke Watanabe (https://github.com/ryohsuke1231/liquid-glass).
// This file is a separate implementation for ParchaOS: it draws one pane per actor from a
// Clutter.Clone of the desktop instead of capturing the whole screen.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import GObject from 'gi://GObject';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

const FRAG = `
uniform sampler2D tex;
uniform float u_w;          // pane width, px
uniform float u_h;          // pane height, px
uniform float u_pad;        // room around the pane in the texture (refraction reach and shadow)
uniform float u_radius;     // corner radius
uniform float u_band;       // width of the curved bezel, px
uniform float u_falloff;    // how the lens builds towards the rim
uniform float u_n;          // bezel profile shape (superellipse exponent)
uniform float u_z;          // bezel height (steepness)
uniform float u_ior;        // index of refraction
uniform float u_disp;       // refraction scale, px
uniform float u_chroma;     // colour fringing, px
uniform float u_blur;       // backdrop blur radius, px
uniform float u_tint;       // tint strength 0..1
uniform float u_tr;
uniform float u_tg;
uniform float u_tb;
uniform float u_bright;
uniform float u_contrast;
uniform float u_sat;
uniform float u_rim;        // rim light strength
uniform float u_rimw;       // rim width, px
uniform float u_rimdir;     // rim directional power
uniform float u_rimpow;     // rim fresnel power
uniform float u_spec;       // specular strength
uniform float u_shin;       // specular shininess
uniform float u_sheen;      // surface sheen
uniform float u_light;      // light direction, radians (screen, y down)
uniform float u_ao;         // inner shadow strength
uniform float u_aor;        // inner shadow reach, px
uniform float u_shr;        // drop shadow radius, px
uniform float u_shi;        // drop shadow strength

float sdRoundRect(vec2 p, vec2 b, float r) {
    vec2 d = abs(p) - b + vec2(r);
    return min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - r;
}

vec2 sdDir(vec2 p, vec2 b, float r) {
    vec2 q = abs(p) - b + vec2(r);
    if (max(q.x, q.y) < 0.0)
        return (q.x > q.y) ? vec2(sign(p.x), 0.0) : vec2(0.0, sign(p.y));
    return sign(p) * normalize(max(q, vec2(0.0)) + vec2(1e-6));
}

// superellipse bezel: h = H (1 - (1 - t)^n)^(1/n), t: edge 0 -> inner end 1
float height(float d, float band) {
    float t = clamp(-d / band, 0.0, 1.0);
    float n = max(u_n, 1.01);
    float inner = max(1.0 - pow(1.0 - t, n), 0.0);
    float fade = 1.0 - smoothstep(-0.5, 0.5, d);
    return pow(inner, 1.0 / n) * u_z * fade;
}

vec3 tap(vec2 px) {
    return texture2D(tex, px / (vec2(u_w, u_h) + 2.0 * vec2(u_pad))).rgb;
}

// blurred backdrop: golden-spiral taps, wider along the lens near the rim
vec3 backdrop(vec2 px, vec2 stretch) {
    vec3 acc = tap(px);
    float ws = 1.0;
    for (int i = 0; i < 12; i++) {
        float a = float(i) * 2.399963;
        float rr = u_blur * sqrt((float(i) + 0.5) / 12.0);
        vec2 o = vec2(cos(a), sin(a)) * rr + stretch * ((float(i) + 0.5) / 12.0 - 0.5);
        acc += tap(px + o);
        ws += 1.0;
    }
    return acc / ws;
}

float dither(vec2 p) {
    return (fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453) - 0.5) / 255.0;
}

void main() {
    vec2 size = vec2(u_w, u_h);
    vec2 px = cogl_tex_coord_in[0].xy * (size + 2.0 * vec2(u_pad));
    vec2 p = px - vec2(u_pad) - size * 0.5;
    vec2 b = size * 0.5;
    float r = min(u_radius, min(b.x, b.y));
    float d = sdRoundRect(p, b, r);

    float band = max(min(u_band, min(b.x, b.y)), 1.0);
    float lensScale = band / max(u_band, 1.0);

    float inside = 1.0 - smoothstep(-0.75, 0.75, d);

    // drop shadow (outside only): umbra at the edge, quintic penumbra, tinted cool
    float la = u_light;
    vec2 L2 = vec2(cos(la), -sin(la));
    float away = max(dot(normalize(p + vec2(1e-4)), -L2), 0.0);
    float sr = max(u_shr * (0.85 + 0.15 * away), 0.001);
    float um = (1.0 - clamp(d / max(sr * 0.4, 0.5), 0.0, 1.0)) * 0.8;
    float pf = 1.0 - clamp(d / sr, 0.0, 1.0);
    float pe = pf * pf * pf * (pf * (pf * 6.0 - 15.0) + 10.0) * 0.55;
    float shadow = clamp((um + pe) * (1.0 - inside) * u_shi * (0.85 + 0.15 * away), 0.0, 1.0);
    shadow *= 1.0 - step(u_pad, d);

    if (d > 0.0 + 4.0 && shadow < 0.002) {
        cogl_color_out = vec4(0.0);
        return;
    }

    // surface normal from the bezel height
    float e = 0.8;
    vec2 dir = sdDir(p, b, r);
    float hOut = height(d + e, band);
    float hIn = height(d - e, band);
    vec2 grad = dir * ((hOut - hIn) / (2.0 * e));
    vec3 N = normalize(vec3(-grad, 1.0));

    // refraction through the bezel (Snell), strongest at the rim
    vec3 refr = refract(vec3(0.0, 0.0, -1.0), N, 1.0 / max(u_ior, 1.001));
    vec2 disp = vec2(0.0);
    if (length(refr) > 1e-4 && d < 0.0) {
        float safeZ = max(-refr.z, 0.15);
        disp = (refr.xy / safeZ) * u_disp;
    }
    float edgeT = clamp(1.0 + d / band, 0.0, 1.0);
    float lens = pow(edgeT, u_falloff);
    vec2 dispPx = disp * lens * lensScale;
    float dl = length(dispPx);
    if (dl > 96.0)
        dispPx *= 96.0 / dl;
    vec2 stretch = dl > 2.0 ? dispPx * 0.5 : vec2(0.0);

    vec2 cdir = dl > 1e-3 ? normalize(dispPx) : vec2(0.0);
    vec2 cv = cdir * u_chroma * lens;
    vec3 col;
    col.r = backdrop(px + dispPx + cv, stretch).r;
    col.g = backdrop(px + dispPx, stretch).g;
    col.b = backdrop(px + dispPx - cv, stretch).b;

    // brightness / contrast / saturation, then tint
    col *= u_bright;
    col = mix(vec3(0.5), col, u_contrast);
    float lum = dot(col, vec3(0.299, 0.587, 0.114));
    col = max(mix(vec3(lum), col, u_sat), 0.0);
    col = mix(col, vec3(u_tr, u_tg, u_tb), u_tint);

    // light
    vec3 Ld = normalize(vec3(cos(la), sin(la), 0.38));
    // screen y points down; the light angle is measured with y up
    Ld.y = -Ld.y;
    float lightMask = pow(abs(dot(N, Ld)), max(u_rimdir, 1.0));
    float aoMask = 1.0 - smoothstep(0.0, max(u_aor, 0.001), -d);
    col *= 1.0 - aoMask * u_ao * (1.0 - lightMask);

    float rw = max(u_rimw, 0.001);
    float band2 = 1.0 - smoothstep(0.0, rw, abs(d));
    float fres = pow(max(1.0 - max(N.z, 0.0), 0.0), max(u_rimpow, 0.001));
    float rimShape = mix(pow(band2, 0.85), fres, 0.55) * band2;
    float rimL = rimShape * lightMask * u_rim;

    vec3 R = reflect(-Ld, N);
    float spec = pow(max(R.z, 0.0), max(u_shin, 1.0)) * u_spec * mix(0.25, 1.0, inside) * clamp(band2 + inside * 0.65, 0.0, 1.0);
    float sheen = pow(max(dot(N, Ld), 0.0), 1.65) * mix(1.0, 0.55, band2) * u_sheen;
    vec3 add = vec3(spec + rimL + band2 * 0.008 + sheen);
    vec3 lit = col + add - col * add;
    float mx = max(lit.r, max(lit.g, lit.b));
    if (mx > 1.0)
        lit /= mx;
    lit = max(lit, 0.0);

    vec3 shadowColor = vec3(0.03, 0.04, 0.08);
    float sc = shadow * (1.0 - inside);
    vec3 rgb = lit * inside + shadowColor * sc;
    float a = inside + sc;
    rgb = max(rgb + dither(px) * a, 0.0);
    cogl_color_out = vec4(rgb, a);
}
`;

export const GLASS_DEFAULTS = {
    radius: 34, band: 22, falloff: 2.0, n: 3.6, z: 88, ior: 2.4, disp: 30, chroma: 1.2,
    blur: 7.0, tint: 0.2, tintc: [0.07, 0.07, 0.08], bright: 1.0, contrast: 1.0, sat: 1.2,
    rim: 0.55, rimw: 2.3, rimdir: 1.9, rimpow: 3.0, spec: 0.0, shin: 42, sheen: 0.0,
    light: 135 * Math.PI / 180, ao: 0.22, aor: 14, shr: 36, shi: 0.2, pad: 44,
};

function floatValue(v) {
    const value = new GObject.Value();
    value.init(GObject.TYPE_FLOAT);
    value.set_float(v);
    return value;
}

export const GlassPane = GObject.registerClass(
class GlassPane extends St.Widget {
    _init(params = {}) {
        super._init({reactive: false});
        this._p = Object.assign({}, GLASS_DEFAULTS, params);
        this._inner = new Clutter.Actor();
        // The wallpaper and the windows above it, both as the desktop shows them.
        this._clone = new Clutter.Clone({source: Main.layoutManager._backgroundGroup});
        this._windows = new Clutter.Clone({source: global.window_group});
        this._inner.add_child(this._clone);
        this._inner.add_child(this._windows);
        this.add_child(this._inner);
        this._effect = new Clutter.ShaderEffect();
        this._effect.set_shader_source(FRAG);
        this._inner.add_effect(this._effect);
        this.connect('notify::allocation', () => this._sync());
        this.connect('notify::mapped', () => {
            this._watch();
            this._sync();
        });
        this.connect('destroy', () => {
            this._unwatch();
            if (this._retry)
                GLib.source_remove(this._retry);
            this._retry = 0;
        });
    }

    // Every frame, check whether the pane moved (menus slide, panels open), so the copy of the
    // desktop stays lined up with what is behind the pane.
    _watch() {
        if (this._frameId || !this.mapped)
            return;
        this._frameId = global.stage.connect('before-update', () => {
            if (!this.mapped)
                return;
            const [x, y] = this.get_transformed_position();
            if (x !== this._lastX || y !== this._lastY) {
                this._lastX = x;
                this._lastY = y;
                this._sync();
            }
        });
    }

    _unwatch() {
        if (this._frameId)
            global.stage.disconnect(this._frameId);
        this._frameId = 0;
    }

    set(params) {
        Object.assign(this._p, params);
        this._sync();
    }

    // Place the clone so the part of the desktop under the pane (plus padding) shows in it.
    _sync() {
        const p = this._p;
        const pad = p.pad;
        const [w, h] = this.get_size();
        if (w <= 0 || h <= 0)
            return;
        const [ax, ay] = this.get_transformed_position();
        if (!Number.isFinite(ax) || !Number.isFinite(ay)) {
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
        this._windows.set_position(-(ax - pad), -(ay - pad));
        const f = (k, v) => this._effect.set_uniform_value(k, floatValue(v));
        const tex = new GObject.Value();
        tex.init(GObject.TYPE_INT);
        tex.set_int(0);
        this._effect.set_uniform_value('tex', tex);
        f('u_w', w); f('u_h', h); f('u_pad', pad);
        f('u_radius', p.radius); f('u_band', p.band); f('u_falloff', p.falloff); f('u_n', p.n); f('u_z', p.z);
        f('u_ior', p.ior); f('u_disp', p.disp); f('u_chroma', p.chroma); f('u_blur', p.blur);
        f('u_tint', p.tint); f('u_bright', p.bright); f('u_contrast', p.contrast); f('u_sat', p.sat);
        f('u_rim', p.rim); f('u_rimw', p.rimw); f('u_rimdir', p.rimdir); f('u_rimpow', p.rimpow);
        f('u_spec', p.spec); f('u_shin', p.shin); f('u_sheen', p.sheen); f('u_light', p.light);
        f('u_ao', p.ao); f('u_aor', p.aor); f('u_shr', p.shr); f('u_shi', p.shi);
        f('u_tr', p.tintc[0]); f('u_tg', p.tintc[1]); f('u_tb', p.tintc[2]);
        this._effect.queue_repaint();
    }
});
