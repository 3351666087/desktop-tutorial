const fs = require("fs");
const https = require("https");
const http = require("http");
const net = require("net");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const aedes = require("aedes")();
const express = require("express");
const selfsigned = require("selfsigned");
const WebSocket = require("ws");

const MQTT_PORT = Number(process.env.MQTT_PORT || 1883);
const WEB_PORT = Number(process.env.WEB_PORT || 3000);
const WEB_HTTPS_PORT = Number(process.env.WEB_HTTPS_PORT || 3443);
const HOST = "0.0.0.0";

const TOPIC_PREFIX = "smartclassroom/edge1";
const TOPIC_TELEMETRY = `${TOPIC_PREFIX}/telemetry`;
const TOPIC_COMMAND = `${TOPIC_PREFIX}/command`;
const TOPIC_COMMAND_ACK = `${TOPIC_PREFIX}/command_ack`;

const DATA_DIR = path.join(__dirname, "data");
const SETTINGS_PATH = path.join(DATA_DIR, "settings.json");
const SECRETS_PATH = path.join(DATA_DIR, "secrets.json");
const CERT_DIR = path.join(DATA_DIR, "certs");
const CERT_KEY_PATH = path.join(CERT_DIR, "localhost-key.pem");
const CERT_PATH = path.join(CERT_DIR, "localhost-cert.pem");
const TELEMETRY_SAMPLES_PATH = path.join(DATA_DIR, "telemetry_samples.jsonl");
const PREFERENCE_EVENTS_PATH = path.join(DATA_DIR, "preference_events.jsonl");
const UPLOAD_DIR = path.join(DATA_DIR, "voice_uploads");
const AI_SCRIPT_DIR = path.join(__dirname, "..", "smart_ai");
const ASR_SCRIPT_PATH = path.join(AI_SCRIPT_DIR, "asr_transcribe.py");
const PREFERENCE_SCRIPT_PATH = path.join(AI_SCRIPT_DIR, "preference_model.py");
const MEDIA_ASR_PYTHON = process.env.SMARTCLASSROOM_ASR_PYTHON || "C:\\Users\\33516\\.conda\\envs\\media-asr\\python.exe";
const QWEN_BASE_URL = process.env.QWEN_BASE_URL || "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions";
const QWEN_MODEL = process.env.QWEN_MODEL || "qwen3.6-plus";
const QWEN_TASK_MAX_COUNT = 10;
const QWEN_TASK_MAX_DELAY_SEC = 6 * 60 * 60;
const QWEN_TASK_MIN_CONFIDENCE = 0.35;
const TASK_PLAN_AUTO_CLEAR_DELAY_MS = 30000;

const PRESETS = [
  {
    id: "comfort",
    name: { en: "Comfort", zh: "舒适" },
    description: { en: "Balanced classroom operation.", zh: "教室日常演示的平衡策略。" },
    auto: { fanOnC: 28.0, fanOffC: 26.0, ledMax: 230, statusMax: 220, lightDark: 420, lightBright: 560 }
  },
  {
    id: "energy",
    name: { en: "Energy Saver", zh: "节能" },
    description: { en: "Later cooling, dimmer indicators.", zh: "更晚启动风扇，降低灯光上限。" },
    auto: { fanOnC: 30.0, fanOffC: 27.5, ledMax: 170, statusMax: 150, lightDark: 360, lightBright: 520 }
  },
  {
    id: "presentation",
    name: { en: "Presentation", zh: "展示" },
    description: { en: "Soft status lights and stable lighting.", zh: "柔和状态灯，适合课堂展示。" },
    auto: { fanOnC: 27.5, fanOffC: 25.5, ledMax: 210, statusMax: 120, lightDark: 500, lightBright: 650 }
  },
  {
    id: "safety",
    name: { en: "Safety First", zh: "安全优先" },
    description: { en: "Early ventilation and bright indicators.", zh: "更早通风，状态灯更亮。" },
    auto: { fanOnC: 26.0, fanOffC: 24.5, ledMax: 255, statusMax: 255, lightDark: 460, lightBright: 610 }
  }
];

const DEFAULT_SETTINGS = {
  language: "zh",
  background: "aurora",
  accent: "cyan",
  activePreset: "comfort",
  commandDelayMs: 1000,
  auto: { fanOnC: 28.0, fanOffC: 26.0, ledMax: 230, statusMax: 220, lightDark: 420, lightBright: 560 },
  manual: { enabled: false, lamp: false, fan: false, pwm: 150, buzzer: false, status: "ALL" },
  customStrategies: []
};

const app = express();
const httpServer = http.createServer(app);
const mqttServer = net.createServer(aedes.handle);
const wsServers = [];

app.use(express.json({ limit: "1mb" }));
app.use(express.static(path.join(__dirname, "public")));

function ensureDataDir() {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}

function ensureUploadDir() {
  fs.mkdirSync(UPLOAD_DIR, { recursive: true });
}

async function ensureHttpsCertificate() {
  fs.mkdirSync(CERT_DIR, { recursive: true });
  if (!fs.existsSync(CERT_KEY_PATH) || !fs.existsSync(CERT_PATH)) {
    const cert = await selfsigned.generate(
      [
        { name: "commonName", value: "smartclassroom.local" },
        { name: "organizationName", value: "Smart Classroom Local Lab" }
      ],
      {
        days: 365,
        keySize: 2048,
        algorithm: "sha256",
        extensions: [
          { name: "basicConstraints", cA: true },
          {
            name: "subjectAltName",
            altNames: [
              { type: 2, value: "localhost" },
              { type: 2, value: "smartclassroom.local" },
              { type: 7, ip: "127.0.0.1" },
              ...getLanAddresses().map((ip) => ({ type: 7, ip }))
            ]
          }
        ]
      }
    );
    fs.writeFileSync(CERT_KEY_PATH, cert.private || cert.privateKey);
    fs.writeFileSync(CERT_PATH, cert.cert);
  }
  return {
    key: fs.readFileSync(CERT_KEY_PATH),
    cert: fs.readFileSync(CERT_PATH)
  };
}

function getLanAddresses() {
  const addresses = [];
  for (const infos of Object.values(os.networkInterfaces())) {
    for (const info of infos || []) {
      if (info.family === "IPv4" && !info.internal) {
        addresses.push(info.address);
      }
    }
  }
  return addresses;
}

function readSecrets() {
  try {
    return JSON.parse(fs.readFileSync(SECRETS_PATH, "utf8").replace(/^\uFEFF/, ""));
  } catch (_error) {
    return {};
  }
}

function getDashScopeApiKey() {
  return process.env.DASHSCOPE_API_KEY || readSecrets().dashscopeApiKey || "";
}

function appendJsonl(filePath, entry) {
  ensureDataDir();
  fs.appendFile(filePath, JSON.stringify(entry) + "\n", () => {});
}

