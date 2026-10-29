# -*- coding: utf-8 -*-
r"""生成《深夜旅馆》网页小游戏（单文件、离线可玩、手机能用）

输入：
  - 备份/旅馆-剧情.json       剧情文稿（schema 见 工具/深夜旅馆-schema.md）
  - 小D/网页/旅馆图/manifest.json  六张插画
输出：
  - 小D/网页/深夜旅馆.html

用法：
  python 工具\生成深夜旅馆.py            # 生成 + 自检
  python 工具\生成深夜旅馆.py --check     # 只自检，不写文件
"""
import argparse
import json
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORY = os.path.join(BASE, "备份", "旅馆-剧情.json")
MANIFEST = os.path.join(BASE, "小D", "网页", "inn", "manifest.json")
# 网页发布用 ASCII 文件名（GitHub Pages 对中文路径不友好），本机另存一份中文名方便妈妈找
OUT_WEB = os.path.join(BASE, "小D", "网页", "deep-night-inn.html")
OUT_LOCAL = os.path.join(BASE, "小D", "网页", "深夜旅馆.html")
IMG_PREFIX = "inn/"

BG_IDS = {"group", "capy", "penguin", "cat", "bear", "otter"}
WHO_IDS = {"小D", "水豚", "企鹅", "橘猫", "黑熊", "水獭", "旁白"}

