Set-StrictMode -Version 2
function Read-BlockProbe {
 param([Parameter(Mandatory)][string]$Path)
 $lines=Get-Content -LiteralPath $Path -Encoding UTF8
 if($lines -notcontains 'END_OF_REPORT' -or $lines -notcontains 'ReadErrorCount=0' -or @($lines|Where-Object {$_ -match '^(INCOMPLETE_REPORT|BlockError|EntityError)='}).Count){throw 'Incomplete/error probe cannot establish equality'}
 $blocks=@();$b=$null;$e=$null
 foreach($line in $lines){
  if($line -match '^Block_BEGIN="(.*)"$'){$b=[pscustomobject]@{Name=$matches[1];Definition=@();Entities=@()};$blocks+=,$b}
  elseif($line -match '^DefinitionDXF:(-?\d+)=(.*)$'){$b.Definition+=,@{Code=[int]$matches[1];Value=$matches[2]}}
  elseif($line -match '^EntityHandle="(.*)"$'){$e=[pscustomobject]@{Handle=$matches[1];Fields=@()};$b.Entities+=,$e}
  elseif($line -match '^(DXF|LayerDXF):(-?\d+)=(.*)$'){
   $prefix=$matches[1];$code=[int]$matches[2];$v=$matches[3]
   if($prefix -eq 'LayerDXF'){$code+=10000}
   if($null -ne $e){$e.Fields+=,@{Code=$code;Value=$v}}
  }
  elseif($line -match '^Subentity_(BEGIN|END)$'){$e.Fields+=,@{Code=-999;Value=$line}}
  elseif($line -match '^BinaryDXFOmitted=') {throw 'Binary omission: complete definition comparison unsupported'}
  elseif($line -eq 'Entity_END'){$e=$null}
 }
 [pscustomobject]@{SourcePath=(Resolve-Path $Path).Path;Snapshot=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash;Blocks=$blocks}
}
function Select-ProbeFields($entity,$mode){
 @($entity.Fields|Where-Object {
  $c=$_.Code;$base=$c;if($c -ge 10000){$base=$c-10000}
  $identity=$base -in @(-1,-2,5,105) -or ($base -ge 320 -and $base -le 369) -or ($base -ge 390 -and $base -le 399)
  if($identity){$false}
  elseif($mode -eq 'content'){$true}
  elseif($mode -eq 'style'){$c -in @(0,8,6,7,48,62,370,420,430,440,10002,10006,10062,10070,10370,10420,10430)}
  elseif($mode -eq 'visibility'){$c -in @(0,60,10062,10070)}
  else {$c -lt 10000 -and ($c -in @(-999,0,1,2,3,9,38,39,40,41,42,43,44,45,50,51,70,71,72,73,74,75,90) -or ($c -ge 10 -and $c -le 37) -or ($c -ge 210 -and $c -le 239))}
 })
}
function Test-ProbeFields([AllowEmptyCollection()][object[]]$a,[AllowEmptyCollection()][object[]]$b,$tol){
 $a=@($a);$b=@($b)
 if($a.Count -ne $b.Count){return $false}
 for($i=0;$i -lt $a.Count;$i++){
  if($a[$i].Code -ne $b[$i].Code){return $false}
  $x=$a[$i].Value;$y=$b[$i].Value
  if($x -ceq $y){continue}
  # Tolerance only for geometric numeric fields; strings/codes/flags remain exact.
  $c=$a[$i].Code
  if(!((($c -ge 10 -and $c -le 59) -or ($c -ge 210 -and $c -le 239)) -and $x -match '^[()0-9eE+. -]+$' -and $y -match '^[()0-9eE+. -]+$')){return $false}
  $xx=@([regex]::Matches($x,'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})
  $yy=@([regex]::Matches($y,'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?')|ForEach-Object {[double]::Parse($_.Value,[cultureinfo]::InvariantCulture)})
  if($xx.Count -ne $yy.Count){return $false};for($j=0;$j -lt $xx.Count;$j++){if([math]::Abs($xx[$j]-$yy[$j]) -gt $tol){return $false}}
 }
 return $true
}
function Compare-ProbeEntities {
 param([object[]]$Left,[object[]]$Right,[ValidateSet('content','geometry','style','visibility')][string]$Mode='content',[double]$Tolerance=0.00001)
 if($Tolerance -le 0 -or [double]::IsNaN($Tolerance) -or [double]::IsInfinity($Tolerance)){throw 'Positive finite tolerance required'}
 # Capture even zero/one selected fields as arrays, never a scalar hashtable.
 $lf=@{};$rf=@{}
 for($i=0;$i -lt $Left.Count;$i++){$lf[$i]=@(Select-ProbeFields $Left[$i] $Mode)}
 for($j=0;$j -lt $Right.Count;$j++){$rf[$j]=@(Select-ProbeFields $Right[$j] $Mode)}
 $adj=@{};for($i=0;$i -lt $Left.Count;$i++){$adj[$i]=@();for($j=0;$j -lt $Right.Count;$j++){if(Test-ProbeFields $lf[$i] $rf[$j] $Tolerance){$adj[$i]+=,$j}}}
 # Maximum bipartite matching preserves duplicate multiplicity, avoids greedy tolerance failures.
 $match=@{}
 function Visit([int]$i,$seen){foreach($j in $adj[$i]){if($seen.ContainsKey($j)){continue};$seen[$j]=$true;if(!$match.ContainsKey($j) -or (Visit $match[$j] $seen)){$match[$j]=$i;return $true}};return $false}
 for($i=0;$i -lt $Left.Count;$i++){[void](Visit $i @{})}
 $pairs=@(foreach($j in $match.Keys){[pscustomobject]@{LeftHandle=$Left[$match[$j]].Handle;RightHandle=$Right[$j].Handle}})
 [pscustomobject]@{Mode=$Mode;Equal=($match.Count -eq $Left.Count -and $match.Count -eq $Right.Count);Matched=$match.Count;LeftCount=$Left.Count;RightCount=$Right.Count;Pairs=$pairs;UnmatchedLeft=@(for($i=0;$i -lt $Left.Count;$i++){if($match.Values -notcontains $i){$Left[$i].Handle}});UnmatchedRight=@(for($j=0;$j -lt $Right.Count;$j++){if(!$match.ContainsKey($j)){$Right[$j].Handle}})}
}
Export-ModuleMember -Function Read-BlockProbe,Compare-ProbeEntities
