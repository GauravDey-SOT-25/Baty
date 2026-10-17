const menuButton = document.querySelector('.menu-toggle');
const menuOverlay = document.querySelector('.menu-overlay');

const promptTrack = document.querySelector('.prompt-track');
[...promptTrack.children].forEach((card) => {
  const clone = card.cloneNode(true);
  clone.setAttribute('aria-hidden', 'true');
  promptTrack.append(clone);
});

menuButton.addEventListener('click', () => {
  const isOpen = menuButton.getAttribute('aria-expanded') === 'true';
  menuButton.setAttribute('aria-expanded', String(!isOpen));
  menuButton.setAttribute('aria-label', isOpen ? 'Open menu' : 'Close menu');
  menuOverlay.classList.toggle('is-open', !isOpen);
  menuOverlay.setAttribute('aria-hidden', String(isOpen));
  document.body.classList.toggle('menu-open', !isOpen);
});

menuOverlay.addEventListener('click', (event) => {
  if (event.target === menuOverlay) menuButton.click();
});

menuOverlay.querySelectorAll('a').forEach((link) => {
  link.addEventListener('click', () => {
    menuButton.setAttribute('aria-expanded', 'false');
    menuButton.setAttribute('aria-label', 'Open menu');
    menuOverlay.classList.remove('is-open');
    menuOverlay.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('menu-open');
  });
});

const heroTitle = document.querySelector('.hero h1');
const rotatingWord = document.querySelector('.rotating-word');
const heroWords = ['Verifies', 'Scans', 'Detects', 'Defends', 'Protects', 'Investigates', 'Secures', 'Checks'];
const promptRail = document.querySelector('.prompt-rail');
const heroGlimmer = document.querySelector('#hero-glimmer');
const heroPosterUrl = new URL('./assets/hero.webp', document.currentScript?.src || document.baseURI).href;
const isStackedDesktop = window.matchMedia('(min-width: 961px)').matches;
const heroVideo = heroGlimmer.querySelector('.hero-glimmer-video');
const morphCanvas = heroGlimmer.querySelector('.hero-morph-canvas');
let wordIndex = 0;
rotatingWord.textContent = heroWords[wordIndex];

