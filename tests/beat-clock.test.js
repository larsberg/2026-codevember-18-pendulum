import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { cameraCut, createBeatClock, takeAt } from '../src/beat-clock.js';

test('every click cuts once at its audio deadline, including the first click and the loop', () => {
  let now = 10;
  const clock = createBeatClock(() => now);
  clock.configure(true, 120);
  const { shots } = JSON.parse(readFileSync(new URL('../public/models/shots.json', import.meta.url)));
  const sequence = ['parlor', 'breakfast', 'library', 'listening', 'exchange',
    'conservatory', 'launderette', 'daybed', 'citrus', 'nocturne'];
  assert.deepEqual(shots.map(shot => shot.name), sequence);
  const cycle = sequence.length * 3;
  const visits = new Set();
  for (let beat = 1; beat <= cycle; beat++) {
    now = 10 + beat / 2;
    assert.equal(clock.position(), beat);
    assert.equal(clock.timeAt(beat), now);
    assert.equal(takeAt(clock.position(now - .001)), beat - 1);
    const { shot, angle } = cameraCut(takeAt(clock.position()), shots);
    assert.equal(shot.name, sequence[beat % sequence.length]);
    assert.equal(angle, Math.floor(beat / sequence.length) % 3);
    visits.add(shot.name + '/' + shot.cameras[angle].label);
  }
  assert.equal(visits.size, cycle);
  clock.seek(39.47);
  assert.deepEqual(cameraCut(takeAt(clock.position()), shots), cameraCut(39 - cycle, shots));
});

test('tempo edits, pause, resume and restoring a saved phase keep the beat continuous', () => {
  let now = 0;
  const clock = createBeatClock(() => now);
  clock.configure(true, 60);
  now = 1.25;
  clock.configure(true, 120);
  assert.equal(clock.position(), 1.25);
  assert.equal(clock.timeAt(2), 1.625);
  now = 1.5;
  clock.configure(false, 120);
  now = 1000;
  assert.equal(clock.position(), 1.75);
  clock.seek(6.5);
  clock.configure(true, 60);
  now += .5;
  assert.equal(clock.position(), 7);
  assert.equal(takeAt(clock.position()), 7);
});
