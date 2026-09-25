// SPDX-License-Identifier: GPL-3.0-or-later

// src/logger.ts
import Gio from "gi://Gio";
var schemaId = "io.github.jeffshee.hanabi-extension";
var logPrefix = "Hanabi:";
var Logger = class {
  settings;
  logOpt;
  isDebugMode;
  constructor(opt) {
    const settingsSchemaSource = Gio.SettingsSchemaSource.get_default();
    if (settingsSchemaSource?.lookup(schemaId, false))
      this.settings = Gio.Settings.new(schemaId);
    this.logOpt = opt;
    this.isDebugMode = this.settings ? this.settings.get_boolean("debug-mode") : false;
    this.settings?.connect("changed::debug-mode", () => {
      this.isDebugMode = this.settings.get_boolean("debug-mode");
    });
  }
  processArgs(args) {
    args.unshift(
      this.logOpt ? `${logPrefix} (${this.logOpt})` : logPrefix
    );
    return args;
  }
  log(...args) {
    console.log(...this.processArgs(args));
  }
  debug(...args) {
    args = this.processArgs(args);
    if (this.isDebugMode)
      console.log(...args);
    else
      console.debug(...args);
  }
  warn(...args) {
    console.warn(...this.processArgs(args));
  }
  error(...args) {
    console.error(...this.processArgs(args));
  }
  trace(...args) {
    console.trace(...this.processArgs(args));
  }
};
function getMethods(obj) {
  const properties = /* @__PURE__ */ new Set();
  let currentObj = obj;
  do {
    Object.getOwnPropertyNames(currentObj).forEach(
      (item) => properties.add(item)
    );
  } while (currentObj = Object.getPrototypeOf(currentObj));
  return [...properties.keys()].filter((item) => typeof obj[item] === "function");
}

// src/roundedCornersEffect.ts
import Cogl from "gi://Cogl";
import GLib from "gi://GLib";
import GObject from "gi://GObject";
import Shell from "gi://Shell";
var logger = new Logger("roundedCorners");
var LOG_DEBOUNCE_MS = 250;
var fragmentShaderDeclarations = [
  "uniform vec4 bounds;           // x, y: top left; z, w: bottom right     \n",
  "uniform float clip_radius;                                               \n",
  "uniform vec2 pixel_step;                                                 \n",
  "uniform float border_stroke;                                             \n",
  "uniform vec4 border_color;                                               \n",
  "                                                                         \n",
  "float                                                                    \n",
  "rounded_rect_coverage (vec2 p)                                           \n",
  "{                                                                        \n",
  "  float center_left  = bounds.x + clip_radius;                           \n",
  "  float center_right = bounds.z - clip_radius;                           \n",
  "  float center_x;                                                        \n",
  "                                                                         \n",
  "  if (p.x < center_left)                                                 \n",
  "    center_x = center_left;                                              \n",
  "  else if (p.x > center_right)                                           \n",
  "    center_x = center_right;                                             \n",
  "  else                                                                   \n",
  "    return 1.0; // The vast majority of pixels exit early here           \n",
  "                                                                         \n",
  "  float center_top    = bounds.y + clip_radius;                          \n",
  "  float center_bottom = bounds.w - clip_radius;                          \n",
  "  float center_y;                                                        \n",
  "                                                                         \n",
  "  if (p.y < center_top)                                                  \n",
  "    center_y = center_top;                                               \n",
  "  else if (p.y > center_bottom)                                          \n",
  "    center_y = center_bottom;                                            \n",
  "  else                                                                   \n",
  "    return 1.0;                                                          \n",
  "                                                                         \n",
  "  vec2 delta = p - vec2 (center_x, center_y);                            \n",
  "  float dist_squared = dot (delta, delta);                               \n",
  "                                                                         \n",
  "  // Fully outside the circle                                            \n",
  "  float outer_radius = clip_radius + 0.5;                                \n",
  "  if (dist_squared >= (outer_radius * outer_radius))                     \n",
  "    return 0.0;                                                          \n",
  "                                                                         \n",
  "  // Fully inside the circle                                             \n",
  "  float inner_radius = clip_radius - 0.5;                                \n",
  "  if (dist_squared <= (inner_radius * inner_radius))                     \n",
  "    return 1.0;                                                          \n",
  "                                                                         \n",
  "  // Only pixels on the edge of the curve need expensive antialiasing    \n",
  "  return outer_radius - sqrt (dist_squared);                             \n",
  "}                                                                        \n"
].join("");
var fragmentShaderCode = [
  "vec2 texture_coord;                                                      \n",
  "                                                                         \n",
  "texture_coord = cogl_tex_coord0_in.xy / pixel_step;                      \n",
  "                                                                         \n",
  "bool inside = texture_coord.x >= bounds.x && texture_coord.x <= bounds.z \n",
  "           && texture_coord.y >= bounds.y && texture_coord.y <= bounds.w;\n",
  "                                                                         \n",
  "// border stroke for debug purposes                                      \n",
  "bool on_border = border_stroke > 0.0 && inside && (                      \n",
  "    texture_coord.x < bounds.x + border_stroke ||                        \n",
  "    texture_coord.x > bounds.z - border_stroke ||                        \n",
  "    texture_coord.y < bounds.y + border_stroke ||                        \n",
  "    texture_coord.y > bounds.w - border_stroke);                         \n",
  "                                                                         \n",
  "if (on_border)                                                           \n",
  "    cogl_color_out = border_color;                                       \n",
  "else if (clip_radius > 0.0 && !inside)                                   \n",
  "    cogl_color_out = vec4 (0.0);                                         \n",
  "else if (clip_radius > 0.0)                                              \n",
  "    cogl_color_out *= rounded_rect_coverage (texture_coord);             \n"
].join("");
function enlargeForEffects(x1, y1, width, height) {
  if (width <= 0 || height <= 0)
    return [x1, y1];
  const x2 = Math.ceil(x1 + width + 0.75);
  const y2 = Math.ceil(y1 + height + 0.75);
  return [x2 - Math.round(width) - 3, y2 - Math.round(height) - 3];
}
function getFboOffset(actor) {
  const volume = actor.get_paint_volume();
  if (volume) {
    const origin = volume.get_origin();
    const [x12, y12] = enlargeForEffects(
      origin.x,
      origin.y,
      volume.get_width(),
      volume.get_height()
    );
    return [Math.trunc(x12), Math.trunc(y12)];
  }
  const box = actor.get_allocation_box();
  const [x1, y1] = enlargeForEffects(
    box.x1,
    box.y1,
    box.x2 - box.x1,
    box.y2 - box.y1
  );
  return [Math.trunc(x1 - box.x1), Math.trunc(y1 - box.y1)];
}
var RoundedCornersEffect = GObject.registerClass(
  class RoundedCornersEffect2 extends Shell.GLSLEffect {
    // Pending debounced log timers, keyed by label.
    logTimeouts = /* @__PURE__ */ new Map();
    // Uniform values in actor-local logical pixels, as set by callers.
    bounds = [0, 0, 0, 0];
    clipRadius = 0;
    borderStroke = 0;
    uniformsDirty = true;
    // Actor-to-texture mapping the uniforms were last uploaded for.
    textureWidth = 0;
    textureHeight = 0;
    textureScale = 0;
    textureOffsetX = 0;
    textureOffsetY = 0;
    // Logs `label: ...args` only once the value stops changing for LOG_DEBOUNCE_MS.
    debugDebounced(label, ...args) {
      const pending = this.logTimeouts.get(label);
      if (pending)
        GLib.source_remove(pending);
      this.logTimeouts.set(
        label,
        GLib.timeout_add(GLib.PRIORITY_DEFAULT, LOG_DEBOUNCE_MS, () => {
          this.logTimeouts.delete(label);
          logger.debug(`${label}:`, ...args);
          return GLib.SOURCE_REMOVE;
        })
      );
    }
    vfunc_build_pipeline() {
      this.add_glsl_snippet(
        Cogl.SnippetHook.FRAGMENT,
        fragmentShaderDeclarations,
        fragmentShaderCode,
        false
      );
    }
    // The shader compares texture coordinates (converted to texture pixels
    // via pixel_step) against bounds/clip_radius/border_stroke, so those
    // uniforms must be expressed in pixels of the offscreen texture this
    // effect renders into. mutter sizes that texture from the actor's paint
    // box, not its allocation, and the relation between the two varies
    // across mutter versions (e.g. Clutter.Clone paint volumes changed in
    // 50.2, commit d26ac38b) and monitor scales (the texture uses the
    // ceiled resource scale). Instead of predicting the size, read the
    // actual texture at paint time and mirror mutter's actor-to-texture
    // mapping: texture_px = (logical_px - fbo_offset) * resource_scale.
    vfunc_paint_target(node, paintContext) {
      this.updateUniforms();
      super.vfunc_paint_target(node, paintContext);
    }
    updateUniforms() {
      const texture = this.get_texture();
      const actor = this.get_actor();
      if (!texture || !actor)
        return;
      const width = texture.get_width();
      const height = texture.get_height();
      const scale = actor.get_resource_scale();
      const [offsetX, offsetY] = getFboOffset(actor);
      if (!this.uniformsDirty && width === this.textureWidth && height === this.textureHeight && scale === this.textureScale && offsetX === this.textureOffsetX && offsetY === this.textureOffsetY)
        return;
      this.uniformsDirty = false;
      this.textureWidth = width;
      this.textureHeight = height;
      this.textureScale = scale;
      this.textureOffsetX = offsetX;
      this.textureOffsetY = offsetY;
      this.debugDebounced("textureMapping", width, height, scale, offsetX, offsetY);
      this.set_uniform_float(
        this.get_uniform_location("pixel_step"),
        2,
        [1 / width, 1 / height]
      );
      const [x1, y1, x2, y2] = this.bounds;
      this.set_uniform_float(
        this.get_uniform_location("bounds"),
        4,
        [
          (x1 - offsetX) * scale,
          (y1 - offsetY) * scale,
          (x2 - offsetX) * scale,
          (y2 - offsetY) * scale
        ]
      );
      this.set_uniform_float(
        this.get_uniform_location("clip_radius"),
        1,
        [this.clipRadius * scale]
      );
      this.set_uniform_float(
        this.get_uniform_location("border_stroke"),
        1,
        [this.borderStroke * scale]
      );
    }
    setBounds(bounds) {
      this.debugDebounced("bounds", ...bounds);
      this.bounds = bounds;
      this.uniformsDirty = true;
    }
    setClipRadius(clipRadius) {
      this.debugDebounced("clipRadius", clipRadius);
      this.clipRadius = clipRadius;
      this.uniformsDirty = true;
    }
    setBorderStroke(stroke) {
      this.debugDebounced("borderStroke", stroke);
      this.borderStroke = stroke;
      this.uniformsDirty = true;
    }
    setBorderColor(color) {
      this.debugDebounced("borderColor", ...color);
      this.set_uniform_float(
        this.get_uniform_location("border_color"),
        4,
        color
      );
    }
  }
);

