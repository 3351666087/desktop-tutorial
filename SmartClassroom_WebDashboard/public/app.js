const i18n = {
  zh: {
    kicker: "IoT 边缘控制中心",
    title: "智慧教室能源、安全与资产监测系统",
    subtitle: "UNO 实时控制，ESP32 网关，MQTT 与 Web Dashboard 联动。",
    background: "背景",
    accent: "强调色",
    currentMode: "当前模式",
    websocket: "WebSocket",
    mqtt: "MQTT",
    lastSeen: "最后更新",
    queue: "命令队列",
    autoManual: "自动 / 手动",
    ping: "Ping UNO",
    buzz: "蜂鸣器短响",
    demoOn: "模拟报警",
    demoOff: "清除报警",
    restoreStatus: "恢复状态灯",
    reapply: "重新下发配置",
    liveDashboard: "实时仪表盘",
    temperatureChart: "温度趋势",
    airLightChart: "环境传感",
    fanChart: "风扇行为",
    eventChart: "安全与占用",
    autoPolicy: "自动策略",
    thresholds: "阈值与亮度",
    applySave: "应用并保存",
    fanStart: "风扇启动温度",
    fanStop: "风扇停止温度",
    ledMax: "教室灯上限",
    statusMax: "状态灯上限",
    lightDark: "光线变暗阈值",
    lightBright: "光线变亮阈值",
    presetPolicy: "预设策略",
    presets: "一键场景",
    manualModule: "手动模块",
    manualControl: "元件控制",
    applyManual: "应用手动",
    manualHint: "打开手动模式后显示元件控制。",
    lamp: "教室灯",
    fan: "风扇",
    buzzer: "蜂鸣器",
    fanPwm: "风扇 PWM",
    statusLight: "状态灯",
    statusAll: "三灯全亮",
    red: "红",
    yellow: "黄",
    green: "绿",
    off: "关闭",
    allStatus: "三灯全亮",
    returnAuto: "回到自动",
    customStrategy: "自定义策略",
    saveStrategy: "保存策略",
    strategyName: "策略名称",
    strategyDesc: "说明",
    rawTelemetry: "原始遥测",
    mqttLog: "MQTT 日志",
    expandLog: "点击展开",
    applyPreset: "应用",
    delete: "删除",
    saved: "已保存",
    applying: "下发中",
    online: "在线",
    offline: "离线"
    ,
    adaptiveTitle: "偏好学习与声控",
    collectData: "开始收集数据",
    stopCollectData: "停止收集数据",
    refreshAnalytics: "刷新分析",
    applyRecommendation: "应用推荐",
    collection: "数据采集",
    comfortRisk: "舒适风险",
    modelRecommendation: "模型推荐",
    voiceControl: "语音控制",
    holdToSpeak: "按住说话",
    sendTextCommand: "发送文字",
    voicePlaceholder: "例如：打开手动模式，风扇调到 180",
    occupancyRate: "占用率",
    fanDuty: "风扇占空",
    manualRate: "手动覆盖",
    dataNeeded: "还需样本"
  },
  en: {
    kicker: "IoT Edge Command Center",
    title: "Smart Classroom Energy, Safety & Asset System",
    subtitle: "UNO real-time control, ESP32 gateway, MQTT and Web Dashboard.",
    background: "Background",
    accent: "Accent",
    currentMode: "Current Mode",
    websocket: "WebSocket",
    mqtt: "MQTT",
    lastSeen: "Last Seen",
    queue: "Queue",
    autoManual: "Auto / Manual",
    ping: "Ping UNO",
    buzz: "Buzzer Pulse",
    demoOn: "Demo Alarm",
    demoOff: "Clear Alarm",
    restoreStatus: "Restore Status Light",
    reapply: "Reapply Config",
    liveDashboard: "Live Dashboard",
    temperatureChart: "Temperature Trend",
    airLightChart: "Environment Sensors",
    fanChart: "Fan Behavior",
    eventChart: "Safety & Occupancy",
    autoPolicy: "Auto Policy",
    thresholds: "Thresholds & Brightness",
    applySave: "Apply & Save",
    fanStart: "Fan Start C",
    fanStop: "Fan Stop C",
    ledMax: "Lamp Limit",
    statusMax: "Status Limit",
    lightDark: "Dark Threshold",
    lightBright: "Bright Threshold",
    presetPolicy: "Preset Policy",
    presets: "One-Tap Scenes",
    manualModule: "Manual Module",
    manualControl: "Device Control",
    applyManual: "Apply Manual",
    manualHint: "Turn on manual mode to reveal device controls.",
    lamp: "Lamp",
    fan: "Fan",
    buzzer: "Buzzer",
    fanPwm: "Fan PWM",
    statusLight: "Status Light",
    statusAll: "All Lights",
    red: "Red",
    yellow: "Yellow",
    green: "Green",
    off: "Off",
    allStatus: "All Lights",
    returnAuto: "Return Auto",
    customStrategy: "Custom Strategy",
    saveStrategy: "Save Strategy",
    strategyName: "Strategy Name",
    strategyDesc: "Description",
    rawTelemetry: "Raw Telemetry",
    mqttLog: "MQTT Log",
    expandLog: "Click to expand",
    applyPreset: "Apply",
    delete: "Delete",
    saved: "Saved",
    applying: "Applying",
    online: "Online",
    offline: "Offline"
    ,
    adaptiveTitle: "Preference Learning & Voice",
    collectData: "Start Data",
    stopCollectData: "Stop Data",
    refreshAnalytics: "Refresh Analytics",
    applyRecommendation: "Apply Recommendation",
    collection: "Data Collection",
    comfortRisk: "Comfort Risk",
    modelRecommendation: "Model Recommendation",
    voiceControl: "Voice Control",
    holdToSpeak: "Hold to Speak",
    sendTextCommand: "Send Text",
    voicePlaceholder: "Example: enable manual mode and set fan PWM to 180",
    occupancyRate: "Occupancy",
    fanDuty: "Fan Duty",
    manualRate: "Manual Override",
    dataNeeded: "Samples Needed"
  }
};

