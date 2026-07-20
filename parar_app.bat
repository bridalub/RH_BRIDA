@echo off
setlocal
cd /d "%~dp0"
echo Encerrando RH Juliana (portas 8501 e 8502)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ports = 8501,8502; foreach ($p in $ports) { Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Write-Host ('Encerrando PID ' + $_.OwningProcess + ' porta ' + $p); Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -and ($_.CommandLine -match 'streamlit.*(app\.py|RH_Juliana)') } | ForEach-Object { Write-Host ('Encerrando Streamlit PID ' + $_.ProcessId); Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
echo Concluido.
endlocal
