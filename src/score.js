import { createSynthPattern, modulateVoice, synthValue } from './synth.js';
import { createLiveModulation, liveSynthValue } from './live-modulation.js';
import { resumeAudioContext } from './audio-autoplay.js';
import { createAudioAnalysis, silentAnalysis } from './audio-analysis.js';

// The studio audition plays one cycle of the two configured Strudel voices.
export function createAudio({ load = () => import('@strudel/web'), onError = console.warn,
  onStatus = () => {}, resumeContext = resumeAudioContext, createModulation = createLiveModulation,
  createAnalysis = createAudioAnalysis } = {}) {
  let api, context, repl, loading, starting, contextResume, settings, modulation;
  let patternKey, hits = [], busy = false, disposed = false, running = true;
  let suspended = Promise.resolve();
  let active = false, waitingForInteraction = false, operation = 0, eventCount = 0, failed = false;
  let recentNotes = [];
  let analysis; const silence = silentAnalysis();
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
    const key = JSON.stringify(settings.voices.map(({ rhythm, gate, enabled }) => ({ rhythm, gate, enabled })));
    if (key === patternKey) return;
    patternKey = key;
    hits = createSynthPattern(api, settings.voices, index => index).queryArc(0, 1)
      .map(hap => ({ voice: hap.value, start: Number(hap.whole.begin), end: Number(hap.whole.end) }));
  }
  function halt() {
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
      // Initialize the inherited transport without an independent beat.
      await repl.setPattern(api.silence, false); refresh();
    })().catch(error => { loading = undefined; patternKey = undefined; throw error; });
    return loading;
  }
  function playHit({voice, start, end}, lead = .008) {
    const seconds = 60 / settings.tempo;
    const value = liveSynthValue(synthValue(settings, voice, positions, floor), voice);
    const duration = (end - start) * seconds;
    const when = context.currentTime + lead + start * seconds;
    const token = operation;
    void api.superdough(value, when, duration, 1 / seconds)
      .then(() => {
        if (token !== operation) return;
        eventCount++;
        recentNotes.push({ voice, note: value.note, duration });
        recentNotes = recentNotes.slice(-24);
      }).catch(error => { if (token === operation) report(error); });
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
      await repl.start();
      if (token !== operation || !wanted()) return;
      syncModulation();
      active = true; busy = false; status('Sounds enabled');
    } catch (error) { if (token === operation) report(error); } })();
    return starting;
  }
  return {
    get analysis() { if (active) analysis ??= createAnalysis(api, context); return active ? analysis?.read() ?? silence : silence; },
    get unlocked() { return active && context?.state === 'running'; },
    get diagnostics() { return { engine: 'Strudel', enabled: !!settings?.enabled, running: active, busy, waitingForInteraction,
      events: eventCount, recentNotes, live: modulation?.diagnostics, context: context?.state ?? 'locked' }; },
    get modulation() { return settings?.voices.map(voice => modulateVoice(voice, positions, floor).routes) ?? []; },
    configure(next) {
      const changedEnabled = settings?.enabled !== next.enabled;
      const retrigger = active && settings.tempo !== next.tempo;
      if (retrigger) halt();
      settings = structuredClone(next);
      refresh(); if (active) syncModulation();
      if (!settings.enabled) { if (changedEnabled || active || busy) halt(); }
      else if (!running) status('Sounds enabled · paused with sketch');
      else if (changedEnabled || retrigger) { failed = false; void start(); }
    },
    async unlock() { failed = false; return start(); },
    strike(beat) {
      if (active) for (const hit of hits) if (hit.voice === beat % 2) playHit(hit);
    },
    audition() {
      if (active) hits.forEach(hit => playHit(hit, .045));
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
