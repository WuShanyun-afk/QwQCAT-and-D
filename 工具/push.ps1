# 小鲸鱼的作品集 · 保存并推送到 GitHub
# 由 工具\推送到github.bat 调用；也可以右键“使用 PowerShell 运行”
# 特点：不写死盘符（仓库挪到哪都能跑）· 推送前先拉取 · 全程有超时，卡住不会挂死窗口

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [Text.Encoding]::UTF8 } catch {}

# ---------- 0. 定位仓库：脚本在 工具\ 里，上一级就是仓库根 ----------
$repo = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repo '.git'))) {
    Write-Host ""
    Write-Host "  这里不是 git 仓库：$repo" -ForegroundColor Red
    exit 1
}
Set-Location $repo

# 找不到 git 就自己找安装位置（新装的 Git 不会立刻出现在老终端里）
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    $hit = @(
        (Join-Path $env:ProgramFiles 'Git\cmd'),
        (Join-Path ${env:ProgramFiles(x86)} 'Git\cmd'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Git\cmd')
    ) | Where-Object { $_ -and (Test-Path (Join-Path $_ 'git.exe')) } | Select-Object -First 1
    if ($hit) { $env:Path = $hit + ';' + $env:Path }
    else {
        Write-Host "  找不到 git，重开一个窗口再试。" -ForegroundColor Red
        exit 1
    }
}

# 限死 SSH 等待时间：校园网卡住时不会一直挂着
$env:GIT_SSH_COMMAND = "ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=10 -o ServerAliveCountMax=2"

function Invoke-Git {
    param([string[]]$GitArgs, [int]$TimeoutSec = 90)
    $outF = Join-Path $env:TEMP ("uu_git_out_{0}.txt" -f [guid]::NewGuid().ToString('N'))
    $errF = Join-Path $env:TEMP ("uu_git_err_{0}.txt" -f [guid]::NewGuid().ToString('N'))
    # 注意：Start-Process 把数组用空格拼成一行，带空格的参数（比如 commit 消息）必须自己套引号
    $argStr = ($GitArgs | ForEach-Object {
        if ($_ -match '\s') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }) -join ' '
    $p = Start-Process -FilePath 'git' -ArgumentList $argStr -NoNewWindow -PassThru `
        -RedirectStandardOutput $outF -RedirectStandardError $errF
    $null = $p | Wait-Process -Timeout $TimeoutSec -ErrorAction SilentlyContinue
    $timedOut = -not $p.HasExited
    $code = -1
    if ($timedOut) { try { $p.Kill() } catch {} } else { try { $code = $p.ExitCode } catch {} }
    $log = ''
    foreach ($f in @($outF, $errF)) { if (Test-Path $f) { $log += (Get-Content $f -Raw -Encoding UTF8) } }
    Remove-Item $outF, $errF -Force -ErrorAction SilentlyContinue
    [pscustomobject]@{
        Ok       = ((-not $timedOut) -and ($code -eq 0))
        TimedOut = $timedOut
        Log      = ($log -replace "`r", '').Trim()
    }
}

function Show-Tail($text, $n = 3) {
    foreach ($line in @($text -split "`n" | Where-Object { $_.Trim() } | Select-Object -Last $n)) {
        Write-Host ("         " + $line.Trim()) -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "  ===== 小鲸鱼的作品集 -> GitHub =====" -ForegroundColor Cyan
Write-Host ""

# ---------- 1. 本地存一次 ----------
git add -A
git diff --cached --quiet
$hasStaged = ($LASTEXITCODE -ne 0)

if (-not $hasStaged) {
    Write-Host "  [跳过] 没有新改动。" -ForegroundColor DarkGray
}
else {
    $msg = "更新：" + (Get-Date -Format 'yyyy-MM-dd HH:mm')
    $r = Invoke-Git @('commit', '-m', $msg) -TimeoutSec 60
    if ($r.Ok) { Write-Host "  [完成] 已保存：$msg" -ForegroundColor Green }
    else {
        Write-Host "  [失败] 本地这次没存上！" -ForegroundColor Red
        Show-Tail $r.Log 4
    }
}

# ---------- 2. 推送前先拉取（免得被 GitHub 拒收） ----------
$r = Invoke-Git @('pull', '--rebase', '--autostash') -TimeoutSec 90
if ($r.Ok) {
    if ($r.Log -match 'Already up to date|已经是最新的') {
        Write-Host "  [拉取] 线上没有新东西。" -ForegroundColor DarkGray
    }
    else {
        Write-Host "  [拉取] 已合上线上的改动。" -ForegroundColor Green
    }
}
elseif ($r.TimedOut) {
    Write-Host "  [超时] GitHub 没连上，本地已经存好了。" -ForegroundColor Yellow
    Write-Host "         校园网就这脾气，过会儿再双击一次就行。" -ForegroundColor DarkGray
    Write-Host ""
    git log --oneline -6
    exit 0
}
else {
    Write-Host "  [警告] 拉取没成功，直接试着推推看。" -ForegroundColor Yellow
    Show-Tail $r.Log 3
}

# ---------- 3. 推送 ----------
$r = Invoke-Git @('push', 'origin', 'main') -TimeoutSec 90

if ($r.TimedOut) {
    Write-Host "  [超时] GitHub 没连上，本地已经存好了。" -ForegroundColor Yellow
    Write-Host "         过会儿再双击一次这个脚本就行。" -ForegroundColor DarkGray
}
elseif ($r.Ok) {
    if ($r.Log -match 'Everything up-to-date') {
        Write-Host "  [同步] 线上已经是最新的。" -ForegroundColor DarkGray
    }
    else {
        Write-Host "  [同步] 已推送到 GitHub！" -ForegroundColor Green
        Write-Host ""
        Write-Host "  线上看图：https://wushanyun-afk.github.io/QwQCAT-and-D/" -ForegroundColor Cyan
        Write-Host "  （Pages 要重新构建，大概等 1 分钟再刷新）" -ForegroundColor DarkGray
    }
}
else {
    # 典型情况：远端有新提交导致拒收 -> 再拉一次，然后重推
    if ($r.Log -match 'non-fast-forward|rejected|fetch first') {
        Write-Host "  [重试] 线上有新提交，先拉再推..." -ForegroundColor Yellow
        $r2 = Invoke-Git @('pull', '--rebase', '--autostash') -TimeoutSec 90
        if ($r2.Ok) {
            $r = Invoke-Git @('push', 'origin', 'main') -TimeoutSec 90
        }
    }
    if ($r.Ok) {
        Write-Host "  [同步] 已推送到 GitHub！" -ForegroundColor Green
        Write-Host "  线上看图：https://wushanyun-afk.github.io/QwQCAT-and-D/" -ForegroundColor Cyan
    }
    else {
        Write-Host "  [失败] GitHub 没推上去，本地已经存好了。" -ForegroundColor Yellow
        Show-Tail $r.Log 3
        Write-Host "         改动没丢，过会儿再双击一次这个脚本。" -ForegroundColor DarkGray
    }
}

Write-Host ""
Write-Host "  ---- 最近 6 次记录 ----" -ForegroundColor Cyan
git log --oneline -6
Write-Host ""
