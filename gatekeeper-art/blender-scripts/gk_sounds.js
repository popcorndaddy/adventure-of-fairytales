// Extra cinematic sounds for the Gatekeeper (44.1 kHz mono WAV): portal hum, portal flicker, stone drag,
// heavy footstep, sword impact boom, whoosh, eyes-open swell.
const fs = require('fs'), path = require('path');
const OUT = process.argv[2]; fs.mkdirSync(OUT, { recursive: true });
const SR = 44100;
let seed = 99; const rnd = () => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed / 0x7fffffff; };
function wav(name, b, peakTo = 0.89) {
  let pk = 0; for (const v of b) pk = Math.max(pk, Math.abs(v));
  const g = pk ? peakTo / pk : 1, d = Buffer.alloc(b.length * 2);
  b.forEach((v, i) => d.writeInt16LE(Math.round(Math.max(-1, Math.min(1, v * g)) * 32767), i * 2));
  const h = Buffer.alloc(44); h.write('RIFF', 0); h.writeUInt32LE(36 + d.length, 4); h.write('WAVE', 8); h.write('fmt ', 12);
  h.writeUInt32LE(16, 16); h.writeUInt16LE(1, 20); h.writeUInt16LE(1, 22); h.writeUInt32LE(SR, 24); h.writeUInt32LE(SR * 2, 28);
  h.writeUInt16LE(2, 32); h.writeUInt16LE(16, 34); h.write('data', 36); h.writeUInt32LE(d.length, 40);
  fs.writeFileSync(path.join(OUT, name), Buffer.concat([h, d]));
}
function reverb(b, mix = 0.4) {
  const o = Float32Array.from(b), taps = [[0.031, 0.62], [0.037, 0.58], [0.043, 0.55], [0.053, 0.5], [0.13, 0.35], [0.21, 0.28]];
  const L = taps.map(([d, fb]) => ({ n: Math.floor(d * SR), fb, buf: new Float32Array(Math.floor(d * SR)), i: 0 }));
  for (let n = 0; n < b.length; n++) { let w = 0; for (const l of L) { const y = l.buf[l.i]; l.buf[l.i] = b[n] + y * l.fb; l.i = (l.i + 1) % l.n; w += y; } o[n] = b[n] * (1 - mix) + w / L.length * mix * 2.2; }
  return o;
}
const fade = (b, s) => { const n = Math.floor(s * SR); for (let i = 0; i < n; i++) { b[i] *= i / n; b[b.length - 1 - i] *= i / n; } return b; };

{ // portal hum: deep beating drone with a slow swirling filter, 10 s loop
  const N = 10 * SR, b = new Float32Array(N); let lp = 0;
  for (let i = 0; i < N; i++) { const t = i / SR;
    let s = 0.5 * Math.sin(2 * Math.PI * 36.7 * t) + 0.4 * Math.sin(2 * Math.PI * 37.4 * t) + 0.2 * Math.sin(2 * Math.PI * 73.4 * t + Math.sin(t * 0.7));
    lp += 0.01 * ((rnd() * 2 - 1) - lp); s += lp * 2.5 * (0.6 + 0.4 * Math.sin(2 * Math.PI * 0.2 * t));
    s += 0.04 * Math.sin(2 * Math.PI * (440 + 30 * Math.sin(t * 0.5)) * t) * (0.5 + 0.5 * Math.sin(t * 1.3));
    b[i] = s; }
  wav('portal_hum.wav', fade(reverb(b, 0.5), 0.8));
}
{ // portal flicker: crackling electric stutter
  const N = Math.floor(1.6 * SR), b = new Float32Array(N);
  for (let i = 0; i < N; i++) { const t = i / SR; const gate = (Math.floor(t * 23) % 3 === 0 || rnd() < 0.02) ? 1 : 0.15;
    b[i] = gate * ((rnd() * 2 - 1) * 0.5 + 0.5 * Math.sign(Math.sin(2 * Math.PI * 120 * t))) * Math.exp(-t * 1.4); }
  wav('portal_flicker.wav', reverb(b, 0.35));
}
{ // stone drag: gritty scraping noise with random grain bursts and sparks
  const N = Math.floor(3.5 * SR), b = new Float32Array(N); let lp = 0, hp = 0, prev = 0;
  for (let i = 0; i < N; i++) { const t = i / SR; const w = rnd() * 2 - 1;
    lp += 0.25 * (w - lp); hp = 0.97 * (hp + lp - prev); prev = lp;
    const grain = 0.5 + 0.5 * Math.sin(2 * Math.PI * 17 * t + 3 * Math.sin(t * 5)) * (rnd() < 0.3 ? 1 : 0.6);
    let s = hp * grain * Math.min(1, t * 3) * Math.min(1, (3.5 - t) * 2);
    if (rnd() < 0.0009) for (let k = 0; k < 300 && i + k < N; k++) b[i + k] += 0.4 * Math.sin(k * 1.9) * Math.exp(-k / 60);
    b[i] += s; }
  wav('stone_drag.wav', reverb(b, 0.3));
}
{ // heavy footstep: sub thump + stone crunch
  const N = Math.floor(1.8 * SR), b = new Float32Array(N); let ph = 0;
  for (let i = 0; i < N; i++) { const t = i / SR; const f = 28 + 70 * Math.exp(-t * 14); ph += 2 * Math.PI * f / SR;
    b[i] = Math.sin(ph) * Math.exp(-t * 4.5) + (rnd() * 2 - 1) * 0.35 * Math.exp(-t * 22); }
  wav('heavy_step.wav', reverb(b, 0.45));
}
{ // impact boom: overhead smash, layered thump + debris rattle
  const N = Math.floor(3 * SR), b = new Float32Array(N); let ph = 0;
  for (let i = 0; i < N; i++) { const t = i / SR; const f = 24 + 90 * Math.exp(-t * 10); ph += 2 * Math.PI * f / SR;
    let s = Math.sin(ph) * Math.exp(-t * 2.2) + (rnd() * 2 - 1) * 0.5 * Math.exp(-t * 9);
    if (t > 0.15 && rnd() < 0.004) s += (rnd() - 0.5) * 0.8;
    b[i] = s; }
  wav('impact_boom.wav', reverb(b, 0.5));
}
{ // whoosh: heavy blade through air
  const N = Math.floor(1.2 * SR), b = new Float32Array(N); let lp = 0;
  for (let i = 0; i < N; i++) { const t = i / SR, env = Math.sin(Math.PI * Math.min(1, t / 1.0)) ** 2;
    const a = 0.02 + 0.2 * env; lp += a * ((rnd() * 2 - 1) - lp); b[i] = lp * env; }
  wav('whoosh.wav', reverb(b, 0.3));
}
{ // eyes open: rising resonant swell with a bright ping
  const N = Math.floor(3 * SR), b = new Float32Array(N); let ph = 0;
  for (let i = 0; i < N; i++) { const t = i / SR, f = 110 + 220 * Math.min(1, t / 1.6); ph += 2 * Math.PI * f / SR;
    b[i] = (Math.sin(ph) + 0.5 * Math.sin(ph * 1.5)) * Math.min(1, t / 1.4) * Math.exp(-Math.max(0, t - 1.6) * 2.5)
      + (t > 1.6 ? 0.6 * Math.sin(2 * Math.PI * 1760 * t) * Math.exp(-(t - 1.6) * 5) : 0); }
  wav('eyes_open.wav', reverb(b, 0.55));
}
console.log('SOUNDS_OK');