function readJsonlTail(filePath, limit = 400) {
  try {
    const lines = fs.readFileSync(filePath, "utf8").trim().split(/\r?\n/).filter(Boolean);
    return lines.slice(-limit).map((line) => JSON.parse(line));
  } catch (_error) {
    return [];
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function readSettings() {
  ensureDataDir();
  try {
    const saved = JSON.parse(fs.readFileSync(SETTINGS_PATH, "utf8"));
    return mergeSettings(clone(DEFAULT_SETTINGS), saved);
  } catch (_error) {
    return clone(DEFAULT_SETTINGS);
  }
}

function saveSettings() {
  ensureDataDir();
  fs.writeFileSync(SETTINGS_PATH, JSON.stringify(settings, null, 2));
}

function mergeSettings(base, incoming) {
  for (const [key, value] of Object.entries(incoming || {})) {
    if (value && typeof value === "object" && !Array.isArray(value) && base[key] && typeof base[key] === "object" && !Array.isArray(base[key])) {
      base[key] = mergeSettings(base[key], value);
    } else {
      base[key] = value;
    }
  }
  base.auto = sanitizeAuto(base.auto);
  base.manual = sanitizeManual(base.manual);
  if (!Array.isArray(base.customStrategies)) base.customStrategies = [];
  return base;
}

function clampNumber(value, min, max, fallback, digits = null) {
  const n = Number(value);
  const safe = Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : fallback;
  return digits === null ? Math.round(safe) : Number(safe.toFixed(digits));
}

function sanitizeAuto(input = {}) {
  const fanOnC = clampNumber(input.fanOnC, 15, 45, DEFAULT_SETTINGS.auto.fanOnC, 1);
  let fanOffC = clampNumber(input.fanOffC, 10, 44, DEFAULT_SETTINGS.auto.fanOffC, 1);
  if (fanOffC >= fanOnC) fanOffC = Number((fanOnC - 0.5).toFixed(1));
  return {
    fanOnC,
    fanOffC,
    ledMax: clampNumber(input.ledMax, 0, 255, DEFAULT_SETTINGS.auto.ledMax),
    statusMax: clampNumber(input.statusMax, 0, 255, DEFAULT_SETTINGS.auto.statusMax),
    lightDark: clampNumber(input.lightDark, 0, 1023, DEFAULT_SETTINGS.auto.lightDark),
    lightBright: Math.max(
      clampNumber(input.lightDark, 0, 1023, DEFAULT_SETTINGS.auto.lightDark) + 50,
      clampNumber(input.lightBright, 0, 1023, DEFAULT_SETTINGS.auto.lightBright)
    )
  };
}

function sanitizeManual(input = {}) {
  return {
    enabled: Boolean(input.enabled),
    lamp: Boolean(input.lamp),
    fan: Boolean(input.fan),
    pwm: clampNumber(input.pwm, 0, 255, DEFAULT_SETTINGS.manual.pwm),
    buzzer: Boolean(input.buzzer),
    status: ["ALL", "R", "Y", "G", "OFF"].includes(input.status) ? input.status : "ALL"
  };
}

let settings = readSettings();

const state = {
  online: false,
  brokerOnline: true,
  lastSeen: 0,
  ageMs: null,
  status: "waiting",
  mode: "--",
  pir: null,
  occupied: null,
  light: null,
  dark: null,
  lightGate: "--",
  temperatureC: null,
  temperatureSource: "--",
  esp32AdcTempC: null,
  esp32AdcMv: null,
  esp32AdcRawMv: null,
  esp32AdcCorrectedMv: null,
  esp32AdcAmbientMv: null,
  esp32AdcTrustedMv: null,
  esp32AdcRawTempC: null,
  esp32AdcSuspect: 0,
  esp32AdcDummyRawMv: null,
  esp32AdcDummyMv: null,
  esp32AdcDummyBaselineMv: null,
  esp32AdcDummyCompMv: null,
  esp32AdcDummyValid: 0,
  esp32AdcDummyCompActive: 0,
  esp32AdcValid: 0,
  gas: null,
  gasDanger: 0,
  flameDigital: null,
  flameAnalog: null,
  flameDetected: 0,
  demoEmergency: 0,
  safetyAlarm: 0,
  fan: 0,
  pwm: 0,
  rpm: 0,
  lamp: 0,
  manual: 0,
  fanOnC: settings.auto.fanOnC,
  fanOffC: settings.auto.fanOffC,
  ledMax: settings.auto.ledMax,
  statusMax: settings.auto.statusMax,
  statusLight: "--",
  fanHealth: "STANDBY",
  commandAck: "",
  lastCommand: "",
  commandQueue: 0,
  raw: "",
  topics: {},
  log: [],
  dataCollection: { enabled: false, sampleCount: 0, preferenceCount: 0 },
  analytics: null,
  taskPlan: null,
  voice: { status: "idle", transcript: "", intent: null, lastError: "", lastAt: 0 }
};

let commandQueue = [];
let commandTimer = null;
let activeTaskPlan = null;
let taskTimers = new Map();
let taskPlanClearTimer = null;
let dataCollectionEnabled = false;
let dataSampleCount = readJsonlTail(TELEMETRY_SAMPLES_PATH, 1_000_000).length;
let preferenceEventCount = readJsonlTail(PREFERENCE_EVENTS_PATH, 1_000_000).length;
let lastTelemetrySampleMs = 0;

function pushLog(type, message, topic = "") {
  state.log.unshift({
    at: new Date().toLocaleTimeString(),
    type,
    topic,
    message: String(message).slice(0, 700)
  });
  state.log = state.log.slice(0, 120);
}

function buildTelemetrySample() {
  return {
    at: new Date().toISOString(),
    ts: Date.now(),
    status: state.status,
    mode: state.mode,
    occupied: state.occupied,
    light: state.light,
    dark: state.dark,
    temperatureC: state.temperatureC,
    temperatureSource: state.temperatureSource,
    gas: state.gas,
    gasDanger: state.gasDanger,
    flameDetected: state.flameDetected,
    safetyAlarm: state.safetyAlarm,
    fan: state.fan,
    pwm: state.pwm,
    rpm: state.rpm,
    lamp: state.lamp,
    manual: state.manual,
    statusLight: state.statusLight,
    esp32AdcMv: state.esp32AdcMv,
    esp32AdcRawMv: state.esp32AdcRawMv,
    esp32AdcCorrectedMv: state.esp32AdcCorrectedMv,
    esp32AdcAmbientMv: state.esp32AdcAmbientMv,
    esp32AdcTrustedMv: state.esp32AdcTrustedMv,
    esp32AdcRawTempC: state.esp32AdcRawTempC,
    esp32AdcSuspect: state.esp32AdcSuspect,
    esp32AdcDummyRawMv: state.esp32AdcDummyRawMv,
    esp32AdcDummyMv: state.esp32AdcDummyMv,
    esp32AdcDummyBaselineMv: state.esp32AdcDummyBaselineMv,
    esp32AdcDummyCompMv: state.esp32AdcDummyCompMv,
    esp32AdcDummyValid: state.esp32AdcDummyValid,
    esp32AdcDummyCompActive: state.esp32AdcDummyCompActive,
    esp32AdcValid: state.esp32AdcValid,
    fanOnC: state.fanOnC,
    fanOffC: state.fanOffC,
    ledMax: state.ledMax,
    statusMax: state.statusMax
  };
}

function recordTelemetrySample(force = false) {
  if (!dataCollectionEnabled && !force) return;
  const now = Date.now();
  if (!force && now - lastTelemetrySampleMs < 1500) return;
  lastTelemetrySampleMs = now;
  appendJsonl(TELEMETRY_SAMPLES_PATH, buildTelemetrySample());
  dataSampleCount += 1;
  state.dataCollection = {
    enabled: dataCollectionEnabled,
    sampleCount: dataSampleCount,
    preferenceCount: preferenceEventCount
  };
}

function recordPreferenceEvent(type, detail = {}) {
  appendJsonl(PREFERENCE_EVENTS_PATH, {
    at: new Date().toISOString(),
    ts: Date.now(),
    type,
    state: buildTelemetrySample(),
    settings: clone(settings),
    detail
  });
  preferenceEventCount += 1;
  state.dataCollection = {
    enabled: dataCollectionEnabled,
    sampleCount: dataSampleCount,
    preferenceCount: preferenceEventCount
  };
}

function toNumber(value, fallback = null) {
  if (value === undefined || value === null || value === "") return fallback;
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function buildConfigCommands(auto = settings.auto) {
  const cfg = sanitizeAuto(auto);
  return [
    `CMD,CFG,FAN_ON=${cfg.fanOnC.toFixed(1)},FAN_OFF=${cfg.fanOffC.toFixed(1)}`,
    `CMD,CFG,LED_MAX=${cfg.ledMax}`,
    `CMD,CFG,STATUS_MAX=${cfg.statusMax}`,
    `CMD,CFG,LIGHT_DARK=${cfg.lightDark}`,
    `CMD,CFG,LIGHT_BRIGHT=${cfg.lightBright}`
  ];
}

function buildManualCommands(manual = settings.manual) {
  const m = sanitizeManual(manual);
  if (!m.enabled) {
    return ["CMD,AUTO", "CMD,BUZZER=0"];
  }
  return [
    `CMD,MANUAL=1,STATUS=${m.status}`,
    `CMD,LAMP=${m.lamp ? 1 : 0}`,
    `CMD,FAN=${m.fan ? 1 : 0},PWM=${m.pwm}`,
    `CMD,BUZZER=${m.buzzer ? 1 : 0}`
  ];
}

function commandForVoiceKey(key) {
  const map = {
    ping: "CMD,PING",
    buzz: "CMD,BUZZ=120",
    demo_on: "CMD,DEMO=1",
    demo_off: "CMD,DEMO=0",
    status_on: `CMD,CFG,STATUS_MAX=${settings.auto.statusMax || 220}`
  };
  return map[String(key || "").trim()] || "";
}

function queueCommands(commands, reason = "command") {
  for (const command of Array.isArray(commands) ? commands : [commands]) {
    if (!command) continue;
    commandQueue.push({ command, reason, queuedAt: Date.now() });
  }
  state.commandQueue = commandQueue.length;
  scheduleCommandPump(0);
  broadcast();
}

function scheduleCommandPump(delayMs) {
  if (commandTimer) return;
  commandTimer = setTimeout(pumpCommandQueue, delayMs);
}

function pumpCommandQueue() {
  commandTimer = null;
  const item = commandQueue.shift();
  state.commandQueue = commandQueue.length;
  if (!item) {
    broadcast();
    return;
  }

  aedes.publish({ topic: TOPIC_COMMAND, payload: Buffer.from(item.command), qos: 0, retain: false });
  state.lastCommand = item.command;
  pushLog(item.reason, item.command, TOPIC_COMMAND);
  broadcast();

  if (commandQueue.length > 0) {
    scheduleCommandPump(Math.max(settings.commandDelayMs || 1000, 900));
  }
}

function normalizeTelemetry(payload) {
  const next = typeof payload === "string" ? JSON.parse(payload) : payload;

  state.online = true;
  state.lastSeen = Date.now();
  state.status = "online";
  state.mode = next.mode ?? state.mode;
  state.pir = toNumber(next.pir, state.pir);
  state.occupied = toNumber(next.occupied ?? next.pir, state.occupied);
  state.light = toNumber(next.light, state.light);
  state.dark = toNumber(next.dark, state.dark);
  state.lightGate = state.dark === 1 ? "Enabled" : "Blocked";
  state.temperatureC = toNumber(next.temperatureC, state.temperatureC);
  state.temperatureSource = next.temperatureSource ?? state.temperatureSource;
  state.esp32AdcTempC = toNumber(next.esp32AdcTempC, state.esp32AdcTempC);
  state.esp32AdcMv = toNumber(next.esp32AdcMv, state.esp32AdcMv);
  state.esp32AdcRawMv = toNumber(next.esp32AdcRawMv, state.esp32AdcRawMv);
  state.esp32AdcCorrectedMv = toNumber(next.esp32AdcCorrectedMv, state.esp32AdcCorrectedMv);
  state.esp32AdcAmbientMv = toNumber(next.esp32AdcAmbientMv, state.esp32AdcAmbientMv);
  state.esp32AdcTrustedMv = toNumber(next.esp32AdcTrustedMv, state.esp32AdcTrustedMv);
  state.esp32AdcRawTempC = toNumber(next.esp32AdcRawTempC, state.esp32AdcRawTempC);
  state.esp32AdcSuspect = toNumber(next.esp32AdcSuspect, state.esp32AdcSuspect) || 0;
  state.esp32AdcDummyRawMv = toNumber(next.esp32AdcDummyRawMv, state.esp32AdcDummyRawMv);
  state.esp32AdcDummyMv = toNumber(next.esp32AdcDummyMv, state.esp32AdcDummyMv);
  state.esp32AdcDummyBaselineMv = toNumber(next.esp32AdcDummyBaselineMv, state.esp32AdcDummyBaselineMv);
  state.esp32AdcDummyCompMv = toNumber(next.esp32AdcDummyCompMv, state.esp32AdcDummyCompMv);
  state.esp32AdcDummyValid = toNumber(next.esp32AdcDummyValid, state.esp32AdcDummyValid) || 0;
  state.esp32AdcDummyCompActive = toNumber(next.esp32AdcDummyCompActive, state.esp32AdcDummyCompActive) || 0;
  state.esp32AdcValid = toNumber(next.esp32AdcValid, state.esp32AdcValid) || 0;
  state.gas = toNumber(next.gas, state.gas);
  state.gasDanger = toNumber(next.gasDanger, state.gasDanger) || 0;
  state.flameDigital = toNumber(next.flameDigital, state.flameDigital);
  state.flameAnalog = toNumber(next.flameAnalog, state.flameAnalog);
  state.flameDetected = toNumber(next.flameDetected, state.flameDetected) || 0;
  state.demoEmergency = toNumber(next.demoEmergency, state.demoEmergency) || 0;
  state.safetyAlarm = toNumber(next.safetyAlarm, state.safetyAlarm) || 0;
  state.fan = toNumber(next.fan, state.fan) || 0;
  state.pwm = toNumber(next.pwm, state.pwm) || 0;
  state.rpm = toNumber(next.rpm, state.rpm) || 0;
  state.lamp = toNumber(next.lamp, state.lamp) || 0;
  state.manual = toNumber(next.manual, state.manual) || 0;
  state.fanOnC = toNumber(next.fanOnC ?? (next.fanOn10 == null ? null : Number(next.fanOn10) / 10), state.fanOnC);
  state.fanOffC = toNumber(next.fanOffC ?? (next.fanOff10 == null ? null : Number(next.fanOff10) / 10), state.fanOffC);
  state.ledMax = toNumber(next.ledMax, state.ledMax);
  state.statusMax = toNumber(next.statusMax, state.statusMax);
  state.statusLight = next.statusLight ?? state.statusLight;
  state.raw = next.raw ?? JSON.stringify(next);
  state.fanHealth = deriveFanHealth();
  recordTelemetrySample();
}

function deriveFanHealth() {
  if (state.fan && state.rpm > 0) return "RUNNING";
  if (state.fan && state.rpm <= 0) return "STARTING";
  return "STANDBY";
}

function handleTopic(topic, payloadBuffer) {
  const payload = payloadBuffer.toString();
  state.topics[topic] = payload;

  if (!topic.startsWith(TOPIC_PREFIX)) return;

  try {
    if (topic === TOPIC_TELEMETRY) {
      normalizeTelemetry(payload);
    } else if (topic === TOPIC_COMMAND_ACK) {
      state.commandAck = payload;
    } else if (topic.endsWith("/status")) {
      state.status = payload;
      if (payload === "uno_offline" || payload === "esp32_offline") {
        state.online = false;
      }
    } else if (topic.endsWith("/mode")) {
      state.mode = payload;
    } else if (topic.endsWith("/safety/alarm")) {
      state.safetyAlarm = toNumber(payload, state.safetyAlarm) || 0;
    } else if (topic.endsWith("/sensors/occupancy")) {
      state.occupied = toNumber(payload, state.occupied);
      state.pir = state.occupied;
    } else if (topic.endsWith("/sensors/light")) {
      state.light = toNumber(payload, state.light);
    } else if (topic.endsWith("/sensors/temperature")) {
      state.temperatureC = toNumber(payload, state.temperatureC);
    } else if (topic.endsWith("/sensors/gas")) {
      state.gas = toNumber(payload, state.gas);
    } else if (topic.endsWith("/sensors/flame")) {
      state.flameDetected = toNumber(payload, state.flameDetected) || 0;
    } else if (topic.endsWith("/actuators/lamp")) {
      state.lamp = toNumber(payload, state.lamp) || 0;
    } else if (topic.endsWith("/actuators/fan")) {
      state.fan = toNumber(payload, state.fan) || 0;
      state.fanHealth = deriveFanHealth();
    } else if (topic.endsWith("/actuators/rpm")) {
      state.rpm = toNumber(payload, state.rpm) || 0;
      state.fanHealth = deriveFanHealth();
    } else if (topic.endsWith("/actuators/status_light")) {
      state.statusLight = payload;
    }

    pushLog("mqtt", payload, topic);
    broadcast();
  } catch (error) {
    pushLog("error", error.message, topic);
  }
}

function applyConfig(auto, reason = "config") {
  settings.auto = sanitizeAuto(auto);
  saveSettings();
  state.fanOnC = settings.auto.fanOnC;
  state.fanOffC = settings.auto.fanOffC;
  state.ledMax = settings.auto.ledMax;
  state.statusMax = settings.auto.statusMax;
  queueCommands(buildConfigCommands(settings.auto), reason);
  recordPreferenceEvent(reason, { auto: settings.auto });
  broadcast();
  return settings.auto;
}

function applyManual(manual, reason = "manual") {
  settings.manual = sanitizeManual(manual);
  saveSettings();
  state.manual = settings.manual.enabled ? 1 : 0;
  if (settings.manual.enabled) {
    state.lamp = settings.manual.lamp ? 1 : 0;
    state.fan = settings.manual.fan ? 1 : 0;
    state.pwm = settings.manual.fan ? settings.manual.pwm : 0;
    state.statusLight = "M";
  }
  queueCommands(buildManualCommands(settings.manual), reason);
  recordPreferenceEvent(reason, { manual: settings.manual });
  broadcast();
  return settings.manual;
}

aedes.on("client", (client) => {
  pushLog("client", `connected: ${client?.id || "unknown"}`);
  setTimeout(() => {
    queueCommands(buildConfigCommands(settings.auto), "restore");
    if (settings.manual.enabled) {
      queueCommands(buildManualCommands(settings.manual), "restore");
    }
  }, 1400);
  broadcast();
});

aedes.on("clientDisconnect", (client) => {
  pushLog("client", `disconnected: ${client?.id || "unknown"}`);
  broadcast();
});

aedes.on("publish", (packet, client) => {
  if (!client) return;
  handleTopic(packet.topic, packet.payload);
});

function snapshot() {
  state.ageMs = state.lastSeen ? Date.now() - state.lastSeen : null;
  if (state.ageMs !== null && state.ageMs > 7000 && state.status === "online") {
    state.status = "stale";
    state.online = false;
  }
  state.dataCollection = {
    enabled: dataCollectionEnabled,
    sampleCount: dataSampleCount,
    preferenceCount: preferenceEventCount
  };
  if (activeTaskPlan) updateTaskPlanState();
  return { ...state, settings, presets: PRESETS };
}

function broadcast() {
  const data = JSON.stringify(snapshot());
  for (const server of wsServers) {
    for (const client of server.clients) {
      if (client.readyState === WebSocket.OPEN) {
        client.send(data);
      }
    }
  }
}

function attachWebSocket(server) {
  const wsServer = new WebSocket.Server({ server, path: "/ws" });
  wsServer.on("connection", (socket) => {
    socket.send(JSON.stringify(snapshot()));
  });
  wsServers.push(wsServer);
  return wsServer;
}

attachWebSocket(httpServer);

app.get("/api/state", (_req, res) => {
  res.json(snapshot());
});

app.post("/api/data/collection", (req, res) => {
  dataCollectionEnabled = Boolean(req.body?.enabled);
  if (dataCollectionEnabled) {
    recordTelemetrySample(true);
    recordPreferenceEvent("collection_started", {});
  } else {
    recordPreferenceEvent("collection_stopped", {});
  }
  broadcast();
  res.json({ ok: true, dataCollection: state.dataCollection });
});

app.get("/api/analytics", async (_req, res) => {
  const analytics = await buildAnalytics();
  state.analytics = analytics;
  broadcast();
  res.json({ ok: true, analytics });
});

app.post("/api/analytics/apply-recommendation", async (_req, res) => {
  const analytics = await buildAnalytics();
  const auto = analytics?.ml?.recommendedAuto || analytics?.expected?.recommendedAuto;
  if (!auto) {
    res.status(400).json({ ok: false, error: "no_recommendation" });
    return;
  }
  const applied = applyConfig({ ...settings.auto, ...auto }, "analytics");
  res.json({ ok: true, auto: applied });
});

app.post("/api/voice/text", async (req, res) => {
  const transcript = String(req.body?.transcript || "").trim();
  const dryRun = Boolean(req.body?.dryRun || req.body?.preview);
  if (!transcript) {
    res.status(400).json({ ok: false, error: "empty_transcript" });
    return;
  }
  state.voice = { status: "understanding", transcript, intent: null, lastError: "", lastAt: Date.now() };
  broadcast();
  try {
    const plan = await callQwenTaskPlan(transcript);
    const result = scheduleTaskPlan(plan, { dryRun });
    state.voice = { status: dryRun ? "preview" : "done", transcript, intent: { ...plan, result, taskPlan: result.plan }, lastError: "", lastAt: Date.now() };
    broadcast();
    res.json({ ok: true, transcript, plan, intent: plan, result });
  } catch (error) {
    state.voice = { status: "error", transcript, intent: null, lastError: error.message, lastAt: Date.now() };
    broadcast();
    res.status(500).json({ ok: false, error: error.message, transcript });
  }
});

app.post("/api/voice/plan", async (req, res) => {
  const transcript = String(req.body?.transcript || "").trim();
  if (!transcript) {
    res.status(400).json({ ok: false, error: "empty_transcript" });
    return;
  }
  state.voice = { status: "planning", transcript, intent: null, lastError: "", lastAt: Date.now() };
  broadcast();
  try {
    const plan = await callQwenTaskPlan(transcript);
    const result = scheduleTaskPlan(plan, { dryRun: true });
    state.voice = { status: "preview", transcript, intent: { ...plan, result, taskPlan: result.plan }, lastError: "", lastAt: Date.now() };
    broadcast();
    res.json({ ok: true, transcript, plan, result });
  } catch (error) {
    state.voice = { status: "error", transcript, intent: null, lastError: error.message, lastAt: Date.now() };
    broadcast();
    res.status(500).json({ ok: false, error: error.message, transcript });
  }
});

app.post("/api/voice/plan/cancel", (_req, res) => {
  cancelActiveTaskPlan("cancelled_by_user");
  res.json({ ok: true, taskPlan: state.taskPlan });
});

app.post("/api/voice/audio", express.raw({ type: ["audio/*", "application/octet-stream"], limit: "30mb" }), async (req, res) => {
  if (!req.body || req.body.length < 200) {
    res.status(400).json({ ok: false, error: "empty_audio" });
    return;
  }
  ensureUploadDir();
  const extension = String(req.headers["content-type"] || "").includes("wav") ? "wav" : "webm";
  const audioPath = path.join(UPLOAD_DIR, `voice-${Date.now()}-${Math.random().toString(16).slice(2)}.${extension}`);
  fs.writeFileSync(audioPath, req.body);
  state.voice = { status: "transcribing", transcript: "", intent: null, lastError: "", lastAt: Date.now() };
  broadcast();
  try {
    const asr = await runPythonJson(ASR_SCRIPT_PATH, [audioPath], 180000);
    const transcript = String(asr.text || "").trim();
    if (!transcript) {
      throw new Error("empty_transcript_after_asr");
    }
    state.voice = { status: "understanding", transcript, intent: null, lastError: "", lastAt: Date.now() };
    broadcast();
    const plan = await callQwenTaskPlan(transcript);
    const result = scheduleTaskPlan(plan);
    state.voice = { status: "done", transcript, intent: { ...plan, result, taskPlan: result.plan }, lastError: "", lastAt: Date.now() };
    broadcast();
    res.json({ ok: true, asr, transcript, plan, intent: plan, result });
  } catch (error) {
    state.voice = { status: "error", transcript: "", intent: null, lastError: error.message, lastAt: Date.now() };
    broadcast();
    res.status(500).json({ ok: false, error: error.message });
  } finally {
    fs.unlink(audioPath, () => {});
  }
});

app.get("/api/settings", (_req, res) => {
  res.json({ settings, presets: PRESETS });
});

function runPythonJson(scriptPath, args = [], timeoutMs = 120000) {
  return new Promise((resolve, reject) => {
    const child = spawn(MEDIA_ASR_PYTHON, [scriptPath, ...args], {
      cwd: path.join(__dirname, ".."),
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONUTF8: "1"
      }
    });
    let stdout = "";
    let stderr = "";
    const timer = setTimeout(() => {
      child.kill();
      reject(new Error(`python_timeout:${path.basename(scriptPath)}`));
    }, timeoutMs);
    child.stdout.on("data", (chunk) => { stdout += chunk.toString(); });
    child.stderr.on("data", (chunk) => { stderr += chunk.toString(); });
    child.on("error", (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) {
        reject(new Error((stderr || stdout || `python_exit_${code}`).slice(0, 2000)));
        return;
      }
      try {
        resolve(JSON.parse(stdout || "{}"));
      } catch (error) {
        reject(new Error(`python_json_parse_failed:${error.message}:${stdout.slice(0, 500)}`));
      }
    });
  });
}

function average(items, getter) {
  const values = items.map(getter).map(Number).filter(Number.isFinite);
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function buildLocalAnalytics() {
  const samples = readJsonlTail(TELEMETRY_SAMPLES_PATH, 1200);
  const events = readJsonlTail(PREFERENCE_EVENTS_PATH, 300);
  const occupiedSamples = samples.filter((item) => Number(item.occupied || 0) === 1);
  const latest = samples[samples.length - 1] || buildTelemetrySample();
  const occupancyRate = samples.length ? samples.filter((item) => Number(item.occupied || 0) === 1).length / samples.length : 0;
  const fanDuty = samples.length ? samples.filter((item) => Number(item.fan || 0) === 1 || Number(item.pwm || 0) > 0).length / samples.length : 0;
  const lampDuty = samples.length ? samples.filter((item) => Number(item.lamp || 0) === 1).length / samples.length : 0;
  const manualRate = samples.length ? samples.filter((item) => Number(item.manual || 0) === 1).length / samples.length : 0;
  const safetyEvents = samples.filter((item) => Number(item.safetyAlarm || 0) === 1).length;
  const avgTemp = average(samples, (item) => item.temperatureC);
  const occupiedAvgTemp = average(occupiedSamples, (item) => item.temperatureC);
  const avgLight = average(samples, (item) => item.light);
  const avgPwm = average(samples, (item) => item.pwm);
  const tempTarget = occupiedAvgTemp == null ? settings.auto.fanOffC + 1.2 : Math.max(22, Math.min(29, occupiedAvgTemp - fanDuty * 1.1));
  const recommendedFanOn = Math.max(24, Math.min(32, tempTarget + 1.1));
  const recommendedFanOff = Math.max(20, Math.min(recommendedFanOn - 0.5, tempTarget - 0.6));
  const recommendedLedMax = Math.max(80, Math.min(255, Math.round((settings.auto.ledMax || 210) * (occupancyRate > 0.55 ? 1.04 : 0.94))));
  return {
    generatedAt: new Date().toISOString(),
    collectionEnabled: dataCollectionEnabled,
    sampleCount: dataSampleCount,
    preferenceEventCount,
    windowSampleCount: samples.length,
    eventCount: events.length,
    metrics: {
      avgTemp: avgTemp == null ? null : Number(avgTemp.toFixed(2)),
      occupiedAvgTemp: occupiedAvgTemp == null ? null : Number(occupiedAvgTemp.toFixed(2)),
      avgLight: avgLight == null ? null : Number(avgLight.toFixed(1)),
      avgPwm: avgPwm == null ? null : Number(avgPwm.toFixed(1)),
      occupancyRate: Number(occupancyRate.toFixed(3)),
      fanDuty: Number(fanDuty.toFixed(3)),
      lampDuty: Number(lampDuty.toFixed(3)),
      manualRate: Number(manualRate.toFixed(3)),
      safetyEvents
    },
    expected: {
      comfortRisk: latest.temperatureC == null ? 0 : Number(Math.max(0, Math.min(1, (Number(latest.temperatureC) - settings.auto.fanOnC) / 6)).toFixed(3)),
      energyLoad: Number(Math.min(1, fanDuty * 0.55 + lampDuty * 0.35 + (average(samples, (item) => item.statusMax) || 0) / 255 * 0.1).toFixed(3)),
      nextHourFanDuty: Number(Math.max(0, Math.min(1, fanDuty * 0.72 + (latest.temperatureC > settings.auto.fanOnC ? 0.24 : 0.04))).toFixed(3)),
      recommendedAuto: {
        fanOnC: Number(recommendedFanOn.toFixed(1)),
        fanOffC: Number(recommendedFanOff.toFixed(1)),
        ledMax: recommendedLedMax,
        statusMax: settings.auto.statusMax
      },
      dataNeeded: Math.max(0, 160 - samples.length),
      businessValue: [
        "偏好模型会把用户真实调参记录变成默认策略，而不是靠猜阈值。",
        "能估算未来风扇占空和照明负载，用于节能演示和设施运营汇报。",
        "异常安全事件、手动覆盖率、舒适风险可以作为 classroom service KPI。"
      ]
    }
  };
}

async function buildAnalytics() {
  const local = buildLocalAnalytics();
  try {
    const ml = await runPythonJson(PREFERENCE_SCRIPT_PATH, [TELEMETRY_SAMPLES_PATH, PREFERENCE_EVENTS_PATH], 90000);
    return { ...local, ml };
  } catch (error) {
    return { ...local, ml: { ok: false, error: error.message } };
  }
}

async function callQwenIntent(transcript) {
  const apiKey = getDashScopeApiKey();
  if (!apiKey) {
    return {
      action: "noop",
      confidence: 0,
      reply: "Qwen API key is not configured.",
      error: "missing_api_key"
    };
  }

  const systemPrompt = [
    "你是 Smart Classroom 的语音控制器。只输出 JSON，不要输出 Markdown。",
    "你不能直接操作硬件，只能选择 action，让后端执行白名单动作。",
    "支持 action: noop, return_auto, set_manual, set_auto_config, preset, command。",
    "manual 字段可包含 enabled,lamp,fan,pwm,buzzer,status。status 只能是 ALL/R/Y/G/OFF。",
    "auto 字段可包含 fanOnC,fanOffC,ledMax,statusMax,lightDark,lightBright。",
    "presetId 只能是 comfort/energy/presentation/safety。",
    "command 只能是 ping,buzz,demo_on,demo_off,status_on。",
    "如果用户要求控制灯、风扇、蜂鸣器、状态灯，通常 action=set_manual 并 enabled=true。",
    "如果用户要求回到自动或智能模式，action=return_auto。",
    "必须给 confidence 0-1 和中文 reply。"
  ].join("\n");

  const body = {
    model: QWEN_MODEL,
    messages: [
      { role: "system", content: systemPrompt },
      {
        role: "user",
        content: JSON.stringify({
          transcript,
          telemetry: buildTelemetrySample(),
          settings,
          allowedManualStatus: ["ALL", "R", "Y", "G", "OFF"],
          requiredOutput: {
            action: "noop|return_auto|set_manual|set_auto_config|preset|command",
            confidence: 0.0,
            reply: "中文短句",
            manual: {},
            auto: {},
            presetId: "",
            command: ""
          }
        })
      }
    ],
    temperature: 0.1,
    enable_thinking: false,
    response_format: { type: "json_object" }
  };

  const response = await fetch(QWEN_BASE_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error?.message || `qwen_http_${response.status}`);
  }
  const content = payload?.choices?.[0]?.message?.content || "{}";
  return JSON.parse(content);
}

function applyVoiceIntent(intent) {
  const action = String(intent?.action || "noop");
  const confidence = Number(intent?.confidence || 0);
  if (confidence < 0.35 && action !== "noop") {
    return { applied: false, action, reason: "low_confidence" };
  }

  if (action === "return_auto") {
    const manual = applyManual({ ...settings.manual, enabled: false, buzzer: false }, "voice");
    return { applied: true, action, manual };
  }
  if (action === "set_manual") {
    const next = sanitizeManual({ ...settings.manual, enabled: true, ...(intent.manual || {}) });
    const manual = applyManual(next, "voice");
    return { applied: true, action, manual };
  }
  if (action === "set_auto_config") {
    const auto = applyConfig({ ...settings.auto, ...(intent.auto || {}) }, "voice");
    return { applied: true, action, auto };
  }
  if (action === "preset") {
    const preset = PRESETS.find((item) => item.id === intent.presetId);
    if (!preset) return { applied: false, action, reason: "unknown_preset" };
    settings.activePreset = preset.id;
    const auto = applyConfig(preset.auto, "voice");
    saveSettings();
    return { applied: true, action, preset: preset.id, auto };
  }
  if (action === "command") {
    const map = {
      ping: "CMD,PING",
      buzz: "CMD,BUZZ=120",
      demo_on: "CMD,DEMO=1",
      demo_off: "CMD,DEMO=0",
      status_on: `CMD,CFG,STATUS_MAX=${settings.auto.statusMax || 220}`
    };
    const command = map[intent.command];
    if (!command) return { applied: false, action, reason: "unknown_command" };
    queueCommands(command, "voice");
    recordPreferenceEvent("voice", { intent });
    return { applied: true, action, command };
  }
  recordPreferenceEvent("voice", { intent });
  return { applied: false, action: "noop" };
}

function stripJsonEnvelope(text) {
  const raw = String(text || "").trim();
  if (!raw) return "{}";
  const fenced = raw.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fenced) return fenced[1].trim();
  const first = raw.indexOf("{");
  const last = raw.lastIndexOf("}");
  if (first >= 0 && last > first) return raw.slice(first, last + 1);
  return raw;
}

