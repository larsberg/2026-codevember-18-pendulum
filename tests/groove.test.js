import assert from 'node:assert/strict';
import test from 'node:test';
import * as strudel from '@strudel/core/pattern.mjs';
import { createGroove } from '../src/groove.js';
import { defaultVoices } from '../src/synth-settings.js';

test('every metronome click has exactly one kick at its onset, including the loop boundary', () => {
  for (const tempo of [20, 30, 45]) {
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
    for (const kick of kicks) {
      const after = seconds => groove.kickStroke(kick + seconds * tempo / 60);
      assert.ok(after(.025) > 0, 'cone moves out on the attack');
      assert.ok(after(.090) < 0, 'cone rebounds');
      assert.equal(after(.32), 0);
    }
  }
});

test('the snare holds two and four, with room between kicks and one syncopation per phrase', () => {
  const voices = defaultVoices();
  assert.equal(voices[0].sound, 'snare');
  const score = createGroove(30, voices).pattern(strudel);
  for (const start of [1, 5]) {
    const notes = score.queryArc(start, start + 4).filter(h => h.hasOnset())
      .sort((a, b) => a.whole.begin - b.whole.begin);
    const quarterNotes = voice => notes.filter(h => h.value.voice === voice).map(h => {
      // Keep the comparison in Strudel's rational clock until the last step.
      return Number(h.whole.begin.sub(start).mul(3));
    });
    assert.deepEqual(quarterNotes(0), [1, 3, 5, 7, 9, 11]);
    assert.deepEqual(quarterNotes(1), [0, 2, 3, 4, 6, 8, 9, 10.5]);
    const snares = notes.filter(h => h.value.voice === 0);
    assert.ok(snares[0].value.accent < snares[1].value.accent);
    for (const snare of snares) {
      if (!notes.some(h => h.value.click && h.whole.begin.equals(snare.whole.begin))) continue;
      const kick = notes.find(h => h.value.voice === 1 && h.whole.begin.equals(snare.whole.begin));
      assert.ok(kick.value.accent < snare.value.accent);
    }
  }
});

test('snare beat buttons change only the snare onsets across all three bars', () => {
  const voices = defaultVoices();
  const score = () => createGroove(30, voices).pattern(strudel).queryArc(1, 5).filter(h => h.hasOnset());
  const otherHits = notes => notes.filter(h => h.value.voice !== 0).map(h => [Number(h.whole.begin), h.value]);
  const baseline = otherHits(score());
  for (const [beats, quarters] of [['x.x.', [0, 2, 4, 6, 8, 10]], ['....', []]]) {
    voices[0].beats = beats;
    const notes = score();
    assert.deepEqual(notes.filter(h => h.value.voice === 0).map(h => Number(h.whole.begin.sub(1).mul(3))).sort((a, b) => a - b), quarters);
    assert.deepEqual(otherHits(notes), baseline);
  }
});
