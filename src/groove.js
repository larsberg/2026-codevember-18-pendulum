import { rhythmOnsets } from './synth.js';

// Three bars of 4/4. Positions and gates are in musical quarter notes.
// The pendulum reaches an end stop once every three quarters.
const quartersPerClick = 3;
const quartersPerLoop = 12;

function envelope(age, hold, { attack, decay, sustain, release }) {
  if (age < 0 || age >= hold + release) return 0;
  const t = Math.min(age, hold);
  const level = t < attack ? t / attack : 1 - (1 - sustain) * Math.min(1, (t - attack) / decay);
  return age <= hold ? level : level * (1 - (age - hold) / release);
}

export function createGroove(tempo, voices) {
  const seconds = 60 / (tempo * quartersPerClick);
  const notes = [];
  function add(voice, start, span, accent) {
    const patch = voices[voice];
    if (!patch.enabled) return;
    for (const onset of rhythmOnsets(patch.rhythm)) {
      notes.push({ voice, start: start + span * onset, duration: span * patch.gate / patch.rhythm.length, accent });
    }
  }
  // Count in fours while the pendulum clicks every three quarter notes.
  for (let bar = 0; bar < quartersPerLoop; bar += 4) {
    add(1, bar, .43, 1);
    // Move just the last bar's second kick to the "and" of three.
    add(1, bar + (bar === quartersPerLoop - 4 ? 2.5 : 2), .36, .82);
    add(0, bar + 1, .30, .91);
    add(0, bar + 3, .30, 1);
  }
  // Clicks on one or three already have a kick. Give each click on a
  // backbeat a lighter kick underneath the snare at the very same onset.
  for (let click = quartersPerClick; click < quartersPerLoop; click += quartersPerClick) {
    if (click % 2 === 1) add(1, click, .27, .56);
  }

  return {
    pattern(api) {
      const layers = notes.map(({ start, duration, voice, accent }) =>
        api.pure({ voice, accent }).compress(start / quartersPerLoop, (start + duration) / quartersPerLoop));
      const loop = layers.length ? api.stack(...layers).slow(quartersPerLoop / quartersPerClick).late(1) : api.silence;
      return api.stack(api.pure({ click: true }), loop);
    },
    kickStroke(position) {
      // The first audible metronome click is the downbeat.
      const quarter = (position - 1) * quartersPerClick;
      let kick = 0;
      for (const { start, duration, voice, accent } of notes) {
        if (voice !== 1 || quarter < start) continue;
        const age = ((quarter - start) % quartersPerLoop) * seconds;
        const patch = voices[voice];
        const amplitude = patch.level * accent * envelope(age, duration * seconds, patch);
        const stroke = amplitude * Math.cos(2 * Math.PI * 6.4 * age - .9);
        if (Math.abs(stroke) > Math.abs(kick)) kick = stroke;
      }
      return kick;
    },
  };
}