function normalizeDelaySec(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return 0;
  return Math.min(QWEN_TASK_MAX_DELAY_SEC, Math.max(0, Math.round(n)));
}

function normalizeTaskAction(action) {
  const value = String(action || "noop").trim();
  return ["noop", "wait", "return_auto", "set_manual", "set_auto_config", "preset", "command"].includes(value)
    ? value
    : "noop";
}

function normalizeTaskRisk(risk) {
  const value = String(risk || "low").trim();
  return ["low", "medium", "high"].includes(value) ? value : "low";
}

function normalizeTask(rawTask = {}, index = 0) {
  const action = normalizeTaskAction(rawTask.action || rawTask.type);
  const delaySec = normalizeDelaySec(rawTask.delaySec ?? rawTask.delaySeconds ?? rawTask.offsetSec ?? rawTask.afterSeconds);
  const title = String(rawTask.title || rawTask.label || `${action} ${index + 1}`).slice(0, 80);
  const task = {
    id: String(rawTask.id || `task_${index + 1}`).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 48) || `task_${index + 1}`,
    index,
    title,
    action,
    delaySec,
    executeAt: Date.now() + delaySec * 1000,
    status: "pending",
    risk: normalizeTaskRisk(rawTask.risk),
    note: String(rawTask.note || rawTask.reason || "").slice(0, 180)
  };

  if (action === "set_manual") {
    task.manual = sanitizeManual({ ...settings.manual, enabled: true, ...(rawTask.manual || {}) });
  } else if (action === "set_auto_config") {
    task.auto = sanitizeAuto({ ...settings.auto, ...(rawTask.auto || {}) });
  } else if (action === "preset") {
    task.presetId = String(rawTask.presetId || rawTask.preset || "").trim();
  } else if (action === "command") {
    task.command = String(rawTask.command || "").trim();
  }
  return task;
}

