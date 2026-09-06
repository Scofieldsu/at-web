# 结束占用 at-web 后端（run_server / at-web 路径）的 python 进程
$procs = Get-CimInstance Win32_Process -Filter 'Name="python.exe" or Name="pythonw.exe"' | Where-Object { $_.CommandLine -match 'run_server|at-web' }
foreach ($p in $procs) {
    Write-Output ("killing " + $p.ProcessId + " :: " + $p.CommandLine)
    [void]$p | Invoke-CimMethod -MethodName Delete
}
Start-Sleep -Seconds 1
Write-Output "done"
