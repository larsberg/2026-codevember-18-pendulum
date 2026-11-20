import { attachPlayerBridge } from './player-bridge.js';
// Studio shell inherited from 14-tension.
import './style.css';
import './mesh-style.css';
import {
  ACESFilmicToneMapping, Color, DirectionalLight, HemisphereLight, PCFShadowMap,
  MOUSE, TOUCH, PerspectiveCamera, PMREMGenerator, Scene, SpotLight, SRGBColorSpace, Vector3, WebGLRenderer,
} from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { applyCameraView, applyShotLens, captureCameraView, configureOrbitInputs } from './camera.js';
import { createPhysics, initPhysics } from './physics.js';
import { createControls } from './controls.js';
import { defaultSetup, validateSetup, DEFAULT_CAMERA } from './settings.js';
import { requestSetup } from './persistence.js';
import { libraryPalettes } from './palette-library.js';

import { createShadowFollow } from './shadows.js';
import { createBeatClock, takeAt } from './beat-clock.js';
import { createEscapement, loadSet } from './pendulum.js';
import { applyStudioLighting, bindLightingControls } from './lighting-controls.js';
import { drawerRequested } from './drawer-url.js';
import { bindMaterialControls } from './material-controls.js';
import { applyStudioPalette } from './studio-palettes.js';
import { createSceneEffects } from './scene-effects.js';
import { createAudio } from './score.js';
let settings = defaultSetup(), setupLoadError;
try { settings = await requestSetup(); } catch (error) { setupLoadError = error.message; console.warn(error.message); }
await initPhysics();
const canvas = document.querySelector('canvas');
const renderer = new WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5)); renderer.outputColorSpace = SRGBColorSpace;
renderer.toneMapping = ACESFilmicToneMapping; renderer.toneMappingExposure = .9;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = PCFShadowMap;
const scene = new Scene(); scene.background = new Color(settings.studio.background);
// Preserve the studio camera range.
const camera = new PerspectiveCamera(42, innerWidth / innerHeight, .1, 900);
const orbit = new OrbitControls(camera, canvas);
configureOrbitInputs(orbit);
orbit.mouseButtons = { LEFT: MOUSE.ROTATE, MIDDLE: MOUSE.DOLLY, RIGHT: MOUSE.PAN };
orbit.enablePan = true; orbit.touches = { ONE: TOUCH.ROTATE, TWO: TOUCH.DOLLY_PAN };
orbit.minDistance = .5; orbit.maxDistance = 600; orbit.minPolarAngle = .09; orbit.maxPolarAngle = Math.PI - .09;
orbit.enableDamping = true; orbit.dampingFactor = .07;
const focus = new Vector3();
const pmrem = new PMREMGenerator(renderer), room = new RoomEnvironment();
let environmentBlur = settings.lighting.environment.blur;
let environment = pmrem.fromScene(room, environmentBlur); scene.environment = environment.texture;
function configureEnvironment() {
  const blur = settings.lighting.environment.blur;
  if (blur === environmentBlur) return;
  const previous = environment;
  environment = pmrem.fromScene(room, blur); environmentBlur = blur;
  scene.environment = environment.texture;
  previous.dispose();
}
const hemisphere = new HemisphereLight('#fff8ed', '#7e8b9d', 1.4); scene.add(hemisphere);
const light = new DirectionalLight('#fff5df', 3.1);
light.position.set(-8, 18, 10); light.castShadow = true; light.shadow.mapSize.set(2048, 2048);
Object.assign(light.shadow.camera, { left: -12, right: 12, top: 12, bottom: -12, near: .5, far: 75 });
light.shadow.camera.updateProjectionMatrix();
light.shadow.bias = -.00015; light.shadow.normalBias = .04; light.shadow.radius = 3;
scene.add(light, light.target);
const lightOffset = new Vector3();
const followShadow = createShadowFollow(light, () => lightOffset);
const fill = new DirectionalLight('#c0e4ff', 1.1); fill.position.set(12, 8, -10);
fill.shadow.mapSize.set(2048, 2048); Object.assign(fill.shadow.camera, { left: -20, right: 20, top: 20, bottom: -20, near: .5, far: 900 });
fill.shadow.camera.updateProjectionMatrix();
scene.add(fill, fill.target);
const spotlight = new SpotLight(); spotlight.shadow.mapSize.set(2048, 2048);
spotlight.shadow.camera.near = 1; spotlight.shadow.camera.far = 240; scene.add(spotlight, spotlight.target);
const effects = createSceneEffects(renderer, scene, camera, { clampBeauty: false });
const set = await loadSet(scene);
const simulation = createPhysics(settings.physics);
const lightingDefaults = defaultSetup().lighting.directional;
const clock = createBeatClock();
const escapement = createEscapement(simulation, set.pivot, clock);
let currentTake;
let elapsed = 0;
simulation.onAfterStep(dt => { elapsed += dt; });

