// dsh-xiaod-ledger · Host 半
// 小D记账：显示 DeepSeek 余额 + 按每轮真实 usage 记账（今日 / 累计 / 账本明细）。
// 设计原则：宿主半只做「路由 + 事件监听 + 读写文件」；任何服务都按可选处理，
// 绝不把可选服务写进 inject，也绝不让异常把 DSH 的启动卡住（apply 全程 try/catch）。

import fs from 'node:fs'
import path from 'node:path'
import os from 'node:os'
import { fileURLToPath } from 'node:url'
import {
  beijingDay, beijingClock, round4, turnCost, isPeakTime,
  readLedger, writeLedger, summarize, recentEntries, freshLedger,
} from './core.js'

const PACKAGE_ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const DSH_HOME = process.env.DSH_HOME || path.join(os.homedir(), '.dsh')
const DATA_DIR = path.join(DSH_HOME, 'xiaod-ledger')
const LEDGER_FILE = path.join(DATA_DIR, 'ledger.json')
const CONFIG_FILE = path.join(DATA_DIR, 'config.json')
const PREFIX = '/dsh-xiaod'
const LEDGER_FILE_ALT = path.join(DSH_HOME, 'xiaod-ledger.json')

const JSON_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'Cache-Control': 'no-store',
}

const WIDGET_CANDIDATES = [
  path.join(PACKAGE_ROOT, 'lib', 'widget.js'),
  path.join(PACKAGE_ROOT, 'widget.js'),
]
const CHARACTER_CANDIDATES = [
  path.join(PACKAGE_ROOT, 'assets', 'character.png'),
  path.join(DATA_DIR, 'character.png'),
]

/* ---------------- 小工具 ---------------- */

function readConfig() {
  try {
    const c = JSON.parse(fs.readFileSync(CONFIG_FILE, 'utf8'))
    return c && typeof c === 'object' ? c : {}
  } catch (err) { return {} }
}

function readFileCached(candidates, cache) {
  for (const p of candidates) {
    try {
      const st = fs.statSync(p)
      if (cache && cache.mtimeMs === st.mtimeMs && cache.path === p) return cache.bytes
      const bytes = fs.readFileSync(p)
      if (bytes && bytes.length) return { bytes, mtimeMs: st.mtimeMs, path: p }
    } catch (err) { /* 试下一个 */ }
  }
  return null
}

/* ---------------- 账本（内存 + 文件） ---------------- */

let ledger = null
function getLedger() {
  if (!ledger) {
    ledger = readLedger(LEDGER_FILE)
    // 兼容旧路径：第一次找不到时试 $DSH_HOME/xiaod-ledger.json
    if ((!ledger.entries || ledger.entries.length === 0) && fs.existsSync(LEDGER_FILE_ALT)) {
      try {
        const alt = JSON.parse(fs.readFileSync(LEDGER_FILE_ALT, 'utf8'))
        if (alt && Array.isArray(alt.entries) && alt.entries.length) ledger = alt
      } catch (err) { /* 忽略 */ }
    }
  }
  return ledger
}
function saveLedger() {
  try { writeLedger(LEDGER_FILE, getLedger()) } catch (err) { /* 不抛 */ }
}

/* ---------------- 余额 ---------------- */

let balanceCache = null // { value, at, error }
const BALANCE_TTL_MS = 25000
const BALANCE_ERR_TTL_MS = 12000
let balanceInFlight = null

function walletSum(list) {
  const arr = Array.isArray(list) ? list : []
  return arr.map((w) => ({
    balance: Number(w && w.balance),
    currency: String((w && w.currency) || 'CNY').toUpperCase(),
  })).filter((w) => Number.isFinite(w.balance))
}