function expandImplicitTasks(tasks) {
  const expanded = [];
  for (const task of tasks) {
    expanded.push(task);
    const text = `${task.title || ""} ${task.note || ""}`.toLowerCase();
    const asksForBuzzerPulse = /buzz|buzzer|beep|蜂鸣|短响/.test(text);
    if (asksForBuzzerPulse && task.action !== "command" && !task.manual?.buzzer) {
      expanded.push(normalizeTask({
        id: `${task.id}_buzz`,
        title: "Buzzer confirmation pulse",
        action: "command",
        delaySec: Math.min(QWEN_TASK_MAX_DELAY_SEC, task.delaySec + 1),
        risk: "low",
        note: "Planner repair: the model mentioned a buzzer pulse in note/title, so it was split into an executable task.",
        command: "buzz"
      }, expanded.length));
    }
  }
  return expanded.slice(0, QWEN_TASK_MAX_COUNT).map((task, index) => ({ ...task, index }));
}

function normalizeTaskPlan(rawPlan = {}, transcript = "") {
  const sourceTasks = Array.isArray(rawPlan.tasks) && rawPlan.tasks.length
    ? rawPlan.tasks
    : [rawPlan];
  const tasks = expandImplicitTasks(sourceTasks
    .slice(0, QWEN_TASK_MAX_COUNT)
    .map((task, index) => normalizeTask(task, index)));
  const confidence = Math.max(0, Math.min(1, Number(rawPlan.confidence ?? 0)));
  return {
    planId: String(rawPlan.planId || rawPlan.id || `plan_${Date.now()}`).replace(/[^a-zA-Z0-9_-]/g, "_").slice(0, 64),
    transcript,
    reply: String(rawPlan.reply || rawPlan.summary || "Task plan ready.").slice(0, 240),
    confidence,
    createdAt: new Date().toISOString(),
    status: "planned",
    tasks: tasks.length ? tasks : [normalizeTask({ action: "noop", title: "No operation" }, 0)]
  };
}

