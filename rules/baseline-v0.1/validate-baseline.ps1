$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

$files = @{
    engineering = Join-Path $root "engineering-rules.json"
    evidence    = Join-Path $root "project-evidence.json"
    assumptions = Join-Path $root "approved-assumptions.json"
    authority   = Join-Path $root "authority-evidence.json"
    unresolved  = Join-Path $root "unresolved-register.json"
}

foreach ($path in $files.Values) {
    if (-not (Test-Path $path)) {
        throw "Missing baseline file: $path"
    }
}

$engineering = Get-Content $files.engineering -Raw -Encoding utf8 | ConvertFrom-Json
$evidence = Get-Content $files.evidence -Raw -Encoding utf8 | ConvertFrom-Json
$assumptions = Get-Content $files.assumptions -Raw -Encoding utf8 | ConvertFrom-Json
$authority = Get-Content $files.authority -Raw -Encoding utf8 | ConvertFrom-Json
$unresolved = Get-Content $files.unresolved -Raw -Encoding utf8 | ConvertFrom-Json

$records = @()

foreach ($x in $engineering.rules) {
    $records += [pscustomobject]@{ type="engineering"; record=$x }
}
foreach ($x in $evidence.evidence) {
    $records += [pscustomobject]@{ type="evidence"; record=$x }
}
foreach ($x in $assumptions.assumptions) {
    $records += [pscustomobject]@{ type="assumption"; record=$x }
}
foreach ($x in $authority.authority_evidence) {
    $records += [pscustomobject]@{ type="authority"; record=$x }
}
foreach ($x in $unresolved.items) {
    $records += [pscustomobject]@{ type="unresolved"; record=$x }
}

$allowed = @{
    engineering = @("candidate","confirmed","active","deprecated","superseded","rejected")
    evidence    = @("supported","partial","unresolved","conflicting","rejected","superseded")
    assumption  = @("approved","deprecated","superseded","rejected")
    authority   = @("active","superseded","rejected")
    unresolved  = @("candidate","unresolved","conflicting","rejected","deprecated","superseded")
}

$ids = @{}

foreach ($entry in $records) {
    $r = $entry.record
    $type = $entry.type

    if ([string]::IsNullOrWhiteSpace($r.id)) {
        throw "$type record missing id"
    }

    if ($ids.ContainsKey($r.id)) {
        throw "Duplicate baseline id: $($r.id)"
    }
    $ids[$r.id] = $true

    if ([string]::IsNullOrWhiteSpace($r.statement)) {
        throw "$($r.id): missing statement"
    }

    if ($allowed[$type] -notcontains $r.status) {
        throw "$($r.id): invalid status '$($r.status)' for type '$type'"
    }

    if ($null -eq $r.applicability) {
        throw "$($r.id): missing applicability"
    }

    if ($null -eq $r.sources) {
        throw "$($r.id): missing sources"
    }

    if ($null -eq $r.supersedes) {
        throw "$($r.id): missing supersedes"
    }

    if ($null -eq $r.superseded_by) {
        throw "$($r.id): missing superseded_by"
    }

    if ($null -eq $r.notes) {
        throw "$($r.id): missing notes"
    }

    if ($null -eq $r.PSObject.Properties['provenance_gaps']) {
        throw "$($r.id): missing provenance_gaps"
    }

    if ($r.provenance_gaps -isnot [array]) {
        throw "$($r.id): provenance_gaps must be an array"
    }

    foreach ($gap in $r.provenance_gaps) {
        if ($gap -isnot [string] -or [string]::IsNullOrWhiteSpace($gap)) {
            throw "$($r.id): provenance_gaps elements must be non-empty strings"
        }
    }

    # Prevent obvious local Windows paths from entering the baseline.
    $serialized = $r | ConvertTo-Json -Depth 30

    if ($serialized -match '[A-Za-z]:\\\\') {
        throw "$($r.id): contains machine-absolute Windows path"
    }

    # States that affect engineering decisions require traceable sources.
    if ($r.status -in @("confirmed","active","supported","approved","rejected")) {
        if (@($r.sources).Count -eq 0) {
            throw "$($r.id): engineering-impacting status requires sources"
        }
    }
}

Write-Host ""
Write-Host "Rule Baseline validation PASSED" -ForegroundColor Green
Write-Host "Records: $($records.Count)"
Write-Host "Unique IDs: $($ids.Count)"
Write-Host "Engineering rules: $(@($engineering.rules).Count)"
Write-Host "Project evidence: $(@($evidence.evidence).Count)"
Write-Host "Approved assumptions: $(@($assumptions.assumptions).Count)"
Write-Host "Authority evidence: $(@($authority.authority_evidence).Count)"
Write-Host "Unresolved register: $(@($unresolved.items).Count)"
