Set-StrictMode -Version 2
function Get-TextLayoutBox($Record) {
 if($Record.entityType -ne 'TEXT'){return $null}
 $r=$Record.rawRecord
 if($r -notmatch '(?m)^bboxStatus="read"\r?$' -or $r -notmatch '(?m)^bboxFrame="WCS"\r?$'){return $null}
 $lo=[regex]::Match($r,'(?m)^bboxMin=\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)');$hi=[regex]::Match($r,'(?m)^bboxMax=\(([-\d.]+) ([-\d.]+) ([-\d.]+)\)')
 if(!$lo.Success -or !$hi.Success){return $null}
 $a=@(1..3|ForEach-Object {[double]::Parse($lo.Groups[$_].Value,[cultureinfo]::InvariantCulture)});$b=@(1..3|ForEach-Object {[double]::Parse($hi.Groups[$_].Value,[cultureinfo]::InvariantCulture)})
 if($b[0] -le $a[0] -or $b[1] -le $a[1] -or $b[2] -lt $a[2]){return $null}
 $height=[regex]::Match($r,'(?m)^TextHeight=([\d.]+)')
 [pscustomobject]@{sourceRef=$Record.id;minX=$a[0];maxX=$b[0];minY=$a[1];maxY=$b[1];height=if($height.Success){[double]::Parse($height.Groups[1].Value,[cultureinfo]::InvariantCulture)}else{$b[1]-$a[1]};frame='WCS';status='read'}
}
function Get-BoxXOverlap($A,$B) {
 if(!$A -or !$B){return 0.0};$w=[math]::Min($A.maxX-$A.minX,$B.maxX-$B.minX);if($w -le 0){return 0.0}
 [math]::Min(1.0,[math]::Max(0.0,[math]::Min($A.maxX,$B.maxX)-[math]::Max($A.minX,$B.minX))/$w)
}
function Get-BoxReferencePoint($Record,$Box) {
 if(!$Box){return $Record}
 [pscustomobject]@{x=($Box.minX+$Box.maxX)/2;y=($Box.minY+$Box.maxY)/2;sourceSnapshot=$Record.sourceSnapshot}
}
function New-ContinuationEvidence($Start,$Previous,$Next,$StartBox,$PreviousBox,$NextBox,[double]$Pitch,[bool]$Blocked) {
 $legacy=($Next.x -ge $Start.x-1.4*$Pitch -and $Next.x -le $Start.x+.2*$Pitch)
 $available=($null -ne $StartBox -and $null -ne $PreviousBox -and $null -ne $NextBox)
 $columnOverlap=0.0;$previousOverlap=0.0;$gap=$null;$sizeCompatible=$true
 if($available){
  $extent=[pscustomobject]@{minX=[math]::Min($StartBox.minX,$PreviousBox.minX);maxX=[math]::Max($StartBox.maxX,$PreviousBox.maxX)}
  $columnOverlap=Get-BoxXOverlap $extent $NextBox;$previousOverlap=Get-BoxXOverlap $PreviousBox $NextBox
  $gap=[math]::Max(0.0,[math]::Max($PreviousBox.minX,$NextBox.minX)-[math]::Min($PreviousBox.maxX,$NextBox.maxX))
  $sizeCompatible=($PreviousBox.height -gt 0 -and $NextBox.height -ge .65*$PreviousBox.height -and $NextBox.height -le 1.4*$PreviousBox.height)
 }
 $numbered=($Next.rawText -match '^\s*(?:\d+(?:\.\d+)+(?:[.、\s]|[\p{IsCJKUnifiedIdeographs}])|[一二三四五六七八九十]+[.、])')
 $punct=($Previous.rawText -notmatch '[。；;？！!?]\s*$');$lexical=($Next.rawText -match '^\s*[\p{IsCJKUnifiedIdeographs}0-9\-（(]')
 $title=($Next.rawText -notmatch '[，,。；;：:]' -and $Next.rawText -match '(说明|图例|系统图|一览表|标题)\s*$')
 $spacing=($Previous.y-$Next.y -ge .35*$Pitch -and $Previous.y-$Next.y -le 1.65*$Pitch)
 $compatible=($available -and $columnOverlap -ge .65 -and $previousOverlap -ge .65 -and $sizeCompatible)
 $accept=(!$legacy -and $compatible -and $spacing -and $punct -and $lexical -and !$numbered -and !$title -and !$Blocked)
 [pscustomobject]@{modelType='ContinuationEvidence';sourceA=$Previous.id;sourceB=$Next.id;sourceSnapshot=$Next.sourceSnapshot;bboxAvailable=$available;bboxXMin=if($NextBox){$NextBox.minX}else{$null};bboxXMax=if($NextBox){$NextBox.maxX}else{$null};bboxOverlapWithColumn=$columnOverlap;bboxOverlapWithPreviousLine=$previousOverlap;horizontalGap=$gap;separatorCrossing=$Blocked;separatorBlocked=$Blocked;verticalSpacingConsistent=$spacing;bboxColumnCompatible=$compatible;lexicalContinuation=$lexical;punctuationContinuation=$punct;indentationCompatible=($legacy -or $compatible);legacyInsertionCompatible=$legacy;nextNumberedItem=$numbered;titleCandidate=$title;fontSizeCompatible=$sizeCompatible;acceptedBBoxExtension=$accept;decision='pending';status='candidate'}
}
Export-ModuleMember -Function Get-TextLayoutBox,Get-BoxXOverlap,Get-BoxReferencePoint,New-ContinuationEvidence
