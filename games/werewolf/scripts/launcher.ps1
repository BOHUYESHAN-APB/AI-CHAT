# 狼人杀AI对战 - 一键启动脚本（Windows PowerShell）

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   狼人杀AI对战 - 桌面应用启动器" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# 修正路径计算：脚本在 games/werewolf/scripts，向上一级到 games/werewolf
$werewolfRoot = Split-Path $PSScriptRoot
$projectRoot = Split-Path (Split-Path $werewolfRoot)
$backendPath = Join-Path $werewolfRoot "backend\app.py"
$frontendPath = Join-Path $werewolfRoot "frontend"

Write-Host "[1/3] 检查Python环境..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python已安装: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Python未安装或不在PATH中" -ForegroundColor Red
    Write-Host "请从 https://www.python.org/downloads/ 下载Python 3.8+" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[2/3] 检查Node.js环境..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "✓ Node.js已安装: $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "✗ Node.js未安装或不在PATH中" -ForegroundColor Red
    Write-Host "请从 https://nodejs.org/ 下载Node.js LTS版本" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[3/3] 检查依赖..." -ForegroundColor Yellow

# 检查Python依赖
$requirementsPath = Join-Path $projectRoot "requirements.txt"
if (Test-Path $requirementsPath) {
    Write-Host "→ 安装Python依赖..." -ForegroundColor Gray
    pip install -q -r $requirementsPath
    Write-Host "✓ Python依赖已安装" -ForegroundColor Green
}

# 检查Node依赖
$nodeModulesPath = Join-Path $frontendPath "node_modules"
$concurrentlyPath = Join-Path $nodeModulesPath ".bin\concurrently.cmd"

function Invoke-NpmInstallWithRetry {
    param(
        [Parameter(Mandatory=$true)] [string] $FrontendPath,
        [int] $Retries = 3,
        [int] $SleepSeconds = 3
    )

    # 常用镜像与 Electron 下载镜像，能显著降低国内环境下载失败概率
    $env:NPM_CONFIG_REGISTRY = $env:NPM_CONFIG_REGISTRY -or 'https://registry.npmmirror.com'
    $env:ELECTRON_MIRROR = $env:ELECTRON_MIRROR -or 'https://npmmirror.com/mirrors/electron/'
    $env:ELECTRON_DOWNLOAD_HOST = $env:ELECTRON_DOWNLOAD_HOST -or 'https://npmmirror.com'

    Push-Location $FrontendPath
    try {
        for ($i = 1; $i -le $Retries; $i++) {
            Write-Host "→ npm install 尝试：#${i}/${Retries} (Registry: $($env:NPM_CONFIG_REGISTRY))" -ForegroundColor Gray
            # 使用更保守的并发与重试参数，减少网络中断影响
            $npmArgs = '--no-audit --network-concurrency=1 --legacy-peer-deps --fetch-retries=5 --fetch-retry-factor=10 --loglevel=info'
            & npm install $npmArgs
            if ($LASTEXITCODE -eq 0) {
                Write-Host "✓ Node依赖已安装/更新" -ForegroundColor Green
                Pop-Location
                return $true
            }

            Write-Host "✗ npm install 第 $i 次失败 (ExitCode: $LASTEXITCODE)。正在清理缓存并稍后重试..." -ForegroundColor Yellow
            & npm cache clean --force | Out-Null
            Start-Sleep -Seconds ($SleepSeconds * $i)
        }

        Write-Host "✗ 所有 npm install 尝试均失败，请查看 npm debug 日志以获取详细信息。" -ForegroundColor Red
        Write-Host "日志路径示例: C:\Users\<you>\AppData\Local\npm-cache\_logs\<timestamp>-debug-0.log" -ForegroundColor Yellow
        Pop-Location
        return $false
    } catch {
        Pop-Location
        throw
    }
}

if (-not (Test-Path $nodeModulesPath)) {
    Write-Host "→ 安装Node依赖（首次运行需要几分钟）..." -ForegroundColor Gray
    $success = Invoke-NpmInstallWithRetry -FrontendPath $frontendPath -Retries 3 -SleepSeconds 4
    if (-not $success) { exit 1 }
} elseif (-not (Test-Path $concurrentlyPath)) {
    Write-Host "→ 更新Node依赖（检测到缺少必需包）..." -ForegroundColor Gray
    $success = Invoke-NpmInstallWithRetry -FrontendPath $frontendPath -Retries 2 -SleepSeconds 3
    if (-not $success) { exit 1 }
} else {
    Write-Host "✓ Node依赖已存在" -ForegroundColor Green
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "   选择启动模式" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "[1] 桌面应用模式（推荐）" -ForegroundColor White
Write-Host "[2] 浏览器开发模式" -ForegroundColor White
Write-Host "[3] 运行自动化测试" -ForegroundColor White
Write-Host "[4] 打包桌面应用" -ForegroundColor White
Write-Host "[0] 退出`n" -ForegroundColor White

$choice = Read-Host "请选择"

switch ($choice) {
    "1" {
        Write-Host "`n启动桌面应用..." -ForegroundColor Cyan
        Push-Location $frontendPath
        npm run electron:dev
        Pop-Location
    }
    "2" {
        Write-Host "`n启动浏览器模式..." -ForegroundColor Cyan
        Write-Host "→ 后端将在端口8080启动" -ForegroundColor Gray
        Write-Host "→ 前端将在端口5173启动" -ForegroundColor Gray
        Write-Host "→ 浏览器访问: http://localhost:5173`n" -ForegroundColor Yellow
        
        # 启动后端（后台）
        $backendJob = Start-Job -ScriptBlock {
            param($path)
            Set-Location (Split-Path $path)
            python $path
        } -ArgumentList $backendPath
        
        Write-Host "✓ 后端已启动（Job ID: $($backendJob.Id)）" -ForegroundColor Green
        
        # 等待2秒让后端启动
        Start-Sleep -Seconds 2
        
        # 启动前端
        Push-Location $frontendPath
        npm run dev
        Pop-Location
        
        # 清理后台任务
        Stop-Job $backendJob
        Remove-Job $backendJob
    }
    "3" {
        Write-Host "`n运行自动化测试..." -ForegroundColor Cyan
        
        # 先启动后端
        $backendJob = Start-Job -ScriptBlock {
            param($path)
            Set-Location (Split-Path $path)
            python $path
        } -ArgumentList $backendPath
        
        Write-Host "→ 等待后端启动..." -ForegroundColor Gray
        Start-Sleep -Seconds 3
        
        # 运行测试
        $testScript = Join-Path $projectRoot "games\werewolf\scripts\test_game_flow.py"
        python $testScript
        
        # 清理
        Stop-Job $backendJob
        Remove-Job $backendJob
        
        Write-Host "`n测试完成！" -ForegroundColor Green
        Read-Host "按回车键退出"
    }
    "4" {
        Write-Host "`n打包桌面应用..." -ForegroundColor Cyan
        Push-Location $frontendPath
        npm run electron:build
        Pop-Location
        
        Write-Host "`n✓ 打包完成！" -ForegroundColor Green
        Write-Host "安装包位置: $frontendPath\dist-electron" -ForegroundColor Yellow
        Read-Host "按回车键退出"
    }
    "0" {
        Write-Host "`n再见！" -ForegroundColor Cyan
        exit 0
    }
    default {
        Write-Host "`n无效选择！" -ForegroundColor Red
        exit 1
    }
}