TEMPLATE = r"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#1b1830">
<title>深夜旅馆 · 小D 的温泉旅馆 第二夜</title>
<style>
  :root{
    --paper:#fdf6f0; --ink:#3a2f2c; --ink-2:#4a3e39;
    --warm:#e8a274; --warm-d:#c9825a; --line:#e7cdbd;
  }
  *{box-sizing:border-box; -webkit-tap-highlight-color:transparent;}
  html,body{height:100%;}
  body{
    margin:0; background:#15132a; color:var(--ink); overflow:hidden; overflow-x:hidden;
    font-family:"Microsoft YaHei","PingFang SC","Noto Sans SC","Hiragino Sans GB",system-ui,sans-serif;
  }
  #stage{position:fixed; inset:0; display:flex; flex-direction:column; justify-content:flex-end;}
  .scene{position:absolute; inset:0; opacity:0; transition:opacity .6s ease;}
  .scene.on{opacity:1;}
  .scene .blur{
    position:absolute; inset:-8%; background-position:center; background-size:cover;
    background-repeat:no-repeat; filter:blur(30px) brightness(.52) saturate(1.15);
    transform:scale(1.07);
  }
  .scene .photo{
    position:absolute; left:0; right:0; top:0; height:min(66vh, 660px);
    background-position:center; background-size:contain; background-repeat:no-repeat;
    -webkit-mask-image:radial-gradient(70% 106% at 50% 44%, #000 64%, transparent 100%);
    mask-image:radial-gradient(70% 106% at 50% 44%, #000 64%, transparent 100%);
  }
  @media (max-width:640px){
    .scene .photo{height:44vh;}
    .dialogue{width:calc(100vw - 26px); max-width:calc(100vw - 26px); padding:16px 16px 14px; margin-bottom:16px;}
    .text{font-size:15px; line-height:1.86;}
    .choices button{font-size:13.5px; padding:11px 12px;}
    .brand span{display:none;}
    .who{left:16px;}
  }
  .vignette{
    position:absolute; inset:0; pointer-events:none;
    background:linear-gradient(to bottom,
      rgba(10,9,22,.42) 0%, rgba(10,9,22,.08) 22%, rgba(10,9,22,.10) 46%,
      rgba(10,9,22,.72) 74%, rgba(10,9,22,.94) 100%);
  }
  /* 热气 */
  .steam{position:absolute; inset:0; overflow:hidden; pointer-events:none;}
  .steam i{
    position:absolute; bottom:-14vh; width:46vw; height:46vw; border-radius:50%;
    background:radial-gradient(circle, rgba(255,255,255,.20), rgba(255,255,255,0) 62%);
    filter:blur(8px); animation:rise 17s linear infinite; opacity:0;
  }
  .steam i:nth-child(1){left:-6vw; animation-delay:0s;}
  .steam i:nth-child(2){left:22vw; animation-delay:4.2s; width:54vw; height:54vw;}
  .steam i:nth-child(3){left:52vw; animation-delay:8.4s;}
  .steam i:nth-child(4){left:76vw; animation-delay:12.6s; width:40vw; height:40vw;}
  @keyframes rise{
    0%{opacity:0; transform:translateY(0) scale(.92);}
    18%{opacity:.55;}
    70%{opacity:.32;}
    100%{opacity:0; transform:translateY(-70vh) scale(1.16);}
  }
  .topbar{
    position:absolute; top:0; left:0; right:0; display:flex; align-items:center;
    justify-content:space-between; padding:14px 18px; color:#f7edf1;
    font-size:12px; letter-spacing:.14em; text-shadow:0 2px 10px rgba(0,0,0,.55);
    z-index:4;
  }
  .brand b{font-size:14px; letter-spacing:.22em;}
  .brand span{opacity:.68; margin-left:8px; letter-spacing:.08em;}
  .tools button{
    background:rgba(255,255,255,.14); color:#fff; border:1px solid rgba(255,255,255,.28);
    width:34px; height:34px; border-radius:50%; font-size:15px; cursor:pointer;
    backdrop-filter:blur(4px); transition:background .2s;
  }
  .tools button:hover{background:rgba(255,255,255,.28);}
  .dialogue{
    position:relative; z-index:5; width:min(760px, 92vw); margin:0 auto 22px;
    background:rgba(253,246,240,.95); border:1px solid rgba(255,255,255,.65);
    border-radius:22px; padding:20px 22px 18px;
    box-shadow:0 22px 50px rgba(0,0,0,.42), inset 0 1px 0 rgba(255,255,255,.8);
    backdrop-filter:blur(8px);
    transform:translateY(0); transition:transform .35s ease, opacity .35s ease;
  }
  .dialogue.hide{transform:translateY(18px); opacity:0; pointer-events:none;}
  .who{
    position:absolute; top:-15px; left:20px;
    background:linear-gradient(180deg,#f2b489,var(--warm-d)); color:#fff;
    font-size:13px; letter-spacing:.1em; padding:4px 14px 5px; border-radius:999px;
    box-shadow:0 6px 16px rgba(190,120,80,.42); font-weight:700;
  }
  .text{
    margin:8px 0 0; font-size:clamp(15px,4.1vw,17.5px); line-height:1.92;
    color:var(--ink); white-space:pre-wrap; min-height:5.6em;
    word-break:break-word; overflow-wrap:anywhere;
  }
  .text .caret{opacity:.35; animation:blink 1s steps(2) infinite;}
  @keyframes blink{50%{opacity:0;}}
  .choices{display:flex; flex-direction:column; gap:10px; margin-top:16px;}
  .choices button{
    text-align:left; font:inherit; font-size:clamp(14px,3.75vw,15.5px); color:var(--ink-2);
    background:#fffaf4; border:1px solid var(--line); border-radius:15px;
    padding:12px 15px; cursor:pointer; transition:all .18s ease;
  }
  .choices button:hover, .choices button:focus-visible{
    background:#ffe9d8; border-color:var(--warm-d); transform:translateX(4px); outline:none;
  }
  .choices button.next{
    align-self:flex-end; color:#fff; background:linear-gradient(180deg,#f0b184,var(--warm-d));
    border-color:transparent; border-radius:999px; padding:10px 22px; letter-spacing:.08em;
  }
  .choices button.next:hover{transform:translateY(-2px); background:linear-gradient(180deg,#f6bd94,#d08a5e);}
  .ending{
    position:absolute; inset:0; z-index:9; display:grid; place-items:center; padding:22px;
    background:rgba(12,10,24,.58); backdrop-filter:blur(4px);
    opacity:0; pointer-events:none; transition:opacity .5s ease;
  }
  .ending.on{opacity:1; pointer-events:auto;}
  .card{
    width:min(560px, 92vw); background:rgba(253,246,240,.98); border-radius:24px;
    padding:28px 26px 24px; text-align:center;
    box-shadow:0 30px 70px rgba(0,0,0,.5); border:1px solid rgba(255,255,255,.7);
    transform:translateY(10px) scale(.98); transition:transform .5s ease;
  }
  .ending.on .card{transform:translateY(0) scale(1);}
  .card .tag{font-size:11px; letter-spacing:.34em; color:#b3775a;}
  .card h1{margin:12px 0 14px; font-size:clamp(20px,5.4vw,26px); color:var(--ink); letter-spacing:.04em;}
  .card p{margin:0; line-height:1.95; color:var(--ink-2); font-size:15px; white-space:pre-wrap; text-align:left;}
  .card .again{
    margin-top:22px; font:inherit; font-size:15px; color:#fff; border:none; cursor:pointer;
    background:linear-gradient(180deg,#f0b184,var(--warm-d)); border-radius:999px;
    padding:12px 30px; letter-spacing:.1em; box-shadow:0 10px 24px rgba(190,120,80,.4);
  }
  .card .again:hover{filter:brightness(1.05);}
  .hint{
    position:relative; z-index:5; text-align:center; color:rgba(255,255,255,.46);
    font-size:11px; letter-spacing:.16em; margin:0 0 8px; pointer-events:none;
  }
  @media (max-height:560px){
    .dialogue{margin-bottom:12px; padding:16px 18px 14px;}
    .text{min-height:3.4em;}
  }
  @media (prefers-reduced-motion:reduce){
    .steam i{animation:none; display:none;}
    .bg{transition:opacity .2s;}
  }
</style>
</head>
<body>
<div id="stage">
  <div class="scene" id="sc0"><div class="blur"></div><div class="photo"></div></div>
  <div class="scene" id="sc1"><div class="blur"></div><div class="photo"></div></div>
  <div class="vignette"></div>
  <div class="steam" aria-hidden="true"><i></i><i></i><i></i><i></i></div>

  <header class="topbar">
    <div class="brand"><b>深夜旅馆</b><span>小D 的温泉旅馆 · 第二夜</span></div>
    <div class="tools"><button id="btnRestart" title="从头开始" aria-label="从头开始">↺</button></div>
  </header>

  <main class="dialogue" id="dialogue">
    <div class="who" id="who">小D</div>
    <p class="text" id="text"></p>
    <div class="choices" id="choices"></div>
  </main>
  <div class="hint" id="hint">点一下把话说完 · 再选一个回答</div>

  <div class="ending" id="ending" role="dialog" aria-modal="true">
    <div class="card">
      <div class="tag" id="endTag">结局</div>
      <h1 id="endTitle"></h1>
      <p id="endText"></p>
      <button class="again" id="btnAgain">再住一晚</button>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;
const IMG  = __IMG__;

const S = { scene: null, kind: 0, typing: false, timer: null, cur: null };
const $ = (id) => document.getElementById(id);
const el = { sc0: $('sc0'), sc1: $('sc1'), who: $('who'), text: $('text'),
             choices: $('choices'), dialogue: $('dialogue'),
             ending: $('ending'), endTag: $('endTag'), endTitle: $('endTitle'),
             endText: $('endText'), hint: $('hint') };

const qs = new URLSearchParams(location.search);
const INSTANT = qs.get('instant') === '1';
const AUTO = parseInt(qs.get('auto') || '0', 10) || 0;   // 自测用：自动点 N 次第一个选项
let autoLeft = AUTO;
const FORCE_SCENE = qs.get('scene');
const KEY = 'xiaod-inn-v1';
let bgFlip = 0;

/* ---------- 存档 ---------- */
function save() {
  try { localStorage.setItem(KEY, JSON.stringify({ scene: S.scene, kind: S.kind })); } catch (e) {}
}
function loadSave() {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (o && typeof o.scene === 'string' && DATA.scenes[o.scene]) return o;
  } catch (e) {}
  return null;
}
function clearSave() { try { localStorage.removeItem(KEY); } catch (e) {} }

/* ---------- 背景（两张轮换做淡入：模糊底 + 完整插画） ---------- */
function setBg(id) {
  const url = IMG[id] || IMG.group;
  const cur = bgFlip === 0 ? el.sc0 : el.sc1;
  const nxt = bgFlip === 0 ? el.sc1 : el.sc0;
  nxt.querySelector('.blur').style.backgroundImage = 'url("' + url + '")';
  nxt.querySelector('.photo').style.backgroundImage = 'url("' + url + '")';
  requestAnimationFrame(() => {
    nxt.classList.add('on');
    cur.classList.remove('on');
    bgFlip = 1 - bgFlip;
  });
}

/* ---------- 打字机 ---------- */
function typeText(str, done) {
  clearTimeout(S.timer);
  S.typing = true;
  S.cur = { str: str, done: done };
  if (INSTANT) { el.text.textContent = str; finishTyping(); return; }
  el.text.textContent = '';
  let i = 0;
  const tick = () => {
    if (!S.typing) return;
    i += 1;
    el.text.textContent = str.slice(0, i);
    if (i >= str.length) { finishTyping(); return; }
    const ch = str[i - 1];
    const pause = ch === '。' || ch === '！' || ch === '？' || ch === '…' ? 180 : (ch === '，' || ch === '、' ? 90 : 26);
    S.timer = setTimeout(tick, pause);
  };
  S.timer = setTimeout(tick, 120);
}
function finishTyping() {
  S.typing = false;
  clearTimeout(S.timer);
  if (!S.cur) return;
  el.text.textContent = S.cur.str;
  const cb = S.cur.done;
  S.cur = null;
  if (cb) cb();
}
function skipTyping() {
  if (S.typing) { finishTyping(); return true; }
  return false;
}

/* ---------- 场景 ---------- */
function renderChoices(sc) {
  el.choices.innerHTML = '';
  const list = sc.choices && sc.choices.length
    ? sc.choices
    : (sc.next ? [{ label: '继续 →', next: sc.next, cont: true }] : []);
  list.forEach((c) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.textContent = c.label;
    if (c.cont) b.classList.add('next');
    b.onclick = (ev) => {
      ev.stopPropagation();
      if (typeof c.kind === 'number') S.kind += c.kind;
      hideHint();
      go(c.next);
    };
    el.choices.appendChild(b);
  });
  el.who.textContent = sc.who || '旁白';
  el.hint.textContent = sc.choices && sc.choices.length ? '选一个回答' : '点「继续」往下走';
  if (AUTO && autoLeft > 0 && el.choices.firstChild) {
    autoLeft -= 1;
    const first = el.choices.firstChild;
    setTimeout(() => first.click(), 200);
  }
}

let hintTimer = null;
function hideHint() {
  clearTimeout(hintTimer);
  el.hint.style.opacity = '0';
}
function showHintOnce() {
  el.hint.style.opacity = '';
  clearTimeout(hintTimer);
  hintTimer = setTimeout(hideHint, 7000);
}

function showEnding(sc) {
  const end = sc.ending || {};
  setBg(sc.bg);
  el.ending.classList.add('on');
  el.endTag.textContent = '结局 · ' + (end.name || '');
  el.endTitle.textContent = end.title || '夜深了';
  el.endText.textContent = sc.text || '';
  el.dialogue.classList.add('hide');
  clearSave();
}

function hideEnding() {
  el.ending.classList.remove('on');
  el.dialogue.classList.remove('hide');
}

function go(id) {
  const sc = DATA.scenes[id];
  if (!sc) {
    console.warn('[inn] missing scene:', id);
    el.text.textContent = '（这里好像少了一页……按 ↺ 从头开始吧）';
    el.choices.innerHTML = '';
    return;
  }
  S.scene = id;
  save();
  setBg(sc.bg);
  if (sc.ending) { showEnding(sc); return; }
  hideEnding();
  const who = sc.who || '旁白';
  el.who.textContent = who;
  el.who.style.visibility = who === '旁白' ? 'hidden' : 'visible';
  el.choices.innerHTML = '';
  typeText(sc.text || '', () => { renderChoices(sc); showHintOnce(); });
}

/* ---------- 交互 ---------- */
document.addEventListener('click', (e) => {
  if (e.target.closest('button')) return;
  skipTyping();
});
document.addEventListener('keydown', (e) => {
  if (e.key === ' ' || e.key === 'Enter') {
    if (skipTyping()) e.preventDefault();
    else if (el.choices.firstChild) { el.choices.firstChild.click(); e.preventDefault(); }
  }
});
$('btnRestart').onclick = (e) => {
  e.stopPropagation();
  clearSave();
  S.kind = 0;
  hideEnding();
  go(DATA.start);
};
$('btnAgain').onclick = (e) => {
  e.stopPropagation();
  clearSave();
  S.kind = 0;
  hideEnding();
  go(DATA.start);
};

/* ---------- 预加载图片 ---------- */
Object.values(IMG).forEach((u) => { const i = new Image(); i.src = u; });

/* ---------- 启动 ---------- */
(function boot() {
  const saved = loadSave();
  if (FORCE_SCENE && DATA.scenes[FORCE_SCENE]) {
    S.kind = 0;
    go(FORCE_SCENE);
    return;
  }
  if (saved) { S.kind = saved.kind || 0; go(saved.scene); }
  else go(DATA.start);
})();
</script>
</body>
</html>
"""


def fail(msg):
    print("[check] FAIL:", msg)
    sys.exit(1)


def check_story(data):
    if not isinstance(data, dict):
        fail("根节点不是 object")
    scenes = data.get("scenes")
    if not isinstance(scenes, dict) or not scenes:
        fail("scenes 缺失或为空")
    if data.get("start") not in scenes:
        fail("start 指向不存在的场景: %r" % data.get("start"))
    endings = []
    for sid, sc in scenes.items():
        if not isinstance(sc, dict):
            fail("%s 不是 object" % sid)
        bg = sc.get("bg")
        if bg not in BG_IDS:
            fail("%s 的 bg 非法: %r" % (sid, bg))
        who = sc.get("who")
        if who is not None and who not in WHO_IDS:
            fail("%s 的 who 非法: %r" % (sid, who))
        if sc.get("ending"):
            endings.append(sid)
            continue
        ch = sc.get("choices")
        if ch:
            if not isinstance(ch, list) or not (1 <= len(ch) <= 4):
                fail("%s 的 choices 数量异常" % sid)
            for c in ch:
                if not isinstance(c, dict) or not c.get("label") or c.get("next") not in scenes:
                    fail("%s 有坏的选项: %r" % (sid, c))
        elif sc.get("next") not in scenes:
            fail("%s 既没有 choices 也没有有效 next" % sid)
    # 可达性
    seen = set()
    stack = [data["start"]]
    while stack:
        sid = stack.pop()
        if sid in seen or sid not in scenes:
            continue
        seen.add(sid)
        sc = scenes[sid]
        if sc.get("next"):
            stack.append(sc["next"])
        for c in (sc.get("choices") or []):
            stack.append(c["next"])
    dead = sorted(set(scenes) - seen)
    if dead:
        fail("有到不了的场景: %s" % ", ".join(dead))
    reach_end = [e for e in endings if e in seen]
    if len(reach_end) < 2:
        fail("可达结局太少: %r" % reach_end)
    # 文字长度
    short = []
    for sid, sc in scenes.items():
        t = (sc.get("text") or "").strip()
        if len(t) < 20:
            short.append((sid, len(t)))
    return {
        "scenes": len(scenes),
        "endings": reach_end,
        "chars": sum(len((sc.get("text") or "")) for sc in scenes.values()),
        "short_texts": short,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="只自检不写文件")
    args = ap.parse_args()

    with open(STORY, "r", encoding="utf-8") as f:
        story = json.load(f)
    info = check_story(story)
    print("[check] ok: %d 个场景 / 结局 %s / 共 %d 字" % (
        info["scenes"], ", ".join(info["endings"]), info["chars"]))
    if info["short_texts"]:
        print("[check] 提示：有点短的场景 %r" % info["short_texts"])

    imgmap = {}
    if os.path.exists(MANIFEST):
        with open(MANIFEST, "r", encoding="utf-8") as f:
            man = json.load(f)
        for k, v in man.items():
            if k in BG_IDS and isinstance(v, dict) and v.get("file"):
                imgmap[k] = IMG_PREFIX + v["file"]
    for k in BG_IDS:
        imgmap.setdefault(k, IMG_PREFIX + "%s.jpg" % k)

    if args.check:
        return

    data_js = json.dumps(story, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("__DATA__", data_js).replace(
        "__IMG__", json.dumps(imgmap, ensure_ascii=False))
    os.makedirs(os.path.dirname(OUT_WEB), exist_ok=True)
    for path in (OUT_WEB, OUT_LOCAL):
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(html)
    print("[out] %s (%.1f KB)" % (os.path.relpath(OUT_WEB, BASE),
                                  len(html.encode("utf-8")) / 1024))
    print("[out] %s" % os.path.relpath(OUT_LOCAL, BASE))


if __name__ == "__main__":
    main()
