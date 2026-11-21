import { defaultLighting, validateLighting } from './lighting-settings.js';
import { defaultMaterials, validateMaterials } from './material-settings.js';
import { defaultPaletteLibrary, validatePaletteLibrary, libraryPalettes } from './palette-library.js';
import { audioFields, defaultVoices, validateVoices } from './synth-settings.js';

export const DEFAULT_CAMERA = { yaw: 22, elevation: 13, distance: 19.2, offsetX: 0, offsetY: 0, offsetZ: 0 };
export const fields = {
  motion: { playing: ['Playing', true], position: ['Beat position', 0, 0, Number.MAX_SAFE_INTEGER] },
  physics: {
    gravity: ['Gravity', 9.8, 0, 1000, .1], friction: ['Ground friction', 1.1, 0, 10, .01],
  },
  studio: { background: ['Background', '#eee9df'], exposure: ['Exposure', .78, .1, 3, .01], shadowOpacity: ['Ground shadow opacity', .96, 0, 1, .01] },
  bloom: { enabled: ['Enable bloom', false], strength: ['Bloom strength', .85, 0, 4, .05], radius: ['Bloom radius', .45, 0, 1, .01], threshold: ['Bloom threshold', 1.4, 0, 3, .01] },
  focus: { enabled: ['Tilt blur', false], tilt: ['Sharp band angle °', 0, -85, 85, 1], band: ['Sharp band half-width', .18, .02, .5, .01], strength: ['Blur amount', 1.5, 0, 8, .1], offset: ['Band vertical offset', 0, -.5, .5, .01] },
  audio: audioFields,
  tvWave: {
    height: ['Wave height (×)', 1, 0, 2, .05],
    density: ['Wave density (×)', 1, .25, 3, .05],
  },
  visibility: { fps: ['Show frame-rate meter', false] },
  camera: {
    yaw: ['Yaw', DEFAULT_CAMERA.yaw, -360, 360, .1], elevation: ['Elevation', DEFAULT_CAMERA.elevation, -85, 85, .1],
    distance: ['Distance', DEFAULT_CAMERA.distance, 5, 600, .1], offsetX: ['Target X', 0, -200, 200, .01],
    offsetY: ['Target Y', 0, -200, 200, .01], offsetZ: ['Target Z', 0, -200, 200, .01],
  },
};


export function defaultSetup() {
  const result = Object.fromEntries(Object.entries(fields).map(([group, entries]) => [group,
    Object.fromEntries(Object.entries(entries).map(([key, [, initial]]) => [key, initial]))]));
  result.version = 3;
  result.sketch = '18-pendulum';
  result.audio.voices = defaultVoices();
  result.lighting = defaultLighting(); result.materials = defaultMaterials();
  result.lighting.spotlight.enabled = false;
  result.lighting.directional.enabled = true;
  result.lighting.directional.intensity = 2.4;
  result.lighting.hemisphere.intensity = .65;
  result.lighting.fill.enabled = false;
  Object.assign(result.lighting.occlusion, { enabled: true, radius: .3, intensity: .85 });
  result.lighting.environment.intensity = .60;
  result.paletteLibrary = defaultPaletteLibrary();
  result.paletteId = 'ink';
  return result;
}
export function validateSetup(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid setup.');
  if (value.sketch !== undefined && value.sketch !== '18-pendulum') throw Error('Expected a 18-pendulum setup.');
  if (value.version !== undefined && ![0, 1, 2, 3].includes(value.version)) throw Error('Unsupported setup version.');
  const result = defaultSetup();
  // Unversioned files retain edits and acquire missing studio defaults.
  for (const [group, entries] of Object.entries(fields)) for (const [key, [, initial, min, max]] of Object.entries(entries)) {
    const x = value[group]?.[key] ?? result[group][key];
    const valid = typeof initial === 'number' ? Number.isFinite(x) && x >= min && x <= max
      : typeof initial === 'boolean' ? typeof x === 'boolean' : typeof x === 'string' && /^#[0-9a-f]{6}$/i.test(x);
    if (!valid) throw Error(`Invalid ${group}.${key}.`);
    result[group][key] = x;
  }
  result.audio.voices = validateVoices(value.audio?.voices, (value.version ?? 0) < 3);
  result.lighting = validateLighting(Object.fromEntries(Object.entries(result.lighting).map(([key, defaults]) => [key, { ...defaults, ...value.lighting?.[key] }])));
  result.materials = validateMaterials(value.materials);
  result.paletteLibrary = validatePaletteLibrary(value.paletteLibrary ?? result.paletteLibrary);
  result.paletteId = value.paletteId ?? result.paletteId;
  if (!libraryPalettes(result.paletteLibrary).some(p => p.id === result.paletteId)) throw Error('Invalid palette.');
  return result;
}