async function fetchBalance(ctx) {
  const out = { value: null, error: null }
  /* 1) DSH 账号登录态（最常用：只登录客户端、没有 API key） */
  try {
    const account = typeof ctx.get === 'function' ? ctx.get('deepseekAccount') : null
    if (account && typeof account.getBalance === 'function') {
      const result = await account.getBalance({
        version: String(process.env.DSH_CLIENT_VERSION || process.env.DSH_VERSION || '') || 'unknown',
        locale: String(process.env.DSH_LOCALE || '') || 'zh_CN',
        timezoneOffsetSeconds: -new Date().getTimezoneOffset() * 60,
      })
      if (result && result.status === 'ready') {
        const wallets = walletSum(result.value).concat(walletSum(result.bonusWallets))
        if (wallets.length) {
          const nonzero = wallets.filter((w) => w.balance > 0)
          const pick = nonzero.find((w) => w.currency === 'CNY') || nonzero[0]
            || wallets.find((w) => w.currency === 'CNY') || wallets[0]
          const sameCur = wallets.filter((w) => w.currency === pick.currency)
          const total = sameCur.reduce((s, w) => s + w.balance, 0)
          return {
            value: {
              total: round4(total),
              currency: pick.currency,
              source: 'account',
              updatedAt: new Date().toISOString(),
            },
          }
        }
        out.error = '账号里没有可用的余额钱包'
      } else {
        out.error = '账号余额未就绪（' + String((result && result.status) || 'unknown') + '）'
      }
    } else {
      out.error = '当前 DSH 没有账号余额服务'
    }
  } catch (err) {
    out.error = '账号余额读取失败：' + String((err && err.message) || err).slice(0, 120)
  }

  /* 2) API key 兜底 */
  try {
    const credSvc = typeof ctx.get === 'function' ? ctx.get('credentials') : null
    if (credSvc && typeof credSvc.resolve === 'function') {
      const cred = await credSvc.resolve('DEEPSEEK_API_KEY')
      if (cred && cred.value) {
        const res = await fetch('https://api.deepseek.com/user/balance', {
          headers: { Authorization: 'Bearer ' + cred.value },
          signal: AbortSignal.timeout(8000),
        })
        if (res.ok) {
          const data = await res.json()
          const list = Array.isArray(data && data.balance_infos) ? data.balance_infos : []
          const pick = list.find((x) => x && x.currency === 'CNY' && Number(x.total_balance) > 0)
            || list.find((x) => Number(x && x.total_balance) > 0) || list[0]
          if (pick && Number.isFinite(Number(pick.total_balance))) {
            return {
              value: {
                total: round4(Number(pick.total_balance)),
                currency: String(pick.currency || 'CNY'),
                source: 'apikey',
                updatedAt: new Date().toISOString(),
              },
            }
          }
          out.error = '余额接口返回结构异常'
        } else {
          out.error = '余额接口 HTTP ' + res.status
        }
      }
    }
  } catch (err) { /* API key 路失败不覆盖账号路的错误文案 */ }

  return out
}

async function getBalance(ctx, force) {
  const now = Date.now()
  if (!force && balanceCache) {
    const ttl = balanceCache.value ? BALANCE_TTL_MS : BALANCE_ERR_TTL_MS
    if (now - balanceCache.at < ttl) return balanceCache
  }
  if (balanceInFlight) return balanceInFlight
  balanceInFlight = (async () => {
    let r = null
    try { r = await fetchBalance(ctx) } catch (err) {
      r = { value: null, error: '余额读取异常：' + String((err && err.message) || err).slice(0, 120) }
    }
    balanceCache = { at: Date.now(), value: r && r.value ? r.value : null, error: r && r.error ? r.error : null }
    if (r && r.value) {
      try {
        const lg = getLedger()
        lg.balance = r.value
        saveLedger()
      } catch (err) { /* 忽略 */ }
    }
    balanceInFlight = null
    return balanceCache
  })()
  return balanceInFlight
}

/* ---------------- 每轮 usage 聚合 ---------------- */

const turnAggs = new Map() // sessionId -> { turn, cost, tokens, model, ts }
let lastTurn = null

function finalizeTurn(sessionId) {
  const agg = turnAggs.get(sessionId)
  if (agg && agg.cost > 0) {
    const entry = {
      ts: Date.now(),
      date: beijingDay(),
      sid: String(sessionId || 'default').slice(0, 80),
      turn: agg.turn,
      model: agg.model || '',
      tokens: agg.tokens,
      cost: round4(agg.cost),
      currency: 'CNY',
    }
    const lg = getLedger()
    lg.entries.push(entry)
    lastTurn = { cost: entry.cost, tokens: entry.tokens, model: entry.model, turn: entry.turn, ts: entry.ts }
    saveLedger()
  }
  turnAggs.delete(sessionId)
}

