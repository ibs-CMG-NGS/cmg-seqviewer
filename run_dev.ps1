# 개발 모드 실행 스크립트
# 사용법: .\run_dev.ps1

param(
    [switch]$Debug,
    [switch]$Test,
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

# 색상 출력 함수
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# 프로젝트 루트로 이동
Set-Location $PSScriptRoot

Write-ColorOutput "========================================" "Cyan"
Write-ColorOutput "  RNA-Seq Data Analyzer - Dev Mode" "Cyan"
Write-ColorOutput "========================================" "Cyan"
Write-Host ""

# 가상환경 확인 및 활성화
if (-not $env:VIRTUAL_ENV) {
    Write-ColorOutput "[1/4] Activating virtual environment..." "Yellow"
    
    if (Test-Path ".\venv\Scripts\Activate.ps1") {
        & ".\venv\Scripts\Activate.ps1"
        Write-ColorOutput "      ✓ Virtual environment activated" "Green"
    } else {
        Write-ColorOutput "      ✗ Virtual environment not found!" "Red"
        Write-ColorOutput "      Run: python -m venv venv" "Yellow"
        exit 1
    }
} else {
    Write-ColorOutput "[1/4] Virtual environment already active" "Green"
}

# PYTHONPATH 설정
Write-ColorOutput "[2/4] Setting PYTHONPATH..." "Yellow"
$env:PYTHONPATH = "$PWD\src"
Write-ColorOutput "      ✓ PYTHONPATH = $env:PYTHONPATH" "Green"

# 클린 모드
if ($Clean) {
    Write-ColorOutput "[3/4] Cleaning cache files..." "Yellow"
    Get-ChildItem -Path . -Include __pycache__,*.pyc,.pytest_cache,.mypy_cache -Recurse -Force | Remove-Item -Recurse -Force
    Write-ColorOutput "      ✓ Cache cleaned" "Green"
} else {
    Write-ColorOutput "[3/4] Skipping clean (use -Clean to clean cache)" "Gray"
}

# 테스트 모드
if ($Test) {
    Write-ColorOutput "[4/4] Running tests..." "Yellow"
    python -m pytest test/ -v
    
    if ($LASTEXITCODE -eq 0) {
        Write-ColorOutput "      ✓ All tests passed!" "Green"
    } else {
        Write-ColorOutput "      ✗ Tests failed!" "Red"
        exit $LASTEXITCODE
    }
    exit 0
}

# 프로그램 실행
Write-ColorOutput "[4/4] Starting RNA-Seq Analyzer..." "Yellow"
Write-Host ""
Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"
Write-Host ""

if ($Debug) {
    # 디버그 모드로 실행
    python -m pdb src\main.py
} else {
    # 일반 실행
    python src\main.py
}

# 종료 코드 확인
Write-Host ""
Write-ColorOutput "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" "Cyan"

if ($LASTEXITCODE -eq 0) {
    Write-ColorOutput "Program exited successfully." "Green"
} else {
    Write-ColorOutput "Program exited with error code: $LASTEXITCODE" "Red"
    Write-Host ""
    Write-ColorOutput "Recent logs:" "Yellow"
    
    # 최근 로그 파일 표시
    $logFile = Get-ChildItem logs\*.log -ErrorAction SilentlyContinue | 
               Sort-Object LastWriteTime -Descending | 
               Select-Object -First 1
    
    if ($logFile) {
        Write-ColorOutput "From: $($logFile.Name)" "Gray"
        Get-Content $logFile.FullName -Tail 20 | ForEach-Object {
            if ($_ -match "ERROR|CRITICAL") {
                Write-ColorOutput $_ "Red"
            } elseif ($_ -match "WARNING") {
                Write-ColorOutput $_ "Yellow"
            } else {
                Write-Host $_
            }
        }
    }
}

Write-Host ""