const createHeroMorph = () => {
  const gl = morphCanvas.getContext('webgl', { alpha: true, antialias: false, premultipliedAlpha: false });
  if (!gl) {
    heroVideo.classList.add('hero-video--direct');
    return null;
  }

  const vertexSource = `
    attribute vec2 aPosition;
    varying vec2 vUv;
    void main() {
      vUv = aPosition * 0.5 + 0.5;
      gl_Position = vec4(aPosition, 0.0, 1.0);
    }
  `;
  const fragmentSource = `
    precision mediump float;
    uniform sampler2D uTexture1;
    uniform sampler2D uTexture2;
    uniform float uProgress;
    uniform float uMode;
    uniform float uGrid;
    uniform float uWaveWidth;
    uniform float uDistortion;
    uniform float uOpacity;
    uniform vec2 uResolution;
    varying vec2 vUv;
    void main() {
      vec2 uv = (vUv - vec2(0.5)) * uResolution + vec2(0.5);
      float wavePos = 1.0 - uv.y;
      float wave = 1.0 - smoothstep(uProgress - uWaveWidth, uProgress, wavePos);
      float distFromWave = abs(wavePos - uProgress);
      float pixelateAmount = 1.0 - smoothstep(0.0, uWaveWidth, distFromWave);
      if (uProgress <= 0.001 || uProgress >= 0.999) pixelateAmount = 0.0;
      vec2 pixelUV = floor(uv * uGrid) / uGrid;
      vec2 distortedUV = mix(uv, pixelUV, pixelateAmount);
      distortedUV += pixelateAmount * uDistortion * vec2(
        sin(uv.y * 25.0 + uProgress * 6.28),
        cos(uv.x * 25.0 + uProgress * 6.28)
      );
      vec4 cleanOld = texture2D(uTexture1, uv);
      vec4 cleanNew = texture2D(uTexture2, uv);
      vec4 pixOld = texture2D(uTexture1, clamp(distortedUV, 0.0, 1.0));
      vec4 pixNew = texture2D(uTexture2, clamp(distortedUV, 0.0, 1.0));
      vec4 oldColor = mix(cleanOld, pixOld, pixelateAmount);
      vec4 newColor = mix(cleanNew, pixNew, pixelateAmount);
      vec4 color = uMode > 0.5 ? mix(oldColor, newColor, wave) : newColor;
      color.a *= uOpacity;
      gl_FragColor = color;
    }
  `;
  const compile = (type, source) => {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (gl.getShaderParameter(shader, gl.COMPILE_STATUS)) return shader;
    gl.deleteShader(shader);
    return null;
  };
  const vertexShader = compile(gl.VERTEX_SHADER, vertexSource);
  const fragmentShader = compile(gl.FRAGMENT_SHADER, fragmentSource);
  if (!vertexShader || !fragmentShader) {
    heroVideo.classList.add('hero-video--direct');
    return null;
  }

  const program = gl.createProgram();
  gl.attachShader(program, vertexShader);
  gl.attachShader(program, fragmentShader);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    heroVideo.classList.add('hero-video--direct');
    return null;
  }
  gl.useProgram(program);

  const vertices = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, vertices);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  const position = gl.getAttribLocation(program, 'aPosition');
  gl.enableVertexAttribArray(position);
  gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);

  const posterTexture = gl.createTexture();
  const videoTexture = gl.createTexture();
  for (const texture of [posterTexture, videoTexture]) {
    gl.bindTexture(gl.TEXTURE_2D, texture);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  }
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  const poster = new Image();
  poster.onload = () => {
    gl.bindTexture(gl.TEXTURE_2D, posterTexture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, poster);
    gl.bindTexture(gl.TEXTURE_2D, videoTexture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, poster);
  };
  poster.src = heroPosterUrl;
  gl.enable(gl.BLEND);
  gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

  const uniforms = Object.fromEntries(['uTexture1', 'uTexture2', 'uProgress', 'uMode', 'uGrid', 'uWaveWidth', 'uDistortion', 'uOpacity', 'uResolution'].map((name) => [name, gl.getUniformLocation(program, name)]));
  gl.uniform1i(uniforms.uTexture1, 0);
  gl.uniform1i(uniforms.uTexture2, 1);
  gl.uniform1f(uniforms.uGrid, 40);
  gl.uniform1f(uniforms.uWaveWidth, 0.48);
  gl.uniform1f(uniforms.uDistortion, 0.024);
  gl.uniform1f(uniforms.uOpacity, 0.8);

  let mode = 0;
  let transitionStartedAt = null;
  let transitionDuration = 0;
  let transitionComplete = null;
  const easing = (t) => {
    const bezier = (p, a, b) => 3 * (1 - p) * (1 - p) * p * a + 3 * (1 - p) * p * p * b + p * p * p;
    let low = 0;
    let high = 1;
    let point = t;
    for (let i = 0; i < 10; i += 1) {
      const x = bezier(point, 0.76, 0.24);
      if (Math.abs(x - t) < 0.00001) break;
      if (x < t) low = point;
      else high = point;
      point = (low + high) / 2;
    }
    return bezier(point, 0, 1);
  };

  const resize = () => {
    const bounds = morphCanvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    morphCanvas.width = Math.max(1, Math.round(bounds.width * ratio));
    morphCanvas.height = Math.max(1, Math.round(bounds.height * ratio));
    gl.viewport(0, 0, morphCanvas.width, morphCanvas.height);
    const videoAspect = (heroVideo.videoWidth || 1600) / (heroVideo.videoHeight || 900);
    const hostAspect = morphCanvas.width / morphCanvas.height;
    const scaleX = hostAspect > videoAspect ? 1 : hostAspect / videoAspect;
    const scaleY = hostAspect > videoAspect ? videoAspect / hostAspect : 1;
    gl.uniform2f(uniforms.uResolution, scaleX, scaleY);
  };
  new ResizeObserver(resize).observe(heroGlimmer);
  resize();

  let videoTextureReady = false;
  const render = (now) => {
    if (heroVideo.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
      try {
        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, videoTexture);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, heroVideo);
        if (mode === 2) {
          gl.activeTexture(gl.TEXTURE0);
          gl.bindTexture(gl.TEXTURE_2D, posterTexture);
          gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, heroVideo);
        }
        if (!videoTextureReady) {
          videoTextureReady = true;
          heroVideo.classList.remove('hero-video--direct');
          mode = 1;
          transitionStartedAt = now;
          transitionDuration = 2000;
        }
      } catch {
        morphCanvas.style.display = 'none';
        heroVideo.classList.add('hero-video--direct');
        return;
      }
    }

    let progress = -1;
    if (transitionStartedAt !== null) {
      const t = Math.min(1, (now - transitionStartedAt) / transitionDuration);
      progress = easing(t);
      if (t >= 1) {
        transitionStartedAt = null;
        mode = 0;
        transitionComplete?.();
        transitionComplete = null;
      }
    }
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.useProgram(program);
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, posterTexture);
    gl.activeTexture(gl.TEXTURE1);
    gl.bindTexture(gl.TEXTURE_2D, videoTexture);
    gl.uniform1f(uniforms.uProgress, progress);
    gl.uniform1f(uniforms.uMode, mode);
    gl.drawArrays(gl.TRIANGLES, 0, 6);
    window.requestAnimationFrame(render);
  };
  window.requestAnimationFrame(render);

  return () => {
    if (!videoTextureReady || transitionStartedAt !== null) return;
    gl.activeTexture(gl.TEXTURE0);
    gl.bindTexture(gl.TEXTURE_2D, posterTexture);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, heroVideo);
    mode = 2;
    transitionDuration = 1200;
    transitionStartedAt = performance.now();
  };
};
const morphHeroBackground = createHeroMorph();