// src/constants.ts
var APPLICATION_ID = "io.github.jeffshee.HanabiRenderer";
var RENDERER_OBJECT_PATH = `/${APPLICATION_ID.replaceAll(".", "/")}`;

// src/wallpaper.ts
import Clutter2 from "gi://Clutter";
import GLib2 from "gi://GLib";
import GObject2 from "gi://GObject";
import St from "gi://St";
import Graphene from "gi://Graphene";
import * as Main from "resource:///org/gnome/shell/ui/main.js";
var logger2 = new Logger("wallpaper");
var BACKGROUND_FADE_ANIMATION_TIME = 1e3;
var RENDERER_POLL_INTERVAL_MS = 1e3;
var LiveWallpaper = GObject2.registerClass(
  class LiveWallpaper2 extends St.Widget {
    // Background actor we sit on, and values derived from it.
    backgroundActor;
    // Meta.BackgroundGroup normally, or an St.Widget (with style_class) on the lock screen.
    metaBackgroundGroup;
    monitorIndex;
    // Injected dependencies.
    settings;
    // Returns all window actors unfiltered (renderer windows are hidden from the
    // public get_window_actors by GnomeShellOverride); injected so getRenderer can find them.
    getWindowActors;
    // Lifecycle bookkeeping, cleaned up on destroy.
    isDisposed = false;
    rendererPollTimeoutId = 0;
    settingsChangedIds = [];
    // The wallpaper clone and its source-destroy handler.
    wallpaper = null;
    sourceDestroyId = null;
    // Rendering effect and monitor geometry, set up in the constructor.
    roundedCornersEffect;
    monitorWidth;
    monitorHeight;
    constructor(backgroundActor, settings, getWindowActors) {
      super({
        layout_manager: new Clutter2.BinLayout(),
        width: backgroundActor.width,
        height: backgroundActor.height,
        x_expand: true,
        y_expand: true,
        opacity: 0
      });
      this.backgroundActor = backgroundActor;
      this.metaBackgroundGroup = backgroundActor.get_parent();
      this.monitorIndex = this.backgroundActor.monitor;
      this.settings = settings;
      this.getWindowActors = getWindowActors;
      this.connect("destroy", () => {
        this.isDisposed = true;
        if (this.rendererPollTimeoutId) {
          GLib2.source_remove(this.rendererPollTimeoutId);
          this.rendererPollTimeoutId = 0;
        }
        for (const id of this.settingsChangedIds)
          this.settings.disconnect(id);
        this.settingsChangedIds = [];
        if (this.wallpaper) {
          if (this.sourceDestroyId) {
            this.wallpaper.source?.disconnect(this.sourceDestroyId);
            this.sourceDestroyId = null;
          }
          this.wallpaper.set_source(null);
          this.wallpaper.destroy();
          this.wallpaper = null;
        }
      });
      const { width, height } = Main.layoutManager.monitors[this.monitorIndex];
      this.monitorWidth = width;
      this.monitorHeight = height;
      backgroundActor.layout_manager = new Clutter2.BinLayout();
      backgroundActor.add_child(this);
      this.roundedCornersEffect = new RoundedCornersEffect();
      this.backgroundActor.add_effect(this.roundedCornersEffect);
      this.setRoundedClipRadius(0);
      this.setBorderStroke(this.settings.get_int("border-stroke"));
      this.setBorderColor([1, 0, 0, 1]);
      this.settingsChangedIds.push(
        this.settings.connect("changed::border-stroke", () => {
          this.setBorderStroke(this.settings.get_int("border-stroke"));
          this.backgroundActor?.queue_redraw();
        })
      );
      this.setRoundedClipBounds(0, 0, this.monitorWidth, this.monitorHeight);
      this.connect("notify::allocation", () => this.applyBounds());
      this.applyWallpaper();
    }
    isLockScreen() {
      const group = this.metaBackgroundGroup;
      return group?.style_class?.includes("screen-shield-background") ?? false;
    }
    applyBounds() {
      const monitor = Main.layoutManager.monitors[this.monitorIndex];
      if (!monitor)
        return;
      const workArea = Main.layoutManager.getWorkAreaForMonitor(this.monitorIndex);
      const panelOffset = (workArea.y - monitor.y) / monitor.height * this.backgroundActor.height;
      this.roundedCornersEffect.setBounds(
        [0, panelOffset, this.width, this.height]
      );
    }
    setRoundedClipRadius(radius) {
      if (this.isDisposed)
        return;
      this.roundedCornersEffect.setClipRadius(radius);
    }
    setRoundedClipBounds(x1, y1, x2, y2) {
      if (this.isDisposed)
        return;
      this.roundedCornersEffect.setBounds([x1, y1, x2, y2]);
    }
    setBorderStroke(stroke) {
      if (this.isDisposed)
        return;
      this.roundedCornersEffect.setBorderStroke(stroke);
    }
    setBorderColor(color) {
      if (this.isDisposed)
        return;
      this.roundedCornersEffect.setBorderColor(color);
    }
    applyWallpaper() {
      if (this.isDisposed)
        return;
      logger2.debug("Applying wallpaper...");
      const operation = () => {
        if (this.isDisposed) {
          logger2.debug("LiveWallpaper disposed, stopping wallpaper operation");
          return false;
        }
        const renderer = this.getRenderer();
        if (renderer) {
          this.wallpaper = new Clutter2.Clone({
            source: renderer,
            pivot_point: new Graphene.Point({ x: 0.5, y: 0.5 })
          });
          this.wallpaper.connect("destroy", () => {
            this.wallpaper = null;
          });
          this.sourceDestroyId = this.wallpaper.source.connect(
            "destroy",
            () => {
              if (this.wallpaper)
                this.wallpaper.destroy();
              if (!this.isDisposed)
                this.applyWallpaper();
            }
          );
          this.add_child(this.wallpaper);
          this.fade();
          logger2.debug("Wallpaper applied");
          this.rendererPollTimeoutId = 0;
          return false;
        } else {
          return true;
        }
      };
      if (operation()) {
        this.rendererPollTimeoutId = GLib2.timeout_add(
          GLib2.PRIORITY_DEFAULT,
          RENDERER_POLL_INTERVAL_MS,
          operation
        );
      }
    }
    getRenderer() {
      const hanabiWindowActors = this.getWindowActors().filter(
        (actor) => actor.meta_window?.title?.includes(APPLICATION_ID)
      );
      const numMonitors = global.display.get_n_monitors();
      if (hanabiWindowActors.length < numMonitors) {
        logger2.debug(
          `Hanabi windows (${hanabiWindowActors.length}) < monitors (${numMonitors}), rejecting`
        );
        return null;
      }
      const monitorIndices = hanabiWindowActors.map((actor) => actor.meta_window.get_monitor());
      const uniqueMonitorIndices = new Set(monitorIndices);
      if (uniqueMonitorIndices.size !== monitorIndices.length) {
        logger2.debug("Non-unique monitor indices detected, rejecting");
        return null;
      }
      const monitorIndex = this.backgroundActor.monitor;
      const renderer = hanabiWindowActors.find(
        (actor) => actor.meta_window.get_monitor() === monitorIndex
      );
      if (!renderer) {
        logger2.debug(
          `No renderer found for monitor ${monitorIndex}. Found actors for monitors: ${monitorIndices}`
        );
      }
      return renderer ?? null;
    }
    fade(visible = true) {
      if (this.isDisposed)
        return;
      this.ease({
        opacity: visible ? 255 : 0,
        duration: BACKGROUND_FADE_ANIMATION_TIME,
        mode: Clutter2.AnimationMode.EASE_OUT_QUAD
      });
    }
  }
);