function handleSessionEvent(sessionId, event) {
  try {
    const type = event && event.type
    const d = (event && event.data) || {}
    if (!d || typeof d !== 'object') return
    if (type === 'turn/end') { finalizeTurn(sessionId); return }
    if (type !== 'assistant/message') return
    const turn = Number(d.turn)
    const usage = d.usage
    if (!usage || typeof usage !== 'object' || !Number.isFinite(turn)) return
    const model = (d.message && d.message.source && d.message.source.model) || ''
    const c = turnCost(usage, model, Date.now())
    let agg = turnAggs.get(sessionId)
    if (!agg || agg.turn !== turn) {
      if (agg) finalizeTurn(sessionId)
      agg = { turn, cost: 0, tokens: 0, model, ts: Date.now() }
      turnAggs.set(sessionId, agg)
    }
    agg.cost = round4(agg.cost + c.cost)
    agg.tokens += c.tokens
    if (model) agg.model = model
    agg.ts = Date.now()
  } catch (err) { /* 事件解析失败不能影响会话 */ }
}

/* ---------------- 请求守卫 ---------------- */

function isLoopback(hostname) {
  const h = String(hostname || '').toLowerCase().replace(/^\[/, '').replace(/\]$/, '')
  if (!h) return false
  if (h === 'localhost' || h.endsWith('.localhost') || h === '::1') return true
  const m = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/.exec(h)
  if (!m) return false
  return Number(m[1]) === 127 && [m[2], m[3], m[4]].every((x) => Number(x) <= 255)
}

function guard(req, res) {
  try {
    const headers = req.headers || {}
    let host = ''
    try { host = new URL('http://' + String(headers.host || '')).hostname } catch (err) { host = '' }
    if (!isLoopback(host)) {
      const trusted = String(process.env.DSH_XIAOD_TRUSTED_HOSTS || '')
        .split(',').map((s) => s.trim().toLowerCase()).filter(Boolean)
      if (!trusted.includes(host.toLowerCase())) {
        res.writeHead(403); res.end('forbidden'); return false
      }
    }
    if (String(headers['sec-fetch-site'] || '').toLowerCase() === 'cross-site') {
      res.writeHead(403); res.end('forbidden'); return false
    }
    return true
  } catch (err) {
    try { res.writeHead(403); res.end('forbidden') } catch (e) { /* 忽略 */ }
    return false
  }
}

/* ---------------- 插件本体 ---------------- */