const cardDefs = [
  ["mode", "Mode", "mode", "state machine"],
  ["temperature", "Temperature", "temperatureC", "LM35"],
  ["tempSource", "Temp Source", "temperatureSource", "ADC route"],
  ["occupancy", "Occupancy", "occupied", "PIR"],
  ["light", "Light", "light", "TEMT6000"],
  ["gas", "Gas", "gas", "analog"],
  ["flame", "Flame", "flameDetected", "DO/AO"],
  ["safety", "Safety", "safetyAlarm", "priority layer"],
  ["fan", "Fan", "fan", "relay"],
  ["pwm", "PWM", "pwm", "fan drive"],
  ["rpm", "RPM", "rpm", "tach"],
  ["lamp", "Lamp", "lamp", "D5"],
  ["status", "Status Light", "statusLight", "R/Y/G"],
  ["limits", "Limits", "statusMax", "brightness"],
  ["ack", "ACK", "commandAck", "command feedback"]
];

const cardRoot = document.querySelector("#cards");
const cardEls = new Map();
let currentState = {};
let settings = {};
let presets = [];
let language = "zh";
let presetRenderKey = "";
let telemetryRenderKey = "";
const history = [];
const HISTORY_LIMIT = 150;

class DynamicBackdrop {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas?.getContext("2d");
    this.width = 1;
    this.height = 1;
    this.dpr = 1;
    this.particles = [];
    this.bg = "aurora";
    this.accent = "cyan";
    this.mode = "";
    this.alarm = false;
    this.online = false;
    this.temp = 24;
    this.pwm = 0;
    this.gas = 0;
    this.last = 0;
    this.paused = false;
    this.reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!this.canvas || !this.ctx) return;

    window.addEventListener("resize", () => this.resize(), { passive: true });
    document.addEventListener("visibilitychange", () => {
      this.paused = document.visibilityState !== "visible";
      if (!this.paused) this.last = performance.now();
    });
    this.resize();
    requestAnimationFrame((time) => this.frame(time));
  }

  setState(nextSettings = {}, nextState = {}) {
    this.bg = nextSettings.background || "aurora";
    this.accent = nextSettings.accent || "cyan";
    this.mode = String(nextState.mode || "");
    this.alarm = Number(nextState.safetyAlarm || 0) === 1 || this.mode === "SAFETY_ALARM";
    this.online = Boolean(nextState.online);
    this.temp = Number(nextState.temperatureC ?? this.temp ?? 24);
    this.pwm = Number(nextState.pwm ?? this.pwm ?? 0);
    this.gas = Number(nextState.gas ?? this.gas ?? 0);
  }

  resize() {
    const rect = this.canvas.getBoundingClientRect();
    const nextDpr = Math.min(window.devicePixelRatio || 1, 2);
    const nextWidth = Math.max(1, Math.floor(rect.width));
    const nextHeight = Math.max(1, Math.floor(rect.height));
    if (nextWidth === this.width && nextHeight === this.height && nextDpr === this.dpr) return;
    this.width = nextWidth;
    this.height = nextHeight;
    this.dpr = nextDpr;
    this.canvas.width = Math.floor(this.width * this.dpr);
    this.canvas.height = Math.floor(this.height * this.dpr);
    this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    this.seedParticles();
  }

  seedParticles() {
    const density = this.width < 720 ? 15500 : 10500;
    const count = Math.max(72, Math.min(190, Math.floor((this.width * this.height) / density)));
    this.particles = Array.from({ length: count }, () => this.makeParticle(true));
  }

  makeParticle(randomize = false) {
    return {
      x: randomize ? Math.random() * this.width : this.width * 0.5,
      y: randomize ? Math.random() * this.height : this.height * 0.5,
      vx: (Math.random() - 0.5) * 0.26,
      vy: (Math.random() - 0.5) * 0.26,
      size: 0.7 + Math.random() * 2.2,
      seed: Math.random() * 1000,
      depth: 0.35 + Math.random() * 0.9,
      hue: Math.floor(Math.random() * 3)
    };
  }

  palette() {
    if (this.alarm) return [[255, 93, 104], [255, 170, 92], [255, 216, 148]];
    if (this.mode === "COOLING") return [[85, 230, 255], [98, 168, 255], [255, 209, 102]];
    if (this.bg === "thermal") return [[255, 93, 104], [255, 209, 102], [85, 230, 255]];
    if (this.bg === "cosmos") return [[179, 140, 255], [98, 168, 255], [255, 122, 165]];
    if (this.bg === "matrix") return [[99, 242, 160], [196, 255, 122], [85, 230, 255]];
    const accents = {
      cyan: [[85, 230, 255], [125, 246, 183], [98, 168, 255]],
      blue: [[98, 168, 255], [141, 215, 255], [179, 140, 255]],
      violet: [[179, 140, 255], [255, 158, 232], [85, 230, 255]],
      green: [[99, 242, 160], [196, 255, 122], [85, 230, 255]],
      rose: [[255, 122, 165], [255, 211, 122], [179, 140, 255]]
    };
    return accents[this.accent] || accents.cyan;
  }

  rgba(color, alpha) {
    return `rgba(${color[0]}, ${color[1]}, ${color[2]}, ${alpha})`;
  }

  frame(time) {
    if (!this.paused) {
      const dt = Math.min(42, time - (this.last || time));
      this.last = time;
      this.draw(time * 0.001, dt / 16.67);
    }
    requestAnimationFrame((next) => this.frame(next));
  }

  clear() {
    this.ctx.clearRect(0, 0, this.width, this.height);
  }

  draw(time, step) {
    this.clear();
    const palette = this.palette();
    if (this.reduced) {
      this.drawReduced(palette);
      return;
    }
    this.drawAmbient(palette, time);
    if (this.bg === "neural") this.drawNeural(palette, time, step);
    else if (this.bg === "hologrid") this.drawHoloGrid(palette, time);
    else if (this.bg === "cosmos") this.drawCosmos(palette, time, step);
    else if (this.bg === "thermal") this.drawThermal(palette, time);
    else this.drawFlow(palette, time, step);
  }

  drawAmbient(palette, time) {
    const ctx = this.ctx;
    const heat = Math.min(1, Math.max(0, (this.temp - 24) / 10));
    const fan = Math.min(1, Math.max(0, this.pwm / 255));
    const alarmBoost = this.alarm ? 0.28 + Math.sin(time * 5) * 0.06 : 0;
    const glow = ctx.createRadialGradient(this.width * 0.24, this.height * 0.18, 0, this.width * 0.24, this.height * 0.18, this.width * 0.62);
    glow.addColorStop(0, this.rgba(palette[0], 0.12 + heat * 0.08 + alarmBoost));
    glow.addColorStop(1, this.rgba(palette[0], 0));
    ctx.fillStyle = glow;
    ctx.fillRect(0, 0, this.width, this.height);

    const lower = ctx.createRadialGradient(this.width * 0.78, this.height * 0.82, 0, this.width * 0.78, this.height * 0.82, this.width * 0.56);
    lower.addColorStop(0, this.rgba(palette[1], 0.08 + fan * 0.08));
    lower.addColorStop(1, this.rgba(palette[1], 0));
    ctx.fillStyle = lower;
    ctx.fillRect(0, 0, this.width, this.height);
  }

  drawFlow(palette, time, step) {
    const ctx = this.ctx;
    ctx.lineCap = "round";
    ctx.globalCompositeOperation = "lighter";
    for (let band = 0; band < 6; band += 1) {
      const color = palette[band % palette.length];
      ctx.beginPath();
      const baseY = this.height * (0.18 + band * 0.11);
      for (let x = -40; x <= this.width + 40; x += 18) {
        const y = baseY
          + Math.sin(x * 0.008 + time * (0.75 + band * 0.12) + band) * (28 + band * 5)
          + Math.sin(x * 0.021 - time * 0.55) * 10;
        if (x === -40) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = this.rgba(color, 0.055 + band * 0.012);
      ctx.lineWidth = 18 + band * 2;
      ctx.stroke();
    }
    this.moveParticles(time, step, 0.45);
    for (const p of this.particles) {
      const color = palette[p.hue % palette.length];
      ctx.fillStyle = this.rgba(color, 0.2 * p.depth);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.globalCompositeOperation = "source-over";
  }

  drawNeural(palette, time, step) {
    const ctx = this.ctx;
    this.moveParticles(time, step, 0.72);
    ctx.globalCompositeOperation = "lighter";
    const maxDist = this.width < 760 ? 92 : 122;
    for (let i = 0; i < this.particles.length; i += 1) {
      const a = this.particles[i];
      for (let j = i + 1; j < this.particles.length; j += 1) {
        const b = this.particles[j];
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.hypot(dx, dy);
        if (dist > maxDist) continue;
        const alpha = (1 - dist / maxDist) * (this.alarm ? 0.26 : 0.16);
        ctx.strokeStyle = this.rgba(palette[(a.hue + b.hue) % palette.length], alpha);
        ctx.lineWidth = 0.8;
        ctx.beginPath();
        ctx.moveTo(a.x, a.y);
        ctx.lineTo(b.x, b.y);
        ctx.stroke();
      }
    }
    for (const p of this.particles) {
      ctx.fillStyle = this.rgba(palette[p.hue % palette.length], 0.32 + p.depth * 0.2);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * 1.05, 0, Math.PI * 2);
      ctx.fill();
    }
    this.drawPulseRing(palette[0], time, 0.5, 0.48);
    ctx.globalCompositeOperation = "source-over";
  }

  drawHoloGrid(palette, time) {
    const ctx = this.ctx;
    const horizon = this.height * 0.48;
    const cx = this.width * 0.5;
    ctx.globalCompositeOperation = "lighter";
    ctx.lineCap = "round";
    for (let i = 0; i < 28; i += 1) {
      const depth = (i + ((time * 0.42) % 1)) / 28;
      const y = horizon + Math.pow(depth, 2.1) * this.height * 0.72;
      const alpha = Math.max(0, 0.24 - depth * 0.18);
      ctx.strokeStyle = this.rgba(palette[i % palette.length], alpha);
      ctx.lineWidth = 1 + depth * 2.4;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.width, y);
      ctx.stroke();
    }
    for (let i = -14; i <= 14; i += 1) {
      const x = cx + i * this.width * 0.055;
      ctx.strokeStyle = this.rgba(palette[Math.abs(i) % palette.length], 0.11);
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(cx, horizon);
      ctx.lineTo(x, this.height);
      ctx.stroke();
    }
    for (let i = 0; i < 5; i += 1) {
      const x = ((time * (42 + i * 11) + i * 180) % (this.width + 260)) - 130;
      const y = horizon + this.height * (0.16 + i * 0.12);
      const width = 90 + i * 18;
      const gradient = ctx.createLinearGradient(x - width, y, x + width, y);
      gradient.addColorStop(0, this.rgba(palette[i % palette.length], 0));
      gradient.addColorStop(0.5, this.rgba(palette[i % palette.length], 0.36));
      gradient.addColorStop(1, this.rgba(palette[i % palette.length], 0));
      ctx.strokeStyle = gradient;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(x - width, y);
      ctx.lineTo(x + width, y);
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
  }

  drawCosmos(palette, time, step) {
    const ctx = this.ctx;
    const cx = this.width * 0.5;
    const cy = this.height * 0.46;
    ctx.globalCompositeOperation = "lighter";
    for (let ring = 0; ring < 4; ring += 1) {
      ctx.strokeStyle = this.rgba(palette[ring % palette.length], 0.08 + ring * 0.015);
      ctx.lineWidth = 1.2;
      ctx.beginPath();
      ctx.ellipse(cx, cy, this.width * (0.18 + ring * 0.1), this.height * (0.08 + ring * 0.045), Math.sin(time * 0.12 + ring) * 0.28, 0, Math.PI * 2);
      ctx.stroke();
    }
    for (const p of this.particles) {
      const orbit = 0.25 + p.depth * 0.5;
      const angle = time * (0.035 + p.depth * 0.045) + p.seed;
      p.x += Math.cos(angle) * orbit * step;
      p.y += Math.sin(angle * 1.23) * orbit * step;
      this.wrapParticle(p);
      const twinkle = 0.15 + Math.abs(Math.sin(time * 2.5 + p.seed)) * 0.45;
      ctx.fillStyle = this.rgba(palette[p.hue % palette.length], twinkle);
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.size * 0.82, 0, Math.PI * 2);
      ctx.fill();
    }
    this.drawPulseRing(palette[1], time, 0.5, 0.46);
    ctx.globalCompositeOperation = "source-over";
  }

  drawThermal(palette, time) {
    const ctx = this.ctx;
    const heat = Math.min(1, Math.max(0, (this.temp - 22) / 14));
    const fan = Math.min(1, Math.max(0, this.pwm / 255));
    const gas = Math.min(1, Math.max(0, this.gas / 650));
    const blobs = [
      [0.22, 0.24, 0.34 + heat * 0.18, palette[0], 0.14 + heat * 0.18],
      [0.74, 0.22, 0.28 + gas * 0.18, palette[1], 0.11 + gas * 0.22],
      [0.55 + Math.sin(time * 0.35) * 0.08, 0.76, 0.35 + fan * 0.12, palette[2], 0.1 + fan * 0.18]
    ];
    ctx.globalCompositeOperation = "lighter";
    for (const [x, y, r, color, alpha] of blobs) {
      const grad = ctx.createRadialGradient(this.width * x, this.height * y, 0, this.width * x, this.height * y, this.width * r);
      grad.addColorStop(0, this.rgba(color, alpha));
      grad.addColorStop(0.48, this.rgba(color, alpha * 0.36));
      grad.addColorStop(1, this.rgba(color, 0));
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, this.width, this.height);
    }
    for (let i = 0; i < 7; i += 1) {
      const y = this.height * (0.18 + i * 0.105) + Math.sin(time * 0.9 + i) * 16;
      ctx.strokeStyle = this.rgba(palette[i % 3], 0.05 + heat * 0.04);
      ctx.lineWidth = 22;
      ctx.beginPath();
      for (let x = -40; x <= this.width + 40; x += 22) {
        const yy = y + Math.sin(x * 0.012 + time * 0.7 + i) * (18 + heat * 18);
        if (x === -40) ctx.moveTo(x, yy);
        else ctx.lineTo(x, yy);
      }
      ctx.stroke();
    }
    ctx.globalCompositeOperation = "source-over";
  }

  drawReduced(palette) {
    const ctx = this.ctx;
    const grad = ctx.createRadialGradient(this.width * 0.5, this.height * 0.35, 0, this.width * 0.5, this.height * 0.35, this.width * 0.72);
    grad.addColorStop(0, this.rgba(palette[0], 0.18));
    grad.addColorStop(1, this.rgba(palette[1], 0));
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, this.width, this.height);
  }

  moveParticles(time, step, force) {
    const speed = (this.alarm ? 1.85 : this.online ? 1 : 0.55) * force;
    for (const p of this.particles) {
      const fieldA = Math.sin((p.y + p.seed) * 0.008 + time * 0.9);
      const fieldB = Math.cos((p.x - p.seed) * 0.006 - time * 0.72);
      p.vx += fieldA * 0.012 * speed;
      p.vy += fieldB * 0.012 * speed;
      const drag = 0.982;
      p.vx *= drag;
      p.vy *= drag;
      p.x += p.vx * step * (1.5 + p.depth);
      p.y += p.vy * step * (1.5 + p.depth);
      this.wrapParticle(p);
    }
  }

  wrapParticle(p) {
    const pad = 24;
    if (p.x < -pad) p.x = this.width + pad;
    if (p.x > this.width + pad) p.x = -pad;
    if (p.y < -pad) p.y = this.height + pad;
    if (p.y > this.height + pad) p.y = -pad;
  }

  drawPulseRing(color, time, xRatio, yRatio) {
    const ctx = this.ctx;
    const wave = (time * 0.18) % 1;
    const radius = (0.12 + wave * 0.38) * Math.min(this.width, this.height);
    ctx.strokeStyle = this.rgba(color, (1 - wave) * 0.16);
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.arc(this.width * xRatio, this.height * yRatio, radius, 0, Math.PI * 2);
    ctx.stroke();
  }
}

