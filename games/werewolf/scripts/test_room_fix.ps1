# 房间持久化修复验证脚本
# 使用方法:
#   1. 在终端1运行: python games/werewolf/backend/app.py
#   2. 在终端2运行: .\games\werewolf\scripts\test_room_fix.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "房间持久化修复验证" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查后端是否运行
Write-Host "检查后端连接..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/health" -Method GET -TimeoutSec 2 -ErrorAction Stop
    Write-Host "✓ 后端连接正常" -ForegroundColor Green
} catch {
    Write-Host "❌ 后端未运行!" -ForegroundColor Red
    Write-Host "请先启动后端: python games/werewolf/backend/app.py" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "开始测试..." -ForegroundColor Cyan
Write-Host ""

# 运行Python测试脚本
python games/werewolf/tests/test_room_persistence.py

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✅ 修复验证成功!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "现在可以测试前端:" -ForegroundColor Cyan
    Write-Host "  1. cd games/werewolf/frontend" -ForegroundColor Yellow
    Write-Host "  2. npm install" -ForegroundColor Yellow
    Write-Host "  3. npm run dev" -ForegroundColor Yellow
    Write-Host "  4. 打开浏览器访问前端地址" -ForegroundColor Yellow
    Write-Host "  5. 点击'创建房间',然后切换到'游戏查看'标签" -ForegroundColor Yellow
    Write-Host "  6. 验证房间不会消失" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "❌ 测试失败,请检查日志" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
}
