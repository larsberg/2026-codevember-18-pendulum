import assert from 'node:assert/strict';
import test from 'node:test';
import * as strudel from '@strudel/core/pattern.mjs';
import { createGroove } from '../src/groove.js';
import { defaultVoices } from '../src/synth-settings.js';

test('each metronome click gets two kick hits and a three-tap TV reply', () => {
  const groove = createGroove(30, defaultVoices());
  const score = groove.pattern(strudel);
  const clicks = [], kicks = [], taps = [];
  for (let from = 1; from < 9; from += .125) {
    for (const hap of score.queryArc(from, from + .125)) {
      if (!hap.hasOnset()) continue;
      const beat = Number(hap.whole.begin);
      if (hap.value.click) clicks.push(beat);
      else if (hap.value.voice === 1) kicks.push(beat);
      else taps.push({ beat, ...hap.value });
    }
  }
  assert.deepEqual(clicks, [1,2,3,4,5,6,7,8]);
  assert.equal(taps.length, clicks.length * 3);
  for (const beat of clicks) {
    assert.equal(kicks.filter(start => start > beat && start < beat + 1).length, 2);
    const reply = taps.filter(tap => tap.beat >= beat && tap.beat < beat + 1);
    assert.equal(reply.length, 3);
    assert.equal(reply[0].beat, beat + .5);
    assert.ok(reply[1].beat > beat + 2/3 && reply[1].beat < beat + .70);
    assert.ok(Math.abs(reply[2].beat - (beat + 5/6)) < 1e-8);
    assert.ok(reply[1].accent < reply[2].accent && reply[2].accent < reply[0].accent);
    for (const tap of reply) {
      assert.ok(groove.motion(tap.beat + .01).bass > 0);
      assert.equal(groove.motion(tap.beat + .09).bass, 0, 'leave a gap after every tap');
    }
  }
  assert.deepEqual(taps.filter((_, i) => i % 3 === 2).map(tap => tap.interval), [0,3,0,-2,0,3,0,-2]);
  for (const beat of kicks) {
    assert.ok(groove.motion(beat + .0125).kick > 0, 'cone moves out on the attack');
    assert.ok(groove.motion(beat + .045).kick < 0, 'cone rebounds');
    assert.equal(groove.motion(beat + .16).kick, 0);
  }
});

test('the TV follows the audible pitches and rests, independently of the speaker', () => {
  const voices = defaultVoices();
  voices[0].rhythm = '.x';
  voices[1].enabled = false;
  const groove = createGroove(30, voices);
  const notes = groove.pattern(strudel).queryArc(1, 5).filter(hap => hap.value.voice !== undefined);
  assert.equal(notes.length, 12);
  assert.equal(groove.motion(1.1).bass, 0);
  for (const note of notes) {
    assert.equal(note.value.voice, 0);
    const frame = groove.motion(Number(note.whole.begin) + .02);
    assert.ok(frame.bass > 0);
    assert.equal(frame.kick, 0);
    assert.ok(Math.abs(frame.cycles - 1.25 * 2 ** (note.value.interval / 12)) < 1e-8);
  }
});
