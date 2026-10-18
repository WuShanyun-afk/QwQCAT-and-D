/* dsh-xiaod-ledger · 浏览器挂件（小D记账）
 * 由 Host 半注入的 <script> 加载；不依赖任何框架，自己建 DOM。
 * 数据来自 /dsh-xiaod/state。 */
(function () {
  'use strict'
  try {
    if (window.__dshXiaodLedgerInit) return
    window.__dshXiaodLedgerInit = true

    var API = '/dsh-xiaod/state'
    var IMG = '/dsh-xiaod/character.png'
    var POLL_MS = 12000
    var LS_POS = 'dxl-pos'
    var LS_OPEN = 'dxl-open'

    var css = ''
      + '#dxl-root{position:fixed;z-index:2147483000;right:22px;bottom:206px;font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif;'
      + 'color:#4c3a50;-webkit-font-smoothing:antialiased;user-select:none;touch-action:none;}'
      + '#dxl-root *{box-sizing:border-box;}'
      + '.dxl-card{display:flex;align-items:center;gap:10px;padding:9px 13px 9px 9px;border-radius:18px;cursor:grab;'
      + 'background:linear-gradient(145deg,rgba(255,251,253,.97),rgba(252,240,247,.95));'
      + 'border:1px solid rgba(255,255,255,.9);box-shadow:0 10px 32px rgba(126,92,140,.20),inset 0 1px 0 rgba(255,255,255,.95);'
      + 'backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);transition:transform .16s ease,box-shadow .2s ease;}'
      + '.dxl-card:hover{transform:translateY(-2px);box-shadow:0 14px 38px rgba(126,92,140,.26),inset 0 1px 0 rgba(255,255,255,.95);}'
      + '.dxl-card.dxl-dragging{cursor:grabbing;transform:none;}'
      + '.dxl-char{width:62px;height:62px;object-fit:contain;pointer-events:none;filter:drop-shadow(0 4px 8px rgba(120,90,140,.22));flex:0 0 auto;}'
      + '.dxl-info{display:flex;flex-direction:column;gap:2px;min-width:108px;}'
      + '.dxl-top{display:flex;align-items:center;gap:5px;font-size:11px;letter-spacing:1.2px;color:#8d7a94;}'
      + '.dxl-dot{width:7px;height:7px;border-radius:50%;background:#7ed6a5;box-shadow:0 0 0 3px rgba(126,214,165,.18);flex:0 0 auto;}'
      + '.dxl-dot.bad{background:#f0b36b;box-shadow:0 0 0 3px rgba(240,179,107,.18);}'
      + '.dxl-balance{font-size:20px;font-weight:700;line-height:1.15;letter-spacing:.4px;color:#4b3552;}'
      + '.dxl-balance small{font-size:12px;font-weight:600;opacity:.55;margin-right:2px;}'
      + '.dxl-today{font-size:11px;color:#95839b;letter-spacing:.4px;white-space:nowrap;}'
      + '.dxl-panel{display:none;position:absolute;right:0;bottom:calc(100% + 10px);width:312px;max-height:388px;overflow:auto;'
      + 'background:rgba(255,252,254,.98);border:1px solid rgba(255,255,255,.95);border-radius:16px;padding:12px 13px 10px;'
      + 'box-shadow:0 16px 44px rgba(120,90,140,.24);}'
      + '#dxl-root.dxl-open .dxl-panel{display:block;}'
      + '.dxl-ph{display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;}'
      + '.dxl-ptitle{font-size:13px;font-weight:700;letter-spacing:1.4px;color:#6a5074;}'
      + '.dxl-refresh{border:0;background:rgba(160,120,175,.12);color:#7a5c86;border-radius:9px;padding:3px 9px;font-size:12px;cursor:pointer;}'
      + '.dxl-refresh:hover{background:rgba(160,120,175,.22);}'
      + '.dxl-sum{display:flex;gap:8px;margin-bottom:9px;}'
      + '.dxl-cell{flex:1;background:linear-gradient(150deg,rgba(255,255,255,.9),rgba(250,238,246,.9));border-radius:11px;padding:7px 9px;}'
      + '.dxl-cell b{display:block;font-size:15px;font-weight:700;color:#4b3552;letter-spacing:.3px;}'
      + '.dxl-cell span{font-size:10px;color:#9c8aa2;letter-spacing:.6px;}'
      + '.dxl-list{display:flex;flex-direction:column;gap:1px;}'
      + '.dxl-row{display:flex;align-items:baseline;gap:8px;padding:5px 2px;border-bottom:1px dashed rgba(180,150,190,.18);font-size:12px;}'
      + '.dxl-row:last-child{border-bottom:0;}'
      + '.dxl-t{color:#a190a8;font-variant-numeric:tabular-nums;font-size:11px;width:38px;flex:0 0 auto;}'
      + '.dxl-cost{font-weight:600;color:#7a5c86;min-width:52px;}'
      + '.dxl-meta{color:#b2a2b8;font-size:10.5px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;}'
      + '.dxl-empty{color:#b3a3b9;font-size:11.5px;padding:10px 2px 4px;}'
      + '.dxl-foot{margin-top:8px;font-size:10px;color:#b0a0b6;letter-spacing:.4px;line-height:1.6;}'
      + '.dxl-err{color:#c1743f;font-size:11px;margin-top:6px;line-height:1.5;}'
      + '@media (max-width:560px){#dxl-root{right:10px;bottom:150px}.dxl-card{padding:7px 10px 7px 7px;gap:8px}.dxl-char{width:48px;height:48px}'
      + '.dxl-balance{font-size:17px}.dxl-panel{width:min(86vw,300px)}}'

    function injectCss() {
      if (document.getElementById('dxl-style')) return
      var st = document.createElement('style')
      st.id = 'dxl-style'
      st.textContent = css
      ;(document.head || document.documentElement).appendChild(st)
    }

    function el(tag, cls, text) {
      var n = document.createElement(tag)
      if (cls) n.className = cls
      if (text != null) n.textContent = text
      return n
    }

    function money(n) {
      if (!isFinite(Number(n))) return '--'
      return '¥' + (Math.round(Number(n) * 100) / 100).toFixed(2)
    }

    var root = null
    var card = null
    var panel = null
    var refs = {}
    var state = null
    var timer = null
    var dragging = null
    var moved = false

    function build() {
      injectCss()
      root = el('div')
      root.id = 'dxl-root'

      card = el('div', 'dxl-card')
      var img = el('img', 'dxl-char')
      img.src = IMG
      img.alt = ''
      img.draggable = false
      img.onerror = function () { img.style.display = 'none' }

      var info = el('div', 'dxl-info')
      var top = el('div', 'dxl-top')
      var dot = el('span', 'dxl-dot')
      top.appendChild(dot)
      top.appendChild(el('span', null, '小D记账'))
      var bal = el('div', 'dxl-balance', '¥ --')
      var today = el('div', 'dxl-today', '今天 ¥0.00 · 0 轮')
      info.appendChild(top)
      info.appendChild(bal)
      info.appendChild(today)

      card.appendChild(img)
      card.appendChild(info)
      refs.dot = dot
      refs.bal = bal
      refs.today = today

      panel = el('div', 'dxl-panel')
      var ph = el('div', 'dxl-ph')
      ph.appendChild(el('div', 'dxl-ptitle', '今日账单'))
      var btn = el('button', 'dxl-refresh', '↻ 刷新')
      btn.type = 'button'
      btn.onclick = function (e) {
        e.stopPropagation()
        fetchState(true)
        btn.textContent = '读取中…'
        setTimeout(function () { btn.textContent = '↻ 刷新' }, 1200)
      }
      ph.appendChild(btn)
      panel.appendChild(ph)

      var sum = el('div', 'dxl-sum')
      var cell1 = el('div', 'dxl-cell')
      var b1 = el('b', null, '¥0.00')
      cell1.appendChild(b1); cell1.appendChild(el('span', null, '今天'))
      var cell2 = el('div', 'dxl-cell')
      var b2 = el('b', null, '¥0.00')
      cell2.appendChild(b2); cell2.appendChild(el('span', null, '本轮'))
      var cell3 = el('div', 'dxl-cell')
      var b3 = el('b', null, '¥0.00')
      cell3.appendChild(b3); cell3.appendChild(el('span', null, '累计'))
      sum.appendChild(cell1); sum.appendChild(cell2); sum.appendChild(cell3)
      panel.appendChild(sum)
      refs.today2 = b1
      refs.last = b2
      refs.total = b3

      var list = el('div', 'dxl-list')
      panel.appendChild(list)
      refs.list = list

      var foot = el('div', 'dxl-foot', '')
      panel.appendChild(foot)
      refs.foot = foot

      root.appendChild(card)
      root.appendChild(panel)
      document.body.appendChild(root)

      /* 位置记忆 */
      var saved = null
      try { saved = JSON.parse(localStorage.getItem(LS_POS) || 'null') } catch (e) { saved = null }
      if (saved && isFinite(saved.left) && isFinite(saved.top)) {
        root.style.left = Math.round(saved.left) + 'px'
        root.style.top = Math.round(saved.top) + 'px'
        root.style.right = 'auto'
        root.style.bottom = 'auto'
      } else {
        try { if (localStorage.getItem(LS_OPEN) === '1') root.classList.add('dxl-open') } catch (e) {}
      }

      /* 拖动 + 点击 */
      card.addEventListener('pointerdown', function (e) {
        if (e.button !== undefined && e.button !== 0) return
        var rect = root.getBoundingClientRect()
        dragging = { x: e.clientX, y: e.clientY, left: rect.left, top: rect.top }
        moved = false
        card.classList.add('dxl-dragging')
        try { card.setPointerCapture(e.pointerId) } catch (err) {}
      })
      card.addEventListener('pointermove', function (e) {
        if (!dragging) return
        var dx = e.clientX - dragging.x
        var dy = e.clientY - dragging.y
        if (!moved && Math.abs(dx) + Math.abs(dy) > 4) moved = true
        if (!moved) return
        var left = Math.max(4, Math.min(window.innerWidth - 90, dragging.left + dx))
        var top = Math.max(4, Math.min(window.innerHeight - 70, dragging.top + dy))
        root.style.left = Math.round(left) + 'px'
        root.style.top = Math.round(top) + 'px'
        root.style.right = 'auto'
        root.style.bottom = 'auto'
      })
      function endDrag(e) {
        if (!dragging) return
        card.classList.remove('dxl-dragging')
        var wasMoved = moved
        dragging = null
        moved = false
        if (wasMoved) {
          try {
            var rect = root.getBoundingClientRect()
            localStorage.setItem(LS_POS, JSON.stringify({ left: rect.left, top: rect.top }))
          } catch (err) {}
        } else {
          root.classList.toggle('dxl-open')
          try { localStorage.setItem(LS_OPEN, root.classList.contains('dxl-open') ? '1' : '0') } catch (err) {}
          if (root.classList.contains('dxl-open')) fetchState(false)
        }
      }
      card.addEventListener('pointerup', endDrag)
      card.addEventListener('pointercancel', function () { if (dragging) { dragging = null; card.classList.remove('dxl-dragging'); moved = false } })

      document.addEventListener('pointerdown', function (e) {
        if (root && root.classList.contains('dxl-open') && !root.contains(e.target)) {
          root.classList.remove('dxl-open')
          try { localStorage.setItem(LS_OPEN, '0') } catch (err) {}
        }
      })
    }

    function render(d) {
      if (!d || !d.ok) {
        if (refs.dot) refs.dot.classList.add('bad')
        if (refs.bal) refs.bal.textContent = '¥ --'
        if (refs.today) refs.today.textContent = (d && d.error) ? '读不到账本' : '等待连接…'
        return
      }
      state = d
      if (refs.bal) {
        refs.bal.textContent = d.balance ? money(d.balance.total) : '¥ --'
        refs.bal.title = d.balance ? ('余额来源：' + (d.balance.source === 'account' ? '账号登录' : 'API key')) : (d.balanceError || '')
      }
      if (refs.dot) refs.dot.classList.toggle('bad', !d.balance)
      if (refs.today) {
        refs.today.textContent = '今天 ' + money(d.today.cost) + ' · ' + d.today.turns + ' 轮'
      }
      if (refs.today2) refs.today2.textContent = money(d.today.cost)
      if (refs.last) refs.last.textContent = d.lastTurn ? money(d.lastTurn.cost) : '¥0.00'
      if (refs.total) refs.total.textContent = money(d.total.cost)

      if (refs.list) {
        refs.list.textContent = ''
        var entries = d.entries || []
        if (!entries.length) {
          refs.list.appendChild(el('div', 'dxl-empty', '还没有记账记录～ 跟小D聊几句，这里就会长出小账本 ✨'))
        } else {
          entries.forEach(function (e) {
            var row = el('div', 'dxl-row')
            row.appendChild(el('span', 'dxl-t', e.clock || ''))
            row.appendChild(el('span', 'dxl-cost', (Number(e.cost) < 0.01 && Number(e.cost) > 0 ? '<¥0.01' : money(e.cost))))
            var meta = (e.model ? e.model : '模型未知') + ' · ' + (e.tokens ? e.tokens + ' tok' : '')
            row.appendChild(el('span', 'dxl-meta', meta))
            refs.list.appendChild(row)
          })
        }
      }
      if (refs.foot) {
        var bits = []
        if (d.balanceError) bits.push('余额：' + d.balanceError)
        else if (d.balance) bits.push('余额更新 ' + (d.clock || ''))
        if (d.peak) bits.push('当前高峰时段')
        refs.foot.textContent = bits.join(' · ')
      }
    }

    function fetchState(force) {
      try {
        var url = API + (force ? '?force=1' : '')
        fetch(url, { cache: 'no-store', credentials: 'same-origin' })
          .then(function (r) { return r.json() })
          .then(function (d) { render(d) })
          .catch(function () {
            if (refs.today) refs.today.textContent = '连接失败，稍后再试'
          })
      } catch (err) { /* 忽略 */ }
    }

    function boot() {
      if (!document.body) { setTimeout(boot, 300); return }
      try {
        build()
        fetchState(false)
        timer = setInterval(function () {
          if (!document.hidden) fetchState(false)
        }, POLL_MS)
      } catch (err) {
        // 挂件失败不能影响页面
        console.warn('[xiaod-ledger] widget init failed: ' + String((err && err.message) || err))
      }
    }

    boot()
  } catch (err) {
    console.warn('[xiaod-ledger] widget bootstrap failed: ' + String((err && err.message) || err))
  }
})()