const backdrop = new DynamicBackdrop(document.querySelector("#backdropCanvas"));

for (const [id, title] of cardDefs) {
  const el = document.createElement("article");
  el.className = "card glass";
  el.dataset.card = id;
  el.innerHTML = `<span class="card-title">${title}</span><strong>--</strong><small></small>`;
  cardRoot.appendChild(el);
  cardEls.set(id, el);
}

function tr(key) {
  return i18n[language]?.[key] || i18n.en[key] || key;
}

function applyLanguage(lang) {
  language = lang || "zh";
  document.documentElement.lang = language;
  for (const node of document.querySelectorAll("[data-i18n]")) {
    const key = node.dataset.i18n;
    const value = tr(key);
    if (node.tagName === "OPTION") node.textContent = value;
    else node.textContent = value;
  }
  for (const node of document.querySelectorAll("[data-i18n-placeholder]")) {
    node.placeholder = tr(node.dataset.i18nPlaceholder);
  }
  document.querySelector("#langZh").classList.toggle("active", language === "zh");
  document.querySelector("#langEn").classList.toggle("active", language === "en");
  renderPresets();
  renderCards(currentState);
}

function fmtBool(value) {
  return Number(value || 0) === 1 ? "ON" : "OFF";
}

function fixed1(value) {
  return value == null ? "--" : Number(value).toFixed(1);
}

