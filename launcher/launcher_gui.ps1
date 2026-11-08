param([int]$AutoCloseMs = 0)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName Microsoft.VisualBasic

$ErrorActionPreference = "Stop"
$Script:SkillDir = Split-Path -Parent $PSScriptRoot
$Script:LogBox = $null
$Script:Status = $null
$Script:PyExe = $null
$Script:PyArgs = @()

function Find-Python {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return @{ Exe = $cmd.Source; Args = @() } }
    $cmd = Get-Command py -ErrorAction SilentlyContinue
    if ($cmd) { return @{ Exe = $cmd.Source; Args = @("-3") } }
    $known = "C:\Users\Administrator.DESKTOP-E0OH4IJ\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $known) { return @{ Exe = $known; Args = @() } }
    return $null
}

function Append-Log([string]$text) {
    if ([string]::IsNullOrWhiteSpace($text)) { return }
    $stamp = Get-Date -Format "HH:mm:ss"
    foreach ($line in ($text -split "`r?`n")) {
        $Script:LogBox.AppendText("[$stamp] $line`n")
    }
    $Script:LogBox.SelectionStart = $Script:LogBox.TextLength
    $Script:LogBox.ScrollToCaret()
    [System.Windows.Forms.Application]::DoEvents()
}

function Set-Status([string]$text) {
    $Script:Status.Text = $text
    [System.Windows.Forms.Application]::DoEvents()
}

function Quote-Arg([string]$a) {
    if ($a -match '[\s"]') { return '"' + ($a -replace '"', '\"') + '"' }
    return $a
}

function Invoke-Bot([string[]]$BotArgs) {
    if (-not $Script:PyExe) { Append-Log "未找到 Python：请安装 Python 3.10+ 或把 python 加入 PATH"; return 1 }
    $all = @()
    $all += $Script:PyArgs
    $all += $BotArgs
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Script:PyExe
    $psi.Arguments = (($all | ForEach-Object { Quote-Arg $_ }) -join " ")
    $psi.WorkingDirectory = $Script:SkillDir
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
    $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
    $psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8"
    $psi.EnvironmentVariables["PYTHONUTF8"] = "1"
    Append-Log ("▶ " + ($all | ForEach-Object { Quote-Arg $_ }) -join " ")
    $p = [System.Diagnostics.Process]::Start($psi)
    $out = $p.StandardOutput.ReadToEnd()
    $err = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    Append-Log $out
    if ($err) { Append-Log $err }
    if ($p.ExitCode -eq 0) {
        Set-Status "完成"
    } else {
        Set-Status "失败（退出码 $($p.ExitCode)）"
    }
    return $p.ExitCode
}

function Select-Folder([string]$title) {
    $dlg = New-Object System.Windows.Forms.FolderBrowserDialog
    $dlg.Description = $title
    $dlg.ShowNewFolderButton = $true
    if ($dlg.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $dlg.SelectedPath }
    return $null
}

function Pick-Platform {
    $p = Select-Folder "请选择平台目录（包含 course-config.json 的文件夹）"
    if (-not $p) { return $null }
    if (-not (Test-Path (Join-Path $p "course-config.json"))) {
        $r = [System.Windows.Forms.MessageBox]::Show("这个目录里没有 course-config.json，仍要继续吗？", "提示", "YesNo", "Question")
        if ($r -ne "Yes") { return $null }
    }
    return $p
}

function New-Platform {
    $dest = Select-Folder "选择新平台的存放位置（建议新建空文件夹或选择父目录）"
    if (-not $dest) { return }
    $title = [Microsoft.VisualBasic.Interaction]::InputBox("请输入平台名称（会显示在页面顶部）", "新建平台", "我的学习平台")
    if (-not $title) { return }
    $res = Select-Folder "选择课程资源根目录（视频/PDF 所在的文件夹）"
    if (-not $res) { return }
    Set-Status "正在创建平台…"
    Invoke-Bot @("new", "--dest", $dest, "--title", $title, "--resources", $res) | Out-Null
    Append-Log "接下来：点「扫描课程」生成配置草稿。"
}

function Scan-Courses {
    $platform = Pick-Platform
    if (-not $platform) { return }
    $res = Select-Folder "选择课程资源根目录（可跳过，默认用配置里的路径）"
    $args = @("scan", "--platform", $platform)
    if ($res) { $args += @("--resources", $res) }
    Set-Status "正在扫描课程…"
    Invoke-Bot $args | Out-Null
}

function Build-Platform {
    $platform = Pick-Platform
    if (-not $platform) { return }
    Set-Status "正在生成课程数据…"
    Invoke-Bot @("build", "--platform", $platform) | Out-Null
}

function Check-Platform {
    $platform = Pick-Platform
    if (-not $platform) { return }
    Set-Status "正在检查内容覆盖…"
    Invoke-Bot @("check", "--platform", $platform) | Out-Null
}