async function callQwenTaskPlan(transcript) {
  const apiKey = getDashScopeApiKey();
  if (!apiKey) {
    return normalizeTaskPlan({
      confidence: 0,
      reply: "Qwen API key is not configured.",
      tasks: [{ action: "noop", title: "Missing API key", note: "No device action was taken." }]
    }, transcript);
  }

  const now = new Date();
  const systemPrompt = [
    "You are the Smart Classroom task planner.",
    "Return one JSON object only. Do not output Markdown.",
    "Convert the user's natural-language command into a linear timeline of executable tasks.",
    "You may decide how many tasks are needed. Split compound requests into ordered tasks.",
    "Use delaySec as seconds relative to now. Example: 'in 3 minutes' => delaySec=180.",
    "For chained timing, calculate cumulative delaySec from now. Example: 'now do A, 2 minutes later do B' => A delaySec=0, B delaySec=120.",
    "If the user gives an absolute time, use currentLocalTime and timezone to convert it into delaySec.",
    "Do not hide executable device actions inside note. If one sentence contains two actions, output two tasks.",
    "Example: 'return auto and buzz' must become one return_auto task plus one command=buzz task at the same delaySec or one second later.",
    "Allowed actions: noop, wait, return_auto, set_manual, set_auto_config, preset, command.",
    "manual may include enabled,lamp,fan,pwm,buzzer,status. status must be ALL/R/Y/G/OFF.",
    "auto may include fanOnC,fanOffC,ledMax,statusMax,lightDark,lightBright.",
    "presetId must be comfort, energy, presentation, or safety.",
    "command must be ping, buzz, demo_on, demo_off, or status_on.",
    "Never invent raw hardware commands. Use only the allowed actions and fields.",
    "Keep the plan practical for a classroom IoT demo. Safety alarm behavior on UNO has priority.",
    "Output schema: {planId, confidence, reply, tasks:[{id,title,action,delaySec,risk,note,manual,auto,presetId,command}]}."
  ].join("\n");

  const body = {
    model: QWEN_MODEL,
    messages: [
      { role: "system", content: systemPrompt },
      {
        role: "user",
        content: JSON.stringify({
          transcript,
          nowUnixMs: now.getTime(),
          currentLocalTime: now.toLocaleString("zh-CN", { timeZone: "Asia/Shanghai", hour12: false }),
          timezone: "Asia/Shanghai",
          telemetry: buildTelemetrySample(),
          settings,
          allowedManualStatus: ["ALL", "R", "Y", "G", "OFF"],
          examples: [
            {
              input: "3分钟后切换为手动模式，风扇调到180，然后再过2分钟恢复自动",
              output: {
                confidence: 0.95,
                reply: "已规划两个延迟任务。",
                tasks: [
                  { id: "manual_after_3m", title: "Switch to manual cooling", action: "set_manual", delaySec: 180, risk: "medium", manual: { enabled: true, fan: true, pwm: 180, status: "ALL" } },
                  { id: "auto_after_5m", title: "Return to automatic mode", action: "return_auto", delaySec: 300, risk: "low" }
                ]
              }
            }
          ]
        })
      }
    ],
    temperature: 0.1,
    enable_thinking: false,
    response_format: { type: "json_object" }
  };

  const response = await fetch(QWEN_BASE_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify(body)
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload?.error?.message || `qwen_http_${response.status}`);
  }
  const content = payload?.choices?.[0]?.message?.content || "{}";
  return normalizeTaskPlan(JSON.parse(stripJsonEnvelope(content)), transcript);
}