// src/gnomeShellOverride.ts
import Meta2 from "gi://Meta";
import St2 from "gi://St";
import Shell2 from "gi://Shell";
import GLib3 from "gi://GLib";
import { InjectionManager } from "resource:///org/gnome/shell/extensions/extension.js";
import * as Background from "resource:///org/gnome/shell/ui/background.js";
import * as Main2 from "resource:///org/gnome/shell/ui/main.js";
import * as Workspace from "resource:///org/gnome/shell/ui/workspace.js";
import * as WorkspaceThumbnail from "resource:///org/gnome/shell/ui/workspaceThumbnail.js";
var logger3 = new Logger("override");
var BACKGROUND_RELOAD_REFRESH_DELAY_MS = 500;
var GnomeShellOverride = class {
  // Method patching, plus the original get_window_actors captured from our override of it
  // (the override hides renderer windows, so LiveWallpaper uses this to still find them).
  injectionManager = new InjectionManager();
  getAllWindowActors = () => global.get_window_actors();
  // Live wallpaper actors we've injected.
  wallpaperActors = /* @__PURE__ */ new Set();
  // Settings and its tracked signal connections.
  settings;
  settingsChangedIds = [];
  constructor(settings) {
    this.settings = settings;
  }
  reloadBackgrounds() {
    logger3.debug("Reloading backgrounds");
    this.wallpaperActors.forEach((actor) => actor.destroy());
    this.wallpaperActors.clear();
    global.compositor.get_laters().add(Meta2.LaterType.BEFORE_REDRAW, () => {
      Main2.layoutManager._updateBackgrounds();
      if (Main2.screenShield?._dialog?._updateBackgrounds != null)
        Main2.screenShield._dialog._updateBackgrounds();
      try {
        Main2.overview._overview._controls._workspacesDisplay._updateWorkspacesViews();
      } catch {
      }
      return GLib3.SOURCE_REMOVE;
    });
    GLib3.timeout_add(GLib3.PRIORITY_DEFAULT, BACKGROUND_RELOAD_REFRESH_DELAY_MS, () => {
      const { _enabledExtensions } = Main2.extensionManager;
      if (_enabledExtensions?.includes("blur-my-shell@aunetx"))
        Main2.layoutManager.emit("monitors-changed");
      global.display.emit("workareas-changed");
      return GLib3.SOURCE_REMOVE;
    });
  }
  reloadLockScreenBackgrounds() {
    logger3.debug("Reloading lock screen backgrounds");
    for (const actor of [...this.wallpaperActors]) {
      if (actor.isLockScreen())
        actor.destroy();
    }
    global.compositor.get_laters().add(Meta2.LaterType.BEFORE_REDRAW, () => {
      if (Main2.screenShield?._dialog?._updateBackgrounds != null)
        Main2.screenShield._dialog._updateBackgrounds();
      return GLib3.SOURCE_REMOVE;
    });
  }
  enable() {
    logger3.debug("Installing overrides");
    const thisRef = this;
    this.injectionManager.overrideMethod(
      Background.BackgroundManager.prototype,
      "_createBackgroundActor",
      (originalMethod) => {
        return function() {
          const backgroundActor = originalMethod.call(this);
          const isLockScreen = this._container?.style_class?.includes("screen-shield-background") ?? false;
          if (isLockScreen && !thisRef.settings.get_boolean("show-on-lock-screen")) {
            logger3.debug("Skipping live wallpaper on lock screen");
            return backgroundActor;
          }
          logger3.debug(`Injecting live wallpaper (monitor ${backgroundActor.monitor})`);
          this.wallpaperActor = new LiveWallpaper(
            backgroundActor,
            thisRef.settings,
            thisRef.getAllWindowActors
          );
          thisRef.wallpaperActors.add(this.wallpaperActor);
          this.wallpaperActor.connect("destroy", (actor) => {
            thisRef.wallpaperActors.delete(actor);
            if (this.wallpaperActor === actor)
              this.wallpaperActor = void 0;
          });
          return backgroundActor;
        };
      }
    );
    this.injectionManager.overrideMethod(
      Workspace.WorkspaceBackground.prototype,
      "_updateBorderRadius",
      (originalMethod) => {
        return function() {
          originalMethod.call(this);
          const { scaleFactor } = St2.ThemeContext.get_for_stage(global.stage);
          const cornerRadius = scaleFactor * thisRef.settings.get_int("corner-radius");
          const radius = cornerRadius * this._stateAdjustment.value;
          this._bgManager.wallpaperActor?.setRoundedClipRadius(radius);
          const backgroundContent = this._bgManager.backgroundActor?.content;
          if (backgroundContent)
            backgroundContent.rounded_clip_radius = radius;
          this.style = `border-radius: ${thisRef.settings.get_int("corner-radius")}px`;
        };
      }
    );
    this.injectionManager.overrideMethod(
      Shell2.Global.prototype,
      "get_window_actors",
      (originalMethod) => {
        thisRef.getAllWindowActors = () => originalMethod.call(global);
        return function() {
          return originalMethod.call(this).filter(
            (actor) => !actor.meta_window?.title?.includes(APPLICATION_ID)
          );
        };
      }
    );
    this.injectionManager.overrideMethod(
      Workspace.Workspace.prototype,
      "_isOverviewWindow",
      (originalMethod) => {
        return function(window) {
          const isRenderer = window.title?.includes(APPLICATION_ID);
          return isRenderer ? false : originalMethod.apply(this, [window]);
        };
      }
    );
    this.injectionManager.overrideMethod(
      WorkspaceThumbnail.WorkspaceThumbnail.prototype,
      "_isOverviewWindow",
      (originalMethod) => {
        return function(window) {
          const isRenderer = window.title?.includes(APPLICATION_ID);
          return isRenderer ? false : originalMethod.apply(this, [window]);
        };
      }
    );
    this.injectionManager.overrideMethod(
      Meta2.Display.prototype,
      "get_tab_list",
      (originalMethod) => {
        return function(type, workspace) {
          return originalMethod.call(this, type, workspace).filter((metaWindow) => !metaWindow.title?.includes(APPLICATION_ID));
        };
      }
    );
    this.injectionManager.overrideMethod(
      Shell2.WindowTracker.prototype,
      "get_window_app",
      (originalMethod) => {
        return function(window) {
          const isRenderer = window.title?.includes(APPLICATION_ID);
          return isRenderer ? null : originalMethod.apply(this, [window]);
        };
      }
    );
    this.injectionManager.overrideMethod(
      Shell2.App.prototype,
      "get_windows",
      (originalMethod) => {
        return function() {
          return originalMethod.call(this).filter((metaWindow) => !metaWindow.title?.includes(APPLICATION_ID));
        };
      }
    );
    this.injectionManager.overrideMethod(
      Shell2.App.prototype,
      "get_n_windows",
      (_2) => {
        return function() {
          return this.get_windows().length;
        };
      }
    );
    this.injectionManager.overrideMethod(
      Shell2.AppSystem.prototype,
      "get_running",
      (originalMethod) => {
        return function() {
          return originalMethod.call(this).filter((app) => app.get_n_windows() > 0);
        };
      }
    );
    this.settingsChangedIds.push(
      this.settings.connect("changed::show-on-lock-screen", () => {
        this.reloadLockScreenBackgrounds();
      })
    );
    this.reloadBackgrounds();
  }
  disable() {
    logger3.debug("Removing overrides");
    for (const id of this.settingsChangedIds)
      this.settings.disconnect(id);
    this.settingsChangedIds = [];
    this.injectionManager.clear();
    this.reloadBackgrounds();
  }
};

// src/waylandSubprocess.ts
import Meta3 from "gi://Meta";
import Gio4 from "gi://Gio";
import GLib4 from "gi://GLib";
var logger4 = new Logger("waylandSubprocess");
var rendererLogger = new Logger("renderer");
var WaylandSubprocess = class {
  cancellable = new Gio4.Cancellable();
  subprocess = null;
  running = false;
  flags;
  launcher;
  waylandClient = null;
  dataInputStream = null;
  constructor(flags = Gio4.SubprocessFlags.NONE) {
    this.flags = flags | Gio4.SubprocessFlags.STDOUT_PIPE | Gio4.SubprocessFlags.STDERR_MERGE;
    this.launcher = new Gio4.SubprocessLauncher({ flags: this.flags });
  }
  spawn(argv) {
    this.waylandClient = Meta3.WaylandClient.new_subprocess(
      global.context,
      this.launcher,
      argv
    );
    this.subprocess = this.waylandClient.get_subprocess();
    if (this.launcher?.close)
      this.launcher.close();
    this.launcher = null;
    if (this.subprocess) {
      this.dataInputStream = Gio4.DataInputStream.new(
        this.subprocess.get_stdout_pipe()
      );
      this.readOutput();
      this.subprocess.wait_async(this.cancellable, () => {
        this.running = false;
        this.dataInputStream = null;
        this.cancellable = null;
      });
      this.running = true;
    }
    return this.subprocess;
  }
  setCwd(cwd) {
    this.launcher?.set_cwd(cwd);
  }
  readOutput() {
    if (!this.dataInputStream)
      return;
    this.dataInputStream.read_line_async(
      GLib4.PRIORITY_DEFAULT,
      this.cancellable,
      (object, res) => {
        try {
          const [output, length] = object.read_line_finish_utf8(res);
          if (length)
            rendererLogger.log(output);
        } catch (e) {
          if (e.matches?.(
            Gio4.IOErrorEnum,
            Gio4.IOErrorEnum.CANCELLED
          ))
            return;
          logger4.trace(e);
        }
        this.readOutput();
      }
    );
  }
  queryWindowBelongsTo(window) {
    if (!this.running)
      return false;
    try {
      return this.waylandClient.owns_window(window);
    } catch (e) {
      logger4.trace(e);
      return false;
    }
  }
  queryPidOfProgram() {
    if (!this.running)
      return 0;
    const pid = this.subprocess?.get_identifier();
    return pid ? parseInt(pid) : 0;
  }
};

