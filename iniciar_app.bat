@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Ambiente .venv nao encontrado.
  echo Crie o ambiente e instale as dependencias de requirements.txt.
  pause
  exit /b 1
)

echo ==================================================
echo RH Juliana — inicializacao unica (.venv + porta 8501)
echo ==================================================

echo.
echo [1/3] Encerrando instancias anteriores nas portas 8501 e 8502...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports = 8501,8502; foreach ($p in $ports) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { $pid = $_.OwningProcess; if ($pid) { Write-Host ('  Encerrando PID ' + $pid + ' na porta ' + $p); Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } } }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'streamlit.*(app\.py|RH_Juliana)') } | ForEach-Object { Write-Host ('  Encerrando Streamlit PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; Start-Sleep -Seconds 1"

echo.
echo [2/3] Validando interpretador e dependencias...
"%~dp0.venv\Scripts\python.exe" -c "import sys; print('  Python:', sys.executable)"
"%~dp0.venv\Scripts\python.exe" -c "import reportlab, streamlit, openpyxl; from repositories.colaborador_repository import caminho_csv_colaboradores; print('  Base CSV:', caminho_csv_colaboradores())"
if errorlevel 1 (
  echo   Instalando dependencias do requirements.txt...
  "%~dp0.venv\Scripts\python.exe" -m pip install -r "%~dp0requirements.txt"
  "%~dp0.venv\Scripts\python.exe" -c "import reportlab, streamlit, openpyxl; from repositories.colaborador_repository import caminho_csv_colaboradores; print('  Base CSV:', caminho_csv_colaboradores())"
  if errorlevel 1 (
    echo Falha na validacao do ambiente.
    pause
    exit /b 1
  )
)

echo.
echo [3/3] Iniciando Streamlit oficial...
echo   URL: http://localhost:8501
echo   NAO use a porta 8502.
echo   NAO execute streamlit pelo Python do sistema.
echo.

"%~dp0.venv\Scripts\python.exe" -m streamlit run app.py --server.port 8501 --server.headless false
endlocal
