# 小D 桌宠 / 陪写作业 看门狗
# 用「心跳文件」判断还活着吗：活着的进程会每 2 秒刷新自己的 .hb
# 这样不会误判、也不会一下拉出两只小D（两只的情况已经彻底修掉了）
$ErrorActionPreference = 'SilentlyContinue'

$pyw = 'C:\Program Files\Python314\pythonw.exe'
$base = 'D:\小鲸鱼的专属文件夹\我的插件'
$log = Join-Path $base 'widgets-watchdog.log'

$items = @(
  @{ Name = 'pet';   Script = (Join-Path $base 'dsh-desktop-pet\pet.py');
     Hb = (Join-Path $base 'dsh-desktop-pet\pet.hb');     Pause = (Join-Path $base 'dsh-desktop-pet\pet.pause') },
  @{ Name = 'study'; Script = (Join-Path $base 'dsh-study-buddy\study.py');
     Hb = (Join-Path $base 'dsh-study-buddy\study.hb');   Pause = (Join-Path $base 'dsh-study-buddy\study.pause') }
)

function Log($msg) {
  $t = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
  Add-Content -Path $log -Value "$t $msg" -Encoding UTF8
}

foreach ($it in $items) {
  # 妈妈主动关掉之后 60 分钟内不自动拉回来
  if (Test-Path $it.Pause) {
    $pausedFor = ((Get-Date) - (Get-Item $it.Pause).LastWriteTime).TotalMinutes
    if ($pausedFor -lt 60) {
      Log "$($it.Name) paused by user ($([int]$pausedFor) min ago)"
      continue
    }
  }

  $fresh = $false
  if (Test-Path $it.Hb) {
    $age = ((Get-Date) - (Get-Item $it.Hb).LastWriteTime).TotalSeconds
    $fresh = ($age -lt 30)
  }

  if ($fresh) {
    Log "$($it.Name) ok"
  } else {
    Start-Process -FilePath $pyw -ArgumentList ('"' + $it.Script + '"')
    Log "restarted $($it.Name)"
  }
}
