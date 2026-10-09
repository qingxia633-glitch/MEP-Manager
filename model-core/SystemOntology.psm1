# Domain vocabulary only. No drawing IDs, handles, section numbers or task IDs.
function Find-SystemAlias {
 param([string]$Text)
 $aliases=[ordered]@{
  fire_alarm_power='(?:火灾(?:自动)?报警|火灾警报)(?:系统)?(?:的)?(?:供电|电源)'
  fire_phone='消防(?:专用|对讲)?电话(?:系统|网络)?|火警电话(?:系统)?'
  fire_broadcast='消防(?:应急)?广播(?:系统)?|火灾应急广播(?:系统)?'
  fire_alarm='火灾自动报警(?:系统)?|火灾报警(?:系统)?|火灾警报(?:系统)?|火灾声[、，,]?光警报器|火灾声警报器'
  monitoring_security='视频监控(?:系统)?|入侵报警(?:系统)?|安防监控(?:系统)?'
 }
 $accepted=@()
 foreach($key in $aliases.Keys){foreach($m in [regex]::Matches($Text,$aliases[$key])){
  if($m.Index -gt 0 -and $Text.Substring($m.Index-1,1) -in @('非','无')){continue}
  if(@($accepted|Where-Object {$_.start -le $m.Index -and ($_.start+$_.length) -ge ($m.Index+$m.Length)}).Count){continue}
  $hit=[pscustomobject]@{canonicalSystemTypeCandidate=$key;rawTerm=$m.Value;start=$m.Index;length=$m.Length;ontologyVersion='experimental-1';status='candidate'}
  $accepted+=,$hit;$hit
 }}
}
Export-ModuleMember -Function Find-SystemAlias
