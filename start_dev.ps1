# start_dev.ps1 - Runs FastAPI backend and Vite frontend together
Write-Host "Starting Bekon Interview Platform..." -ForegroundColor Cyan

$backendProcess = Start-Process -FilePath ".\venv\Scripts\python.exe" -ArgumentList "-m uvicorn backend.main:app --port 8000 --reload" -PassThru
Write-Host "FastAPI backend started (PID $($backendProcess.Id)) on http://127.0.0.1:8000" -ForegroundColor Green

Set-Location "frontend"
Write-Host "Starting Vite React development server on http://127.0.0.1:5173..." -ForegroundColor Green
npm run dev
