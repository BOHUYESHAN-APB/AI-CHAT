# Start both backend and frontend in separate PowerShell windows
# Usage: from repo root run: .\games\werewolf\scripts\start_all.ps1
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
# repo root is two levels up from scripts directory
$repoRoot = Resolve-Path (Join-Path $scriptDir '..\..')
$frontend = Join-Path $repoRoot 'games\werewolf\frontend'
$backend = $repoRoot

Write-Host "Starting backend and frontend in separate pwsh windows..."

# Backend: run flask app directly
$backend_cmd = "cd '$backend'; python games/werewolf/backend/app.py"
Start-Process -FilePath pwsh -ArgumentList "-NoExit","-Command",$backend_cmd -WorkingDirectory $backend

# Frontend: if node_modules missing, run npm install then dev server
$node_modules_path = Join-Path $frontend 'node_modules'
if (-not (Test-Path $node_modules_path)) {
    Write-Host "Frontend dependencies not found — running npm install then npm run dev in new window..."
    $frontend_cmd = "cd '$frontend'; npm install; npm run dev"
    Start-Process -FilePath pwsh -ArgumentList "-NoExit","-Command",$frontend_cmd -WorkingDirectory $frontend
} else {
    Write-Host "Starting frontend dev server..."
    $frontend_cmd = "cd '$frontend'; npm run dev"
    Start-Process -FilePath pwsh -ArgumentList "-NoExit","-Command",$frontend_cmd -WorkingDirectory $frontend
}

Write-Host "Launched backend and frontend. Check the new windows for logs."