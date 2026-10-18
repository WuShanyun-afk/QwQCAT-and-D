// dsh-xiaod-ledger · 纯逻辑（价格 / 时间 / 金额 / 账本读写）
// 不依赖 cordis，可单独用 node 测试：node --test 或 import 本文件。

import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'

/* ---------------- 金额 ---------------- */

/** 统一保留 4 位小数（JS 浮点误差用） */
export function round4(x) {
  const n = Number(x)
  if (!Number.isFinite(n)) return 0
  return Math.round(n * 10000) / 10000
}

/** 元，两位小数字符串 */
export function fmtMoney(x) {
  const n = Number(x)
  if (!Number.isFinite(n)) return '--'
  return (Math.round(n * 100) / 100).toFixed(2)
}

/* ---------------- 北京时间 / 峰谷 ---------------- */

export function beijingParts(ts) {
  const n = Number(ts) || Date.now()
  const d = new Date(n + 8 * 3600 * 1000)
  return {
    y: d.getUTCFullYear(),
    m: d.getUTCMonth() + 1,
    d: d.getUTCDate(),
    dow: d.getUTCDay(), // 0=周日
    hour: d.getUTCHours(),
    minute: d.getUTCMinutes(),
  }
}

export function beijingDay(ts) {
  const p = beijingParts(ts)
  const pad = (v) => String(v).padStart(2, '0')
  return `${p.y}-${pad(p.m)}-${pad(p.d)}`
}

export function beijingClock(ts) {
  const n = Number(ts) || Date.now()
  const d = new Date(n + 8 * 3600 * 1000)
  const pad = (v) => String(v).padStart(2, '0')
  return `${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())}`
}

// 峰谷定价：北京时间周一至周五 9:00–12:00、14:00–18:00 为高峰，
// 其余（含周末）为谷时。法定节假日按谷时（2026 年清单）。
const WEEKEND_VALLEY_FROM_SEC = Math.floor(Date.UTC(2026, 7, 22, 16, 0, 0) / 1000)
const HOLIDAY_VALLEY_FROM_SEC = Math.floor(Date.UTC(2026, 8, 18, 16, 0, 0) / 1000)
export const HOLIDAY_VALLEY = {
  '2026-01-01': 1, '2026-01-02': 1, '2026-01-03': 1,
  '2026-02-15': 1, '2026-02-16': 1, '2026-02-17': 1, '2026-02-18': 1, '2026-02-19': 1,
  '2026-02-20': 1, '2026-02-21': 1, '2026-02-22': 1, '2026-02-23': 1,
  '2026-04-04': 1, '2026-04-05': 1, '2026-04-06': 1,
  '2026-05-01': 1, '2026-05-02': 1, '2026-05-03': 1, '2026-05-04': 1, '2026-05-05': 1,
  '2026-06-19': 1, '2026-06-20': 1, '2026-06-21': 1,
  '2026-09-25': 1, '2026-09-26': 1, '2026-09-27': 1,
  '2026-10-01': 1, '2026-10-02': 1, '2026-10-03': 1, '2026-10-04': 1,
  '2026-10-05': 1, '2026-10-06': 1, '2026-10-07': 1,
}

export function isPeakTime(timeSec) {
  const n = Number(timeSec)
  if (!Number.isFinite(n)) return false
  const p = beijingParts(n * 1000)
  if (n >= WEEKEND_VALLEY_FROM_SEC && (p.dow === 0 || p.dow === 6)) return false
  const day = `${p.y}-${String(p.m).padStart(2, '0')}-${String(p.d).padStart(2, '0')}`
  if (n >= HOLIDAY_VALLEY_FROM_SEC && HOLIDAY_VALLEY[day]) return false
  const h = p.hour
  return (h >= 9 && h < 12) || (h >= 14 && h < 18)
}

/* ---------------- 价格表（元 / 百万 token） ---------------- */
// 官方 2026-09 价：Flash 缓存命中 0.02 / 未命中 1 / 输出 4；Pro 为 Flash 的 3 倍。
const FLASH = { hit: [0.02, 0.04], miss: [1, 2], out: [4, 8] }
const PRO = { hit: [0.15, 0.3], miss: [4.5, 9], out: [13.5, 27] }

export function priceFor(model) {
  const m = String(model || '').toLowerCase()
  if (m.indexOf('pro') !== -1) return PRO
  return FLASH
}