function taskPlanForClient(plan = activeTaskPlan) {
  if (!plan) return null;
  const now = Date.now();
  return {
    planId: plan.planId,
    transcript: plan.transcript,
    reply: plan.reply,
    confidence: plan.confidence,
    createdAt: plan.createdAt,
    status: plan.status,
    tasks: plan.tasks.map((task) => ({
      id: task.id,
      title: task.title,
      action: task.action,
      delaySec: task.delaySec,
      executeAt: task.executeAt,
      remainingSec: Math.max(0, Math.ceil((task.executeAt - now) / 1000)),
      status: task.status,
      risk: task.risk,
      note: task.note,
      manual: task.manual,
      auto: task.auto,
      presetId: task.presetId,
      command: task.command,
      result: task.result,
      error: task.error
    }))
  };
}

function updateTaskPlanState() {
  state.taskPlan = taskPlanForClient(activeTaskPlan);
  if (state.voice && state.voice.intent && activeTaskPlan && state.voice.intent.planId === activeTaskPlan.planId) {
    state.voice.intent.taskPlan = state.taskPlan;
  }
}

function clearTaskPlanAutoClearTimer() {
  if (taskPlanClearTimer) {
    clearTimeout(taskPlanClearTimer);
    taskPlanClearTimer = null;
  }
}

