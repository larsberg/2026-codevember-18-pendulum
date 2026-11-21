import { createSynthPattern, modulateVoice, synthValue } from './synth.js';
import { createLiveModulation, liveSynthValue } from './live-modulation.js';
import { resumeAudioContext } from './audio-autoplay.js';
import { createAudioAnalysis, silentAnalysis } from './audio-analysis.js';
import { createGroove } from './groove.js';

export function createAudio({ clock, load = () => import('@strudel/web'), onError = console.warn,
  onStatus = () => {}, resumeContext = resumeAudioContext, createModulation = createLiveModulation,
  createAnalysis = createAudioAnalysis } = {}) {
  let api, context, repl, loading, starting, contextResume, settings, modulation;
  let groove, score, nextQuery, timer, clicks = 0, lastClickBeat = 0;
  let patternKey, hits = [], busy = false, disposed = false, running = true;
  let suspended = Promise.resolve();
  let active = false, waitingForInteraction = false, operation = 0, eventCount = 0, failed = false;
  let recentNotes = [];
  let analysis; const silence = silentAnalysis();
  const analysers = () => analysis ??= createAnalysis(api, context);
  const positions = new Float64Array(48), floor = 0;
  const wanted = () => !disposed && running && settings?.enabled;
  function syncModulation() {
    const musical = settings.voices.some(voice => voice.enabled);
    if (musical && !modulation) modulation = createModulation(api, context);
    if (!musical && modulation) { modulation.dispose(); modulation = undefined; }
    modulation?.update(settings, positions, floor);
  }
  function status(message, error = false) {
    onStatus({ message, error, enabled: !!settings?.enabled, paused: !running, playing: active, busy, waitingForInteraction });
  }
  function refresh() {
    if (!api || !settings) return;
    const key = JSON.stringify([settings.tempo, settings.voices.map(({ rhythm, gate, enabled }) => [rhythm, gate, enabled])]);
    if (key === patternKey) return;
    patternKey = key;
    score = groove.pattern(api);
    hits = createSynthPattern(api, settings.voices, index => index).queryArc(0, 1)
      .map(hap => ({ voice: hap.value, start: Number(hap.whole.begin), end: Number(hap.whole.end) }));
  }
  function halt() {
    clearInterval(timer); nextQuery = undefined;
    operation++; active = false; busy = false;
    contextResume?.cancel(); contextResume = undefined; waitingForInteraction = false;
    analysis?.dispose(); analysis = undefined; repl?.pause(); modulation?.dispose(); modulation = undefined;
    if (context) api?.resetGlobalEffects();
    if (context?.state === 'running') suspended = context.suspend().catch(report);
    if (!disposed) status(settings?.enabled ? 'Sounds enabled · paused with sketch' : 'Sounds muted');
  }
  function report(error) {
    if (disposed) return;
    failed = true; halt(); status(error.message, true); onError(`Audio: ${error.message}`);
  }
  async function initialize() {
    loading ??= (async () => {
      api = await load(); if (disposed) return;
      context = api.getAudioContext(); repl = await api.initStrudel();
      if (disposed) { repl.stop(); if (context.state !== 'closed') await context.close(); return; }
      await api.initAudio(); if (disposed) { repl.stop(); return; }
      const snare = new URL('./assets/tv-snare.wav', import.meta.url).href;
      await api.samples({ snare: { a3: [snare] } });
      await api.loadBuffer(snare, context, 'TV snare');
      if (disposed) return;
      refresh();
    })().catch(error => { loading = undefined; patternKey = undefined; throw error; });
    return loading;
  }
  function playHit(event, when, duration, beat) {
    const seconds = 60 / settings.tempo;
    let value;
    if (event.click) {
      // The two end stops have distinct timbres, one tick per swing.
      value = { s: 'triangle', note: beat % 2 ? 83 : 89, orbit: 0,
        attack: .001, decay: .012, sustain: 0, release: .009,
        cutoff: 6500, fmi: 1.2, fmh: 2.31, gain: settings.volume * .73, pan: .5,
        delay: 0, room: 0 };
      duration = .027;
    } else {
      value = liveSynthValue(synthValue(settings, event.voice, positions, floor), event.voice);
      value.postgain = event.accent ?? 1;
      // A damped drumhead, falling from 87 Hz to 49 Hz on the stock patch.
      if (event.voice === 1) Object.assign(value, { penv: 10, pattack: .003, pdecay: .075, psustain: 0, panchor: 0 });
    }
    const token = operation;
    void api.superdough(value, when, duration, 1 / seconds, beat).then(() => {
      if (token !== operation) return;
      eventCount++;
      if (event.click) { clicks++; lastClickBeat = beat; }
      recentNotes.push({ voice: event.click ? 'click' : event.voice, note: value.note, duration, beat });
      recentNotes = recentNotes.slice(-24);
    }).catch(error => { if (token === operation) report(error); });
  }
  function schedule() {
    if (!active || context.state !== 'running') return;
    const now = performance.now() / 1000;
    const from = Math.max(nextQuery ?? 1, clock.position(now), 1);
    // Query a little ahead, then let the audio hardware execute each onset.
    // getOutputTimestamp maps the visual clock to sound leaving the speakers.
    const stamp = context.getOutputTimestamp?.();
    const audioNow = stamp?.performanceTime > 0
      ? stamp.contextTime + now - stamp.performanceTime / 1000
      : context.currentTime - (context.outputLatency || context.baseLatency || 0);
    const to = clock.position(now + .12 + Math.max(0, context.currentTime - audioNow));
    if (to <= from) return;
    const earliest = context.currentTime + .002;
    for (const hap of score.queryArc(from, to)) {
      if (!hap.hasOnset()) continue;
      const beat = Number(hap.whole.begin);
      const when = Math.max(earliest, audioNow + clock.timeAt(beat) - now);
      playHit(hap.value, when, Number(hap.duration) * 60 / settings.tempo, beat);
    }
    nextQuery = to;
  }
  function start() {
    if (!wanted() || active) return Promise.resolve();
    if (busy) return starting;
    const token = ++operation; busy = true; status('Loading sounds…');
    starting = (async () => { try {
      await initialize();
      await suspended;
      if (token !== operation || !wanted()) return;
      contextResume = resumeContext(context, { onWaiting() { waitingForInteraction = true; status('Sounds enabled · touch or click to hear them'); } });
      const resumed = await contextResume.ready;
      if (token !== operation || !wanted()) return;
      contextResume = undefined; waitingForInteraction = false;
      if (!resumed) throw Error('Audio context closed. Reload to retry.');
      syncModulation();
      active = true; busy = false; schedule();
      timer = setInterval(schedule, 25);
      status('Sounds enabled');
    } catch (error) { if (token === operation) report(error); } })();
    return starting;
  }
  return {
    stageMotion(position) {
      const tv = settings.voices[0];
      const audible = active && context.state === 'running' && settings.volume > 0 && tv.enabled && tv.level > 0;
      return { kick: groove.kickStroke(position), snare: audible ? analysers().tvPeak() : 0, position };
    },
    get analysis() { return active ? analysers().read() : silence; },
    get unlocked() { return active && context?.state === 'running'; },
    get diagnostics() { return { engine: 'Strudel', enabled: !!settings?.enabled, running: active, busy, waitingForInteraction,
      events: eventCount, clicks, lastClickBeat, recentNotes, live: modulation?.diagnostics, context: context?.state ?? 'locked' }; },
    get modulation() { return settings?.voices.map(voice => modulateVoice(voice, positions, floor).routes) ?? []; },
    configure(next) {
      const changedEnabled = settings?.enabled !== next.enabled;
      const retrigger = active && settings.tempo !== next.tempo;
      if (retrigger) halt();
      settings = structuredClone(next);
      groove = createGroove(settings.tempo, settings.voices);
      refresh(); if (active) syncModulation();
      if (!settings.enabled) { if (changedEnabled || active || busy) halt(); }
      else if (!running) status('Sounds enabled · paused with sketch');
      else if (changedEnabled || retrigger || (!active && !busy && !failed)) { failed = false; void start(); }
    },
    async unlock() { failed = false; return start(); },
    resync() { if (active || busy) halt(); },
    audition() {
      if (!active) return;
      const seconds = 60 / settings.tempo;
      for (const hit of hits) playHit(hit, context.currentTime + .03 + hit.start * seconds, (hit.end-hit.start) * seconds, 0);
    },
    update(play) {
      const wasRunning = running;
      running = play;
      if (wasRunning && !play) halt();
      if (wanted() && !failed && !active && !busy) void start();
    },
    dispose() {
      if (disposed) return;
      disposed = true; halt(); repl?.stop();
      if (context && context.state !== 'closed') void context.close();
    },
  };
}