let controls, lightingControls, materialControls;
let audioStatus;
const audio = createAudio({ clock, onStatus(state) {
  audioStatus = state;
  controls?.audioStatus(state);
} });
const lights = { directional: light, hemisphere, spotlight, fill };
const running = () => settings.motion.playing && !document.hidden;

function setLighting() {
  applyStudioLighting(settings.lighting, lights, focus);
  const { sun, keyDirection } = set.current;
  const value = settings.lighting.directional;
  lightOffset.copy(keyDirection).multiplyScalar(15);
  lightOffset.x += value.offsetX - lightingDefaults.offsetX;
  lightOffset.y += value.height - lightingDefaults.height;
  lightOffset.z += value.offsetZ - lightingDefaults.offsetZ;
  light.color.multiply(new Color(...sun.color));
  light.intensity *= sun.power / 1.4;
  hemisphere.intensity *= .32;
  scene.environmentRotation.y = Math.atan2(keyDirection.x, keyDirection.z) + settings.lighting.environment.rotation * Math.PI / 180;
}
function frameShot() {
  applyCameraView(set.cameraView(settings.camera), camera, orbit, focus);
}
function cut(take) {
  currentTake = take;
  set.select(take);
  focus.fromArray(set.current.target);
  applyShotLens(camera, set.current);
  frameShot();
  setLighting();
}
function configure(restoreCamera = false) {
  simulation.configure(settings.physics);
  scene.background.set(settings.studio.background);
  renderer.toneMappingExposure = settings.studio.exposure;
  set.setFloor(settings);
  materialControls?.set(settings.materials);
  configureEnvironment();
  const env = settings.lighting.environment;
  scene.environmentIntensity = env.enabled ? env.intensity * .68 : 0;
  setLighting();
  lightingControls?.set(settings.lighting);
  for (const source of [light, fill, spotlight]) source.shadow.intensity = settings.studio.shadowOpacity;
  effects.configure(settings.lighting.occlusion);
  effects.configureBloom(settings.bloom);
  effects.configureFocus(settings.focus);
  clock.configure(running(), settings.audio.tempo);
  audio.update(running());
  audio.configure(settings.audio);
  if (restoreCamera) frameShot();
  if (settings.visibility.fps && !controls) mountControls();
  controls?.set(settings);
}

function restore(value) {
  settings = validateSetup(value);
  simulation.reset();
  elapsed = 0;
  clock.configure(running(), settings.audio.tempo);
  clock.seek(settings.motion.position);
  escapement.reset(settings.motion.position);
  cut(takeAt(settings.motion.position));
  audio.resync();
  document.activeElement?.blur();
  configure(true);
  controls?.syncPalette();
}

function change(group, key, value) {
  const next = { ...settings, [group]: { ...settings[group], [key]: value } };
  settings = validateSetup(next);
  configure(group === 'camera');
  controls?.status('Unsaved changes');
}

function render() {
  set.updateTelevision(clock.position());
  followShadow(focus);
  effects.render(focus);
}

const actions = {
  change,
  async save() {
    settings.camera = captureView();
    const saved = await requestSetup('PUT', snapshot());
    controls?.status(import.meta.env.PROD ? 'Saved on this device.' : 'Saved to public/settings.json.');
    return saved;
  },
  async reload() {
    restore(await requestSetup());
    controls?.status('Settings reloaded.');
    return structuredClone(settings);
  },
  reset() {
    restore(defaultSetup());
    controls?.status('Defaults restored.');
  },
  resetView() { settings.camera = { ...DEFAULT_CAMERA }; configure(true); },
  togglePlaying() { change('motion', 'playing', !settings.motion.playing); },
  toggleSound() { actions.setSoundEnabled(!settings.audio.enabled); },
  setSoundEnabled(value) {
    change('audio', 'enabled', value);
    if (value) return audio.unlock();
  },
  async audition() {
    if (!running()) return;
    if (!audio.unlocked) await actions.setSoundEnabled(true);
    audio.audition();
  },
  selectPalette(id) {
    settings.lighting = applyStudioPalette(settings.lighting, id, libraryPalettes(settings.paletteLibrary));
    settings.paletteId = id;
    configure();
    controls?.status('Unsaved changes');
  },
  changeLibrary(library) {
    settings.paletteLibrary = library;
    controls?.set(settings);
    controls?.syncPalette();
    controls?.status('Unsaved changes');
  },
  exportDrawing() {
    render();
    canvas.toBlob(blob => {
      if (!blob) return controls?.status('PNG export failed.', true);
      const url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url;
      link.download = '18-pendulum.png';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    }, 'image/png');
  },
};
function mountControls() {
  if (controls) return;
  controls = createControls({ ...actions, settings });
  lightingControls = bindLightingControls(controls.element, (group, key, value) => {
    change('lighting', group, { ...settings.lighting[group], [key]: value });
  });
  materialControls = bindMaterialControls(controls.element, (group, key, value) => {
    change('materials', group, { ...settings.materials[group], [key]: value });
  });
  lightingControls.set(settings.lighting);
  materialControls.set(settings.materials);
  controls.set(settings);
  controls.showControls(false);
  if (audioStatus) controls.audioStatus(audioStatus);
  if (setupLoadError) controls.status(setupLoadError, true);
}

