import assert from 'node:assert/strict';
import test from 'node:test';
import * as strudel from '@strudel/core/pattern.mjs';
import { createGroove } from '../src/groove.js';
import { defaultVoices } from '../src/synth-settings.js';

test('every metronome click has exactly one kick at its onset, including the loop boundary', () => {
  for (const tempo of [15, 21, 30, 45]) {
    const groove = createGroove(tempo, defaultVoices());
    const score = groove.pattern(strudel);
    const clicks = [], kicks = [];
    for (let from = 1; from < 10; from += .125) {
      for (const hap of score.queryArc(from, from + .125)) {
        if (!hap.hasOnset()) continue;
        const beat = Number(hap.whole.begin);
        if (hap.value.click) clicks.push(beat);
        else if (hap.value.voice === 1) kicks.push(beat);
      }
    }
    assert.deepEqual(clicks, [1, 2, 3, 4, 5, 6, 7, 8, 9]);
    for (const click of clicks) assert.equal(kicks.filter(beat => beat === click).length, 1);
    for (const [index, kick] of kicks.entries()) {
      const after = seconds => groove.kickStroke(kick + seconds * tempo / 60);
      assert.ok(after(.025) > 0, 'cone moves out on the attack');
      assert.ok(after(.090) < 0, 'cone rebounds');
      const gap = (kicks[index + 1] - kick) * 60 / tempo;
      if (gap > .6) assert.equal(after(.6), 0, 'the cone settles in the rest');
    }
  }
});

test('the four-bar phrase holds two and four against a deep downbeat and higher answering kicks', () => {
  const voices = defaultVoices();
  assert.equal(voices[0].sound, 'snare');
  const score = createGroove(30, voices).pattern(strudel);
  for (const start of [1, 5]) {
    const notes = score.queryArc(start, start + 4).filter(h => h.hasOnset())
      .sort((a, b) => a.whole.begin - b.whole.begin);
    const quarterNotes = voice => notes.filter(h => h.value.voice === voice).map(h => {
      // Keep the comparison in Strudel's rational clock until the last step.
      return Number(h.whole.begin.sub(start).mul(4));
    });
    assert.deepEqual(quarterNotes(0), [1, 3, 5, 7, 9, 11, 13, 15]);
    assert.deepEqual(quarterNotes(1), [0, 1.5625, 4, 6, 8, 9.5625, 12, 15.5625]);
    const kicks = notes.filter(h => h.value.voice === 1);
    assert.deepEqual(kicks.map(h => h.value.semitones), [0, 3, 0, 0, 0, 3, 0, 5]);
    assert.ok(kicks.filter((_, i) => i % 2 === 1).every(h => h.value.accent < kicks[0].value.accent));
    const snares = notes.filter(h => h.value.voice === 0);
    assert.ok(snares[0].value.accent < snares[1].value.accent);
  }
});

test('snare beat buttons change only the snare onsets across all four bars', () => {
  const voices = defaultVoices();
  const score = () => createGroove(30, voices).pattern(strudel).queryArc(1, 5).filter(h => h.hasOnset());
  const otherHits = notes => notes.filter(h => h.value.voice !== 0).map(h => [Number(h.whole.begin), h.value]);
  const baseline = otherHits(score());
  for (const [beats, quarters] of [['x.x.', [0, 2, 4, 6, 8, 10, 12, 14]], ['....', []]]) {
    voices[0].beats = beats;
    const notes = score();
    assert.deepEqual(notes.filter(h => h.value.voice === 0).map(h => Number(h.whole.begin.sub(1).mul(4))).sort((a, b) => a - b), quarters);
    assert.deepEqual(otherHits(notes), baseline);
  }
});
