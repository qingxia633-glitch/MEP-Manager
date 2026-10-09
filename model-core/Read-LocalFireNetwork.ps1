param([string]$OutputPath)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'LocalLogicalNetwork.psm1') -Force
Import-Module (Join-Path $PSScriptRoot 'LocalFireNetworkSample.psm1') -Force
$result=ConvertTo-LocalLogicalNetworkCandidates (Read-LocalFireNetworkBundle)
if($OutputPath){
 $result|ConvertTo-Json -Depth 90|Set-Content -LiteralPath $OutputPath -Encoding UTF8
 $result.summary|Format-Table -AutoSize
}else{$result|ConvertTo-Json -Depth 90}
