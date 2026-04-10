/**
 * Ambient Soundscape — Data Sonification
 *
 * Maps simulation state to audio parameters via Web Audio API:
 *   - Population health -> base drone frequency (low = healthy, high = crisis)
 *   - Conflict intensity -> percussion / rhythmic elements
 *   - Gini coefficient -> harmonic dissonance
 *   - Awareness spread -> ethereal overtone layer
 *   - Faction count -> harmonic complexity (more factions = more voices)
 */

export type SoundscapeParams = {
	avgHealth: number;       // 0-1
	conflictIntensity: number; // 0-1
	gini: number;            // 0-1
	avgAwareness: number;    // 0-1
	factionCount: number;    // 0+
	population: number;      // 0+
};

const DRONE_BASE_FREQ = 55;   // A1 — low healthy drone
const DRONE_CRISIS_FREQ = 110; // A2 — higher = more tension

class Soundscape {
	private ctx: AudioContext | null = null;
	private masterGain: GainNode | null = null;

	// Drone layer
	private droneOsc: OscillatorNode | null = null;
	private droneGain: GainNode | null = null;

	// Dissonance layer (Gini)
	private dissonanceOsc: OscillatorNode | null = null;
	private dissonanceGain: GainNode | null = null;

	// Awareness overtone layer
	private overtoneOsc: OscillatorNode | null = null;
	private overtoneGain: GainNode | null = null;

	// Percussion layer (conflict)
	private percInterval: ReturnType<typeof setInterval> | null = null;
	private percGain: GainNode | null = null;

	// Faction harmonic voices
	private factionOscs: OscillatorNode[] = [];
	private factionGains: GainNode[] = [];

	private _active = false;
	private _volume = 0.3;

	get active() { return this._active; }

	start() {
		if (this._active) return;
		this._active = true;

		this.ctx = new AudioContext();
		this.masterGain = this.ctx.createGain();
		this.masterGain.gain.value = this._volume;
		this.masterGain.connect(this.ctx.destination);

		// ── Drone: continuous low-frequency oscillator ──
		this.droneOsc = this.ctx.createOscillator();
		this.droneOsc.type = 'sawtooth';
		this.droneOsc.frequency.value = DRONE_BASE_FREQ;
		this.droneGain = this.ctx.createGain();
		this.droneGain.gain.value = 0.15;

		// Low-pass filter for warmth
		const droneLPF = this.ctx.createBiquadFilter();
		droneLPF.type = 'lowpass';
		droneLPF.frequency.value = 200;
		droneLPF.Q.value = 2;

		this.droneOsc.connect(droneLPF);
		droneLPF.connect(this.droneGain);
		this.droneGain.connect(this.masterGain);
		this.droneOsc.start();

		// ── Dissonance layer: detuned oscillator for Gini ──
		this.dissonanceOsc = this.ctx.createOscillator();
		this.dissonanceOsc.type = 'sine';
		this.dissonanceOsc.frequency.value = DRONE_BASE_FREQ * 1.01; // slight beating
		this.dissonanceGain = this.ctx.createGain();
		this.dissonanceGain.gain.value = 0; // starts silent
		this.dissonanceOsc.connect(this.dissonanceGain);
		this.dissonanceGain.connect(this.masterGain);
		this.dissonanceOsc.start();

		// ── Awareness overtone: ethereal high sine ──
		this.overtoneOsc = this.ctx.createOscillator();
		this.overtoneOsc.type = 'sine';
		this.overtoneOsc.frequency.value = 880; // A5
		this.overtoneGain = this.ctx.createGain();
		this.overtoneGain.gain.value = 0;
		this.overtoneOsc.connect(this.overtoneGain);
		this.overtoneGain.connect(this.masterGain);
		this.overtoneOsc.start();

		// ── Percussion: gain node for conflict clicks ──
		this.percGain = this.ctx.createGain();
		this.percGain.gain.value = 0;
		this.percGain.connect(this.masterGain);
	}

	stop() {
		if (!this._active || !this.ctx) return;
		this._active = false;

		this.droneOsc?.stop();
		this.dissonanceOsc?.stop();
		this.overtoneOsc?.stop();
		for (const osc of this.factionOscs) {
			try { osc.stop(); } catch { /* already stopped */ }
		}
		this.factionOscs = [];
		this.factionGains = [];

		if (this.percInterval) {
			clearInterval(this.percInterval);
			this.percInterval = null;
		}

		this.ctx.close();
		this.ctx = null;
		this.masterGain = null;
	}

	setVolume(v: number) {
		this._volume = Math.max(0, Math.min(1, v));
		if (this.masterGain) {
			this.masterGain.gain.setTargetAtTime(this._volume, this.ctx!.currentTime, 0.1);
		}
	}