function statusName(value) {
  const map = { R: "RED", Y: "YELLOW", G: "GREEN", M: "MANUAL" };
  return map[value] || value || "--";
}

function cardValue(id, state) {
  if (id === "temperature") return state.temperatureC == null ? "--" : `${Number(state.temperatureC).toFixed(1)} C`;
  if (id === "tempSource") return state.temperatureSource || "--";
  if (id === "occupancy") return fmtBool(state.occupied);
  if (id === "flame") return fmtBool(state.flameDetected);
  if (id === "safety") return fmtBool(state.safetyAlarm);
  if (id === "fan") return fmtBool(state.fan);
  if (id === "lamp") return fmtBool(state.lamp);
  if (id === "status") return statusName(state.statusLight);
  if (id === "limits") return `${state.ledMax ?? "--"} / ${state.statusMax ?? "--"}`;
  if (id === "ack") return state.commandAck || "--";
  const def = cardDefs.find((item) => item[0] === id);
  return state[def?.[2]] ?? "--";
}

function cardDetail(id, state, fallback) {
  if (id === "temperature") {
    const raw = state.esp32AdcRawMv ?? state.esp32AdcMv ?? "--";
    const corrected = state.esp32AdcCorrectedMv ?? state.esp32AdcMv ?? "--";
    const ambient = state.esp32AdcAmbientMv ?? state.esp32AdcMv ?? "--";
    const dummy = state.esp32AdcDummyMv ?? "--";
    return `raw ${raw} / corr ${corrected} / amb ${ambient} mV / dummy ${dummy}${state.esp32AdcSuspect ? " / guarded" : ""}`;
  }
  if (id === "light") return Number(state.dark || 0) === 1 ? "dark gate enabled" : "bright lockout";
  if (id === "gas") return `danger ${fmtBool(state.gasDanger)}`;
  if (id === "flame") return `DO ${state.flameDigital ?? "--"} / AO ${state.flameAnalog ?? "--"}`;
  if (id === "pwm") return `queue ${state.commandQueue || 0}`;
  if (id === "rpm") return state.fanHealth || "tach";
  if (id === "limits") return `fan ${fixed1(state.fanOffC)} / ${fixed1(state.fanOnC)} C`;
  return fallback;
}

