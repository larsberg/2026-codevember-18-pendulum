import { modulationTargets } from './synth-settings.js';

function rhythmOnsets(rhythm) {
  return [...rhythm].flatMap((hit, step) => hit === 'x' ? [step / rhythm.length] : []);
}

export function mapHeight(height, { heightMin, heightMax, min, max }) {
  const amount = Math.max(0, Math.min(1, (height - heightMin) / (heightMax - heightMin)));
  return min + amount * (max - min);
}
export function cornerHeight(positions, floor, corner) { return positions[corner * 3 + 1] - floor; }
export function modulateVoice(voice, positions, floor = 0) {
  const parameters = { ...voice }, routes = {};
  for (const key of Object.keys(modulationTargets)) {
    const route = voice.modulations[key], height = cornerHeight(positions, floor, route.corner);
    const value = route.enabled ? mapHeight(height, route) : voice[key];
    parameters[key] = value;
    routes[key] = { corner: route.corner, height, value, enabled: route.enabled };
  }
  const addedDrive = (voice.turnDrive ?? 0) * Math.max(0, 1 - parameters.drive / 3);
  parameters.drive += addedDrive;
  // Superdough's waveshaper raises the input exponentially with drive.
  // Trim the added gain so the turn is heard primarily as a change of timbre.
  parameters.driveTrim = Math.exp(-.84 * addedDrive);
  return { parameters, routes };
}

// Canonical Strudel patch. live-modulation replaces effect values with control
// buses so existing notes follow the corners throughout their lifetime.
export function synthValue(audio, index, positions, floor) {
  const p = modulateVoice(audio.voices[index], positions, floor).parameters;
  return { s: p.sound, note: p.note, orbit: index + 1,
    gain: audio.enabled && p.enabled ? audio.volume * p.level * .65 : 0,
    attack: p.attack, decay: p.decay, sustain: p.sustain, release: p.release,
    cutoff: p.lowpass, resonance: p.resonance, hcutoff: p.highpass,
    fmi: p.fm, fmh: p.harmonicity, distort: p.drive, distortvol: p.driveTrim, pan: p.pan,
    room: p.reverb, roomsize: p.roomSize, delay: p.delay,
    delaytime: p.delayTime * 60 / audio.tempo, delayfeedback: p.delayFeedback,
  };
}

// One cycle is one move. Strudel supplies onsets within each tween;
// live buses supply continuous timbre independently of note onsets.
export function createSynthPattern(api, voices, getValue) {
  const steps = voices.flatMap((voice, index) => voice.enabled
    ? rhythmOnsets(voice.rhythm).map(onset =>
      api.pure(index).compress(onset, onset + voice.gate / voice.rhythm.length)) : []);
  return (steps.length ? api.stack(...steps) : api.silence).withValue(index => getValue(index));
}
