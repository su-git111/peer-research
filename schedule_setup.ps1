# Cowork 자동 스케줄 등록 (Windows 작업 스케줄러) — Claude 없이 도는 방식.
# 실행:  우클릭 → PowerShell로 실행,  또는  powershell -ExecutionPolicy Bypass -File schedule_setup.ps1
# 제거:  powershell -ExecutionPolicy Bypass -File schedule_setup.ps1 -Remove

param([switch]$Remove)

$repo = $PSScriptRoot
$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { Write-Error "python을 찾을 수 없습니다. Python을 설치하고 PATH에 추가하세요."; exit 1 }

$jobs = @(
  @{ Name = "Cowork Weekly"; Arg = "cowork.py weekly"; Trigger = (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:30am); Desc = "주간 계획 생성" },
  @{ Name = "Cowork Daily";  Arg = "cowork.py daily";  Trigger = (New-ScheduledTaskTrigger -Daily -At 8:45am);                    Desc = "일간 체크리스트 생성" },
  @{ Name = "Cowork Night";  Arg = "cowork.py night";  Trigger = (New-ScheduledTaskTrigger -Daily -At 11:35pm);                   Desc = "야간 근무: 큐 실행 + 논문 조회" }
)

foreach ($j in $jobs) {
  if (Get-ScheduledTask -TaskName $j.Name -ErrorAction SilentlyContinue) {
    Unregister-ScheduledTask -TaskName $j.Name -Confirm:$false
  }
}
if ($Remove) { Write-Host "Cowork 스케줄 3개 제거 완료."; exit 0 }

$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
foreach ($j in $jobs) {
  $action = New-ScheduledTaskAction -Execute $py -Argument $j.Arg -WorkingDirectory $repo
  Register-ScheduledTask -TaskName $j.Name -Action $action -Trigger $j.Trigger -Settings $settings -Description $j.Desc | Out-Null
  Write-Host ("등록: {0}  ->  {1} {2}" -f $j.Name, $py, $j.Arg)
}
Write-Host "`n완료. '작업 스케줄러'에서 'Cowork ...' 작업 3개를 확인/수정할 수 있습니다."
Write-Host "로그인 상태에서 실행되며, 절전 중이면 PC를 깨워 실행합니다(WakeToRun)."