function cardState(id, state) {
  if (Number(state.safetyAlarm || 0) === 1 && ["mode", "safety", "gas", "flame"].includes(id)) return "danger";
  if (id === "mode" && ["COOLING", "AIR_QUALITY_WARNING"].includes(state.mode)) return "warn";
  if (id === "mode" && state.mode === "MANUAL") return "active";
  if (id === "tempSource" && state.temperatureSource === "ESP32") return "active";
  if (id === "status" && Number(state.statusMax || 0) <= 0) return "danger";
  if (id === "limits" && Number(state.statusMax || 0) <= 0) return "danger";
  if (["fan", "lamp", "pwm", "rpm", "occupancy"].includes(id) && Number(cardValue(id, state).replace?.(/\D/g, "") || state[id] || 0) > 0) return "active";
  return "normal";
}

function renderCards(state = {}) {
  for (const [id, title, _key, fallback] of cardDefs) {
    const el = cardEls.get(id);
    if (!el) continue;
    el.querySelector(".card-title").textContent = title;
    el.querySelector("strong").textContent = cardValue(id, state);
    el.querySelector("small").textContent = cardDetail(id, state, fallback);
    el.dataset.state = cardState(id, state);
  }
}

function pushHistory(state) {
  if (!state || !state.lastSeen) return;
  const last = history[history.length - 1];
  if (last && last.lastSeen === state.lastSeen) return;
  history.push({
    lastSeen: state.lastSeen,
    temperatureC: Number(state.temperatureC ?? 0),
    light: Number(state.light ?? 0),
    gas: Number(state.gas ?? 0),
    pwm: Number(state.pwm ?? 0),
    rpm: Number(state.rpm ?? 0),
    occupied: Number(state.occupied ?? 0),
    safetyAlarm: Number(state.safetyAlarm ?? 0)
  });
  if (history.length > HISTORY_LIMIT) history.shift();
}

function pointsFor(values, min, max, height = 130, width = 340, top = 10, left = 10) {
  const span = Math.max(0.0001, max - min);
  const step = values.length <= 1 ? width : width / (values.length - 1);
  return values.map((value, index) => {
    const x = left + index * step;
    const y = top + height - ((value - min) / span) * height;
    return `${x.toFixed(1)},${Math.max(top, Math.min(top + height, y)).toFixed(1)}`;
  }).join(" ");
}

function lineSvg(series, options = {}) {
  const values = series.length ? series : [0];
  const min = options.min ?? Math.min(...values);
  const max = options.max ?? Math.max(...values, min + 1);
  const points = pointsFor(values, min, max);
  const area = `10,140 ${points} 350,140`;
  return `
    <defs>
      <linearGradient id="${options.id}-fill" x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stop-color="var(--accent)" stop-opacity=".34"/>
        <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
      </linearGradient>
    </defs>
    <path class="chart-gridline" d="M10 42 H350 M10 84 H350 M10 126 H350"/>
    <polyline class="chart-area" points="${area}" fill="url(#${options.id}-fill)"/>
    <polyline class="chart-line" points="${points}" fill="none"/>
  `;
}

function multiLineSvg(seriesList, options = {}) {
  const all = seriesList.flatMap(item => item.values);
  const min = options.min ?? Math.min(...all, 0);
  const max = options.max ?? Math.max(...all, 1);
  const lines = seriesList.map((item, index) => {
    const points = pointsFor(item.values.length ? item.values : [0], min, max);
    return `<polyline class="chart-line alt-${index}" points="${points}" fill="none"/>`;
  }).join("");
  return `<path class="chart-gridline" d="M10 42 H350 M10 84 H350 M10 126 H350"/>${lines}`;
}

function eventSvg() {
  const values = history.length ? history : [{ occupied: 0, safetyAlarm: 0 }];
  const step = values.length <= 1 ? 340 : 340 / (values.length - 1);
  const bars = values.map((item, index) => {
    const x = 10 + index * step;
    const occ = item.occupied ? `<rect class="event-occ" x="${x.toFixed(1)}" y="74" width="${Math.max(2, step - 1).toFixed(1)}" height="44" rx="3"/>` : "";
    const safe = item.safetyAlarm ? `<rect class="event-danger" x="${x.toFixed(1)}" y="24" width="${Math.max(2, step - 1).toFixed(1)}" height="38" rx="3"/>` : "";
    return occ + safe;
  }).join("");
  return `<path class="chart-gridline" d="M10 42 H350 M10 96 H350"/>${bars}`;
}

function renderCharts(state) {
  pushHistory(state);
  const temps = history.map(item => item.temperatureC);
  const lights = history.map(item => Math.min(1023, item.light) / 1023 * 100);
  const gas = history.map(item => Math.min(800, item.gas) / 800 * 100);
  const pwm = history.map(item => item.pwm / 255 * 100);
  const rpm = history.map(item => Math.min(4200, item.rpm) / 4200 * 100);

  document.querySelector("#tempChart").innerHTML = lineSvg(temps, { id: "temp", min: Math.min(18, ...temps), max: Math.max(35, ...temps) });
  document.querySelector("#envChart").innerHTML = multiLineSvg([{ values: lights }, { values: gas }], { min: 0, max: 100 });
  document.querySelector("#fanChart").innerHTML = multiLineSvg([{ values: pwm }, { values: rpm }], { min: 0, max: 100 });
  document.querySelector("#eventChart").innerHTML = eventSvg();

  document.querySelector("#tempChartValue").textContent = state.temperatureC == null ? "--" : `${Number(state.temperatureC).toFixed(1)} C`;
  document.querySelector("#envChartValue").textContent = `L ${state.light ?? "--"} / G ${state.gas ?? "--"}`;
  document.querySelector("#fanChartValue").textContent = `PWM ${state.pwm ?? "--"} / ${state.rpm ?? "--"} rpm`;
  document.querySelector("#eventChartValue").textContent = `${fmtBool(state.occupied)} / ${fmtBool(state.safetyAlarm)}`;
}

function pct(value) {
  if (value == null || Number.isNaN(Number(value))) return "--";
  return `${Math.round(Number(value) * 100)}%`;
}

