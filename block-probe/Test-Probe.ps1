$ErrorActionPreference='Stop'
Import-Module (Join-Path $PSScriptRoot 'BlockProbe.psm1') -Force
$n=0
function Check($v,$msg){if(!$v){throw $msg};$script:n++}
function Entity($h,$x,$color='256',$hidden='0') { [pscustomobject]@{Handle=$h;Fields=@(@{Code=0;Value='"LINE"'},@{Code=8;Value='"0"'},@{Code=62;Value=$color},@{Code=60;Value=$hidden},@{Code=10;Value="($x 0.0 0.0)"},@{Code=11;Value='(10.0 0.0 0.0)'})} }
$a=Entity 'A' '0.0';$b=Entity 'OTHER' '0.000001'
$proxy=[pscustomobject]@{Handle='P';Fields=@(@{Code=0;Value='"ACAD_PROXY_ENTITY"'})}
Check ((Compare-ProbeEntities @($proxy) @($proxy) geometry 0.00001).Equal) 'single selected field remains an array'
$empty=[pscustomobject]@{Handle='empty';Fields=@()}
Check ((Compare-ProbeEntities @($empty) @($empty) geometry 0.00001).Equal) 'empty selected fields remain an array'
Check ((Compare-ProbeEntities @($a) @($b) geometry 0.00001).Equal) 'handle independence and coordinate tolerance'
Check (!(Compare-ProbeEntities @($a) @($b) geometry 0.0000001).Equal) 'outside tolerance'
Check (!(Compare-ProbeEntities @($a,$a) @($b) geometry 0.00001).Equal) 'duplicate multiplicity'
$c=Entity 'C' '0' '3' '1'
Check ((Compare-ProbeEntities @($a) @($c) geometry 0.00001).Equal) 'style separate from geometry'
Check (!(Compare-ProbeEntities @($a) @($c) style 0.00001).Equal) 'color difference'
Check (!(Compare-ProbeEntities @($a) @($c) visibility 0.00001).Equal) 'DXF60 difference'
$layerChanged=Entity 'L' '0.0';$layerChanged.Fields[1].Value='"different"'
Check (!(Compare-ProbeEntities @($a) @($layerChanged) style 0.00001).Equal) 'layer difference'
Check ((Compare-ProbeEntities @($a,$c) @($c,$a) content 0.00001).Equal) 'entity enumeration order independence'
$tmp=Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()+'.txt')
try {
 @('Block_BEGIN="A"','DefinitionDXF:10=(0 0 0)','EntityHandle="AA"','DXF:0="LINE"','DXF:8="0"','DXF:60=0','DXF:10=(0 0 0)','DXF:11=(10 0 0)','Entity_END','DirectEntityCount=1','Block_END','ReadErrorCount=0','END_OF_REPORT')|Set-Content -LiteralPath $tmp -Encoding UTF8
 $p=Read-BlockProbe $tmp
 Check ($p.Blocks.Count -eq 1 -and $p.Blocks[0].Entities.Count -eq 1) 'probe record parsing'
 Check ($p.Blocks[0].Entities[0].Handle -eq 'AA') 'source Handle retained'
 Check ($p.Snapshot.Length -eq 64) 'snapshot SHA256'
 $out=& (Join-Path $PSScriptRoot 'Compare-Blocks.ps1') -Report $tmp
 Check (($out|ConvertFrom-Json).Snapshot -eq $p.Snapshot) 'comparison entrypoint provenance'
} finally {Remove-Item -LiteralPath $tmp}
$lsp=Get-Content (Join-Path $PSScriptRoot 'BlockDefinitionProbe.lsp') -Raw
Check ($lsp -notmatch '(?i)\((?:entmod|entmake|entdel|command|vla-put-\S*|vla-explode|vla-resetblock)\b') 'no CAD mutation calls'
Check ($lsp.Contains('(vlax-for obj block')) 'direct definition traversal'
Check ($lsp.Contains('Nested INSERT references are recorded, not expanded')) 'nonrecursive contract'
Check ($lsp.Contains('(defun c:MEPSUBBLOCKPROBE () (bp:run ''("$element$00000576" "A$C705C5744")))')) 'exact two-target scope'
Check ($lsp.Contains('DefinitionIsDynamicBlockStatus')) 'dynamic definition status explicit'
foreach($key in @('LayerDXF','DXF60','ColorSource','LocalCoordinates','ReadErrorCount')){Check ($lsp.Contains($key)) "preserve $key"}
$clean=[regex]::Replace($lsp,'"(?:\\.|[^"\\])*"|;[^\r\n]*','');$d=0
foreach($ch in $clean.ToCharArray()){if($ch -eq '('){$d++};if($ch -eq ')'){$d--;if($d -lt 0){throw 'unbalanced'}}}
Check ($d -eq 0) 'balanced Lisp'
"PASS: $n probe checks; CAD runtime not exercised"