// src/windowManager.ts
import GLib5 from "gi://GLib";
var logger5 = new Logger("windowManager");
var MINIMIZE_RESYNC_DELAY_MS = 250;
var ManagedWindow = class {
  window;
  signals = [];
  states = {
    position: [0, 0],
    keepAtBottom: false,
    keepMinimized: false,
    keepPosition: false
  };
  isDisposed = false;
  resyncTimeoutId = 0;
  constructor(window) {
    this.window = window;
    this.signals.push(
      window.connect("notify::title", () => {
        if (this.isDisposed)
          return;
        this.parseTitle();
      })
    );
    this.signals.push(
      window.connect_after("shown", () => {
        if (this.isDisposed)
          return;
        if (this.states.keepMinimized) {
          this.window.minimize();
          this.scheduleMinimizeResync();
        }
      })
    );
    this.signals.push(
      window.connect_after("raised", () => {
        if (this.isDisposed)
          return;
        if (this.states.keepAtBottom)
          this.window.lower();
      })
    );
    this.signals.push(
      window.connect("notify::above", () => {
        if (this.isDisposed)
          return;
        if (this.states.keepAtBottom && this.window.above)
          this.window.unmake_above();
      })
    );
    this.signals.push(
      window.connect("notify::minimized", () => {
        if (this.isDisposed)
          return;
        if (this.states.keepMinimized && !this.window.minimized)
          this.window.minimize();
      })
    );
    this.signals.push(
      window.connect("position-changed", () => {
        if (this.isDisposed)
          return;
        if (this.states.keepPosition) {
          const [x, y] = this.states.position;
          this.window.move_frame(true, x, y);
        }
      })
    );
    this.parseTitle();
  }
  parseTitle() {
    const title = this.window.title;
    if (title?.startsWith(`@${APPLICATION_ID}!`)) {
      const json = title.replace(`@${APPLICATION_ID}!`, "").split("|")[0];
      try {
        const newState = JSON.parse(json);
        this.states = { ...this.states, ...newState };
      } catch (e) {
        logger5.trace(e);
      }
    }
    this.refresh();
  }
  // After wake from suspend, a window can stay visible (and clickable) even
  // though mutter already considers it minimized, so minimize() alone does
  // nothing. Since mutter hides windows asynchronously, check again shortly
  // after: if the window is still visible, unminimize + minimize to force
  // mutter to actually hide it.
  scheduleMinimizeResync() {
    if (this.resyncTimeoutId)
      return;
    this.resyncTimeoutId = GLib5.timeout_add(
      GLib5.PRIORITY_DEFAULT,
      MINIMIZE_RESYNC_DELAY_MS,
      () => {
        this.resyncTimeoutId = 0;
        if (this.isDisposed || !this.states.keepMinimized)
          return GLib5.SOURCE_REMOVE;
        const actor = this.window.get_compositor_private();
        if (this.window.minimized && actor?.visible) {
          logger5.debug("Minimized window still mapped, forcing resync");
          this.window.unminimize();
          this.window.minimize();
        }
        return GLib5.SOURCE_REMOVE;
      }
    );
  }
  refresh() {
    if (this.states.keepAtBottom && this.window.above)
      this.window.unmake_above();
    if (this.states.keepMinimized && !this.window.minimized)
      this.window.minimize();
    this.scheduleMinimizeResync();
    if (this.states.keepPosition) {
      const [x, y] = this.states.position;
      this.window.move_frame(true, x, y);
    }
  }
  disconnect() {
    this.isDisposed = true;
    if (this.resyncTimeoutId) {
      GLib5.source_remove(this.resyncTimeoutId);
      this.resyncTimeoutId = 0;
    }
    this.signals.forEach((signal) => this.window.disconnect(signal));
  }
};
var WindowManager = class {
  windows;
  waylandClient;
  mapId;
  constructor() {
    this.windows = /* @__PURE__ */ new Set();
    this.waylandClient = null;
    this.mapId = null;
  }
  setWaylandClient(client) {
    this.waylandClient = client;
  }
  enable() {
    this.mapId = global.window_manager.connect_after(
      "map",
      (_wm, windowActor) => {
        const window = windowActor.get_meta_window();
        if (window && this.waylandClient && this.waylandClient.queryWindowBelongsTo(window))
          this.manageWindow(window);
      }
    );
  }
  disable() {
    this.windows.forEach((window) => this.releaseWindow(window));
    this.windows.clear();
    if (this.mapId !== null) {
      global.window_manager.disconnect(this.mapId);
      this.mapId = null;
    }
  }
  manageWindow(window) {
    const managedWindow = window;
    managedWindow.managed = new ManagedWindow(managedWindow);
    this.windows.add(managedWindow);
    managedWindow.unmanagedId = managedWindow.connect("unmanaged", (unmanagedWindow) => {
      this.releaseWindow(unmanagedWindow);
      this.windows.delete(unmanagedWindow);
    });
  }
  releaseWindow(window) {
    if (window.unmanagedId !== null) {
      window.disconnect(window.unmanagedId);
      window.unmanagedId = null;
    }
    window.managed?.disconnect();
    window.managed = null;
  }
};

// src/dbus.ts
import Gio5 from "gi://Gio";
import * as DBusUtil from "resource:///org/gnome/shell/misc/dbusUtils.js";
var RendererWrapper = class {
  logger;
  proxy;
  constructor() {
    this.logger = new Logger("dbus::renderer");
    this.proxy = this.createProxy();
  }
  createProxy() {
    const interfaceXml = `
        <node>
            <interface name="${APPLICATION_ID}">
                <method name="setPlay"/>
                <method name="setPause"/>
                <property name="isPlaying" type="b" access="read"/>
                <signal name="isPlayingChanged">
                    <arg name="isPlaying" type="b"/>
                </signal>
            </interface>
        </node>`;
    const DBusProxy = Gio5.DBusProxy.makeProxyWrapper(interfaceXml);
    return DBusProxy(Gio5.DBus.session, APPLICATION_ID, RENDERER_OBJECT_PATH);
  }
  async setPlay() {
    try {
      await this.proxy.setPlayAsync();
    } catch (e) {
      this.logger.warn(e);
    }
  }
  async setPause() {
    try {
      await this.proxy.setPauseAsync();
    } catch (e) {
      this.logger.warn(e);
    }
  }
};
var UPowerWrapper = class {
  proxy;
  constructor() {
    this.proxy = this.createProxy();
  }
  createProxy() {
    const DBUS_INTERFACE = "org.freedesktop.UPower.Device";
    const DBUS_BUS_NAME = "org.freedesktop.UPower";
    const DBUS_OBJECT_PATH = "/org/freedesktop/UPower/devices/DisplayDevice";
    const interfaceXml = DBusUtil.loadInterfaceXML(DBUS_INTERFACE);
    const DBusProxy = Gio5.DBusProxy.makeProxyWrapper(interfaceXml);
    return DBusProxy(Gio5.DBus.system, DBUS_BUS_NAME, DBUS_OBJECT_PATH);
  }
  getState() {
    return this.proxy.State ?? 0;
  }
  getPercentage() {
    return this.proxy.Percentage ?? 100;
  }
};
var DBusWrapper = class {
  logger;
  proxy;
  constructor() {
    this.logger = new Logger("dbus::dbus");
    this.proxy = this.createProxy();
  }
  createProxy() {
    const DBUS_INTERFACE = "org.freedesktop.DBus";
    const DBUS_BUS_NAME = "org.freedesktop.DBus";
    const DBUS_OBJECT_PATH = "/org/freedesktop/DBus";
    const interfaceXml = DBusUtil.loadInterfaceXML(DBUS_INTERFACE);
    const DBusProxy = Gio5.DBusProxy.makeProxyWrapper(interfaceXml);
    return DBusProxy(Gio5.DBus.session, DBUS_BUS_NAME, DBUS_OBJECT_PATH);
  }
  listNames() {
    try {
      return this.proxy.ListNamesSync();
    } catch (e) {
      this.logger.warn(e);
    }
    return [];
  }
};
var MprisWrapper = class {
  proxy;
  constructor(mediaPlayerName) {
    this.proxy = this.createProxy(mediaPlayerName);
  }
  createProxy(mediaPlayerName) {
    const DBUS_INTERFACE = "org.mpris.MediaPlayer2.Player";
    const DBUS_BUS_NAME = mediaPlayerName;
    const DBUS_OBJECT_PATH = "/org/mpris/MediaPlayer2";
    const interfaceXml = DBusUtil.loadInterfaceXML(DBUS_INTERFACE);
    const DBusProxy = Gio5.DBusProxy.makeProxyWrapper(interfaceXml);
    return DBusProxy(Gio5.DBus.session, DBUS_BUS_NAME, DBUS_OBJECT_PATH);
  }
  getPlaybackStatus() {
    return this.proxy.PlaybackStatus ?? "Stopped";
  }
};

