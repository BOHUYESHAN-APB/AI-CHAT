# Windows PowerShell 脚本：自动启动后端、前端并可执行评测
# 用法示例：
#   .\run_all.ps1 -ApiKey "sk-..." -RunEval
#   .\run_all.ps1 -ApiProvider "deepseek2" -RunEval
# 参数:
#   -ApiKey      : 直接传入 API secret（优先）
#   -ApiProvider : 从项目根的 api_keys.json 中按 provider key 选择
#   -RunEval     : 运行评测脚本（games/werewolf/scripts/run_eval.py）
#   -InstallDeps : 若前端缺少依赖则运行 npm install
param(
  [string]$ApiKey,
  [string]$ApiProvider,
  [switch]$RunEval,
  [switch]$InstallDeps
)

$ErrorActionPreference = "Stop"

# 根路径（脚本所在目录的上两级： repo/games/werewolf/scripts -> repo）
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $scriptRoot "..\..") | Select-Object -ExpandProperty Path

Write-Host "Repository root: $repoRoot"

# 准备日志目录
$logsDir = Join-Path $repoRoot "games\werewolf\logs"
if (-not (Test-Path $logsDir)) {
  New-Item -ItemType Directory -Path $logsDir | Out-Null
}

# 加载 api_keys.json（若存在）并解析
$apiKeysPath = Join-Path $repoRoot "api_keys.json"
$apiDict = @{}
if (Test-Path $apiKeysPath) {
  try {
    $jsonText = Get-Content -Raw -Path $apiKeysPath
    $apiDict = $jsonText | ConvertFrom-Json
  } catch {
    Write-Warning "无法解析 api_keys.json：$($_.Exception.Message)"
  }
} else {
  Write-Host "未找到 api_keys.json，稍后可通过 -ApiKey 显式传入。"
}

# 决定使用的 api key
$selectedApiKey = $null
if ($PSBoundParameters.ContainsKey('ApiKey') -and $ApiKey) {
  $selectedApiKey = $ApiKey
  Write-Host "使用命令行提供的 ApiKey（长度）:" ($selectedApiKey.Length)
} elseif ($PSBoundParameters.ContainsKey('ApiProvider') -and $ApiProvider) {
  if ($apiDict.PSObject.Properties.Name -contains $ApiProvider) {
    $entry = $apiDict.$ApiProvider
    if ($entry.api_key) {
      $selectedApiKey = $entry.api_key
      Write-Host "使用 api_keys.json 中的 provider: $ApiProvider"
    } else {
      Write-Warning "provider '$ApiProvider' 未包含 api_key 字段"
    }
  } else {
    Write-Warning "provider '$ApiProvider' 未在 api_keys.json 中找到"
  }
} else {
  # 使用 api_keys.json 中第一个可用条目
  $firstKey = $apiDict.PSObject.Properties | Select-Object -First 1
  if ($firstKey) {
    $entryName = $firstKey.Name
    $entry = $apiDict.$entryName
    if ($entry.api_key) {
      $selectedApiKey = $entry.api_key
      Write-Host "使用 api_keys.json 中第一个 provider: $entryName"
    }
  }
}

if (-not $selectedApiKey) {
  Write-Warning "未确定 API key。若需真实模型调用，请使用 -ApiKey 或在 api_keys.json 配置。脚本仍会启动后端/前端并使用本地启发式策略。"
} else {
  # 设置环境变量（对本次 PowerShell 及子进程生效）
  $env:OPENAI_API_KEY = $selectedApiKey
  Write-Host "已设置环境变量 OPENAI_API_KEY（隐藏值）"
}

# 启动后端
$backendPy = Join-Path $repoRoot "games\werewolf\backend\app.py"
$backendLog = Join-Path $logsDir "backend.log"
$backendErr = $backendLog + ".err"
Write-Host "启动后端: python $backendPy (日志 -> $backendLog, stderr -> $backendErr)"
# Start-Process 不允许 stdout 和 stderr 指向同一文件；分别写入 .log 与 .err
$backendProc = Start-Process -FilePath python -ArgumentList "-u", "`"$backendPy`"" -RedirectStandardOutput $backendLog -RedirectStandardError $backendErr -NoNewWindow -PassThru
Start-Sleep -Seconds 1

# 启动前端（Vite / npm）
$frontendDir = Join-Path $repoRoot "games\werewolf\frontend"
$frontendLog = Join-Path $logsDir "frontend.log"
if (Test-Path $frontendDir) {
  if ($InstallDeps) {
    Write-Host "安装前端依赖 (npm install) ..."
    Push-Location $frontendDir
    Start-Process -FilePath npm -ArgumentList "install" -NoNewWindow -Wait
    Pop-Location
  }
  Write-Host "启动前端 (npm run dev)，日志 -> $frontendLog"
  # 使用 npm run dev，并将输出记录到日志中（stderr 写入单独文件以避免 Start-Process 限制）
  $npmArgs = @("run","dev","--","--port","5173")
  $frontendErr = $frontendLog + ".err"
  $frontendProc = Start-Process -FilePath npm -ArgumentList $npmArgs -RedirectStandardOutput $frontendLog -RedirectStandardError $frontendErr -WorkingDirectory $frontendDir -NoNewWindow -PassThru
  Start-Sleep -Seconds 1
} else {
  Write-Warning "未找到前端目录 $frontendDir，跳过前端启动。"
}

# 可选：运行评测脚本
if ($RunEval) {
  $evalScript = Join-Path $repoRoot "games\werewolf\scripts\run_eval.py"
  $evalLog = Join-Path $logsDir "eval.log"
  if (Test-Path $evalScript) {
    Write-Host "运行评测脚本: python $evalScript (日志 -> $evalLog)"
    # 等待短暂时间，确保后端已就绪
    Start-Sleep -Seconds 2
    # 以阻塞方式运行评测（便于观察结果），stderr 写入单独文件
    $evalErr = $evalLog + ".err"
    Start-Process -FilePath python -ArgumentList "`"$evalScript`"" -RedirectStandardOutput $evalLog -RedirectStandardError $evalErr -NoNewWindow -Wait
    Write-Host "评测完成，查看日志: $evalLog (stderr -> $evalErr)"
  } else {
    Write-Warning "未找到评测脚本 $evalScript"
  }
}

# 输出运行信息与如何停止
Write-Host "运行信息："
if ($backendProc) {
  Write-Host ("  后端 PID: {0}  日志: {1}" -f $backendProc.Id, $backendLog)
}
if ($frontendProc) {
  Write-Host ("  前端 PID: {0}  日志: {1}" -f $frontendProc.Id, $frontendLog)
}
Write-Host ""
Write-Host "查看实时日志（PowerShell）："
Write-Host "  Get-Content -Path `"$backendLog`" -Wait -Tail 50"
Write-Host "停止服务示例（按 PID）："
Write-Host "  Stop-Process -Id <PID> -Force"

Write-Host "脚本完成。"