function captureView() {
  const view = set.cameraView(captureCameraView(camera, orbit, focus), true);
  view.distance = Math.max(5, Math.min(600, view.distance));
  return view;
}
function snapshot() {
  const result = structuredClone(settings);
  result.motion.position = clock.position();
  return result;
}
let uiVisible = false;
function showControls(show) {
  if (show) mountControls();
  uiVisible = show;
  controls?.showControls(show);
}
let urlFlag = drawerRequested(location.href);
clock.seek(settings.motion.position);
escapement.reset(settings.motion.position);
cut(takeAt(settings.motion.position));
configure(true);
showControls(urlFlag);
window.addEventListener('hashchange', () => {
  const next = drawerRequested(location.href);
  if (next !== urlFlag) showControls(next);
  urlFlag = next;
});
document.addEventListener('keydown', event => {
  if (!document.hasFocus() || event.repeat || event.isComposing || event.metaKey || event.ctrlKey || event.altKey ||
      event.target.closest('input,textarea,select,[contenteditable="true"]')) return;
  switch (event.code) {
    case 'KeyH': event.preventDefault(); showControls(!uiVisible); break;
    case 'Escape': controls?.close(); break;
    case 'KeyP': event.preventDefault(); actions.togglePlaying(); break;
    case 'KeyM': actions.toggleSound(); break;
    case 'KeyF': void actions.audition(); break;
  }
});

function resize() {
  renderer.setSize(innerWidth, innerHeight, false);
  effects.resize(innerWidth, innerHeight);
  camera.aspect = innerWidth / innerHeight;
  applyShotLens(camera, set.current);
}
window.addEventListener('resize', resize);
resize();
orbit.addEventListener('end', () => {
  settings.camera = captureView();
  controls?.set(settings);
});
canvas.addEventListener('pointerdown', () => {
  if (settings.audio.enabled) void audio.unlock();
});

let previousTime;
renderer.setAnimationLoop(now => {
  const dt = (now - (previousTime ?? now)) / 1000;
  previousTime = now;
  if (running()) {
    const take = takeAt(clock.position());
    if (take !== currentTake) cut(take);
    simulation.step(dt);
  }
  audio.update(running());
  orbit.update();
  render();
  controls?.frame(audio);
});
document.addEventListener('visibilitychange', () => {
  previousTime = undefined;
  clock.configure(running(), settings.audio.tempo);
  audio.update(running());
});

const sketch = {
  getSetup: snapshot,
  getState: () => ({ playing: settings.motion.playing, physics: 'Box3D', time: elapsed, beat: Math.floor(clock.position()), shot: set.current.name, armAngle: 2 * Math.atan2(set.pivot.quaternion.y, set.pivot.quaternion.w), audio: audio.diagnostics }),
  setup(value) { restore(value); return sketch.getSetup(); },
  play() { if (!settings.motion.playing) actions.togglePlaying(); },
  pause() { if (settings.motion.playing) actions.togglePlaying(); },
  reset: actions.reset, saveSetup: actions.save, loadSetup: actions.reload,
};
window.__pendulumSketch = sketch;
const detachPlayer = attachPlayerBridge(sketch);
window.addEventListener('pagehide', () => {
  renderer.setAnimationLoop(null);
  detachPlayer();
  audio.dispose();
  simulation.dispose();
  set.dispose();
  orbit.dispose();
  effects.dispose();
  for (const source of [light, fill, spotlight]) source.shadow.dispose();
  environment.dispose();
  room.dispose();
  pmrem.dispose();
  renderer.dispose();
  window.removeEventListener('resize', resize);
}, { once: true });