// src/playbackState.ts
function createMachine(def) {
  const machine = {
    value: def.initialState,
    transition(currentState, event) {
      const currentStateDef = def[currentState];
      const destinationTransition = currentStateDef.transitions[event];
      if (!destinationTransition)
        return null;
      const destinationState = destinationTransition.target;
      const destinationStateDef = def[destinationState];
      destinationTransition.action();
      currentStateDef.actions.onExit();
      destinationStateDef.actions.onEnter();
      machine.value = destinationState;
      return machine.value;
    }
  };
  return machine;
}
var PlaybackState = class {
  logger = new Logger("playbackState");
  renderer = new RendererWrapper();
  machineDefinition;
  machine;
  constructor() {
    this.machineDefinition = {
      initialState: "playing",
      playing: {
        actions: {
          onEnter: () => void this.renderer.setPlay(),
          onExit() {
          }
        },
        transitions: {
          userPause: {
            target: "pausedByUser",
            action: () => this.logger.debug("playing -> pausedByUser")
          },
          autoPause: {
            target: "pausedByAuto",
            action: () => this.logger.debug("playing -> pausedByAuto")
          }
        }
      },
      pausedByUser: {
        actions: {
          onEnter: () => void this.renderer.setPause(),
          onExit() {
          }
        },
        transitions: {
          userPlay: {
            target: "playing",
            action: () => this.logger.debug("pausedByUser -> playing")
          },
          autoPause: {
            target: "paused",
            action: () => this.logger.debug("pausedByUser -> paused")
          }
        }
      },
      pausedByAuto: {
        actions: {
          onEnter: () => void this.renderer.setPause(),
          onExit() {
          }
        },
        transitions: {
          autoPlay: {
            target: "playing",
            action: () => this.logger.debug("pausedByAuto -> playing")
          },
          userPause: {
            target: "paused",
            action: () => this.logger.debug("pausedByAuto -> paused")
          }
        }
      },
      paused: {
        actions: { onEnter() {
        }, onExit() {
        } },
        transitions: {
          userPlay: {
            target: "pausedByAuto",
            action: () => this.logger.debug("paused -> pausedByAuto")
          },
          autoPlay: {
            target: "pausedByUser",
            action: () => this.logger.debug("paused -> pausedByUser")
          }
        }
      }
    };
    this.renderer.proxy.connectSignal(
      "isPlayingChanged",
      (_proxy, _sender, [isPlaying]) => {
        if (isPlaying && this.getCurrentState() !== "playing")
          void this.renderer.setPause();
      }
    );
    this.reset();
  }
  getCurrentState() {
    return this.machine.value;
  }
  reset() {
    this.machine = createMachine(this.machineDefinition);
  }
  userPlay() {
    this.machine.transition(this.getCurrentState(), "userPlay");
  }
  autoPlay() {
    this.machine.transition(this.getCurrentState(), "autoPlay");
  }
  userPause() {
    this.machine.transition(this.getCurrentState(), "userPause");
  }
  autoPause() {
    this.machine.transition(this.getCurrentState(), "autoPause");
  }
};

