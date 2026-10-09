param([string]$Fixture=(Join-Path $PSScriptRoot 'tests/panel-configuration-fixture.json'),[string]$Output)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'PanelConfiguration.psm1') -Force
$f=Get-Content -LiteralPath $Fixture -Raw -Encoding UTF8|ConvertFrom-Json
$inputs=Read-PanelConfigurationInputs -Spec $f
$model=New-PanelConfigurationModel -Inputs $inputs -Spec $f
if($Output){
 # New result only. Raw reports and prior results cannot be overwritten.
 $path=[IO.Path]::GetFullPath($Output)
 $stream=[IO.File]::Open($path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$writer=New-Object IO.StreamWriter($stream,(New-Object Text.UTF8Encoding($true)));try{$writer.Write((ConvertTo-Json -InputObject $model -Depth 90))}finally{$writer.Dispose()}}finally{$stream.Dispose()}
}
$model
