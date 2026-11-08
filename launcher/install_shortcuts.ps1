$ErrorActionPreference = "Stop"

$here = $PSScriptRoot
$skill = Split-Path -Parent $here
$wscript = Join-Path $env:WINDIR "System32\wscript.exe"
$vbs = Join-Path $here "launch.vbs"
$icon = Join-Path $here "bot.ico"
$desktop = [Environment]::GetFolderPath("Desktop")
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"

function Make-Shortcut([string]$dir, [string]$name) {
    if (-not (Test-Path $dir)) { return }
    $lnkPath = Join-Path $dir ($name + ".lnk")
    $shell = New-Object -ComObject WScript.Shell
    $sc = $shell.CreateShortcut($lnkPath)
    $sc.TargetPath = $wscript
    $sc.Arguments = '"' + $vbs + '"'
    $sc.WorkingDirectory = $here
    if (Test-Path $icon) { $sc.IconLocation = $icon + ",0" }
    $sc.Description = "课程平台 Bot：任意课程资源 → 学习平台"
    $sc.Save()
    Write-Host "已创建：$lnkPath"
}

Make-Shortcut $desktop "课程平台 Bot"
Make-Shortcut $startMenu "课程平台 Bot"
Write-Host ""
Write-Host "完成。桌面和开始菜单都可以找到「课程平台 Bot」。"
Write-Host "技能目录：$skill"