function clearCompletedTaskPlan(planId, reason = "auto_clear") {
  if (!activeTaskPlan || activeTaskPlan.planId !== planId) return;
  if (!["done", "done_with_errors"].includes(activeTaskPlan.status)) return;
  pushLog("qwen-plan", `${activeTaskPlan.planId} ${reason}`);
  activeTaskPlan = null;
  state.taskPlan = null;
  if (state.voice?.intent?.planId === planId) {
    state.voice.intent = {
      ...state.voice.intent,
      taskPlan: null,
      tasks: [],
      result: {
        ...(state.voice.intent.result || {}),
        plan: null,
        autoCleared: true
      }
    };
  }
  broadcast();
}

function scheduleTaskPlanAutoClear(plan) {
  clearTaskPlanAutoClearTimer();
  if (!plan || !["done", "done_with_errors"].includes(plan.status)) return;
  taskPlanClearTimer = setTimeout(() => {
    taskPlanClearTimer = null;
    clearCompletedTaskPlan(plan.planId);
  }, TASK_PLAN_AUTO_CLEAR_DELAY_MS);
}

function cancelActiveTaskPlan(reason = "cancelled") {
  clearTaskPlanAutoClearTimer();
  for (const timer of taskTimers.values()) clearTimeout(timer);
  taskTimers.clear();
  if (activeTaskPlan) {
    for (const task of activeTaskPlan.tasks) {
      if (task.status === "pending") {
        task.status = "cancelled";
        task.result = reason;
      }
    }
    activeTaskPlan.status = "cancelled";
    pushLog("qwen-plan", `${activeTaskPlan.planId} ${reason}`);
  }
  updateTaskPlanState();
  broadcast();
}

function executeTaskAction(task) {
  if (task.action === "wait" || task.action === "noop") {
    return { applied: false, action: task.action };
  }
  if (task.action === "return_auto") {
    const manual = applyManual({ ...settings.manual, enabled: false, buzzer: false }, "qwen-task");
    return { applied: true, action: task.action, manual };
  }
  if (task.action === "set_manual") {
    const manual = applyManual(task.manual || { ...settings.manual, enabled: true }, "qwen-task");
    return { applied: true, action: task.action, manual };
  }
  if (task.action === "set_auto_config") {
    const auto = applyConfig({ ...settings.auto, ...(task.auto || {}) }, "qwen-task");
    return { applied: true, action: task.action, auto };
  }
  if (task.action === "preset") {
    const preset = PRESETS.find((item) => item.id === task.presetId)
      || settings.customStrategies.find((item) => item.id === task.presetId);
    if (!preset) throw new Error(`unknown_preset:${task.presetId || ""}`);
    settings.activePreset = preset.id;
    const auto = applyConfig(preset.auto, "qwen-task");
    saveSettings();
    return { applied: true, action: task.action, preset: preset.id, auto };
  }
  if (task.action === "command") {
    const command = commandForVoiceKey(task.command);
    if (!command) throw new Error(`unknown_command:${task.command || ""}`);
    queueCommands(command, "qwen-task");
    return { applied: true, action: task.action, command };
  }
  return { applied: false, action: "noop" };
}

function runPlannedTask(plan, task) {
  task.status = "running";
  task.startedAt = new Date().toISOString();
  pushLog("qwen-task", `running ${task.id}: ${task.title}`);
  try {
    task.result = executeTaskAction(task);
    task.status = "done";
  } catch (error) {
    task.status = "error";
    task.error = error.message;
    pushLog("error", error.message, `qwen-task:${task.id}`);
  }
  task.finishedAt = new Date().toISOString();
  if (plan.tasks.every((item) => ["done", "error", "cancelled"].includes(item.status))) {
    plan.status = plan.tasks.some((item) => item.status === "error") ? "done_with_errors" : "done";
    scheduleTaskPlanAutoClear(plan);
  }
  recordPreferenceEvent("qwen_task", { planId: plan.planId, task });
  updateTaskPlanState();
  broadcast();
}