// src/autoPause.ts
import GObject3 from "gi://GObject";
import UPower from "gi://UPowerGlib";
import * as Main3 from "resource:///org/gnome/shell/ui/main.js";
var logger6 = new Logger("autoPause");
var AutoPause = class {
  playbackState;
  modules;
  constructor(extension) {
    this.playbackState = extension.getPlaybackState();
    const settings = extension.getSettings();
    this.modules = [
      new PauseOnMaximizeOrFullscreenModule(settings),
      new PauseOnFocusModule(settings),
      new PauseOnBatteryModule(settings),
      new PauseOnMprisPlayingModule(settings)
    ];
    this.modules.forEach(
      (module) => module.connect("updated", () => this.eval())
    );
  }
  enable() {
    this.modules.forEach((module) => module.enable());
  }
  eval() {
    if (this.modules.some((module) => module.shouldAutoPause()))
      this.playbackState.autoPause();
    else
      this.playbackState.autoPlay();
  }
  disable() {
    this.modules.forEach((module) => module.disable());
  }
};
var AutoPauseModule = GObject3.registerClass(
  {
    Signals: { updated: {} }
  },
  class AutoPauseModule2 extends GObject3.Object {
    settings;
    logger;
    constructor(settings, moduleName) {
      super();
      this.settings = settings;
      this.logger = moduleName ? new Logger(`autoPause::${moduleName}`) : logger6;
    }
    enable() {
    }
    update() {
      this.emit("updated");
    }
    shouldAutoPause() {
      return false;
    }
    disable() {
    }
  }
);
var PauseOnMaximizeOrFullscreenMode = Object.freeze({
  never: 0,
  anyMonitor: 1,
  allMonitors: 2
});
var PauseOnMaximizeOrFullscreenModule = GObject3.registerClass(
  class PauseOnMaximizeOrFullscreenModule2 extends AutoPauseModule {
    states;
    conditions;
    workspaceManager;
    activeWorkspace;
    activeWorkspaceChangedId;
    windows;
    windowAddedId;
    windowRemovedId;
    overviewShowingId;
    overviewHiddenId;
    sessionModeUpdatedId;
    showingDesktopChangedId;
    constructor(settings) {
      super(settings, "maximizeOrFullscreen");
      this.states = {
        maximizedOrFullscreenOnAnyMonitor: false,
        maximizedOrFullscreenOnAllMonitors: false,
        inOverview: false,
        onLockScreen: false
      };
      this.conditions = {
        pauseOnMaximizeOrFullscreen: this.settings.get_int(
          "pause-on-maximize-or-fullscreen"
        )
      };
      this.settings.connect(
        "changed::pause-on-maximize-or-fullscreen",
        () => {
          this.conditions.pauseOnMaximizeOrFullscreen = this.settings.get_int("pause-on-maximize-or-fullscreen");
          this.update();
        }
      );
      this.workspaceManager = null;
      this.activeWorkspace = null;
      this.activeWorkspaceChangedId = null;
      this.windows = [];
      this.windowAddedId = null;
      this.windowRemovedId = null;
      this.overviewShowingId = null;
      this.overviewHiddenId = null;
      this.sessionModeUpdatedId = null;
      this.showingDesktopChangedId = null;
    }
    enable() {
      this.overviewShowingId = Main3.overview.connect("showing", () => {
        this.logger.debug("overview showing");
        this.update();
      });
      this.overviewHiddenId = Main3.overview.connect("hidden", () => {
        this.logger.debug("overview hidden");
        this.update();
      });
      this.sessionModeUpdatedId = Main3.sessionMode.connect("updated", () => {
        this.update();
      });
      this.workspaceManager = global.workspace_manager;
      this.activeWorkspace = this.workspaceManager.get_active_workspace();
      this.activeWorkspaceChangedId = this.workspaceManager.connect(
        "active-workspace-changed",
        (wm) => this.onActiveWorkspaceChanged(wm)
      );
      this.showingDesktopChangedId = this.workspaceManager.connect(
        "showing-desktop-changed",
        () => {
          this.logger.debug("showing-desktop changed");
          this.update();
        }
      );
      this.activeWorkspace.list_windows().forEach((w) => this.onWindowAdded(w, false));
      this.windowAddedId = this.activeWorkspace.connect(
        "window-added",
        (_workspace, window) => this.onWindowAdded(window)
      );
      this.windowRemovedId = this.activeWorkspace.connect(
        "window-removed",
        (_workspace, window) => this.onWindowRemoved(window)
      );
      this.update();
    }
    onWindowAdded(metaWindow, doUpdate = true) {
      if (metaWindow.title?.includes(APPLICATION_ID) || metaWindow.skip_taskbar)
        return;
      const signals = [];
      signals.push(metaWindow.connect("notify::maximized-horizontally", () => {
        this.logger.debug("maximized-horizontally changed");
        this.update();
      }));
      signals.push(metaWindow.connect("notify::maximized-vertically", () => {
        this.logger.debug("maximized-vertically changed");
        this.update();
      }));
      signals.push(metaWindow.connect("notify::fullscreen", () => {
        this.logger.debug("fullscreen changed");
        this.update();
      }));
      signals.push(metaWindow.connect("notify::minimized", () => {
        this.logger.debug("minimized changed");
        this.update();
      }));
      this.windows.push({ metaWindow, signals });
      this.logger.debug(`Window ${metaWindow.title} added`);
      if (doUpdate)
        this.update();
    }
    onWindowRemoved(metaWindow) {
      if (metaWindow.title?.includes(APPLICATION_ID) || metaWindow.skip_taskbar)
        return;
      this.windows = this.windows.filter((window) => {
        if (window.metaWindow === metaWindow) {
          window.signals.forEach((signal) => metaWindow.disconnect(signal));
          return false;
        }
        return true;
      });
      this.logger.debug(`Window ${metaWindow.title} removed`);
      this.update();
    }
    onActiveWorkspaceChanged(workspaceManager) {
      this.windows.forEach(({ metaWindow, signals }) => {
        signals.forEach((signal) => metaWindow.disconnect(signal));
      });
      this.windows = [];
      if (this.windowAddedId && this.activeWorkspace) {
        this.activeWorkspace.disconnect(this.windowAddedId);
        this.windowAddedId = null;
      }
      if (this.windowRemovedId && this.activeWorkspace) {
        this.activeWorkspace.disconnect(this.windowRemovedId);
        this.windowRemovedId = null;
      }
      this.activeWorkspace = null;
      this.activeWorkspace = workspaceManager.get_active_workspace();
      this.logger.debug(
        `Active workspace changed to ${this.activeWorkspace.workspace_index}`
      );
      this.activeWorkspace.list_windows().forEach((w) => this.onWindowAdded(w, false));
      this.windowAddedId = this.activeWorkspace.connect(
        "window-added",
        (_workspace, window) => this.onWindowAdded(window)
      );
      this.windowRemovedId = this.activeWorkspace.connect(
        "window-removed",
        (_workspace, window) => this.onWindowRemoved(window)
      );
      this.update();
    }
    update() {
      const metaWindows = this.windows.map(({ metaWindow }) => metaWindow).filter((w) => !w.title?.includes(APPLICATION_ID) && w.showing_on_its_workspace());
      const monitors = Main3.layoutManager.monitors;
      this.states.maximizedOrFullscreenOnAnyMonitor = metaWindows.some((w) => w.is_maximized() || w.fullscreen);
      const monitorsWithMaximized = metaWindows.reduce(
        (acc, w) => {
          if (w.is_maximized() || w.fullscreen)
            acc[w.get_monitor()] = true;
          return acc;
        },
        {}
      );
      this.states.maximizedOrFullscreenOnAllMonitors = monitors.every(
        (monitor) => monitorsWithMaximized[monitor.index]
      );
      this.states.inOverview = Main3.overview.visible;
      this.states.onLockScreen = Main3.sessionMode.currentMode === "unlock-dialog";
      super.update();
    }
    shouldAutoPause() {
      if (this.states.inOverview || this.states.onLockScreen) {
        this.logger.debug("shouldAutoPause: false (overview or lock screen)");
        return false;
      }
      let res = false;
      if (this.conditions.pauseOnMaximizeOrFullscreen === PauseOnMaximizeOrFullscreenMode.anyMonitor && this.states.maximizedOrFullscreenOnAnyMonitor)
        res = true;
      if (this.conditions.pauseOnMaximizeOrFullscreen === PauseOnMaximizeOrFullscreenMode.allMonitors && this.states.maximizedOrFullscreenOnAllMonitors)
        res = true;
      this.logger.debug("shouldAutoPause:", res);
      return res;
    }
    disable() {
      this.workspaceManager?.disconnect(this.activeWorkspaceChangedId);
      if (this.showingDesktopChangedId !== null)
        this.workspaceManager?.disconnect(this.showingDesktopChangedId);
      this.windows.forEach(
        ({ metaWindow, signals }) => signals.forEach((signal) => metaWindow.disconnect(signal))
      );
      this.activeWorkspace?.disconnect(this.windowAddedId);
      this.activeWorkspace?.disconnect(this.windowRemovedId);
      if (this.overviewShowingId !== null)
        Main3.overview.disconnect(this.overviewShowingId);
      if (this.overviewHiddenId !== null)
        Main3.overview.disconnect(this.overviewHiddenId);
      if (this.sessionModeUpdatedId !== null)
        Main3.sessionMode.disconnect(this.sessionModeUpdatedId);
      this.workspaceManager = null;
      this.activeWorkspace = null;
      this.activeWorkspaceChangedId = null;
      this.windows = [];
      this.windowAddedId = null;
      this.windowRemovedId = null;
      this.overviewShowingId = null;
      this.overviewHiddenId = null;
      this.sessionModeUpdatedId = null;
      this.showingDesktopChangedId = null;
    }
  }
);
var PauseOnFocusModule = GObject3.registerClass(
  class PauseOnFocusModule2 extends AutoPauseModule {
    states;
    conditions;
    display;
    focusWindowChangedId;
    trackedWindow;
    appearsFocusedId;
    constructor(settings) {
      super(settings, "focus");
      this.states = { windowFocused: false };
      this.conditions = {
        pauseOnFocus: this.settings.get_boolean("pause-on-focus")
      };
      this.settings.connect("changed::pause-on-focus", () => {
        this.conditions.pauseOnFocus = this.settings.get_boolean("pause-on-focus");
        this.update();
      });
      this.display = null;
      this.focusWindowChangedId = null;
      this.trackedWindow = null;
      this.appearsFocusedId = null;
    }
    enable() {
      this.display = global.display;
      this.focusWindowChangedId = this.display.connect(
        "notify::focus-window",
        () => {
          this.logger.debug("focus-window changed");
          this.trackFocusWindow();
          this.update();
        }
      );
      this.trackFocusWindow();
      this.update();
    }
    trackFocusWindow() {
      if (this.appearsFocusedId && this.trackedWindow) {
        this.trackedWindow.disconnect(this.appearsFocusedId);
        this.appearsFocusedId = null;
        this.trackedWindow = null;
      }
      const focusWindow = this.display?.focus_window;
      if (focusWindow) {
        this.trackedWindow = focusWindow;
        this.appearsFocusedId = focusWindow.connect(
          "notify::appears-focused",
          () => {
            this.logger.debug(`appears-focused changed: ${focusWindow.appears_focused} for ${focusWindow.title}`);
            this.update();
          }
        );
      }
    }
    update() {
      const focusWindow = this.display?.focus_window;
      this.states.windowFocused = focusWindow !== null && focusWindow !== void 0 && focusWindow.appears_focused && !focusWindow.minimized && !(focusWindow.title?.includes(APPLICATION_ID) ?? false) && !focusWindow.skip_taskbar;
      this.logger.debug(
        `Window focused: ${this.states.windowFocused}, title: ${focusWindow?.title}, appears_focused: ${focusWindow?.appears_focused}`
      );
      super.update();
    }
    shouldAutoPause() {
      const res = this.conditions.pauseOnFocus && this.states.windowFocused;
      this.logger.debug("shouldAutoPause:", res);
      return res;
    }
    disable() {
      if (this.focusWindowChangedId && this.display)
        this.display.disconnect(this.focusWindowChangedId);
      if (this.appearsFocusedId && this.trackedWindow)
        this.trackedWindow.disconnect(this.appearsFocusedId);
      this.trackedWindow = null;
      this.display = null;
      this.focusWindowChangedId = null;
      this.appearsFocusedId = null;
    }
  }
);
var PauseOnBatteryMode = Object.freeze({
  never: 0,
  lowBattery: 1,
  always: 2
});
var PauseOnBatteryModule = GObject3.registerClass(
  class PauseOnBatteryModule2 extends AutoPauseModule {
    states;
    conditions;
    upower;
    constructor(settings) {
      super(settings, "battery");
      this.states = { onBattery: false, lowBattery: false };
      this.conditions = {
        pauseOnBattery: this.settings.get_int("pause-on-battery"),
        lowBatteryThreshold: this.settings.get_int("low-battery-threshold")
      };
      this.settings.connect("changed::pause-on-battery", () => {
        this.conditions.pauseOnBattery = this.settings.get_int("pause-on-battery");
        this.update();
      });
      this.settings.connect("changed::low-battery-threshold", () => {
        this.conditions.lowBatteryThreshold = this.settings.get_int("low-battery-threshold");
        this.update();
      });
      this.upower = new UPowerWrapper();
    }
    enable() {
      this.upower.proxy.connect(
        "g-properties-changed",
        (_proxy, properties) => {
          const payload = properties.deep_unpack();
          if (!("State" in payload) && !("Percentage" in payload))
            return;
          this.logger.debug(
            `State ${payload["State"]}, Percentage ${payload["Percentage"]}`
          );
          this.update();
        }
      );
      this.update();
    }
    update() {
      const state = this.upower.getState();
      const percentage = this.upower.getPercentage();
      this.states.onBattery = state === UPower.DeviceState.PENDING_DISCHARGE || state === UPower.DeviceState.DISCHARGING;
      this.states.lowBattery = this.states.onBattery && percentage <= this.conditions.lowBatteryThreshold;
      super.update();
    }
    shouldAutoPause() {
      let res = false;
      if (this.conditions.pauseOnBattery === PauseOnBatteryMode.lowBattery && this.states.lowBattery)
        res = true;
      if (this.conditions.pauseOnBattery === PauseOnBatteryMode.always && this.states.onBattery)
        res = true;
      this.logger.debug("shouldAutoPause:", res);
      return res;
    }
    disable() {
    }
  }
);
var PauseOnMprisPlayingModule = GObject3.registerClass(
  class PauseOnMprisPlayingModule2 extends AutoPauseModule {
    states;
    conditions;
    dbus;
    mediaPlayers;
    constructor(settings) {
      super(settings, "mpris");
      this.states = { mprisPlaying: false };
      this.conditions = {
        pauseOnMprisPlaying: this.settings.get_boolean("pause-on-mpris-playing")
      };
      this.settings.connect("changed::pause-on-mpris-playing", () => {
        this.conditions.pauseOnMprisPlaying = this.settings.get_boolean("pause-on-mpris-playing");
        this.update();
      });
      this.dbus = new DBusWrapper();
      this.mediaPlayers = {};
    }
    enable() {
      const mprisNames = this.queryMprisNames();
      mprisNames.forEach((mprisName) => {
        this.logger.debug("Media Player found:", mprisName);
        const mpris = new MprisWrapper(mprisName);
        const playbackStatus = mpris.getPlaybackStatus();
        const handler = this.mprisPropertiesChangedFactory(mprisName);
        const mprisPropertiesChangedId = mpris.proxy.connect(
          "g-properties-changed",
          handler
        );
        this.mediaPlayers[mprisName] = { playbackStatus, mpris, mprisPropertiesChangedId };
      });
      this.logger.debug(this.stringifyMediaPlayers());
      this.dbus.proxy.connectSignal(
        "NameOwnerChanged",
        (_proxy, _sender, [name, oldOwner, newOwner]) => {
          if (!name.startsWith("org.mpris.MediaPlayer2."))
            return;
          const mprisName = name;
          if (oldOwner === "") {
            this.logger.debug("Media Player created:", mprisName);
            const mpris = new MprisWrapper(mprisName);
            const playbackStatus = mpris.getPlaybackStatus();
            const handler = this.mprisPropertiesChangedFactory(mprisName);
            const mprisPropertiesChangedId = mpris.proxy.connect(
              "g-properties-changed",
              handler
            );
            this.mediaPlayers[mprisName] = { playbackStatus, mpris, mprisPropertiesChangedId };
          } else if (newOwner === "") {
            this.logger.debug("Media Player destroyed:", mprisName);
            const { mpris, mprisPropertiesChangedId } = this.mediaPlayers[mprisName];
            mpris.proxy.disconnect(mprisPropertiesChangedId);
            delete this.mediaPlayers[mprisName];
          }
          this.logger.debug(this.stringifyMediaPlayers());
          this.update();
        }
      );
      this.update();
    }
    queryMprisNames() {
      try {
        const [names] = this.dbus.listNames();
        return names.filter((name) => name.startsWith("org.mpris.MediaPlayer2."));
      } catch (e) {
        this.logger.error("Error:", e.message);
      }
      return [];
    }
    mprisPropertiesChangedFactory(mprisName) {
      return (_proxy, properties) => {
        const payload = properties.deep_unpack();
        if (!("PlaybackStatus" in payload))
          return;
        this.mediaPlayers[mprisName].playbackStatus = payload["PlaybackStatus"].deep_unpack();
        this.logger.debug(this.stringifyMediaPlayers());
        this.update();
      };
    }
    stringifyMediaPlayers() {
      const summary = Object.fromEntries(
        Object.entries(this.mediaPlayers).map(([key, value]) => [
          key,
          { playbackStatus: value.playbackStatus }
        ])
      );
      return JSON.stringify(summary, null, 2);
    }
    update() {
      this.states.mprisPlaying = Object.values(this.mediaPlayers).some(
        (p) => p.playbackStatus === "Playing"
      );
      super.update();
    }
    shouldAutoPause() {
      const res = this.conditions.pauseOnMprisPlaying && this.states.mprisPlaying;
      this.logger.debug("shouldAutoPause:", res);
      return res;
    }
    disable() {
      Object.values(this.mediaPlayers).forEach(
        ({ mpris, mprisPropertiesChangedId }) => mpris.proxy.disconnect(mprisPropertiesChangedId)
      );
      this.mediaPlayers = {};
    }
  }
);

