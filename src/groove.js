import { rhythmOnsets } from './synth.js';

// Three bars of 4/4. Positions and gates are in musical quarter notes.
// The pendulum reaches an end stop once every three quarters.
const quartersPerClick = 3;
const quartersPerLoop = 12;
const kickHits = [[.75, .78], [2, 1], [4, 1], [5.5, .67],
  [6.5, .82], [8, 1], [10, .96], [11.5, .66]];
const tvEndings = [0, 3, 0, -2]; // Last tap of each reply, in semitones.

function envelope(age, hold, { attack, decay, sustain, release }) {
  if (age < 0 || age >= hold + release) return 0;
  const t = Math.min(age, hold);
  const level = t < attack ? t / attack : 1 - (1 - sustain) * Math.min(1, (t - attack) / decay);
  return age <= hold ? level : level * (1 - (age - hold) / release);
}

export function createGroove(tempo, voices) {
  const seconds = 60 / (tempo * quartersPerClick);
  const notes = [];
  function add(voice, start, span, interval, accent) {
    const patch = voices[voice];
    if (!patch.enabled) return;
    for (const onset of rhythmOnsets(patch.rhythm)) {
      notes.push({ voice, start: start + span * onset, duration: span * patch.gate / patch.rhythm.length, interval, accent });
    }
  }
  for (const [quarter, accent] of kickHits) add(1, quarter, .43, 0, accent);
  for (const [swing, ending] of tvEndings.entries()) {
    const click = swing * quartersPerClick;
    // Leave the cut open, then answer with three eighth notes. The lighter
    // middle tap sits 1/32 of a quarter behind the grid (21 ms at 90 BPM).
    add(0, click + 1.5, .24, 0, 1);
    add(0, click + 2 + 1/32, .12, 0, .60);
    add(0, click + 2.5, .18, ending, .84);
  }

  return {
    pattern(api) {
      const layers = notes.map(({ start, duration, voice, interval, accent }) =>
        api.pure({ voice, interval, accent }).compress(start / quartersPerLoop, (start + duration) / quartersPerLoop));
      const loop = layers.length ? api.stack(...layers).slow(quartersPerLoop / quartersPerClick).late(1) : api.silence;
      return api.stack(api.pure({ click: true }), loop);
    },
    motion(position) {
      // The first audible metronome click is the downbeat. Read the same notes
      // and envelopes as Strudel, including on a seek or during muted playback.
      const quarter = (position - 1) * quartersPerClick;
      let bass = 0, kick = 0, cycles = 1.25, phase = 0;
      for (const { start, duration, voice, interval, accent } of notes) {
        if (quarter < start) continue;
        const age = ((quarter - start) % quartersPerLoop) * seconds;
        const patch = voices[voice];
        const amplitude = patch.level * accent * envelope(age, duration * seconds, patch);
        if (voice === 0 && amplitude > bass) {
          bass = amplitude;
          const hz = 440 * 2 ** ((patch.note + interval - 69) / 12);
          cycles = Math.max(.6, Math.min(3, 1.25 * hz / 220));
          // Slow the displayed oscillator so individual crests can be seen.
          phase = -2 * Math.PI * age * hz / 72;
        } else if (voice === 1) {
          const stroke = amplitude * Math.cos(2 * Math.PI * 6.4 * age - .9);
          if (Math.abs(stroke) > Math.abs(kick)) kick = stroke;
        }
      }
      return { bass, kick, cycles, phase };
    },
  };
}
