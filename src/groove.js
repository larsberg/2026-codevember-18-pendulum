import { rhythmOnsets } from './synth.js';

// One metronome click per bar of 4/4. Kick strokes are [quarter, gate, accent, semitones].
const quartersPerBar = 4;
const swungEighth = 9 / 16;
const downbeat = [0, .54, 1, 0];
const rest = [];
const onOne = [downbeat];
const answer = [downbeat, [1 + swungEighth, .24, .60, 3]];
const onThree = [downbeat, [2, .40, .80, 0]];
const lateThree = [downbeat, [2 + swungEighth, .26, .66, 2]];
const pickup = [downbeat, [3 + swungEighth, .22, .48, 5]];
const pocket = [answer, onThree, answer, pickup];

// Each lane repeats its bar figures for the length of the section.
// The snare masks leave space by withholding strokes from the player's beat buttons.
const form = [
  { bars: 4, kicks: [rest], snares: ['....'], level: 1 },
  { bars: 4, kicks: [onOne], snares: ['....'], level: .68 },
  { bars: 4, kicks: [onOne], snares: ['...x'], level: .76 },
  { bars: 4, kicks: [onOne, onThree, onOne, pickup], snares: ['...x', 'xxxx'], level: .88 },

  { bars: 8, kicks: pocket, snares: ['xxxx'], level: 1 },
  { bars: 8, kicks: [onThree, lateThree, answer, onOne], snares: ['xxxx'], level: .96 },
  { bars: 4, kicks: [onThree, onOne, lateThree, onOne], snares: ['xxxx', '...x'], level: .88 },
  { bars: 4, kicks: [onOne], snares: ['...x', '....'], level: .72 },

  { bars: 4, kicks: [rest], snares: ['...x', '....'], level: .58 },
  { bars: 4, kicks: [rest, rest, onOne, onOne], snares: ['....'], level: .65 },
  { bars: 4, kicks: [onOne, onThree], snares: ['...x'], level: .78 },
  { bars: 4, kicks: pocket, snares: ['...x', 'xxxx'], level: .90 },

  { bars: 4, kicks: pocket, snares: ['xxxx'], level: 1 },
  { bars: 4, kicks: [answer, onThree, answer, onOne], snares: ['xxxx', 'xxxx', 'xxxx', '.x..'], level: 1 },
];

function envelope(age, hold, { attack, decay, sustain, release }) {
  if (age < 0 || age >= hold + release) return 0;
  const t = Math.min(age, hold);
  const level = t < attack ? t / attack : 1 - (1 - sustain) * Math.min(1, (t - attack) / decay);
  return age <= hold ? level : level * (1 - (age - hold) / release);
}

export function createGroove(tempo, voices) {
  const secondsPerBar = 60 / tempo;
  const secondsPerQuarter = secondsPerBar / quartersPerBar;
  const subdivisions = voices.map(patch => patch.enabled ? rhythmOnsets(patch.rhythm) : []);
  const bars = [];
  let longestKick = 0;
  for (const section of form) {
    for (let bar = 0; bar < section.bars; bar++) {
      const notes = [];
      function add(voice, start, span, accent, semitones = 0) {
        const patch = voices[voice];
        const duration = span * patch.gate / patch.rhythm.length;
        for (const onset of subdivisions[voice]) {
          notes.push({ start: start + span * onset, duration, voice, accent: accent * section.level, semitones });
        }
        if (voice === 1) longestKick = Math.max(longestKick, duration);
      }
      for (const stroke of section.kicks[bar % section.kicks.length]) add(1, ...stroke);
      const mask = section.snares[bar % section.snares.length];
      for (let beat = 0; beat < quartersPerBar; beat++) {
        if (voices[0].beats[beat] === 'x' && mask[beat] === 'x') add(0, beat, .30, beat === 3 ? 1 : .84);
      }
      bars.push(notes);
    }
  }

  const kickTailInBars = (longestKick * secondsPerQuarter + voices[1].release) / secondsPerBar;
  return {
    pattern(api) {
      const drums = bars.map(notes => {
        const layers = notes.map(({ start, duration, ...hit }) =>
          api.pure(hit).compress(start / quartersPerBar, (start + duration) / quartersPerBar));
        return layers.length ? api.stack(...layers) : api.silence;
      });
      // The first audible click is transport position one. Its clock runs through every rest.
      return api.stack(api.pure({ click: true }), api.slowcat(...drums).late(1));
    },
    kickStroke(position) {
      const barPosition = position - 1;
      const first = Math.max(0, Math.floor(barPosition - kickTailInBars));
      let kick = 0;
      for (let bar = first; bar <= Math.floor(barPosition); bar++) {
        for (const { start, duration, voice, accent, semitones } of bars[bar % bars.length]) {
          if (voice !== 1) continue;
          const age = (barPosition - bar) * secondsPerBar - start * secondsPerQuarter;
          const amplitude = voices[1].level * accent * envelope(age, duration * secondsPerQuarter, voices[1]);
          const vibration = 6.4 * 2 ** (semitones / 12);
          const stroke = amplitude * Math.cos(2 * Math.PI * vibration * age - .9);
          if (Math.abs(stroke) > Math.abs(kick)) kick = stroke;
        }
      }
      return kick;
    },
  };
}
