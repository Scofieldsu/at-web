# 以后台分离进程启动 at-web 后端（脱离 bash 工具进程树）
$cmd = 'G:\yu\at-web\.venv\Scripts\python.exe G:\yu\at-web\run_server.py'
$r = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmd }
Write-Output ("PID=" + $r.ProcessId + " Ret=" + $r.ReturnValue)