function renderIntelligence(state = {}) {
  const dc = state.dataCollection || {};
  const analytics = state.analytics || {};
  const metrics = analytics.metrics || {};
  const expected = analytics.expected || {};
  const ml = analytics.ml || {};
  const recommended = ml.recommendedAuto || expected.recommendedAuto || {};
  const collecting = Boolean(dc.enabled);
  const collectButton = document.querySelector("#dataCollectToggle");
  collectButton.textContent = collecting ? tr("stopCollectData") : tr("collectData");
  collectButton.dataset.active = collecting ? "true" : "false";

  document.querySelector("#collectionState").textContent = collecting ? "COLLECTING" : "PAUSED";
  document.querySelector("#collectionDetail").textContent = `${dc.sampleCount || 0} samples / ${dc.preferenceCount || 0} prefs`;
  document.querySelector("#comfortRiskValue").textContent = pct(expected.comfortRisk);
  document.querySelector("#energyLoadValue").textContent = `energy ${pct(expected.energyLoad)}`;
  document.querySelector("#modelRecommendation").textContent = recommended.fanOnC == null
    ? "--"
    : `${recommended.fanOffC}/${recommended.fanOnC} C`;
  document.querySelector("#modelConfidence").textContent = ml.ok
    ? `torch ${pct(recommended.confidence)}`
    : `local ${expected.dataNeeded ?? "--"} samples`;
  document.querySelector("#occupancyRateValue").textContent = pct(metrics.occupancyRate);
  document.querySelector("#fanDutyValue").textContent = pct(metrics.fanDuty);
  document.querySelector("#manualRateValue").textContent = pct(metrics.manualRate);
  document.querySelector("#dataNeededValue").textContent = expected.dataNeeded ?? "--";

  const voice = state.voice || {};
  document.querySelector("#voiceState").textContent = voice.status || "idle";
  document.querySelector("#voiceTranscript").textContent = voice.lastError || voice.transcript || voice.intent?.reply || "--";
  renderTaskTimeline(state);
}

function taskPlanFromState(state = {}) {
  const active = state.taskPlan || null;
  const voice = state.voice?.intent?.taskPlan || (Array.isArray(state.voice?.intent?.tasks) ? state.voice.intent : null);
  if (!active) return voice;
  if (!voice) return active;
  const activeTime = Date.parse(active.createdAt || 0) || 0;
  const voiceTime = Date.parse(voice.createdAt || 0) || 0;
  return voiceTime >= activeTime ? voice : active;
}

function formatTaskDelay(seconds) {
  const s = Math.max(0, Math.round(Number(seconds || 0)));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const r = s % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${r}s`;
  return `${r}s`;
}

function describeTask(task = {}) {
  if (task.action === "set_manual") {
    const m = task.manual || {};
    return `manual lamp=${m.lamp ? "on" : "off"} fan=${m.fan ? m.pwm ?? "--" : "off"} buzzer=${m.buzzer ? "on" : "off"} status=${m.status || "--"}`;
  }
  if (task.action === "set_auto_config") {
    const a = task.auto || {};
    return `auto fan ${a.fanOffC ?? "--"}-${a.fanOnC ?? "--"}C light ${a.ledMax ?? "--"} status ${a.statusMax ?? "--"}`;
  }
  if (task.action === "preset") return `preset ${task.presetId || "--"}`;
  if (task.action === "command") return `command ${task.command || "--"}`;
  if (task.action === "return_auto") return "restore automatic policy";
  return task.note || task.action || "noop";
}

function renderTaskTimeline(state = {}) {
  const root = document.querySelector("#taskTimeline");
  const title = document.querySelector("#taskPlanTitle");
  const cancel = document.querySelector("#cancelTaskPlan");
  if (!root || !title) return;
  const plan = taskPlanFromState(state);
  if (!plan || !Array.isArray(plan.tasks) || plan.tasks.length === 0) {
    title.textContent = "No active task timeline";
    root.innerHTML = `<div class="task-empty">Qwen can turn phrases like "3 minutes later" into scheduled device tasks.</div>`;
    if (cancel) {
      cancel.disabled = true;
      cancel.hidden = true;
    }
    return;
  }
  const active = plan.status === "scheduled" || plan.tasks.some((task) => task.status === "pending");
  title.textContent = `${plan.status || "planned"} / ${Math.round(Number(plan.confidence || 0) * 100)}% / ${plan.tasks.length} tasks`;
  if (cancel) {
    cancel.disabled = !active;
    cancel.hidden = !active;
  }
  root.innerHTML = plan.tasks.map((task, index) => `
    <div class="task-node" data-status="${escapeHtml(task.status || "pending")}" data-risk="${escapeHtml(task.risk || "low")}">
      <div class="task-index">${index + 1}</div>
      <div class="task-body">
        <div><strong>${escapeHtml(task.title || task.action || "Task")}</strong><span>${escapeHtml(task.status || "pending")}</span></div>
        <p>${escapeHtml(describeTask(task))}</p>
        <small>T+${escapeHtml(formatTaskDelay(task.delaySec))}${task.remainingSec != null ? ` / ${escapeHtml(formatTaskDelay(task.remainingSec))} left` : ""}</small>
      </div>
    </div>
  `).join("");
}

function setInputIfIdle(id, value, digits = null) {
  const input = document.querySelector(`#${id}`);
  if (!input || document.activeElement === input || value == null) return;
  input.value = digits == null ? String(value) : Number(value).toFixed(digits);
}

function setCheckIfIdle(id, value) {
  const input = document.querySelector(`#${id}`);
  if (!input || document.activeElement === input) return;
  input.checked = Boolean(value);
}

function numberFrom(id, fallback, digits = null) {
  const n = Number(document.querySelector(`#${id}`).value);
  if (!Number.isFinite(n)) return fallback;
  return digits === null ? Math.round(n) : Number(n.toFixed(digits));
}

function getAutoForm() {
  return {
    fanOnC: numberFrom("fanOnInput", 28, 1),
    fanOffC: numberFrom("fanOffInput", 26, 1),
    ledMax: numberFrom("ledMaxInput", 230),
    statusMax: numberFrom("statusMaxInput", 220),
    lightDark: numberFrom("lightDarkInput", 420),
    lightBright: numberFrom("lightBrightInput", 560)
  };
}

function getManualForm() {
  return {
    enabled: document.querySelector("#manualSwitch").checked,
    lamp: document.querySelector("#manualLamp").checked,
    fan: document.querySelector("#manualFan").checked,
    pwm: numberFrom("manualPwm", 150),
    buzzer: document.querySelector("#manualBuzzer").checked,
    status: document.querySelector("#manualStatus").value
  };
}

