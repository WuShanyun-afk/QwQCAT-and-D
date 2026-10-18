import assert from 'node:assert'
import {
  beijingDay, beijingClock, isPeakTime, priceFor, turnCost,
  round4, fmtMoney, summarize, recentEntries, readLedger, writeLedger, freshLedger, pruneLedger,
} from './lib/core.js'
import plugin from './lib/index.js'

// 1) 北京时间
assert.equal(beijingDay(Date.UTC(2026, 9, 18, 4, 0, 0)), '2026-10-18') // 12:00 北京
assert.equal(beijingClock(Date.UTC(2026, 9, 18, 4, 5, 0)), '12:05')

// 2) 峰谷：2026-10-18 是周日 → 谷时；10-19 周一 10:00 北京 → 高峰
assert.equal(isPeakTime(Math.floor(Date.UTC(2026, 9, 18, 2, 0, 0) / 1000)), false) // 周日 10:00
assert.equal(isPeakTime(Math.floor(Date.UTC(2026, 9, 19, 2, 0, 0) / 1000)), true)  // 周一 10:00
assert.equal(isPeakTime(Math.floor(Date.UTC(2026, 9, 19, 5, 0, 0) / 1000)), false) // 周一 13:00
assert.equal(isPeakTime(Math.floor(Date.UTC(2026, 9, 1, 2, 0, 0) / 1000)), false)  // 国庆 10:00 谷价
assert.equal(priceFor('deepseek-v4-pro'), priceFor('DeepSeek-V4-Pro'))
assert.notEqual(priceFor('deepseek-v4-pro'), priceFor('deepseek-flash'))

// 3) 费用：flash 谷时 100 万 input + 100 万 output + 100 万 cache
const c = turnCost({ inputTokens: 1e6, cacheReadTokens: 1e6, outputTokens: 1e6 }, 'deepseek-flash', Date.UTC(2026, 9, 18, 2, 0, 0))
assert.equal(c.peak, false)
assert.equal(c.cost, round4(1 + 4 + 0.02)) // 5.02 元
assert.equal(c.tokens, 3e6)
const cp = turnCost({ inputTokens: 1e6, cacheReadTokens: 0, outputTokens: 1e6 }, 'deepseek-flash', Date.UTC(2026, 9, 19, 2, 0, 0))
assert.equal(cp.peak, true)
assert.equal(cp.cost, round4(2 + 8))

// 4) 汇总 / 最近记录
const now = Date.UTC(2026, 9, 18, 4, 0, 0)
const led = { version: 1, entries: [
  { ts: now - 1000, date: '2026-10-18', cost: 0.1, tokens: 100, model: 'deepseek-flash', turn: 1 },
  { ts: now - 2000, date: '2026-10-17', cost: 0.2, tokens: 200, model: 'deepseek-flash', turn: 2 },
  { ts: now - 3000, date: '2026-10-18', cost: 0.3, tokens: 300, model: 'deepseek-v4-pro', turn: 3 },
] }
const s = summarize(led, now)
assert.equal(s.today, round4(0.4))
assert.equal(s.todayTurns, 2)
assert.equal(s.total, round4(0.6))
assert.equal(s.totalTurns, 3)
const rec = recentEntries(led, 2)
assert.equal(rec.length, 2)
assert.equal(rec[0].turn, 3)

// 5) 金额格式
assert.equal(fmtMoney(0.004), '0.00')
assert.equal(fmtMoney(93.269), '93.27')

// 6) 账本：坏文件不会炸
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'
const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'dxl-'))
const f = path.join(dir, 'ledger.json')
fs.writeFileSync(f, '{not json', 'utf8')
const r = readLedger(f)
assert.ok(Array.isArray(r.entries) && r.entries.length === 0)
assert.ok(fs.readdirSync(dir).some((n) => n.indexOf('corrupt') !== -1), '坏文件应被备份')
assert.ok(writeLedger(f, led))
const r2 = readLedger(f)
assert.equal(r2.entries.length, 3)

// 7) prune 保留上限
const big = { version: 1, entries: Array.from({ length: 2500 }, (_, i) => ({ ts: now - i * 1000, date: '2026-10-18', cost: 0.001, tokens: 10 })) }
assert.equal(pruneLedger(big, now).entries.length, 2000)

// 8) 插件导出形状
assert.equal(plugin.name, 'dsh-xiaod-ledger')
assert.equal(typeof plugin.apply, 'function')

console.log('ALL TESTS PASSED ✅')
