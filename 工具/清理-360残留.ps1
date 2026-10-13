# ============================================================
#  小鲸鱼 · 360 残留清理脚本 🐋
#  用法（由小D执行，妈妈不用管）：
#    预览（什么都不删）： powershell -File 清理-360残留.ps1
#    真删（进回收站）  ： powershell -File 清理-360残留.ps1 -Go
#  安全说明：走「回收站」，随时能还原。确认无误后再清空回收站才真正腾空间。
# ============================================================
param([switch]$Go)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$B = Join-Path $root '备份'

# ---- 清单：A 纯缓存 / B 360插件与本地存储 / C 老下载器与回收站残留 ----
$MANIFEST = [ordered]@{

  'A 纯缓存与日志（100% 垃圾，放心删）' = @(
    "$B\360浏览器-数据抢救\User Data\GrShaderCache64"
    "$B\360浏览器-数据抢救\User Data\GrShaderCache"
    "$B\360浏览器-数据抢救\User Data\ShaderCache64"
    "$B\360浏览器-数据抢救\User Data\ShaderCache"
    "$B\360浏览器-数据抢救\User Data\old_GrShaderCache64_000"
    "$B\360浏览器-数据抢救\User Data\GraphiteDawnCache"
    "$B\360浏览器-数据抢救\User Data\Default\DawnGraphiteCache"
    "$B\360浏览器-数据抢救\User Data\Default\DawnWebGPUCache"
    "$B\360浏览器-数据抢救\User Data\Default\GPUCache64"
    "$B\360浏览器-数据抢救\User Data\v3update"
    "$B\360浏览器-数据抢救\User Data\Default\Extension State"
    "$B\360浏览器-数据抢救\User Data\BrowserMetrics-spare.pma"
  )

  'B 360 的插件与本地存储（360 不用了就删）' = @(
    "$B\360浏览器-数据抢救\User Data\Default\Extensions"
    "$B\360浏览器-数据抢救\User Data\Default\Local Extension Settings"
    "$B\360浏览器-数据抢救\User Data\Default\Local Storage"
    "$B\360浏览器-数据抢救\User Data\Default\apps"
    "$B\360浏览器-数据抢救\User Data\Default\45eef1f5bc25e437c54bc5c53638616f"
    "$B\360浏览器-数据抢救\User Data\Default\HisDailyBackup"
    "$B\360浏览器-数据抢救\User Data\Default\shared_proto_db"
    "$B\360浏览器-数据抢救\User Data\chromeshelladddesk"
    "$B\360浏览器-数据抢救\User Data\chromeshellappdesk"
    "$B\360浏览器-数据抢救\User Data\360program"
    "$B\360浏览器-数据抢救\User Data\safemon"
    "$B\360浏览器-数据抢救\User Data\segmentation_platform"
  )

  'C 老下载器与回收站残留' = @(
    "$B\360残留-小文件夹备份\360极速浏览器X下载"
    "$B\360残留-小文件夹备份\360RecycleBin"
    "$B\360残留-小文件夹备份\360用户文件"
    "$B\360残留-小文件夹备份\360Downloads"
  )
}

function Get-Size($p) {
  if (Test-Path -LiteralPath $p) {
    $f = Get-ChildItem -LiteralPath $p -Recurse -File -Force -ErrorAction SilentlyContinue
    if ($null -eq $f) { return @(0, 0) }
    return @((($f | Measure-Object Length -Sum).Sum), $f.Count)
  }
  return @(-1, -1)   # 不存在
}

$grand = 0
Write-Output ''
Write-Output '========== 清理清单 =========='
foreach ($tier in $MANIFEST.Keys) {
  Write-Output ''
  Write-Output "【$tier】"
  $sub = 0
  foreach ($p in $MANIFEST[$tier]) {
    $sz, $n = Get-Size $p
    $rel = $p.Substring($B.Length + 1)
    if ($sz -lt 0) { Write-Output ("   --   {0}  ← 已不在" -f $rel); continue }
    $sub += $sz
    Write-Output ("  {0,7:N1} MB  {1,4} 个文件   {2}" -f ($sz / 1MB), $n, $rel)
  }
  $grand += $sub
  Write-Output ("  小计：{0:N1} MB" -f ($sub / 1MB))
}
Write-Output ''
Write-Output ("========== 合计可腾出：{0:N1} MB ==========" -f ($grand / 1MB))
Write-Output ''

if (-not $Go) {
  Write-Output '（预览模式，什么都没删。加 -Go 才真删）'
  exit 0
}

Write-Output '>>> 开始删除（进回收站，可还原）...'
foreach ($tier in $MANIFEST.Keys) {
  foreach ($p in $MANIFEST[$tier]) {
    if (-not (Test-Path -LiteralPath $p)) { continue }
    Add-Type -AssemblyName Microsoft.VisualBasic
    if ((Get-Item -LiteralPath $p).PSIsContainer) {
      [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteDirectory(
        $p, 'OnlyErrorDialogs', 'SendToRecycleBin')
    } else {
      [Microsoft.VisualBasic.FileIO.FileSystem]::DeleteFile(
        $p, 'OnlyErrorDialogs', 'SendToRecycleBin')
    }
    Write-Output ("  已移入回收站：{0}" -f $p.Substring($B.Length + 1))
  }
}
Write-Output '>>> 完成 ✅'
