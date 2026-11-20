// Beat zero is the initial resting extreme. The first audible click is beat one.
export const takeAt = position => Math.floor(position);

export function createBeatClock(now = () => performance.now() / 1000) {
  let anchorTime = now(), anchorBeat = 0, bpm = 84, running = false;
  function position(time = now()) {
    return anchorBeat + (running ? (time - anchorTime) * bpm / 60 : 0);
  }
  return {
    position,
    timeAt(beat) { return anchorTime + (beat - anchorBeat) * 60 / bpm; },
    configure(play, tempo) {
      if (play === running && tempo === bpm) return;
      const at = now();
      anchorBeat = position(at);
      anchorTime = at;
      running = play;
      bpm = tempo;
    },
    seek(beat) { anchorTime = now(); anchorBeat = beat; },
  };
}
