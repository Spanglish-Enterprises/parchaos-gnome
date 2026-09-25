// SPDX-License-Identifier: GPL-3.0-or-later

// src/constants.ts
var APPLICATION_ID = "io.github.jeffshee.HanabiRenderer";
var RENDERER_OBJECT_PATH = `/${APPLICATION_ID.replaceAll(".", "/")}`;

// src/renderer/renderer.ts
import GObject from "gi://GObject";
import Gtk from "gi://Gtk?version=4.0";
import Gio from "gi://Gio";
import GLib from "gi://GLib";
import Gdk from "gi://Gdk?version=4.0";
import Gst from "gi://Gst";
var gstVersion = Gst.version();
console.log(`GStreamer version: ${gstVersion.join(".")}`);
var gtkVersion = [
  Gtk.get_major_version(),
  Gtk.get_minor_version(),
  Gtk.get_micro_version()
];
console.log(`Gtk version: ${gtkVersion.join(".")}`);
var isGstVersionAtLeast = (major, minor) => gstVersion[0] > major || gstVersion[0] === major && gstVersion[1] >= minor;
var GstPlay = null;
try {
  GstPlay = (await import("gi://GstPlay")).default;
} catch (e) {
  console.error(e);
  console.warn("GstPlay, or the typelib is not installed. Renderer will fallback to GtkMediaFile!");
}
var haveGstPlay = GstPlay !== null;
var GstAudio = null;
try {
  GstAudio = (await import("gi://GstAudio")).default;
} catch (e) {
  console.error(e);
  console.warn("GstAudio, or the typelib is not installed.");
}
var haveGstAudio = GstAudio !== null;
var useGstGL = isGstVersionAtLeast(1, 24);
var extSettings = null;
var extSchemaId = "io.github.jeffshee.hanabi-extension";
var settingsSchemaSource = Gio.SettingsSchemaSource.get_default();
if (settingsSchemaSource?.lookup(extSchemaId, false))
  extSettings = Gio.Settings.new(extSchemaId);