// src/panelMenu.ts
import Gio8 from "gi://Gio";
import GLib7 from "gi://GLib";
import St3 from "gi://St";
import { gettext as _ } from "resource:///org/gnome/shell/extensions/extension.js";
import * as Main4 from "resource:///org/gnome/shell/ui/main.js";
import * as PanelMenu from "resource:///org/gnome/shell/ui/panelMenu.js";
import * as PopupMenu from "resource:///org/gnome/shell/ui/popupMenu.js";
var HanabiPanelMenu = class {
  isEnabled = false;
  extension;
  settings;
  playbackState;
  isPlaying = false;
  renderer = new RendererWrapper();
  isPlayingChangedSubId = null;
  muteChangedId = null;
  changeWallpaperChangedId = null;
  indicator;
  constructor(extension) {
    this.extension = extension;
    this.settings = extension.getSettings();
    this.playbackState = extension.getPlaybackState();
  }
  enable() {
    if (this.isEnabled)
      return;
    const indicatorName = `${this.extension.metadata.name} Indicator`;
    this.indicator = new PanelMenu.Button(0, indicatorName, false);
    const icon = new St3.Icon({
      gicon: Gio8.icon_new_for_string(
        GLib7.build_filenamev([this.extension.path, "hanabi-symbolic.svg"])
      ),
      style_class: "system-status-icon"
    });
    this.indicator.add_child(icon);
    const menu = new PopupMenu.PopupMenu(
      this.indicator,
      0.5,
      St3.Side.BOTTOM
    );
    this.indicator.setMenu(menu);
    Main4.panel.addToStatusArea(indicatorName, this.indicator);
    const playPause = new PopupMenu.PopupMenuItem(
      this.isPlaying ? _("Pause") : _("Play")
    );
    playPause.connect("activate", () => {
      if (this.isPlaying)
        this.playbackState.userPause();
      else
        this.playbackState.userPlay();
    });
    this.isPlayingChangedSubId = this.renderer.proxy.connectSignal(
      "isPlayingChanged",
      (_proxy, _sender, [isPlaying]) => {
        this.isPlaying = isPlaying;
        playPause.label.set_text(this.isPlaying ? _("Pause") : _("Play"));
      }
    );
    menu.addMenuItem(playPause);
    const muteAudio = new PopupMenu.PopupMenuItem(
      this.getMute() ? _("Unmute Audio") : _("Mute Audio")
    );
    muteAudio.connect("activate", () => {
      this.setMute(!this.getMute());
    });
    this.muteChangedId = this.settings.connect("changed::mute", () => {
      muteAudio.label.set_text(
        this.getMute() ? _("Unmute Audio") : _("Mute Audio")
      );
    });
    menu.addMenuItem(muteAudio);
    const nextWallpaperMenuItem = menu.addAction(
      _("Next Wallpaper"),
      () => this.setNextWallpaper()
    );
    if (!this.getChangeWallpaper())
      nextWallpaperMenuItem.hide();
    this.changeWallpaperChangedId = this.settings.connect(
      "changed::change-wallpaper",
      () => {
        if (this.getChangeWallpaper())
          nextWallpaperMenuItem.show();
        else
          nextWallpaperMenuItem.hide();
      }
    );
    menu.addAction(_("Preferences"), () => {
      this.extension.openPreferences();
    });
    this.isEnabled = true;
  }
  getMute() {
    return this.settings.get_boolean("mute");
  }
  setMute(mute) {
    return this.settings.set_boolean("mute", mute);
  }
  getChangeWallpaper() {
    return this.settings.get_boolean("change-wallpaper");
  }
  setNextWallpaper() {
    const changeWallpaperDirectoryPath = this.settings.get_string(
      "change-wallpaper-directory-path"
    );
    let videoPaths = [];
    const dir = Gio8.File.new_for_path(changeWallpaperDirectoryPath);
    if (dir.query_file_type(Gio8.FileQueryInfoFlags.NONE, null) !== Gio8.FileType.DIRECTORY)
      return;
    const enumerator = dir.enumerate_children(
      "standard::*",
      Gio8.FileQueryInfoFlags.NONE,
      null
    );
    let fileInfo;
    while (fileInfo = enumerator.next_file(null)) {
      if (fileInfo.get_content_type()?.startsWith("video/")) {
        const file = dir.get_child(fileInfo.get_name());
        const filePath = file.get_path();
        if (filePath)
          videoPaths.push(filePath);
      }
    }
    videoPaths = videoPaths.sort();
    const currentVideoPath = this.settings.get_string("video-path");
    const currentIndex = videoPaths.findIndex((p) => p === currentVideoPath);
    const nextIndex = currentIndex !== -1 ? (currentIndex + 1) % videoPaths.length : 0;
    this.settings.set_string("video-path", videoPaths[nextIndex]);
  }
  disable() {
    if (!this.isEnabled)
      return;
    if (this.isPlayingChangedSubId !== null) {
      this.renderer.proxy.disconnectSignal(this.isPlayingChangedSubId);
      this.isPlayingChangedSubId = null;
    }
    if (this.muteChangedId !== null) {
      this.settings.disconnect(this.muteChangedId);
      this.muteChangedId = null;
    }
    if (this.changeWallpaperChangedId !== null) {
      this.settings.disconnect(this.changeWallpaperChangedId);
      this.changeWallpaperChangedId = null;
    }
    this.indicator.destroy();
    this.isEnabled = false;
  }
};