const advanceHero = () => {
  morphHeroBackground?.();
  heroTitle.classList.add('word-changing');
  window.setTimeout(() => {
    wordIndex = (wordIndex + 1) % heroWords.length;
    rotatingWord.textContent = heroWords[wordIndex];
    heroTitle.classList.remove('word-changing');
  }, 280);

  if (!isStackedDesktop) return;

  promptTrack.style.transform = 'translate3d(0, -184px, 0)';
  window.setTimeout(() => {
    promptTrack.style.transition = 'none';
    promptTrack.append(promptTrack.firstElementChild);
    promptTrack.style.transform = 'translate3d(0, 0, 0)';
    promptTrack.getBoundingClientRect();
    window.requestAnimationFrame(() => {
      promptTrack.style.transition = 'transform 1000ms cubic-bezier(.12, 1, .72, 1)';
    });
  }, 1000);
};
if (isStackedDesktop) {
  promptTrack.style.animation = 'none';
  promptTrack.style.transition = 'transform 1000ms cubic-bezier(.12, 1, .72, 1)';
  promptTrack.style.transform = 'translate3d(0, 0, 0)';
} else {
  let visiblePrompt = 0;
  let lastScrollMorph = 0;
  promptRail.addEventListener('scroll', () => {
    const step = promptTrack.firstElementChild.getBoundingClientRect().width + parseFloat(getComputedStyle(promptTrack).columnGap || 16);
    const nextPrompt = Math.round(promptRail.scrollLeft / step);
    if (nextPrompt === visiblePrompt) return;
    visiblePrompt = nextPrompt;
    if (performance.now() - lastScrollMorph > 900) {
      morphHeroBackground?.();
      lastScrollMorph = performance.now();
    }
  }, { passive: true });
}
window.setInterval(advanceHero, 3000);