/** 一轮的金额（元）：usage = { inputTokens, cacheReadTokens, outputTokens } */
export function turnCost(usage, model, ts) {
  const peak = isPeakTime(Math.floor((Number(ts) || Date.now()) / 1000)) ? 1 : 0
  const p = priceFor(model)
  const input = Number(usage && usage.inputTokens) || 0
  const cache = Number(usage && usage.cacheReadTokens) || 0
  const output = Number(usage && usage.outputTokens) || 0
  const cost = (cache / 1e6) * p.hit[peak]
    + (input / 1e6) * p.miss[peak]
    + (output / 1e6) * p.out[peak]
  return {
    cost: round4(cost),
    tokens: input + cache + output,
    peak: peak === 1,
  }
}

/* ---------------- 账本文件 ---------------- */

export const MAX_ENTRIES = 2000
export const KEEP_DAYS = 180

export function freshLedger() {
  return { version: 1, createdAt: Date.now(), entries: [], balance: null }
}

/** 清理：只留最近 KEEP_DAYS 天、最多 MAX_ENTRIES 条 */
export function pruneLedger(ledger, now = Date.now()) {
  if (!ledger || !Array.isArray(ledger.entries)) return freshLedger()
  const cutoff = now - KEEP_DAYS * 86400 * 1000
  const list = ledger.entries
    .filter((e) => e && Number(e.ts) >= cutoff)
    .sort((a, b) => Number(a.ts) - Number(b.ts))
    .slice(-MAX_ENTRIES)
  return { ...ledger, entries: list }
}

/** 读账本：坏文件先改名备份再用新账本，绝不让它锁死插件 */
export function readLedger(file) {
  try {
    const raw = fs.readFileSync(file, 'utf8')
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object' || !Array.isArray(parsed.entries)) {
      backupCorrupt(file, 'bad-structure')
      return freshLedger()
    }
    return pruneLedger(parsed)
  } catch (err) {
    if (err && err.code === 'ENOENT') return freshLedger()
    backupCorrupt(file, (err && err.code) || 'read-error')
    return freshLedger()
  }
}

export function backupCorrupt(file, why) {
  try {
    const bak = file + '.corrupt-' + Date.now() + '.bak'
    fs.renameSync(file, bak)
    console.warn('[xiaod-ledger] 账本损坏（' + why + '）→ 已备份到 ' + bak)
  } catch (err) {
    console.warn('[xiaod-ledger] 账本损坏且备份失败：' + String((err && err.message) || err))
  }
}

export function writeLedger(file, ledger) {
  try {
    fs.mkdirSync(path.dirname(file), { recursive: true })
    const tmp = file + '.tmp-' + process.pid
    fs.writeFileSync(tmp, JSON.stringify(pruneLedger(ledger)), 'utf8')
    fs.renameSync(tmp, file)
    return true
  } catch (err) {
    console.warn('[xiaod-ledger] 写账本失败：' + String((err && err.message) || err))
    return false
  }
}

/** 汇总：今天 / 全部 */
export function summarize(ledger, now = Date.now()) {
  const today = beijingDay(now)
  let todayCost = 0
  let todayTurns = 0
  let todayTokens = 0
  let totalCost = 0
  let totalTurns = 0
  let totalTokens = 0
  for (const e of (ledger && ledger.entries) || []) {
    const c = Number(e.cost) || 0
    const tk = Number(e.tokens) || 0
    totalCost += c
    totalTurns += 1
    totalTokens += tk
    if (e.date === today) {
      todayCost += c
      todayTurns += 1
      todayTokens += tk
    }
  }
  return {
    today: round4(todayCost),
    todayTurns,
    todayTokens,
    total: round4(totalCost),
    totalTurns,
    totalTokens,
    currency: 'CNY',
  }
}

/** 最近 n 条（新→旧） */
export function recentEntries(ledger, n = 40) {
  const list = (ledger && ledger.entries) || []
  return list.slice(-n).reverse().map((e) => ({
    ts: e.ts,
    clock: beijingClock(e.ts),
    cost: round4(e.cost),
    tokens: Number(e.tokens) || 0,
    model: e.model || '',
    turn: e.turn,
  }))
}

export function ledgerPath(dshHome) {
  return path.join(dshHome || path.join(os.homedir(), '.dsh'), 'xiaod-ledger', 'ledger.json')
}