export default {
  name: 'dsh-xiaod-ledger',
  apply(root) {
    // 启动标记：方便确认插件真的被加载了（重启 DSH 后看这个文件的时间戳）
    try {
      console.log('[xiaod-ledger] plugin loaded (v0.1.0)')
      fs.mkdirSync(DATA_DIR, { recursive: true })
      fs.writeFileSync(path.join(DATA_DIR, 'loaded.json'),
        JSON.stringify({ at: new Date().toISOString(), pid: process.pid, version: '0.1.0' }), 'utf8')
    } catch (err) { /* 忽略 */ }

    // ① 桌面端注入行：宿主启动时一次性收集 → 页面侧按行插入 <script>。
    //    用内联 script 行 + 自己吞 onerror，插件被关掉时最多静默，不会卡住启动。
    try {
      root.on('webserver/index-inject', (table) => {
        try {
          if (!Array.isArray(table)) return
          const ROW = '(function(){try{var d=document.body||document.head||document.documentElement;'
            + 'if(!d)return;if(document.getElementById("dxl-root"))return;'
            + 'var s=document.createElement("script");s.src="' + PREFIX + '/widget.js";'
            + 's.onerror=function(){};d.appendChild(s)}catch(e){}})()'
          for (const row of table) {
            if (row && row.kind === 'script' && typeof row.text === 'string' && row.text.indexOf(PREFIX + '/widget.js') >= 0) return
            if (row && row.kind === 'script-src' && row.src === PREFIX + '/widget.js') return
          }
          table.push({ kind: 'script', placement: 'body', text: ROW })
        } catch (err) { /* 忽略 */ }
      })
    } catch (err) { /* 忽略 */ }

    // ② 路由 + 事件：等 webServer 就绪（只 inject 必需服务）
    root.inject(['webServer'], (ctx) => {
      const disposers = []
      try {
        // 事件监听
        try {
          disposers.push(ctx.on('session/event', (session, event) => {
            const sid = (session && session.id) || 'default'
            handleSessionEvent(String(sid), event)
          }))
        } catch (err) { /* 忽略 */ }
        try {
          disposers.push(ctx.on('session/disposed', (session) => {
            if (session && session.id) turnAggs.delete(String(session.id))
          }))
        } catch (err) { /* 忽略 */ }

        /* ---------- widget.js ---------- */
        let widgetCache = null
        disposers.push(ctx.webServer.register({
          kind: 'exact',
          path: PREFIX + '/widget.js',
          handler: (req, res) => {
            if (!guard(req, res)) return
            const f = readFileCached(WIDGET_CANDIDATES, widgetCache)
            widgetCache = f
            if (!f) { res.writeHead(404); res.end('widget.js not found'); return }
            res.writeHead(200, {
              'Content-Type': 'application/javascript; charset=utf-8',
              'Cache-Control': 'no-store',
              'Content-Length': String(f.bytes.length),
            })
            res.end(f.bytes)
          },
        }))

        /* ---------- character.png ---------- */
        let charCache = null
        disposers.push(ctx.webServer.register({
          kind: 'exact',
          path: PREFIX + '/character.png',
          handler: (req, res) => {
            if (!guard(req, res)) return
            const cfg = readConfig()
            const cands = [cfg.character, ...CHARACTER_CANDIDATES].filter(Boolean)
            const f = readFileCached(cands, charCache)
            charCache = f
            if (!f) { res.writeHead(404); res.end('character not found'); return }
            res.writeHead(200, {
              'Content-Type': 'image/png',
              'Cache-Control': 'no-store',
              'Content-Length': String(f.bytes.length),
            })
            res.end(f.bytes)
          },
        }))

        /* ---------- state ---------- */
        disposers.push(ctx.webServer.register({
          kind: 'exact',
          path: PREFIX + '/state',
          handler: async (req, res) => {
            if (!guard(req, res)) return
            try {
              const force = /(?:^\?|&)force=1(?:&|$)/.test(String(req.url || ''))
              const lg = getLedger()
              const sum = summarize(lg)
              const bal = await getBalance(ctx, force)
              const payload = {
                ok: true,
                now: new Date().toISOString(),
                balance: bal.value,
                balanceError: bal.value ? null : bal.error,
                today: {
                  cost: sum.today,
                  turns: sum.todayTurns,
                  tokens: sum.todayTokens,
                },
                total: {
                  cost: sum.total,
                  turns: sum.totalTurns,
                  tokens: sum.totalTokens,
                },
                lastTurn,
                clock: beijingClock(),
                day: beijingDay(),
                peak: isPeakTime(Math.floor(Date.now() / 1000)),
                entries: recentEntries(lg, 40),
              }
              res.writeHead(200, JSON_HEADERS)
              res.end(JSON.stringify(payload))
            } catch (err) {
              res.writeHead(200, JSON_HEADERS)
              res.end(JSON.stringify({ ok: false, error: String((err && err.message) || err) }))
            }
          },
        }))

        /* ---------- 健康检查 / 版本 ---------- */
        disposers.push(ctx.webServer.register({
          kind: 'exact',
          path: PREFIX + '/ping',
          handler: (req, res) => {
            if (!guard(req, res)) return
            res.writeHead(200, JSON_HEADERS)
            res.end(JSON.stringify({ ok: true, plugin: 'dsh-xiaod-ledger', v: '0.1.0' }))
          },
        }))

        /* ---------- web 形态兜底：tapIndex 注入 ---------- */
        try {
          disposers.push(ctx.webServer.tapIndex((html) => {
            if (typeof html !== 'string') return html
            if (html.indexOf(PREFIX + '/widget.js') !== -1) return html
            const tag = '<script defer src="' + PREFIX + '/widget.js"></script>'
            if (html.indexOf('</body>') !== -1) return html.replace('</body>', tag + '</body>')
            return html + tag
          }))
        } catch (err) { /* 桌面端没有 tapIndex，正常 */ }

        try {
          fs.writeFileSync(path.join(DATA_DIR, 'routes.json'),
            JSON.stringify({ at: new Date().toISOString(), routes: ['widget.js', 'character.png', 'state', 'ping'] }), 'utf8')
          console.log('[xiaod-ledger] routes ready: /dsh-xiaod/{widget.js,character.png,state,ping}')
        } catch (err) { /* 忽略 */ }

        try {
          ctx.effect(() => () => {
            for (const d of disposers) { try { d() } catch (err) { /* 忽略 */ } }
          })
        } catch (err) { /* 忽略 */ }
      } catch (err) {
        console.warn('[xiaod-ledger] 路由注册失败：' + String((err && err.message) || err))
      }
    })
  },
}

/* 给本地测试用：node --test 或脚本 import 这些纯逻辑 */
export const __test = {
  round4, beijingDay, beijingClock, isPeakTime, turnCost,
  summarize, recentEntries, freshLedger,
}