const unifiesScene = document.querySelector('.unifies');
let sceneFrame = 0;
const smoothRange = (start, end, value) => {
  const amount = Math.max(0, Math.min(1, (value - start) / (end - start)));
  return amount * amount * (3 - 2 * amount);
};
const updateSceneProgress = () => {
  if (sceneFrame) return;
  sceneFrame = window.requestAnimationFrame(() => {
    const rect = unifiesScene.getBoundingClientRect();
    const distance = Math.max(1, rect.height - window.innerHeight);
    const progress = Math.max(0, Math.min(1, -rect.top / distance));
    const titleOpacity = smoothRange(0.06, 0.36, progress);
    const ribbonOpacity = smoothRange(0.34, 0.53, progress);
    const travel = smoothRange(0.36, 0.96, progress);
    const ribbonHold = 1 - 0.18 * smoothRange(0.94, 1, progress);
    unifiesScene.style.setProperty('--scene-progress', progress.toFixed(3));
    unifiesScene.style.setProperty('--mist-opacity', (0.98 * (1 - smoothRange(0.08, 0.43, progress))).toFixed(3));
    unifiesScene.style.setProperty('--mist-x', `${(-1 + progress * 4).toFixed(2)}vw`);
    unifiesScene.style.setProperty('--mist-y', `${(2 - progress * 5).toFixed(2)}vh`);
    unifiesScene.style.setProperty('--glint-opacity', (0.08 + smoothRange(0.2, 0.52, progress) * 0.2).toFixed(3));
    unifiesScene.style.setProperty('--title-opacity', titleOpacity.toFixed(3));
    unifiesScene.style.setProperty('--title-scale', (0.94 + titleOpacity * 0.06).toFixed(3));
    unifiesScene.style.setProperty('--title-blur', `${((1 - titleOpacity) * 12).toFixed(2)}px`);
    unifiesScene.style.setProperty('--scene-shade', (0.18 + smoothRange(0.17, 0.52, progress) * 0.32).toFixed(3));
    unifiesScene.style.setProperty('--ribbon-opacity-back', (ribbonOpacity * 0.66 * ribbonHold).toFixed(3));
    unifiesScene.style.setProperty('--ribbon-opacity-low', (ribbonOpacity * 0.82 * ribbonHold).toFixed(3));
    unifiesScene.style.setProperty('--ribbon-back-x', `${(-8 + travel * 20).toFixed(2)}vw`);
    unifiesScene.style.setProperty('--ribbon-back-y', `${(7 - travel * 13).toFixed(2)}vh`);
    unifiesScene.style.setProperty('--ribbon-back-scale', (0.76 + travel * 0.29).toFixed(3));
    unifiesScene.style.setProperty('--ribbon-low-x', `${(-12 + travel * 21).toFixed(2)}vw`);
    unifiesScene.style.setProperty('--ribbon-low-y', `${(8 - travel * 10).toFixed(2)}vh`);
    unifiesScene.style.setProperty('--ribbon-low-scale', (1.12 - travel * 0.22).toFixed(3));
    sceneFrame = 0;
  });
};
window.addEventListener('scroll', updateSceneProgress, { passive: true });
window.addEventListener('resize', updateSceneProgress, { passive: true });
updateSceneProgress();

const soundButton = document.querySelector('.sound-control button');
soundButton.addEventListener('click', () => {
  const soundOn = soundButton.getAttribute('aria-pressed') === 'true';
  soundButton.setAttribute('aria-pressed', String(!soundOn));
  soundButton.textContent = soundOn ? 'SOUND OFF' : 'SOUND ON';
  soundButton.closest('.sound-control').setAttribute('aria-pressed', String(!soundOn));
  if (heroVideo) heroVideo.muted = soundOn;
});

const status = document.querySelector('.status-dots');
const statusFrames = ['·', '···', '·····', '·······', '··········'];
let statusFrame = 0;
window.setInterval(() => {
  status.textContent = statusFrames[statusFrame % statusFrames.length];
  statusFrame += 1;
}, 470);
