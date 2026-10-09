param([string]$Fixture=(Join-Path $PSScriptRoot 'tests/outgoing-fixture.json'),[string]$Output)
$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'OutgoingRows.psm1') -Force
$f=Get-Content -LiteralPath $Fixture -Raw -Encoding UTF8|ConvertFrom-Json
$data=Read-OutgoingInputs -Spec $f
$model=New-OutgoingRowModel -Inputs $data -Spec $f
if($Output){
 $stream=[IO.File]::Open([IO.Path]::GetFullPath($Output),[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
 try{$writer=New-Object IO.StreamWriter($stream,(New-Object Text.UTF8Encoding($true)));try{$writer.Write((ConvertTo-Json -InputObject $model -Depth 90))}finally{$writer.Dispose()}}finally{$stream.Dispose()}
}
$model