var preferClappersink = extSettings?.get_boolean("prefer-clappersink") ?? false;
var forceMediaFile = extSettings?.get_boolean("force-mediafile") ?? false;
var isEnableVADecoders = extSettings?.get_boolean("enable-va") ?? false;
var isEnableNvSl = extSettings?.get_boolean("enable-nvsl") ?? false;
var isEnableGraphicsOffload = extSettings?.get_boolean("enable-graphics-offload") ?? false;
var codePath = "src";
var contentFit = extSettings?.get_int("content-fit") ?? Gtk.ContentFit.CONTAIN;
var mute = extSettings?.get_boolean("mute") ?? false;
var nohide = false;
var videoPath = extSettings?.get_string("video-path") ?? "";
var volume = (extSettings?.get_int("volume") ?? 50) / 100;
var randomStartPosition = extSettings?.get_boolean("random-start-position") ?? false;
var changeWallpaper = extSettings?.get_boolean("change-wallpaper") ?? true;
var changeWallpaperDirectoryPath = extSettings?.get_string("change-wallpaper-directory-path") ?? "";
var changeWallpaperMode = extSettings?.get_int("change-wallpaper-mode") ?? 0;
var changeWallpaperInterval = extSettings?.get_int("change-wallpaper-interval") ?? 15;
var windowDimension = { width: 1920, height: 1080 };
var windowed = false;
var isDebugMode = extSettings?.get_boolean("debug-mode") ?? true;
var changeWallpaperTimerId = null;
var HanabiRendererWindow = GObject.registerClass(
  { GTypeName: "HanabiRendererWindow" },
  class HanabiRendererWindow2 extends Gtk.ApplicationWindow {
    _setup(widget, gdkMonitor) {
      const cssProvider = new Gtk.CssProvider();
      cssProvider.load_from_file(
        Gio.File.new_for_path(
          GLib.build_filenamev([codePath, "renderer", "stylesheet.css"])
        )
      );
      Gtk.StyleContext.add_provider_for_display(
        Gdk.Display.get_default(),
        cssProvider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
      );
      this.set_child(widget);
      if (!windowed) {
        const geometry = gdkMonitor.get_geometry();
        this.set_size_request(geometry.width, geometry.height);
        this.set_resizable(false);
      }
    }
  }
);
var HanabiRenderer = GObject.registerClass(
  { GTypeName: "HanabiRenderer" },
  class HanabiRenderer2 extends Gtk.Application {
    hanabiWindows;
    pictures;
    sharedPaintable;
    gstImplName;
    playing;
    randomStartPending;
    play;
    adapter;
    media;
    dbus;
    display;
    monitors;
    constructor(props) {
      super({
        application_id: APPLICATION_ID,
        flags: Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        ...props
      });
      GLib.log_set_debug_enabled(isDebugMode);
      this.hanabiWindows = [];
      this.pictures = [];
      this.sharedPaintable = null;
      this.gstImplName = "";
      this.playing = false;
      this.randomStartPending = true;
      this.play = null;
      this.adapter = null;
      this.media = null;
      this.dbus = null;
      this.display = null;
      this.monitors = [];
      this.exportDbus();
      this.setupGst();
      this.connect("activate", (app) => {
        this.display = Gdk.Display.get_default();
        this.monitors = this.display ? Array.from(
          { length: this.display.get_monitors().get_n_items() },
          (_, i) => this.display.get_monitors().get_item(i)
        ) : [];
        if (!app.activeWindow) {
          this.buildUI();
          this.hanabiWindows.forEach((window) => window.present());
        }
      });
      this.connect("command-line", (_app, commandLine) => {
        const argv = commandLine.get_arguments();
        if (this.parseArgs(argv)) {
          this.activate();
          commandLine.set_exit_status(0);
        } else {
          commandLine.set_exit_status(1);
        }
      });
      extSettings?.connect("changed", (settings, key) => {
        switch (key) {
          case "video-path":
            videoPath = settings.get_string(key);
            this.setFilePath(videoPath);
            break;
          case "mute":
            mute = settings.get_boolean(key);
            this.setMute(mute);
            break;
          case "volume":
            volume = settings.get_int(key) / 100;
            this.setVolume(volume);
            break;
          case "random-start-position":
            randomStartPosition = settings.get_boolean(key);
            break;
          case "change-wallpaper":
            changeWallpaper = settings.get_boolean(key);
            this.setAutoWallpaper();
            break;
          case "change-wallpaper-interval":
            changeWallpaperInterval = settings.get_int(key);
            this.setAutoWallpaper();
            break;
          case "change-wallpaper-directory-path":
            changeWallpaperDirectoryPath = settings.get_string(key);
            this.setAutoWallpaper();
            break;
          case "change-wallpaper-mode":
            changeWallpaperMode = settings.get_int(key);
            break;
          case "content-fit":
            contentFit = settings.get_int(key);
            this.pictures.forEach(
              (picture) => picture.set_content_fit(contentFit)
            );
            break;
          case "debug-mode":
            isDebugMode = settings.get_boolean(key);
            GLib.log_set_debug_enabled(isDebugMode);
            break;
        }
      });
    }
    parseArgs(argv) {
      let lastCommand = null;
      for (const arg of argv) {
        if (!lastCommand) {
          switch (arg) {
            case "-M":
            case "--mute":
              mute = true;
              console.debug(`mute = ${mute}`);
              break;
            case "-N":
            case "--nohide":
              nohide = true;
              console.debug(`nohide = ${nohide}`);
              break;
            case "-W":
            case "--windowed":
            case "-P":
            case "--codepath":
            case "-F":
            case "--filepath":
            case "-V":
            case "--volume":
              lastCommand = arg;
              break;
            default:
              console.error(`Argument ${arg} not recognized. Aborting.`);
              return false;
          }
          continue;
        }
        switch (lastCommand) {
          case "-W":
          case "--windowed": {
            windowed = true;
            const data = arg.split(":");
            windowDimension = {
              width: parseInt(data[0]),
              height: parseInt(data[1])
            };
            console.debug(`windowed = ${windowed}, windowDimension = ${JSON.stringify(windowDimension)}`);
            break;
          }
          case "-P":
          case "--codepath":
            codePath = arg;
            console.debug(`codepath = ${codePath}`);
            break;
          case "-F":
          case "--filepath":
            videoPath = arg;
            console.debug(`filepath = ${videoPath}`);
            break;
          case "-V":
          case "--volume":
            volume = Math.max(0, Math.min(1, parseFloat(arg)));
            console.debug(`volume = ${volume}`);
            break;
        }
        lastCommand = null;
      }
      return true;
    }
    setupGst() {
      this.setPluginDecodersRank("nvcodec", Gst.Rank.PRIMARY + 1, isEnableNvSl);
      if (isEnableVADecoders)
        this.setPluginDecodersRank("va", Gst.Rank.PRIMARY + 3);
    }
    setPluginDecodersRank(pluginName, rank, useStateless = false) {
      const gstRegistry = Gst.Registry.get();
      const features = gstRegistry.get_feature_list_by_plugin(pluginName);
      for (const feature of features) {
        const featureName = feature.get_name();
        if (!featureName)
          continue;
        if (!featureName.endsWith("dec") && !featureName.endsWith("postproc"))
          continue;
        const isStateless = featureName.includes("sl");
        if (isStateless !== useStateless)
          continue;
        const oldRank = feature.get_rank();
        if (rank === oldRank)
          continue;
        feature.set_rank(rank);
        console.debug(`changed rank: ${oldRank} -> ${rank} for ${featureName}`);
      }
    }
    buildUI() {
      this.monitors.forEach((gdkMonitor, index) => {
        let widget = this.getWidgetFromSharedPaintable();
        if (index > 0 && !widget)
          return;
        if (!widget) {
          if (!forceMediaFile && haveGstPlay) {
            let sink = null;
            if (preferClappersink)
              sink = Gst.ElementFactory.make("clappersink", "clappersink");
            if (!sink)
              sink = Gst.ElementFactory.make("gtk4paintablesink", "gtk4paintablesink");
            if (sink)
              widget = this.getWidgetFromSink(sink);
          }
          if (!widget)
            widget = this.getGtkStockWidget();
        }
        if (!widget)
          return;
        const geometry = gdkMonitor.get_geometry();
        const state = {
          position: [geometry.x, geometry.y],
          keepAtBottom: true,
          keepMinimized: true,
          keepPosition: true
        };
        const windowTitle = nohide ? `Hanabi Renderer #${index} (using ${this.gstImplName})` : `@${APPLICATION_ID}!${JSON.stringify(state)}|${index}`;
        const window = new HanabiRendererWindow({
          application: this,
          decorated: !!nohide,
          default_height: windowed ? windowDimension.height : geometry.height,
          default_width: windowed ? windowDimension.width : geometry.width,
          title: windowTitle
        });
        window._setup(widget, gdkMonitor);
        this.hanabiWindows.push(window);
      });
      console.log(`using ${this.gstImplName} for video output`);
    }
    getWidgetFromSharedPaintable() {
      if (this.sharedPaintable) {
        const picture = new Gtk.Picture({
          paintable: this.sharedPaintable,
          hexpand: true,
          vexpand: true
        });
        picture.set_content_fit(contentFit);
        this.pictures.push(picture);
        if (isEnableGraphicsOffload) {
          const offload = Gtk.GraphicsOffload["new"](picture);
          offload.set_enabled(Gtk.GraphicsOffloadEnabled.ENABLED);
          return offload;
        }
        return picture;
      }
      return null;
    }
    getWidgetFromSink(sink) {
      this.gstImplName = sink.name;
      let widget = null;
      if (sink.widget) {
        if (sink.widget instanceof Gtk.Picture) {
          this.sharedPaintable = sink.widget.paintable;
          const box = new Gtk.Box();
          box.append(sink.widget);
          box.append(this.getWidgetFromSharedPaintable());
          sink.widget.hide();
          widget = box;
        } else {
          widget = sink.widget;
        }
      } else if (sink.paintable) {
        this.sharedPaintable = sink.paintable;
        widget = this.getWidgetFromSharedPaintable();
      }
      if (!widget)
        return null;
      if (useGstGL) {
        const glsink = Gst.ElementFactory.make("glsinkbin", "glsinkbin");
        if (glsink) {
          this.gstImplName = `glsinkbin + ${this.gstImplName}`;
          glsink.set_property("sink", sink);
          sink = glsink;
        }
      }
      this.play = GstPlay.Play.new(
        GstPlay.PlayVideoOverlayVideoRenderer.new_with_sink(null, sink)
      );
      this.adapter = GstPlay.PlaySignalAdapter.new(this.play);
      this.adapter.connect(
        "end-of-stream",
        (adapter) => adapter.play.seek(0)
      );
      this.adapter.connect(
        "warning",
        (_adapter, err) => console.warn(err)
      );
      this.adapter.connect(
        "error",
        (_adapter, err) => console.error(err)
      );
      let stateSignal = this.adapter.connect(
        "state-changed",
        (_adapter, state) => {
          if (state >= GstPlay.PlayState.PAUSED) {
            this.setVolume(volume);
            this.setMute(mute);
            if (stateSignal !== null) {
              this.adapter.disconnect(stateSignal);
              stateSignal = null;
            }
          }
        }
      );
      this.adapter.connect("state-changed", (_adapter, state) => {
        this.playing = state === GstPlay.PlayState.PLAYING;
        this.dbus.emit_signal(
          "isPlayingChanged",
          new GLib.Variant("(b)", [this.playing])
        );
      });
      this.adapter.connect("state-changed", (_adapter, state) => {
        if (state >= GstPlay.PlayState.PAUSED)
          this.maybeSeekRandomGst();
      });
      const file = Gio.File.new_for_path(videoPath);
      this.play.set_uri(file.get_uri());
      this.markRandomStartPending();
      this.setPlay();
      this.setAutoWallpaper();
      return widget;
    }
    getGtkStockWidget() {
      this.gstImplName = "GtkMediaFile";
      this.media = Gtk.MediaFile.new_for_filename(videoPath);
      this.media.set({ loop: true });
      this.media.connect("notify::prepared", () => {
        this.setVolume(volume);
        this.setMute(mute);
        this.maybeSeekRandomMedia();
      });
      this.media.connect("notify::playing", (media) => {
        this.playing = media.get_playing();
        this.dbus.emit_signal(
          "isPlayingChanged",
          new GLib.Variant("(b)", [this.playing])
        );
      });
      this.sharedPaintable = this.media;
      const widget = this.getWidgetFromSharedPaintable();
      this.markRandomStartPending();
      this.setPlay();
      this.setAutoWallpaper();
      return widget;
    }
    exportDbus() {
      const dbusXml = `
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
      this.dbus = Gio.DBusExportedObject.wrapJSObject(dbusXml, this);
      this.dbus.export(Gio.DBus.session, RENDERER_OBJECT_PATH);
    }
    setVolume(_volume) {
      const player = this.play ?? this.media;
      if (!player)
        return;
      if (this.play) {
        if (haveGstAudio) {
          _volume = GstAudio.StreamVolume.convert_volume(
            GstAudio.StreamVolumeFormat.CUBIC,
            GstAudio.StreamVolumeFormat.LINEAR,
            _volume
          );
        } else {
          _volume = Math.pow(_volume, 3);
        }
      }
      if (player.volume === _volume)
        player.volume = null;
      player.volume = _volume;
    }
    setMute(_mute) {
      if (this.play) {
        if (this.play.mute === _mute)
          this.play.mute = !_mute;
        this.play.mute = _mute;
      } else if (this.media) {
        if (this.media.muted === _mute)
          this.media.muted = !_mute;
        this.media.muted = _mute;
      }
    }
    setFilePath(_videoPath) {
      const file = Gio.File.new_for_path(_videoPath);
      if (this.play) {
        this.play.set_uri(file.get_uri());
      } else if (this.media) {
        this.media.stream_unprepared();
        this.media.file = file;
      }
      this.markRandomStartPending();
      this.setPlay();
    }
    setPlay() {
      if (this.play)
        this.play.play();
      else if (this.media)
        this.media.play();
    }
    setPause() {
      if (this.play)
        this.play.pause();
      else if (this.media)
        this.media.pause();
    }
    setAutoWallpaper() {
      let currentIndex = 0;
      let videoPaths = [];
      const dir = Gio.File.new_for_path(changeWallpaperDirectoryPath);
      if (dir.query_file_type(Gio.FileQueryInfoFlags.NONE, null) !== Gio.FileType.DIRECTORY)
        return;
      const enumerator = dir.enumerate_children(
        "standard::*",
        Gio.FileQueryInfoFlags.NONE,
        null
      );
      let fileInfo;
      while (fileInfo = enumerator.next_file(null)) {
        if (fileInfo.get_content_type()?.startsWith("video/")) {
          const file = dir.get_child(fileInfo.get_name());
          const path = file.get_path();
          if (path)
            videoPaths.push(path);
        }
      }
      if (videoPaths.length === 0)
        return;
      videoPaths = videoPaths.sort();
      const getRandomIndex = (actualIndex, videosLength) => {
        if (videosLength <= 1)
          return actualIndex;
        let newIndex;
        do
          newIndex = Math.floor(Math.random() * videosLength);
        while (newIndex === actualIndex);
        return newIndex;
      };
      const operation = () => {
        console.debug(`setAutoWallpaper operation, interval: ${changeWallpaperInterval} min`);
        if (this.playing) {
          extSettings.set_string("video-path", videoPaths[currentIndex]);
          if (changeWallpaperMode === 0)
            currentIndex = (currentIndex + 1) % videoPaths.length;
          else if (changeWallpaperMode === 1)
            currentIndex = (currentIndex - 1 + videoPaths.length) % videoPaths.length;
          else if (changeWallpaperMode === 2)
            currentIndex = getRandomIndex(currentIndex, videoPaths.length);
        }
        return true;
      };
      if (changeWallpaperTimerId) {
        GLib.source_remove(changeWallpaperTimerId);
        changeWallpaperTimerId = null;
      }
      if (changeWallpaper) {
        operation();
        changeWallpaperTimerId = GLib.timeout_add_seconds(
          GLib.PRIORITY_DEFAULT,
          changeWallpaperInterval * 60,
          operation
        );
      }
    }
    get isPlaying() {
      return this.playing;
    }
    markRandomStartPending() {
      this.randomStartPending = true;
    }
    maybeSeekRandomGst() {
      if (!this.play || !randomStartPosition || !this.randomStartPending)
        return;
      const duration = Number(this.play.get_duration());
      if (!duration || duration <= 0) {
        this.randomStartPending = false;
        return;
      }
      const maxPosition = Math.max(duration - Number(Gst.SECOND ?? 1e9), 0);
      const position = Math.floor(Math.random() * (maxPosition + 1));
      this.play.seek(position);
      this.randomStartPending = false;
    }
    maybeSeekRandomMedia() {
      if (!this.media || !randomStartPosition || !this.randomStartPending)
        return;
      const duration = this.media.get_duration();
      if (!duration || duration <= 0) {
        this.randomStartPending = false;
        return;
      }
      const maxPosition = Math.max(duration - GLib.USEC_PER_SEC, 0);
      const position = Math.floor(Math.random() * (maxPosition + 1));
      this.media.seek(position);
      this.randomStartPending = false;
    }
  }
);
Gst.init([]);
var renderer = new HanabiRenderer();
renderer.run(ARGV);
