import { modulationTargets, voiceFields, voiceSounds, VOICE_NAMES } from './synth-settings.js';

export const noteName = midi => `${['C', 'C♯', 'D', 'D♯', 'E', 'F', 'F♯', 'G', 'G♯', 'A', 'A♯', 'B'][midi % 12]}${Math.floor(midi / 12) - 1}`;
export function synthControlsMarkup(waveControls) {
  const slider = (voice, key, title) => {
    const [label,, min, max, step] = voiceFields[key], id = `synth-${voice}-${key}`;
    return `<label class="slider-label" for="${id}">${title ?? label}<output></output></label><input id="${id}" data-synth-voice="${voice}" data-synth-key="${key}" type="range" min="${min}" max="${max}" step="${step}">`;
  };
  const beatButtons = `<fieldset class="snare-beats"><legend>Snare beats</legend>
    ${[1, 2, 3, 4].map(beat => `<button type="button" data-snare-beat="${beat - 1}" aria-label="Beat ${beat}">${beat}</button>`).join('')}
  </fieldset>`;
  return VOICE_NAMES.map((name, i) => {
    const snare = i === 0;
    const tuning = `<label class="audio-field">${snare ? 'Tuning' : 'Root note'}<select id="synth-${i}-note" data-synth-voice="${i}" data-synth-key="note">${Array.from({ length: 73 }, (_, n) => n + 24).map(note => `<option value="${note}">${noteName(note)}</option>`).join('')}</select></label>`;
    const envelope = ['attack', 'decay', 'sustain', 'release'];
    const filters = Object.keys(voiceFields).filter(key => !['level', 'gate', ...envelope].includes(key));
    const patch = `
      <label class="audio-field">Sound<select id="synth-${i}-sound" data-synth-voice="${i}" data-synth-key="sound">${voiceSounds[i].map(s => `<option value="${s}">${s}</option>`).join('')}</select></label>
      ${snare ? '' : tuning}
      <label class="audio-field">${snare ? 'Stroke subdivision' : 'Rhythm'}<input id="synth-${i}-rhythm" data-synth-voice="${i}" data-synth-key="rhythm" type="text" maxlength="32" required spellcheck="false"></label>
      ${snare ? '' : slider(i, 'level')}${slider(i, 'gate')}
      <details class="material-group"><summary>Envelope</summary>${envelope.filter(key => !snare || key !== 'decay').map(key => slider(i, key)).join('')}</details>
      <details class="material-group"><summary>Filters and effects</summary><p class="camera-hint">Base values apply when a parameter's height mapping is off.</p>${filters.filter(key => !snare || key !== 'lowpass').map(key => slider(i, key)).join('')}</details>
      <p class="control-heading">Body height modulation</p><p class="camera-hint">Height above the ground colors each gesture when it starts. Values stay within your output min and max, including during high jumps. Swap output endpoints to invert it.</p>
      ${Object.entries(modulationTargets).map(([key, [label, unit]]) => `<details class="material-group synth-route"><summary>${label}</summary>
        <label class="lighting-toggle"><input id="synth-${i}-${key}-enabled" data-synth-voice="${i}" data-synth-route="${key}" data-synth-key="enabled" type="checkbox">Use body height</label>
        <label class="audio-field">Body<select id="synth-${i}-${key}-corner" data-synth-voice="${i}" data-synth-route="${key}" data-synth-key="corner">${Array.from({ length: 16 }, (_, n) => `<option value="${n}">Body ${n + 1}</option>`).join('')}</select></label>
        <div class="synth-range">${[['heightMin', 'Height min'], ['heightMax', 'Height max'], ['min', `Output min ${unit}`], ['max', `Output max ${unit}`]].map(([field, title]) => `<label class="audio-field">${title}<input id="synth-${i}-${key}-${field}" data-synth-voice="${i}" data-synth-route="${key}" data-synth-key="${field}" type="number" step="any" required></label>`).join('')}</div>
        <output class="audio-position" data-synth-value="${i}:${key}"></output>
      </details>`).join('')}`;
    return `<details class="material-group" open><summary>${name}</summary>
      <label class="lighting-toggle"><input type="checkbox" id="synth-${i}-enabled" data-synth-voice="${i}" data-synth-key="enabled">Enabled</label>
      ${snare ? `${beatButtons}${slider(i, 'level')}${tuning}${slider(i, 'lowpass', 'Tone (Hz)')}${slider(i, 'decay')}${waveControls}
        <details class="material-group"><summary>Advanced snare settings</summary>${patch}</details>` : patch}
    </details>`;
  }).join('');
}

export function bindSynthControls(root, { getVoices, change }) {
  const inputs = [...root.querySelectorAll('[data-synth-voice][data-synth-key]')];
  const beats = [...root.querySelectorAll('[data-snare-beat]')];
  function sync() {
    const voices = getVoices();
    for (const button of beats) button.setAttribute('aria-pressed', String(voices[0].beats[button.dataset.snareBeat] === 'x'));
    for (const input of inputs) {
      const { synthVoice, synthKey, synthRoute } = input.dataset;
      const values = synthRoute ? voices[synthVoice].modulations[synthRoute] : voices[synthVoice], value = values[synthKey];
      if (input.type === 'checkbox') input.checked = value;
      else if (input !== root.ownerDocument?.activeElement) input.value = value;
      const output = root.querySelector(`label[for="${input.id}"] output`); if (output) output.value = String(value);
    }
  }
  for (const button of beats) {
    button.addEventListener('click', () => {
      const voices = structuredClone(getVoices());
      const pattern = [...voices[0].beats], beat = Number(button.dataset.snareBeat);
      pattern[beat] = pattern[beat] === 'x' ? '.' : 'x';
      voices[0].beats = pattern.join('');
      change(voices);
    });
  }
  for (const input of inputs) {
    input.addEventListener(input.type === 'range' || input.type === 'checkbox' ? 'input' : 'change', () => {
      if (!input.checkValidity() || input.value === '') return;
      const { synthVoice, synthKey, synthRoute } = input.dataset, voices = structuredClone(getVoices());
      const values = synthRoute ? voices[synthVoice].modulations[synthRoute] : voices[synthVoice];
      values[synthKey] = input.type === 'checkbox' ? input.checked : ['sound', 'rhythm'].includes(synthKey) ? input.value : Number(input.value);
      change(voices);
    });
    input.addEventListener('blur', sync);
  }
  return { sync, frame(modulation) {
    for (const output of root.querySelectorAll('[data-synth-value]')) {
      const [index, key] = output.dataset.synthValue.split(':'), route = modulation[index]?.[key];
      if (route) output.value = `${route.enabled ? `Body ${route.corner + 1} · ${route.height.toFixed(2)} →` : 'Base →'} ${Number(route.value.toFixed(3))} ${modulationTargets[key][1]}`;
    }
  } };
}