function scheduleTaskPlan(plan, options = {}) {
  const dryRun = Boolean(options.dryRun);
  if (plan.confidence < QWEN_TASK_MIN_CONFIDENCE && plan.tasks.some((task) => task.action !== "noop")) {
    plan.status = "rejected";
    return { applied: false, dryRun, reason: "low_confidence", plan: taskPlanForClient(plan) || plan };
  }
  if (dryRun) {
    plan.status = "preview";
    return { applied: false, dryRun: true, plan };
  }

  cancelActiveTaskPlan("superseded");
  activeTaskPlan = plan;
  activeTaskPlan.status = "scheduled";
  const now = Date.now();
  for (const task of activeTaskPlan.tasks) {
    task.executeAt = now + task.delaySec * 1000;
    if (task.delaySec <= 0) {
      runPlannedTask(activeTaskPlan, task);
    } else {
      const timer = setTimeout(() => {
        taskTimers.delete(task.id);
        runPlannedTask(activeTaskPlan, task);
      }, task.delaySec * 1000);
      taskTimers.set(task.id, timer);
      pushLog("qwen-task", `scheduled ${task.id} in ${task.delaySec}s`);
    }
  }
  recordPreferenceEvent("qwen_plan", { plan: taskPlanForClient(activeTaskPlan) });
  updateTaskPlanState();
  broadcast();
  return { applied: true, dryRun: false, plan: state.taskPlan };
}

app.put("/api/settings", (req, res) => {
  settings = mergeSettings(settings, req.body || {});
  saveSettings();
  broadcast();
  res.json({ ok: true, settings });
});

app.post("/api/appearance", (req, res) => {
  const { language, background, accent } = req.body || {};
  if (["zh", "en"].includes(language)) settings.language = language;
  if (["aurora", "deep", "sunrise", "matrix", "neural", "hologrid", "cosmos", "thermal", "mono"].includes(background)) {
    settings.background = background;
  }
  if (["cyan", "blue", "violet", "green", "rose"].includes(accent)) settings.accent = accent;
  saveSettings();
  broadcast();
  res.json({ ok: true, settings });
});

app.post("/api/config", (req, res) => {
  const auto = applyConfig(req.body || settings.auto, "config");
  settings.activePreset = req.body?.preset || settings.activePreset;
  saveSettings();
  res.json({ ok: true, auto, commands: buildConfigCommands(auto) });
});

app.post("/api/reapply", (_req, res) => {
  queueCommands(buildConfigCommands(settings.auto), "reapply");
  if (settings.manual.enabled) queueCommands(buildManualCommands(settings.manual), "reapply");
  res.json({ ok: true, settings });
});

app.post("/api/preset/:id", (req, res) => {
  const preset = PRESETS.find((item) => item.id === req.params.id);
  if (!preset) {
    res.status(404).json({ ok: false, error: "preset_not_found" });
    return;
  }
  settings.activePreset = preset.id;
  const auto = applyConfig(preset.auto, "preset");
  saveSettings();
  res.json({ ok: true, preset: preset.id, auto });
});

app.post("/api/manual", (req, res) => {
  const manual = applyManual(req.body || settings.manual, "manual");
  res.json({ ok: true, manual, commands: buildManualCommands(manual) });
});

app.post("/api/auto", (_req, res) => {
  const manual = applyManual({ ...settings.manual, enabled: false, buzzer: false }, "manual");
  res.json({ ok: true, manual });
});

app.post("/api/strategies", (req, res) => {
  const id = String(req.body?.id || req.body?.name || `custom-${Date.now()}`)
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 48);
  const strategy = {
    id: id || `custom-${Date.now()}`,
    name: String(req.body?.name || "Custom Strategy").slice(0, 40),
    description: String(req.body?.description || "").slice(0, 120),
    auto: sanitizeAuto(req.body?.auto || settings.auto)
  };
  const index = settings.customStrategies.findIndex((item) => item.id === strategy.id);
  if (index >= 0) settings.customStrategies[index] = strategy;
  else settings.customStrategies.push(strategy);
  saveSettings();
  broadcast();
  res.json({ ok: true, strategy, settings });
});

app.delete("/api/strategies/:id", (req, res) => {
  settings.customStrategies = settings.customStrategies.filter((item) => item.id !== req.params.id);
  saveSettings();
  broadcast();
  res.json({ ok: true, settings });
});

app.post("/api/strategies/:id/apply", (req, res) => {
  const strategy = settings.customStrategies.find((item) => item.id === req.params.id);
  if (!strategy) {
    res.status(404).json({ ok: false, error: "strategy_not_found" });
    return;
  }
  settings.activePreset = strategy.id;
  const auto = applyConfig(strategy.auto, "strategy");
  saveSettings();
  res.json({ ok: true, strategy: strategy.id, auto });
});

app.post("/api/simulate/:scenario", (req, res) => {
  const scenario = req.params.scenario;
  const base = {
    device: "edge1",
    mode: "NORMAL",
    pir: 1,
    occupied: 1,
    light: 260,
    dark: 1,
    temperatureC: 25.2,
    temperatureSource: "SIM",
    esp32AdcTempC: 25.2,
    esp32AdcMv: 252,
    esp32AdcValid: 1,
    temp10: 252,
    gas: 82,
    gasDanger: 0,
    flameDigital: 1,
    flameAnalog: 1015,
    flameDetected: 0,
    demoEmergency: 0,
    safetyAlarm: 0,
    fan: 0,
    pwm: 0,
    rpm: 0,
    lamp: 1,
    manual: 0,
    fanOnC: settings.auto.fanOnC,
    fanOffC: settings.auto.fanOffC,
    ledMax: settings.auto.ledMax,
    statusMax: settings.auto.statusMax,
    statusLight: "G",
    raw: "SIMULATED"
  };

  if (scenario === "cooling") {
    Object.assign(base, { mode: "COOLING", temperatureC: 29.1, temp10: 291, fan: 1, pwm: 160, rpm: 1900, statusLight: "Y" });
  } else if (scenario === "safety") {
    Object.assign(base, { mode: "SAFETY_ALARM", gas: 520, gasDanger: 1, safetyAlarm: 1, fan: 1, pwm: 255, rpm: 3200, lamp: 1, statusLight: "R" });
  } else if (scenario === "offline") {
    handleTopic(`${TOPIC_PREFIX}/status`, Buffer.from("uno_offline"));
    res.json({ ok: true, scenario });
    return;
  }

  handleTopic(TOPIC_TELEMETRY, Buffer.from(JSON.stringify(base)));
  res.json({ ok: true, scenario });
});

app.post("/api/command/:command", (req, res) => {
  const command = commandForVoiceKey(req.params.command) || req.body?.command || req.params.command;
  queueCommands(command, "command");
  res.json({ ok: true, command, queued: commandQueue.length });
});

let httpsServer = null;

setInterval(broadcast, 1000);

async function startServers() {
  httpsServer = https.createServer(await ensureHttpsCertificate(), app);
  attachWebSocket(httpsServer);

  mqttServer.listen(MQTT_PORT, HOST, () => {
    console.log(`MQTT broker listening on mqtt://${HOST}:${MQTT_PORT}`);
  });

  httpServer.listen(WEB_PORT, HOST, () => {
    console.log(`Dashboard listening on http://localhost:${WEB_PORT}`);
    console.log(`LAN dashboard: http://<this-laptop-ip>:${WEB_PORT}`);
    setTimeout(() => queueCommands(buildConfigCommands(settings.auto), "restore"), 1500);
  });

  httpsServer.listen(WEB_HTTPS_PORT, HOST, () => {
    console.log(`Secure dashboard for LAN microphones: https://localhost:${WEB_HTTPS_PORT}`);
    for (const address of getLanAddresses()) {
      console.log(`Secure LAN dashboard: https://${address}:${WEB_HTTPS_PORT}`);
    }
  });
}

startServers().catch((error) => {
  console.error("Failed to start dashboard:", error);
  process.exit(1);
});

process.on("SIGINT", () => {
  console.log("Shutting down...");
  mqttServer.close();
  httpServer.close();
  if (httpsServer) httpsServer.close();
  aedes.close(() => process.exit(0));
});
