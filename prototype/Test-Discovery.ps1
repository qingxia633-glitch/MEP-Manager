$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'Discover.psm1') -Force -DisableNameChecking
$config=Get-Content (Join-Path $PSScriptRoot 'discovery-window.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$report=Join-Path $PSScriptRoot '../local_test_data/MEP-entity-report.txt'
# Discovery finishes BEFORE ground truth is read.
$result=Find-LocalContours $report $config
$gold=Get-Content (Join-Path $PSScriptRoot 'discovery-expected.json') -Raw | ConvertFrom-Json
$expected=@($gold.inner)+@($gold.outer)
$missing=@($expected | Where-Object {$_ -notin $result.candidates.handle})
if($missing.Count){throw "Missing: $missing"}
function HasChain($chains,$handles){
 foreach($c in $chains){$s=$c.handles -join ',';$r=@($handles);[array]::Reverse($r)
 if($s.Contains(($handles -join ',')) -or $s.Contains(($r -join ','))){return $true}}
 return $false
}
if(-not (HasChain @($result.chains | Where-Object kind -eq 'chamfer') $gold.inner)){throw 'Inner chain missing'}
if(-not (HasChain @($result.chains | Where-Object kind -eq 'rightAngle') $gold.outer)){throw 'Outer chain missing'}
# Rename every handle: discovery geometry and counts must not depend on identity.
$raw=Get-Content $report -Raw -Encoding UTF8
$renamed=[regex]::Replace($raw,'(?m)^EntityHandle="([^"]+)"', 'EntityHandle="blind-$1"')
$again=Find-LocalContours -Text $renamed -Config $config
if($again.chains.Count -ne $result.chains.Count -or $again.pairs.Count -ne $result.pairs.Count -or $again.connections.Count -ne $result.connections.Count){throw 'Handle renaming changed discovery'}
# Check identities cannot leak through module/config and validate selected pair coverage.
$algorithm=Get-Content (Join-Path $PSScriptRoot 'Discover.psm1') -Raw
foreach($h in $expected){if($algorithm.Contains($h) -or (ConvertTo-Json $config).Contains($h)){throw 'Ground truth leaked into discovery inputs'}}
$selected=@(foreach($pair in $result.pairs){foreach($c in $result.chains){if($c.id -in @($pair.inner,$pair.outer)){$c.handles}}}) | Sort-Object -Unique
if(@($expected | Where-Object {$_ -notin $selected}).Count){throw 'Supported pair misses expected handles'}
# Synthetic tolerance and nonconnecting-crossing tests, independent of real handles.
function SegmentText($id,$p,$q){
 "EntityHandle=`"$id`"`nDXF_Type=`"LINE`"`nStart_WCS=($p)`nEnd_WCS=($q)`n"
}
$small= $config | ConvertTo-Json | ConvertFrom-Json
$small.min=@(-10,-10,-10);$small.max=@(10,10,10);$small.endpointTolerance=0.001
function Synthetic($body){"LAYER_BEGIN=`"$($small.layer)`"`n$body`nLayerEntityCount=2`nLAYER_END`nEND_OF_REPORT:"}
$body=(SegmentText 'a' '0 0 0' '1 0 0')+(SegmentText 'b' '1.0005 0 0' '1 1 0')
$near=Find-LocalContours -Text (Synthetic $body) -Config $small
if($near.connections.Count -ne 1){throw 'Within-tolerance endpoints not connected'}
$small.endpointTolerance=0.0001
$far=Find-LocalContours -Text (Synthetic $body) -Config $small
if($far.connections.Count -ne 0){throw 'Outside-tolerance endpoints connected'}
$body=(SegmentText 'a' '-1 0 0' '1 0 0')+(SegmentText 'b' '0 -1 0' '0 1 0')
if((Find-LocalContours -Text (Synthetic $body) -Config $small).connections.Count -ne 0){throw 'Interior crossing was connected'}
$body=(SegmentText 'a' '0 0 0' '1 0 0')+(SegmentText 'b' '1 0 1' '1 1 1')
if((Find-LocalContours -Text (Synthetic $body) -Config $small).connections.Count -ne 0){throw 'Different elevations connected'}
$result | ConvertTo-Json -Depth 20 | Set-Content (Join-Path $PSScriptRoot '../local_test_data/discovery-result.json') -Encoding UTF8
$roundtrip=Get-Content (Join-Path $PSScriptRoot '../local_test_data/discovery-result.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($roundtrip.chains[0].points[0].Count -ne 3 -or $roundtrip.candidates[0].vertices[0].Count -ne 3){throw 'JSON coordinates are not XYZ arrays'}
[pscustomobject]@{status='PASS';candidates=$result.candidates.Count;endpointConnections=$result.connections.Count;chains=$result.chains.Count;pairs=$result.pairs.Count;missing=$missing;extraCandidates=@($result.candidates.handle | Where-Object {$_ -notin $expected});extraInSupportedPair=@($selected | Where-Object {$_ -notin $expected});checks=@('six handles covered','inner ordered subsequence recovered','outer ordered subsequence recovered','all handles renamed without result count change','source/config isolation','supported pair covers ground truth','inside tolerance','outside tolerance','interior crossing disconnected','different elevations disconnected')} | ConvertTo-Json -Depth 5
$result.chains | Select-Object id,kind,@{n='handles';e={$_.handles -join ' -> '}} | Format-Table -AutoSize
$result.pairs | ConvertTo-Json -Depth 6