// src/extension.ts
import Gio9 from "gi://Gio";
import GLib8 from "gi://GLib";
import * as Main5 from "resource:///org/gnome/shell/ui/main.js";
import { Extension } from "resource:///org/gnome/shell/extensions/extension.js";
var logger7 = new Logger("extension");
var RENDERER_RELOAD_DELAY_MS = 100;
var RENDERER_RELOAD_DELAY_ON_ERROR_MS = 1e3;
var MONITORS_CHANGED_DEBOUNCE_MS = 500;
var HanabiExtension = class extends Extension {
  isEnabled = false;
  // Settings and sub-components, created in enable() and torn down in disable().
  settings = null;
  playbackState = null;
  panelMenu = null;
  shellOverride = null;
  windowManager = null;
  autoPause = null;
  // Renderer subprocess and its relaunch timeout.
  currentProcess = null;
  launchRendererTimeoutId = 0;
  reloadTime = RENDERER_RELOAD_DELAY_MS;
  rendererSuspended = false;
  // Signal connections and the monitors-changed timeout, cleaned up in disable().
  signalConnections = [];
  monitorsChangedTimeoutId = 0;
  getPlaybackState() {
    return this.playbackState;
  }
  enable() {
    logger7.debug("Enabling");
    this.killAllProcesses();
    this.settings = this.getSettings();
    this.playbackState = new PlaybackState();
    this.panelMenu = new HanabiPanelMenu(this);
    if (this.settings.get_boolean("show-panel-menu"))
      this.panelMenu.enable();
    const showPanelMenuChangedId = this.settings.connect(
      "changed::show-panel-menu",
      () => {
        if (this.settings.get_boolean("show-panel-menu"))
          this.panelMenu.enable();
        else
          this.panelMenu.disable();
      }
    );
    this.signalConnections.push([this.settings, showPanelMenuChangedId]);
    this.shellOverride = new GnomeShellOverride(this.settings);
    this.windowManager = new WindowManager();
    this.autoPause = new AutoPause(this);
    if (Main5.layoutManager._startingUp) {
      const startupCompleteId = Main5.layoutManager.connect(
        "startup-complete",
        () => {
          GLib8.timeout_add(
            GLib8.PRIORITY_DEFAULT,
            this.settings.get_int("startup-delay"),
            () => {
              this.innerEnable();
              return false;
            }
          );
        }
      );
      this.signalConnections.push([Main5.layoutManager, startupCompleteId]);
    } else {
      GLib8.timeout_add(
        GLib8.PRIORITY_DEFAULT,
        this.settings.get_int("startup-delay"),
        () => {
          this.innerEnable();
          return false;
        }
      );
    }
  }
  innerEnable() {
    logger7.debug("Activating overrides and starting renderer");
    this.shellOverride.enable();
    this.windowManager.enable();
    this.autoPause.enable();
    const monitorsChangedId = Main5.layoutManager.connect(
      "monitors-changed",
      () => {
        if (this.monitorsChangedTimeoutId)
          GLib8.source_remove(this.monitorsChangedTimeoutId);
        this.monitorsChangedTimeoutId = GLib8.timeout_add(
          GLib8.PRIORITY_DEFAULT,
          MONITORS_CHANGED_DEBOUNCE_MS,
          () => {
            this.monitorsChangedTimeoutId = 0;
            this.killCurrentProcess();
            return GLib8.SOURCE_REMOVE;
          }
        );
      }
    );
    this.signalConnections.push([Main5.layoutManager, monitorsChangedId]);
    const sessionModeUpdatedId = Main5.sessionMode.connect("updated", () => {
      this.onSessionModeUpdated();
    });
    this.signalConnections.push([Main5.sessionMode, sessionModeUpdatedId]);
    const showOnLockScreenChangedId = this.settings.connect(
      "changed::show-on-lock-screen",
      () => this.onSessionModeUpdated()
    );
    this.signalConnections.push([this.settings, showOnLockScreenChangedId]);
    this.isEnabled = true;
    if (this.launchRendererTimeoutId)
      GLib8.source_remove(this.launchRendererTimeoutId);
    this.launchRenderer();
  }
  onSessionModeUpdated() {
    const isLockScreen = Main5.sessionMode.currentMode === "unlock-dialog";
    const showOnLockScreen = this.settings?.get_boolean("show-on-lock-screen") ?? true;
    if (isLockScreen && !showOnLockScreen)
      this.suspendRenderer();
    else if (!isLockScreen || showOnLockScreen)
      this.resumeRenderer();
  }
  suspendRenderer() {
    if (this.rendererSuspended)
      return;
    logger7.debug("Suspending renderer (lock screen)");
    this.rendererSuspended = true;
    if (this.launchRendererTimeoutId) {
      GLib8.source_remove(this.launchRendererTimeoutId);
      this.launchRendererTimeoutId = 0;
    }
    if (this.currentProcess?.subprocess)
      this.currentProcess.subprocess.send_signal(15);
  }
  resumeRenderer() {
    if (!this.rendererSuspended)
      return;
    logger7.debug("Resuming renderer");
    this.rendererSuspended = false;
    if (this.isEnabled && !this.currentProcess)
      this.launchRenderer();
  }
  launchRenderer() {
    if (!this.settings)
      return;
    const videoPath = this.settings.get_string("video-path");
    if (videoPath === "")
      this.openPreferences();
    logger7.debug(`Launching renderer (video: ${videoPath})`);
    this.reloadTime = RENDERER_RELOAD_DELAY_MS;
    const argv = [];
    argv.push("gjs", "-m", GLib8.build_filenamev([this.path, "renderer", "renderer.js"]));
    argv.push("-P", this.path);
    argv.push("-F", videoPath);
    this.currentProcess = new WaylandSubprocess();
    this.currentProcess.setCwd(GLib8.get_home_dir());
    this.currentProcess.spawn(argv);
    this.windowManager.setWaylandClient(this.currentProcess);
    this.currentProcess.subprocess.wait_async(null, (obj, res) => {
      obj.wait_finish(res);
      if (!this.currentProcess || obj !== this.currentProcess.subprocess)
        return;
      if (obj.get_if_exited()) {
        const retval = obj.get_exit_status();
        if (retval !== 0)
          this.reloadTime = RENDERER_RELOAD_DELAY_ON_ERROR_MS;
      } else {
        this.reloadTime = RENDERER_RELOAD_DELAY_ON_ERROR_MS;
      }
      this.currentProcess = null;
      this.windowManager?.setWaylandClient(null);
      if (this.isEnabled && !this.rendererSuspended) {
        logger7.debug(`Renderer exited; relaunching in ${this.reloadTime}ms`);
        if (this.launchRendererTimeoutId)
          GLib8.source_remove(this.launchRendererTimeoutId);
        this.launchRendererTimeoutId = GLib8.timeout_add(
          GLib8.PRIORITY_DEFAULT,
          this.reloadTime,
          () => {
            this.launchRendererTimeoutId = 0;
            this.launchRenderer();
            return false;
          }
        );
      }
    });
  }
  disable() {
    logger7.debug("Disabling");
    this.killCurrentProcess();
    this.rendererSuspended = false;
    this.signalConnections.forEach(([emitter, id]) => emitter.disconnect(id));
    this.signalConnections = [];
    this.settings = null;
    this.panelMenu?.disable();
    this.shellOverride?.disable();
    this.windowManager?.disable();
    this.autoPause?.disable();
    if (this.monitorsChangedTimeoutId) {
      GLib8.source_remove(this.monitorsChangedTimeoutId);
      this.monitorsChangedTimeoutId = 0;
    }
    this.isEnabled = false;
  }
  killCurrentProcess() {
    if (this.launchRendererTimeoutId) {
      GLib8.source_remove(this.launchRendererTimeoutId);
      this.launchRendererTimeoutId = 0;
      if (this.isEnabled) {
        this.launchRendererTimeoutId = GLib8.timeout_add(
          GLib8.PRIORITY_DEFAULT,
          this.reloadTime,
          () => {
            this.launchRendererTimeoutId = 0;
            this.launchRenderer();
            return false;
          }
        );
      }
    }
    if (this.currentProcess?.subprocess) {
      logger7.debug("Killing current renderer process");
      this.currentProcess.cancellable?.cancel();
      this.currentProcess.subprocess.send_signal(15);
    }
  }
  killAllProcesses() {
    const procFolder = Gio9.File.new_for_path("/proc");
    if (!procFolder.query_exists(null))
      return;
    const fileEnum = procFolder.enumerate_children(
      "standard::*",
      Gio9.FileQueryInfoFlags.NONE,
      null
    );
    let info;
    while (info = fileEnum.next_file(null)) {
      const filename = info.get_name();
      if (!filename)
        break;
      const processPath = GLib8.build_filenamev(["/proc", filename, "cmdline"]);
      const processUser = Gio9.File.new_for_path(processPath);
      if (!processUser.query_exists(null))
        continue;
      const [binaryData] = processUser.load_bytes(null);
      let contents = "";
      const readData = binaryData.get_data();
      if (readData) {
        for (let i = 0; i < readData.length; i++) {
          if (readData[i] < 32)
            contents += " ";
          else
            contents += String.fromCharCode(readData[i]);
        }
      }
      const path = `gjs ${GLib8.build_filenamev([this.path, "renderer", "renderer.js"])}`;
      if (contents.startsWith(path)) {
        logger7.debug(`Killing orphaned renderer process (pid ${filename})`);
        const proc = new Gio9.Subprocess({ argv: ["/bin/kill", filename] });
        proc.init(null);
        proc.wait(null);
      }
    }
  }
};
export {
  HanabiExtension as default
};