function syncControls(state) {
  const auto = state.settings?.auto || settings.auto || {};
  const manual = state.settings?.manual || settings.manual || {};
  setInputIfIdle("fanOnInput", auto.fanOnC ?? state.fanOnC, 1);
  setInputIfIdle("fanOffInput", auto.fanOffC ?? state.fanOffC, 1);
  setInputIfIdle("ledMaxInput", auto.ledMax ?? state.ledMax);
  setInputIfIdle("statusMaxInput", auto.statusMax ?? state.statusMax);
  setInputIfIdle("lightDarkInput", auto.lightDark);
  setInputIfIdle("lightBrightInput", auto.lightBright);
  setInputIfIdle("manualPwm", manual.pwm);
  setCheckIfIdle("manualSwitch", manual.enabled || Number(state.manual || 0) === 1);
  setCheckIfIdle("manualLamp", manual.lamp);
  setCheckIfIdle("manualFan", manual.fan);
  setCheckIfIdle("manualBuzzer", manual.buzzer);
  if (document.activeElement !== document.querySelector("#manualStatus")) {
    document.querySelector("#manualStatus").value = manual.status || "ALL";
  }
  document.querySelector("#ledMaxValue").textContent = document.querySelector("#ledMaxInput").value;
  document.querySelector("#statusMaxValue").textContent = document.querySelector("#statusMaxInput").value;
  document.querySelector("#manualPwmValue").textContent = document.querySelector("#manualPwm").value;
  const manualOpen = document.querySelector("#manualSwitch").checked;
  document.querySelector("#manualDetails").dataset.open = manualOpen ? "true" : "false";
  document.querySelector("#manualHint").hidden = manualOpen;
}

function renderPresets() {
  const key = JSON.stringify({
    language,
    active: settings.activePreset,
    presets: presets.map(item => item.id),
    custom: (settings.customStrategies || []).map(item => `${item.id}:${item.name}:${item.description}`)
  });
  if (key === presetRenderKey) return;
  presetRenderKey = key;
  const root = document.querySelector("#presetList");
  if (!root) return;
  root.innerHTML = presets.map((preset) => `
    <button class="preset ${settings.activePreset === preset.id ? "active" : ""}" data-preset="${preset.id}">
      <strong>${escapeHtml(preset.name?.[language] || preset.name?.en || preset.id)}</strong>
      <span>${escapeHtml(preset.description?.[language] || preset.description?.en || "")}</span>
    </button>
  `).join("");
  for (const button of root.querySelectorAll("[data-preset]")) {
    button.addEventListener("click", () => postJson(`/api/preset/${button.dataset.preset}`, {}));
  }

  const customRoot = document.querySelector("#customStrategies");
  customRoot.innerHTML = (settings.customStrategies || []).map((item) => `
    <div class="strategy-row">
      <button class="preset" data-custom="${item.id}">
        <strong>${escapeHtml(item.name)}</strong>
        <span>${escapeHtml(item.description || `${item.auto.fanOffC}/${item.auto.fanOnC} C`)}</span>
      </button>
      <button class="icon-btn" data-delete="${item.id}">${tr("delete")}</button>
    </div>
  `).join("");
  for (const button of customRoot.querySelectorAll("[data-custom]")) {
    button.addEventListener("click", () => postJson(`/api/strategies/${button.dataset.custom}/apply`, {}));
  }
  for (const button of customRoot.querySelectorAll("[data-delete]")) {
    button.addEventListener("click", () => fetch(`/api/strategies/${button.dataset.delete}`, { method: "DELETE" }));
  }
}

function renderTelemetryGrid(state) {
  const entries = [
    ["Mode", state.mode],
    ["PIR", fmtBool(state.occupied)],
    ["Light", state.light],
    ["Dark Gate", fmtBool(state.dark)],
    ["Temperature", state.temperatureC == null ? "--" : `${Number(state.temperatureC).toFixed(1)} C`],
    ["Temp Source", state.temperatureSource],
    ["ESP32 ADC", `raw ${state.esp32AdcRawMv ?? "--"} / corrected ${state.esp32AdcCorrectedMv ?? "--"} / ambient ${state.esp32AdcAmbientMv ?? state.esp32AdcMv ?? "--"} mV`],
    ["ADC Dummy", `dummy ${state.esp32AdcDummyMv ?? "--"} / base ${state.esp32AdcDummyBaselineMv ?? "--"} / comp ${state.esp32AdcDummyCompMv ?? "--"} mV`],
    ["ADC Guard", state.esp32AdcSuspect ? "spike guarded" : "normal"],
    ["Gas", state.gas],
    ["Flame", `${fmtBool(state.flameDetected)} / AO ${state.flameAnalog ?? "--"}`],
    ["Fan", `${fmtBool(state.fan)} / PWM ${state.pwm ?? "--"}`],
    ["RPM", state.rpm],
    ["Lamp", fmtBool(state.lamp)],
    ["Status", `${statusName(state.statusLight)} / ${state.statusMax ?? "--"}`],
    ["ACK", state.commandAck || "--"]
  ];
  const key = entries.map(item => item.join(":")).join("|");
  if (key === telemetryRenderKey) return;
  telemetryRenderKey = key;
  document.querySelector("#telemetryGrid").innerHTML = entries.map(([label, value]) => `
    <div class="telemetry-tile">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `).join("");
}

function render(state) {
  currentState = state || {};
  settings = state.settings || settings || {};
  presets = state.presets || presets || [];
  if (settings.language && settings.language !== language) applyLanguage(settings.language);

  document.body.dataset.bg = settings.background || "aurora";
  document.body.dataset.accent = settings.accent || "cyan";
  document.querySelector("#backgroundSelect").value = settings.background || "aurora";
  document.querySelector("#accentSelect").value = settings.accent || "cyan";
  backdrop.setState(settings, state);

  const alarm = Number(state.safetyAlarm || 0) === 1 || state.mode === "SAFETY_ALARM";
  const badge = document.querySelector("#summaryBadge");
  badge.textContent = alarm ? "SAFETY ALARM" : state.online ? state.mode || "ONLINE" : (state.status || "WAITING").toUpperCase();
  document.querySelector("#modeOrb").dataset.state = alarm ? "danger" : state.mode === "COOLING" ? "warn" : state.online ? "ok" : "off";
  document.querySelector("#mqttStatus").textContent = state.status || "waiting";
  document.querySelector("#age").textContent = state.ageMs == null ? "--" : `${Math.round(state.ageMs / 1000)} s`;
  document.querySelector("#queueDepth").textContent = state.commandQueue || 0;
  renderCards(state);
  renderCharts(state);
  renderIntelligence(state);
  syncControls(state);
  renderPresets();
  renderTelemetryGrid(state);
  renderLog(state.log || []);
}

