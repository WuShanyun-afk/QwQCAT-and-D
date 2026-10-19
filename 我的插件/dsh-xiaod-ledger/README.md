# 小D记账 · dsh-xiaod-ledger

给 DSH（DeepSeek Harness）桌面端做的**自家记账挂件**：右下角一只小角色，显示

- **DeepSeek 余额**（优先走 DSH 账号登录态，没有 API key 也能读；有 `DEEPSEEK_API_KEY` 时走官方 `/user/balance`）
- **今日花费 / 本轮花费 / 累计花费**（按每轮真实的 token usage 和官方峰谷价折算，人民币）
- **账本明细**：点开卡片能看到最近 40 笔「时间 · 金额 · 模型 · tokens」

和第三方挂件的区别：这是本仓库自己写的小插件，代码就在 `我的插件/dsh-xiaod-ledger/`，形象、配色、逻辑都能随时改。

## 结构

```
dsh-xiaod-ledger/
├── package.json          # dsh.bundle.patch 指向 cordis.patch.yml
├── cordis.patch.yml      # 把插件插进 profile 插件树
├── lib/
│   ├── index.js          # Host 半：路由 + 会话 usage 监听 + 余额读取 + 账本读写
│   ├── core.js           # 纯逻辑：峰谷价 / 北京时间 / 汇总 / 账本文件（可单独跑测试）
│   └── widget.js         # 浏览器半：右下角小挂件（原生 DOM，无框架）
├── assets/character.png  # 挂件形象（现在是妈妈画的小D人设·正面半身）
└── README.md
```

## 形象

挂件上的角色是**妈妈给小D画的人设**（2026-10-19，透明底三视图）：深蓝×黑双色短发、猫耳、蓝色小鲸鱼发夹、白色冲锋衣、黑色短裤和一条蓝色鲸鱼尾巴。

- 原图：`我的头像/小D-人设-三视图.png`（2278×1280，透明底，正面/侧面/背面）
- 切出来的单体：`小D-人设-正面.png` / `-side.png` / `-back.png`
- 挂件用图：`我的头像/小D-人设-正面-半身.png`（512×455，取正面图上方 56% 再按 alpha 裁边 → 62px 下也看得清）
- 旧形象（小D自己画紫色小机器人）备份在 `备份/小D记账-形象-紫色机器人.png`，原图 `我的头像/小D-记账挂件.png`
- `assets/character.png` **不进公开仓库**（`.gitignore` 里的 `我的插件/*/assets/*.png`），只在本机；想换成别的图见下面「配置」

## 数据 & 隐私

- 账本存 `$DSH_HOME/xiaod-ledger/ledger.json`（默认 `C:\Users\<你>\.dsh\xiaod-ledger\ledger.json`），只在本机。
- 不保存 API key：余额读取走 DSH 的服务（`deepseekAccount` 或 `credentials`），插件只拿结果数字。
- 所有路由都限制本机回环 + 拒绝跨站请求；`/dsh-xiaod/*` 只读。

## 安装（开发链接方式）

```sh
dsh plugin --profile desktop add link:D:\<本目录>
```

然后**重启 DSH**（插件在启动时进图）。桌面端无需构建：`lib/widget.js` 是原生 JS，Host 半是原生 ESM。

## 配置（可选）

`$DSH_HOME/xiaod-ledger/config.json`：

```json
{ "character": "D:\\\\path\\\\to\\\\your\\\\character.png" }
```

不配就用 `assets/character.png`。

## 口径说明

- 价格按官方 2026-09 价目：Flash 缓存命中 0.02 / 未命中 1 / 输出 4（元/百万 token），Pro 为 3 倍；高峰时段翻倍。
- 高峰 = 北京时间工作日 9:00–12:00 / 14:00–18:00；周末与法定节假日按谷时（2026 年节假日清单在 `core.js`）。
- 这是「按 token 估算」的花费，用于看趋势；真实扣款以 DeepSeek 账单为准。