	/**
	 * Update audio parameters from simulation state.
	 * Called each tick (or on a throttled schedule).
	 */
	update(params: SoundscapeParams) {
		if (!this._active || !this.ctx) return;
		const t = this.ctx.currentTime;
		const ramp = 0.3; // smooth transitions

		// ── Drone frequency: health maps to pitch ──
		// Low health (crisis) = higher frequency = more tension
		const healthFreq = DRONE_BASE_FREQ + (1 - params.avgHealth) * (DRONE_CRISIS_FREQ - DRONE_BASE_FREQ);
		this.droneOsc?.frequency.setTargetAtTime(healthFreq, t, ramp);

		// ── Dissonance: Gini coefficient ──
		// Higher Gini = more detuning + volume
		const detune = params.gini * 15; // up to 15 cents detune
		const dissonanceVol = params.gini * 0.12;
		this.dissonanceOsc?.frequency.setTargetAtTime(healthFreq * (1 + detune / 1200), t, ramp);
		this.dissonanceGain?.gain.setTargetAtTime(dissonanceVol, t, ramp);

		// ── Awareness overtone ──
		// Higher average awareness = louder ethereal layer + rising pitch
		const awarenessVol = params.avgAwareness * 0.08;
		const awarenessPitch = 660 + params.avgAwareness * 440; // 660-1100 Hz
		this.overtoneOsc?.frequency.setTargetAtTime(awarenessPitch, t, ramp);
		this.overtoneGain?.gain.setTargetAtTime(awarenessVol, t, ramp);

		// ── Conflict percussion ──
		this._updatePercussion(params.conflictIntensity);

		// ── Faction harmonic complexity ──
		this._updateFactionVoices(params.factionCount, healthFreq);
	}

	private _updatePercussion(intensity: number) {
		if (!this.ctx || !this.percGain) return;

		// Clear previous pattern
		if (this.percInterval) {
			clearInterval(this.percInterval);
			this.percInterval = null;
		}

		if (intensity < 0.05) return; // no percussion when peaceful

		// Interval: faster when conflict is higher (800ms down to 200ms)
		const intervalMs = 800 - intensity * 600;
		this.percInterval = setInterval(() => {
			if (!this.ctx || !this.percGain) return;
			const now = this.ctx.currentTime;

			// Noise burst for percussion
			const bufferSize = this.ctx.sampleRate * 0.03; // 30ms
			const buffer = this.ctx.createBuffer(1, bufferSize, this.ctx.sampleRate);
			const data = buffer.getChannelData(0);
			for (let i = 0; i < bufferSize; i++) {
				data[i] = (Math.random() * 2 - 1) * Math.exp(-i / (bufferSize * 0.3));
			}

			const source = this.ctx.createBufferSource();
			source.buffer = buffer;

			const clickGain = this.ctx.createGain();
			clickGain.gain.setValueAtTime(intensity * 0.15, now);
			clickGain.gain.exponentialRampToValueAtTime(0.001, now + 0.05);

			// Band-pass filter for tonal quality
			const bpf = this.ctx.createBiquadFilter();
			bpf.type = 'bandpass';
			bpf.frequency.value = 100 + intensity * 200;
			bpf.Q.value = 5;

			source.connect(bpf);
			bpf.connect(clickGain);
			clickGain.connect(this.masterGain!);
			source.start(now);
		}, intervalMs);
	}

	private _updateFactionVoices(count: number, baseFreq: number) {
		if (!this.ctx || !this.masterGain) return;

		const targetCount = Math.min(count, 6); // cap at 6 voices

		// Remove excess voices
		while (this.factionOscs.length > targetCount) {
			const osc = this.factionOscs.pop()!;
			const gain = this.factionGains.pop()!;
			gain.gain.setTargetAtTime(0, this.ctx.currentTime, 0.2);
			setTimeout(() => { try { osc.stop(); } catch { /* ok */ } }, 500);
		}

		// Add missing voices — each at a different harmonic
		const harmonics = [1.5, 2, 2.5, 3, 3.5, 4]; // perfect fifth, octave, etc.
		while (this.factionOscs.length < targetCount) {
			const idx = this.factionOscs.length;
			const osc = this.ctx.createOscillator();
			osc.type = 'sine';
			osc.frequency.value = baseFreq * harmonics[idx];

			const gain = this.ctx.createGain();
			gain.gain.value = 0;
			gain.gain.setTargetAtTime(0.03, this.ctx.currentTime, 0.5);

			osc.connect(gain);
			gain.connect(this.masterGain);
			osc.start();

			this.factionOscs.push(osc);
			this.factionGains.push(gain);
		}

		// Update existing voice frequencies
		const t = this.ctx.currentTime;
		for (let i = 0; i < this.factionOscs.length; i++) {
			this.factionOscs[i].frequency.setTargetAtTime(baseFreq * harmonics[i], t, 0.3);
		}
	}
}

/** Singleton soundscape instance */
export const soundscape = new Soundscape();