function renderLog(logItems) {
  const log = document.querySelector("#log");
  log.innerHTML = logItems.slice(0, 60).map((item) => `
    <div class="log-row">
      <span>${escapeHtml(item.at)}</span>
      <strong>${escapeHtml(item.topic || item.type)}</strong>
      <code>${escapeHtml(item.message)}</code>
    </div>
  `).join("");
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  }[ch]));
}

async function postJson(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

async function refreshAnalytics() {
  const response = await fetch("/api/analytics");
  const data = await response.json();
  if (data.analytics) {
    currentState.analytics = data.analytics;
    renderIntelligence(currentState);
  }
  return data;
}

async function updateAppearance(partial) {
  await postJson("/api/appearance", {
    language: settings.language,
    background: settings.background,
    accent: settings.accent,
    ...partial
  });
}

let mediaRecorder = null;
let audioChunks = [];

async function startVoiceRecording() {
  if (!window.isSecureContext && location.hostname !== "localhost" && location.hostname !== "127.0.0.1") {
    document.querySelector("#voiceState").textContent = "HTTPS required";
    document.querySelector("#voiceTranscript").textContent = "局域网设备请打开 https://<电脑IP>:3443";
    return;
  }
  const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
  audioChunks = [];
  mediaRecorder = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "" });
  mediaRecorder.ondataavailable = (event) => {
    if (event.data && event.data.size > 0) audioChunks.push(event.data);
  };
  mediaRecorder.onstop = async () => {
    stream.getTracks().forEach((track) => track.stop());
    const blob = new Blob(audioChunks, { type: audioChunks[0]?.type || "audio/webm" });
    document.querySelector("#voiceState").textContent = "uploading";
    try {
      const response = await fetch("/api/voice/audio", {
        method: "POST",
        headers: { "Content-Type": blob.type || "application/octet-stream" },
        body: blob
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "voice_failed");
      document.querySelector("#voiceTranscript").textContent = data.transcript || "--";
    } catch (error) {
      document.querySelector("#voiceState").textContent = "error";
      document.querySelector("#voiceTranscript").textContent = error.message;
    }
  };
  mediaRecorder.start();
  document.querySelector("#voiceState").textContent = "recording";
  document.querySelector("#voiceTranscript").textContent = "正在听...";
}

function stopVoiceRecording() {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
  }
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws`);
  const wsState = document.querySelector("#wsState");
  ws.onopen = () => { wsState.textContent = "connected"; };
  ws.onclose = () => {
    wsState.textContent = "reconnecting";
    setTimeout(connect, 1000);
  };
  ws.onerror = () => { wsState.textContent = "error"; };
  ws.onmessage = event => render(JSON.parse(event.data));
}

for (const id of ["ledMaxInput", "statusMaxInput", "manualPwm"]) {
  document.querySelector(`#${id}`).addEventListener("input", (event) => {
    document.querySelector(`#${id}Value`).textContent = event.target.value;
  });
}

document.querySelector("#applyConfig").addEventListener("click", async (event) => {
  event.currentTarget.dataset.busy = "true";
  await postJson("/api/config", getAutoForm());
  event.currentTarget.dataset.busy = "false";
});

document.querySelector("#applyManual").addEventListener("click", () => postJson("/api/manual", getManualForm()));
document.querySelector("#manualSwitch").addEventListener("change", () => postJson("/api/manual", getManualForm()));
document.querySelector("#returnAuto").addEventListener("click", () => postJson("/api/auto", {}));
document.querySelector("#allStatusLights").addEventListener("click", () => {
  document.querySelector("#manualSwitch").checked = true;
  document.querySelector("#manualStatus").value = "ALL";
  postJson("/api/manual", getManualForm());
});

document.querySelector("#saveStrategy").addEventListener("click", () => {
  postJson("/api/strategies", {
    name: document.querySelector("#strategyName").value || "Custom Strategy",
    description: document.querySelector("#strategyDesc").value || "",
    auto: getAutoForm()
  });
});

document.querySelector("#backgroundSelect").addEventListener("change", (event) => updateAppearance({ background: event.target.value }));
document.querySelector("#accentSelect").addEventListener("change", (event) => updateAppearance({ accent: event.target.value }));
document.querySelector("#langZh").addEventListener("click", () => updateAppearance({ language: "zh" }));
document.querySelector("#langEn").addEventListener("click", () => updateAppearance({ language: "en" }));
document.querySelector("#reapplyConfig").addEventListener("click", () => postJson("/api/reapply", {}));
document.querySelector("#dataCollectToggle").addEventListener("click", () => {
  const enabled = document.querySelector("#dataCollectToggle").dataset.active !== "true";
  postJson("/api/data/collection", { enabled }).then(refreshAnalytics);
});
document.querySelector("#refreshAnalytics").addEventListener("click", refreshAnalytics);
document.querySelector("#applyRecommendation").addEventListener("click", () => postJson("/api/analytics/apply-recommendation", {}).then(refreshAnalytics));
document.querySelector("#cancelTaskPlan").addEventListener("click", () => postJson("/api/voice/plan/cancel", {}));

const voiceButton = document.querySelector("#voiceRecord");
voiceButton.addEventListener("pointerdown", (event) => {
  event.preventDefault();
  startVoiceRecording().catch((error) => {
    document.querySelector("#voiceState").textContent = "error";
    document.querySelector("#voiceTranscript").textContent = error.message;
  });
});
for (const eventName of ["pointerup", "pointercancel", "pointerleave"]) {
  voiceButton.addEventListener(eventName, stopVoiceRecording);
}
document.querySelector("#sendVoiceText").addEventListener("click", async () => {
  const input = document.querySelector("#voiceTextInput");
  const transcript = input.value.trim();
  if (!transcript) return;
  document.querySelector("#voiceState").textContent = "understanding";
  const data = await postJson("/api/voice/text", { transcript });
  document.querySelector("#voiceTranscript").textContent = data.intent?.reply || data.transcript || "--";
});

for (const button of document.querySelectorAll("[data-cmd]")) {
  button.addEventListener("click", () => postJson(`/api/command/${button.dataset.cmd}`, {}));
}

connect();
refreshAnalytics();
