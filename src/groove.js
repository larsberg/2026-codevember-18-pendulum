import { rhythmOnsets } from './synth.js';

// One swing per bar of 4/4. All positions and gates use quarter notes.
const quartersPerClick = 4;
const quartersPerLoop = 16;
const swungEighth = 9 / 16;

function envelope(age, hold, { attack, decay, sustain, release }) {
  if (age < 0 || age >= hold + release) return 0;
  const t = Math.min(age, hold);
  const level = t < attack ? t / attack : 1 - (1 - sustain) * Math.min(1, (t - attack) / decay);
  return age <= hold ? level : level * (1 - (age - hold) / release);
}

export function createGroove(tempo, voices) {
  const seconds = 60 / (tempo * quartersPerClick);
  const notes = [];
  function add(voice, start, span, accent, semitones = 0) {
    const patch = voices[voice];
    if (!patch.enabled) return;
    for (const onset of rhythmOnsets(patch.rhythm)) {
      notes.push({ voice, start: start + span * onset, duration: span * patch.gate / patch.rhythm.length, accent, semitones });
    }
  }
  for (let bar = 0; bar < quartersPerLoop; bar += quartersPerClick) {
    add(1, bar, .54, 1);
    if (bar === 0 || bar === 8) add(1, bar + 1 + swungEighth, .24, .60, 3);
    if (bar === 4) add(1, bar + 2, .40, .80);
    // Leave beat three empty on the turnaround. A light pickup leads home.
    if (bar === 12) add(1, bar + 3 + swungEighth, .22, .48, 5);
    for (let beat = 0; beat < 4; beat++) {
      if (voices[0].beats[beat] === 'x') add(0, bar + beat, .30, beat === 3 ? 1 : .84);
    }
  }

  return {
    pattern(api) {
      const layers = notes.map(({ start, duration, voice, accent, semitones }) =>
        api.pure({ voice, accent, semitones }).compress(start / quartersPerLoop, (start + duration) / quartersPerLoop));
      const loop = layers.length ? api.stack(...layers).slow(quartersPerLoop / quartersPerClick).late(1) : api.silence;
      return api.stack(api.pure({ click: true }), loop);
    },
    kickStroke(position) {
      // The first audible metronome click is the downbeat.
      const quarter = (position - 1) * quartersPerClick;
      let kick = 0;
      for (const { start, duration, voice, accent, semitones } of notes) {
        if (voice !== 1 || quarter < start) continue;
        const age = ((quarter - start) % quartersPerLoop) * seconds;
        const patch = voices[voice];
        const amplitude = patch.level * accent * envelope(age, duration * seconds, patch);
        const vibration = 6.4 * 2 ** (semitones / 12);
        const stroke = amplitude * Math.cos(2 * Math.PI * vibration * age - .9);
        if (Math.abs(stroke) > Math.abs(kick)) kick = stroke;
      }
      return kick;
    },
  };
}