function Start-Platform {
    $platform = Pick-Platform
    if (-not $platform) { return }
    if (-not $Script:PyExe) { Append-Log "未找到 Python"; return }
    $launcher = Join-Path $platform "scripts\launcher.py"
    if (-not (Test-Path $launcher)) { Append-Log "缺少启动器：$launcher"; return }
    $argList = @()
    $argList += $Script:PyArgs
    $argList += @("`"$launcher`"")
    Start-Process -FilePath $Script:PyExe -ArgumentList ($argList -join " ") -WorkingDirectory $platform -WindowStyle Normal
    Append-Log "已启动平台服务窗口；浏览器将打开 http://127.0.0.1:8899/"
    Start-Sleep -Seconds 2
    Start-Process "http://127.0.0.1:8899/"
}

function Open-Agents {
    Start-Process explorer.exe (Join-Path $Script:SkillDir "agents")
}

function Open-Cloud {
    Start-Process "https://github.com/zhangshirun0615/course-platform-builder"
}

# ---------- 界面 ----------
$form = New-Object System.Windows.Forms.Form
$form.Text = "课程平台 Bot"
$form.Size = New-Object System.Drawing.Size(860, 640)
$form.MinimumSize = New-Object System.Drawing.Size(720, 520)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(24, 21, 18)
$form.ForeColor = [System.Drawing.Color]::FromArgb(240, 232, 220)
$form.Font = New-Object System.Drawing.Font("微软雅黑", 9)

$header = New-Object System.Windows.Forms.Panel
$header.Dock = "Top"
$header.Height = 108
$header.BackColor = [System.Drawing.Color]::FromArgb(32, 27, 23)
$form.Controls.Add($header)

$title = New-Object System.Windows.Forms.Label
$title.Text = "课程平台 Bot"
$title.Font = New-Object System.Drawing.Font("微软雅黑", 18, [System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.Color]::FromArgb(255, 138, 61)
$title.Location = New-Object System.Drawing.Point(22, 16)
$title.AutoSize = $true
$header.Controls.Add($title)

$sub = New-Object System.Windows.Forms.Label
$sub.Text = "任意课程资源 → 学习平台   |   技能目录：" + $Script:SkillDir
$sub.Font = New-Object System.Drawing.Font("微软雅黑", 8)
$sub.ForeColor = [System.Drawing.Color]::FromArgb(170, 160, 148)
$sub.Location = New-Object System.Drawing.Point(24, 62)
$sub.AutoSize = $true
$sub.MaximumSize = New-Object System.Drawing.Size(800, 0)
$header.Controls.Add($sub)

$buttonPanel = New-Object System.Windows.Forms.FlowLayoutPanel
$buttonPanel.Dock = "Top"
$buttonPanel.Height = 118
$buttonPanel.Padding = New-Object System.Windows.Forms.Padding(14, 8, 14, 8)
$buttonPanel.BackColor = [System.Drawing.Color]::FromArgb(24, 21, 18)
$form.Controls.Add($buttonPanel)

function Add-Button([string]$text, [scriptblock]$action) {
    $b = New-Object System.Windows.Forms.Button
    $b.Text = $text
    $b.Width = 150
    $b.Height = 42
    $b.FlatStyle = "Flat"
    $b.BackColor = [System.Drawing.Color]::FromArgb(46, 38, 31)
    $b.ForeColor = [System.Drawing.Color]::FromArgb(240, 232, 220)
    $b.FlatAppearance.BorderColor = [System.Drawing.Color]::FromArgb(90, 70, 55)
    $b.Margin = New-Object System.Windows.Forms.Padding(4)
    $b.Add_Click($action)
    $buttonPanel.Controls.Add($b)
    return $b
}

Add-Button "① 新建平台" { New-Platform } | Out-Null
Add-Button "② 扫描课程" { Scan-Courses } | Out-Null
Add-Button "③ 生成平台" { Build-Platform } | Out-Null
Add-Button "④ 检查内容" { Check-Platform } | Out-Null
Add-Button "⑤ 启动平台" { Start-Platform } | Out-Null
Add-Button "打开 Agent 目录" { Open-Agents } | Out-Null
Add-Button "打开云端仓库" { Open-Cloud } | Out-Null
Add-Button "清空日志" {
    $Script:LogBox.Clear()
} | Out-Null

$Script:LogBox = New-Object System.Windows.Forms.RichTextBox
$Script:LogBox.Dock = "Fill"
$Script:LogBox.BackColor = [System.Drawing.Color]::FromArgb(16, 14, 12)
$Script:LogBox.ForeColor = [System.Drawing.Color]::FromArgb(220, 212, 200)
$Script:LogBox.Font = New-Object System.Drawing.Font("Consolas", 9)
$Script:LogBox.ReadOnly = $true
$Script:LogBox.BorderStyle = "None"
$Script:LogBox.WordWrap = $false
$form.Controls.Add($Script:LogBox)

$statusPanel = New-Object System.Windows.Forms.Panel
$statusPanel.Dock = "Bottom"
$statusPanel.Height = 30
$statusPanel.BackColor = [System.Drawing.Color]::FromArgb(32, 27, 23)
$form.Controls.Add($statusPanel)

$Script:Status = New-Object System.Windows.Forms.Label
$Script:Status.Text = "就绪"
$Script:Status.ForeColor = [System.Drawing.Color]::FromArgb(180, 170, 158)
$Script:Status.Location = New-Object System.Drawing.Point(14, 7)
$Script:Status.AutoSize = $true
$statusPanel.Controls.Add($Script:Status)

$py = Find-Python
if ($py) {
    $Script:PyExe = $py.Exe
    $Script:PyArgs = $py.Args
    Append-Log "Python：$($py.Exe)"
} else {
    Append-Log "⚠ 未找到 Python，请先安装 Python 3.10+ 并加入 PATH"
}
Append-Log "技能目录：$SkillDir"
Append-Log "使用顺序：新建平台 → 扫描课程 → 编辑 course-config.json → 生成平台 → 检查内容 → 启动平台"
Append-Log "两个关键 Agent：agents\ui-adjuster.md（界面/UI）、agents\content-optimizer.md（课程内容体系）"

if ($AutoCloseMs -gt 0) {
    $timer = New-Object System.Windows.Forms.Timer
    $timer.Interval = $AutoCloseMs
    $timer.Add_Tick({ $timer.Stop(); $form.Close() })
    $timer.Start()
}

[void]$form.ShowDialog()
