import assert from 'node:assert/strict';
import test from 'node:test';
import * as strudel from '@strudel/core/pattern.mjs';
import { createGroove } from '../src/groove.js';
import { defaultVoices } from '../src/synth-settings.js';

function events(score, from, to) {
  return score.queryArc(from, to).filter(h => h.hasOnset()).sort((a, b) => a.whole.begin - b.whole.begin)
    .map(h => ({ at: Number(h.whole.begin), ...h.value }));
}
const drum = (hits, voice) => hits.filter(h => h.voice === voice);

test('one mechanical click on every bar, with an identical score on every lap', () => {
  const score = createGroove(21, defaultVoices()).pattern(strudel);
  const lap = offset => events(score, 1 + offset, 65 + offset).map(hit => ({ ...hit, at: hit.at - offset }));
  const first = lap(0);
  assert.deepEqual(first.filter(h => h.click).map(h => h.at), Array.from({ length: 64 }, (_, i) => i + 1));
  assert.deepEqual(lap(64), first);
  assert.deepEqual(lap(64 * 1000), first);
  // The scheduler asks for short arcs, including arcs that straddle the seam.
  const sliced = [];
  for (let t = 63.875; t < 66; t += .125) sliced.push(...events(score, t, t + .125));
  assert.deepEqual(sliced, events(score, 63.875, 66));
});

test('drums enter separately, thin to isolated strokes, and reunite before the seam', () => {
  const score = createGroove(21, defaultVoices()).pattern(strudel);
  const notes = (from, to, voice) => drum(events(score, from, to), voice).map(h => h.at);
  assert.deepEqual(events(score, 1, 5).map(h => h.click), [true, true, true, true]);
  assert.deepEqual(notes(5, 9, 1), [5, 6, 7, 8]);
  assert.deepEqual(notes(5, 9, 0), []);
  assert.deepEqual(notes(9, 13, 0), [9.75, 10.75, 11.75, 12.75]);
  assert.deepEqual(notes(25, 29, 1), [25, 25.5, 26, 26.640625, 27, 27.390625, 28]);
  assert.deepEqual(notes(41, 47, 1), []);
  assert.deepEqual(notes(41, 47, 0), [41.75, 43.75]);
  assert.deepEqual(notes(47, 49, 1), [47, 48]);
  assert.deepEqual(notes(49, 53, 0), [49.75, 50.75, 51.75, 52.75]);
  assert.deepEqual(notes(64, 69, 1), [64]);
  assert.deepEqual(notes(64, 69, 0), [64.25]);
});

test('Composition B returns at full strength with its backbeat, swung kicks and pitches', () => {
  const score = createGroove(21, defaultVoices()).pattern(strudel);
  for (const start of [17, 21, 57]) {
    const hits = events(score, start, start + 4);
    const quarters = voice => drum(hits, voice).map(h => (h.at - start) * 4);
    assert.deepEqual(quarters(0), [1, 3, 5, 7, 9, 11, 13, 15]);
    assert.deepEqual(quarters(1), [0, 1.5625, 4, 6, 8, 9.5625, 12, 15.5625]);
    assert.deepEqual(drum(hits, 1).map(h => h.semitones), [0, 3, 0, 0, 0, 3, 0, 5]);
    assert.deepEqual(drum(hits, 1).map(h => h.accent), [1, .6, 1, .8, 1, .6, 1, .48]);
    assert.deepEqual(drum(hits, 0).map(h => h.accent), [.84, 1, .84, 1, .84, 1, .84, 1]);
  }
});

test('the speaker follows the scheduled strokes, section dynamics and rests at different tempos', () => {
  for (const tempo of [15, 21, 30, 45]) {
    const groove = createGroove(tempo, defaultVoices());
    const kicks = drum(events(groove.pattern(strudel), 1, 65), 1);
    for (const { at } of kicks) {
      assert.ok(groove.kickStroke(at + .025 * tempo / 60) > 0);
      assert.ok(groove.kickStroke(at + .090 * tempo / 60) < 0);
    }
    for (const at of [.75, 1.02, 4.75, 41.5, 46.9, 65.02]) assert.equal(groove.kickStroke(at), 0);
    const attack = .025 * tempo / 60;
    assert.ok(groove.kickStroke(5 + attack) < groove.kickStroke(17 + attack));
    assert.ok(Math.abs(groove.kickStroke(69 + attack) - groove.kickStroke(5 + attack)) < 1e-10);
  }
});

test('snare beat buttons, subdivisions and mute still respect the arrangement', () => {
  const voices = defaultVoices();
  const score = () => createGroove(21, voices).pattern(strudel);
  const unaffected = events(score(), 1, 65).filter(h => h.voice !== 0);
  voices[0].beats = 'x.x.';
  assert.deepEqual(drum(events(score(), 1, 13), 0), []);
  assert.deepEqual(drum(events(score(), 17, 18), 0).map(h => h.at), [17, 17.5]);
  voices[0].rhythm = '.x';
  const delayed = drum(events(score(), 17, 18), 0);
  assert.equal(delayed.length, 2);
  assert.ok(delayed[0].at > 17 && delayed[0].at < 17.25);
  for (const beats of ['....', 'x.x.']) {
    voices[0].beats = beats;
    if (beats === 'x.x.') voices[0].enabled = false;
    assert.deepEqual(events(score(), 1, 65), unaffected);
  }
});
