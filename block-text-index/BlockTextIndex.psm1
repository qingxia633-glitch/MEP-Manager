Set-StrictMode -Version 2

function ConvertFrom-BtiValue([string]$Value) {
    if ($Value -eq 'nil') { return $null }
    if ($Value.Length -ge 2 -and $Value.StartsWith('"') -and $Value.EndsWith('"')) {
        return [regex]::Replace($Value.Substring(1,$Value.Length-2), '\\([\\"nrt])', {
            param($m)
            switch ($m.Groups[1].Value) { 'n' {"`n"} 'r' {"`r"} 't' {"`t"} default {$m.Groups[1].Value} }
        })
    }
    return $Value
}

function Read-BlockTextIndex {
    param([Parameter(Mandatory)][string]$Path, [ValidateSet('UTF8','Default')][string]$Encoding='UTF8')
    $lines=Get-Content -LiteralPath $Path -Encoding $Encoding
    if ($lines -notcontains 'END_OF_REPORT' -or $lines -notcontains 'ReadErrorCount=0' -or
        @($lines | Where-Object {$_ -match '^(INCOMPLETE_REPORT|EntityReadError|BlockReadError)'}).Count) {
        throw 'Incomplete/error index: absence and reference completeness cannot be established'
    }
    $header=[ordered]@{}; $blocks=@(); $texts=@(); $refs=@(); $block=$null; $record=$null; $recordKind=$null
    foreach ($line in $lines) {
        switch -Exact ($line) {
            'Block_BEGIN' {
                if ($block -or $record) { throw 'Nested/unfinished block record' }
                $block=[ordered]@{}; continue
            }
            'Block_END' {
                if (!$block -or $record) { throw 'Unbalanced block end' }
                $blocks+=,[pscustomobject]$block; $block=$null; continue
            }
            'Text_BEGIN' {
                if (!$block -or $record) { throw 'Invalid text start' }
                $record=[ordered]@{RawDXF=@()}; $recordKind='text'; continue
            }
            'Reference_BEGIN' {
                if (!$block -or $record) { throw 'Invalid reference start' }
                $record=[ordered]@{}; $recordKind='reference'; continue
            }
            'Text_END' {
                if (!$record -or $recordKind -ne 'text') { throw 'Invalid text end' }
                if ($record.SourceBlock -ne $block.BlockName -or $block.Kind -ne 'block_definition' -or
                    $record.EntityType -notin @('TEXT','MTEXT','ATTDEF') -or $record.ReadStatus -ne 'read') { throw 'Invalid text provenance/type/status' }
                $texts+=,[pscustomobject]$record; $record=$null; $recordKind=$null; continue
            }
            'Reference_END' {
                if (!$record -or $recordKind -ne 'reference') { throw 'Invalid reference end' }
                if ($record.ParentBlock -ne $block.BlockName -or $record.SourceKind -ne $block.Kind) { throw 'Invalid reference provenance' }
                $refs+=,[pscustomobject]$record; $record=$null; $recordKind=$null; continue
            }
        }
        if ($line -match '^([^=]+)=(.*)$') {
            $key=$matches[1]; $raw=$matches[2]
            if ($record -and $key.StartsWith('DXF:')) {
                $record.RawDXF+=,[pscustomobject]@{Code=[int]$key.Substring(4);Value_RAW=$raw}
            } else {
                $target=if ($null -ne $record) {$record} elseif ($null -ne $block) {$block} else {$header}
                if ($target.Contains($key)) { throw "Duplicate field $key" }
                $target[$key]=ConvertFrom-BtiValue $raw
            }
        }
    }
    if ($null -ne $block -or $null -ne $record) { throw 'Unfinished records' }
    if ($header.IndexVersion -ne '1.0' -or $header.AcquisitionMode -ne 'BlockTableDirectTextAndReferences') { throw 'Unsupported index format' }
    $counts=@{
        BlockTableRecordCount=$blocks.Count
        BlockDefinitionCount=@($blocks|Where-Object Kind -eq 'block_definition').Count
        TextBearingBlockCount=@($texts|ForEach-Object {$_.SourceBlock}|Sort-Object -Unique).Count
        TextRecordCount=$texts.Count
        TEXTCount=@($texts|Where-Object EntityType -eq 'TEXT').Count
        MTEXTCount=@($texts|Where-Object EntityType -eq 'MTEXT').Count
        ATTDEFCount=@($texts|Where-Object EntityType -eq 'ATTDEF').Count
        ReferenceCount=$refs.Count
        ExternalSkippedCount=@($blocks|Where-Object ReadStatus -eq 'not_scanned_external').Count
    }
    foreach ($key in $counts.Keys) {
        if (!$header.Contains($key) -or [int]$header[$key] -ne $counts[$key]) { throw "Count mismatch: $key" }
    }
    $names=@{}
    foreach ($b in $blocks) {
        if ($names.ContainsKey($b.BlockName)) { throw 'Duplicate block definition name' }; $names[$b.BlockName]=$true
        if ($b.ReadStatus -notin @('read','not_scanned_external')) { throw 'Block coverage unavailable' }
        if ([int]$b.BlockTextCount -ne @($texts|Where-Object SourceBlock -eq $b.BlockName).Count) { throw 'Block text count mismatch' }
    }
    $source=[pscustomobject]@{Path=(Resolve-Path -LiteralPath $Path).Path;SHA256=(Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash;DWG=$header.DWG}
    foreach ($record in @($texts)+@($refs)) { $record | Add-Member -NotePropertyName SourceSnapshot -NotePropertyValue $source }
    [pscustomobject]@{SourceSnapshot=$source;Metadata=[pscustomobject]$header;Blocks=$blocks;Texts=$texts;References=$refs
        UnresolvedReferences=@($refs|Where-Object {!$names.ContainsKey($_.ReferencedBlockName)})
        VisibilityStatus='not_evaluated';EngineeringBindings=@()}
}

function Find-BlockDefinitionText {
    param([Parameter(Mandatory)]$Index,[Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$Query)
    $hits=@(foreach ($t in $Index.Texts) {
        # Literal contains search, never regex; raw CAD formatting is not evaluated.
        if ($null -ne $t.Text_RAW -and $t.Text_RAW.IndexOf($Query,[StringComparison]::OrdinalIgnoreCase) -ge 0) {
            $seen=@{}; $queue=New-Object 'System.Collections.Generic.Queue[string]'; $queue.Enqueue($t.SourceBlock)
            $edges=@(); $roots=@()
            while ($queue.Count -gt 0) {
                $name=$queue.Dequeue(); if ($seen.ContainsKey($name)) { continue }; $seen[$name]=$true
                foreach ($r in @($Index.References|Where-Object ReferencedBlockName -eq $name)) {
                    $edges+=,$r
                    if ($r.SourceKind -in @('modelspace_top_level','paperspace_top_level')) { $roots+=,$r }
                    elseif ($r.SourceKind -eq 'block_definition') { $queue.Enqueue($r.ParentBlock) }
                }
            }
            [pscustomobject]@{TextRecord=$t;DirectReferences=@($Index.References|Where-Object ReferencedBlockName -eq $t.SourceBlock)
                ReverseReferenceEdges=$edges;ReachableTopLevelReferences=$roots
                RelationStatus='reference_reachability_only_not_instance_binding';VisibilityStatus='not_evaluated'}
        }
    })
    [pscustomobject]@{Query=$Query;MatchMode='literal_contains_case_insensitive_raw_text';SourceSnapshot=$Index.SourceSnapshot
        Status=$(if($hits.Count){'found_in_readable_block_definition_text'}else{'not_found_in_readable_block_definition_text'})
        Hits=$hits;Limitations=$Index.Metadata.Limitations;ExternalSkippedCount=$Index.Metadata.ExternalSkippedCount
        UnresolvedReferenceCount=$Index.UnresolvedReferences.Count;EngineeringBindings=@()}
}
Export-ModuleMember -Function Read-BlockTextIndex,Find-BlockDefinitionText
