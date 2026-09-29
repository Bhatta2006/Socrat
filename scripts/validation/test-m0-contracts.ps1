[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$script:Failures = [System.Collections.Generic.List[string]]::new()
$script:Passes = [System.Collections.Generic.List[string]]::new()
$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))

function Assert-True {
    param(
        [Parameter(Mandatory)][bool]$Condition,
        [Parameter(Mandatory)][string]$Message
    )

    if ($Condition) {
        $script:Passes.Add($Message)
    }
    else {
        $script:Failures.Add($Message)
    }
}

function Assert-ExactSet {
    param(
        [Parameter(Mandatory)][object[]]$Actual,
        [Parameter(Mandatory)][object[]]$Expected,
        [Parameter(Mandatory)][string]$Message
    )

    $actualNormalized = @($Actual | ForEach-Object { [string]$_ } | Sort-Object -Unique)
    $expectedNormalized = @($Expected | ForEach-Object { [string]$_ } | Sort-Object -Unique)
    $equal = $actualNormalized.Count -eq $expectedNormalized.Count -and
        -not (Compare-Object -ReferenceObject $expectedNormalized -DifferenceObject $actualNormalized)
    Assert-True -Condition $equal -Message $Message
}

function Resolve-LocalMarkdownLinks {
    param([Parameter(Mandatory)][string]$MarkdownPath)

    $content = Get-Content -Raw -LiteralPath $MarkdownPath
    $matches = [regex]::Matches($content, '\[[^\]]*\]\(([^)]+)\)')

    foreach ($match in $matches) {
        $target = $match.Groups[1].Value.Trim()
        if ($target -match '^(https?://|mailto:|#)') {
            continue
        }

        $target = $target.Split('#')[0]
        if ([string]::IsNullOrWhiteSpace($target)) {
            continue
        }

        $resolved = [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $MarkdownPath) $target))
        if (-not $resolved.StartsWith($repoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            $script:Failures.Add("Local link escapes repository: $MarkdownPath -> $target")
            continue
        }

        if (-not (Test-Path -LiteralPath $resolved)) {
            $script:Failures.Add("Broken local link: $MarkdownPath -> $target")
        }
    }
}

$requiredFiles = @(
    'README.md',
    'docs\README.md',
    'docs\product\v1-product-requirements.md',
    'docs\product\domain-glossary.md',
    'docs\product\goal-templates.md',
    'docs\product\deterministic-policy-matrices.md',
    'docs\product\metric-contract.md',
    'docs\product\content-standard.md',
    'docs\research\concierge-pilot.md',
    'docs\security\threat-model.md',
    'docs\delivery\milestones\m0-index.md',
    'docs\delivery\milestones\m0-gate.md',
    'docs\delivery\validation\m0-validation-report.md',
    'docs\architecture\dependency-assessment.md',
    'contracts\product\m0-contracts.json',
    'contracts\schemas\m0-contracts.schema.json',
    'prototypes\concierge\README.md',
    'prototypes\concierge\index.html',
    'prototypes\concierge\styles.css',
    'prototypes\concierge\app.mjs',
    'prototypes\concierge\model.mjs',
    'prototypes\concierge\model.test.mjs'
)

foreach ($relativePath in $requiredFiles) {
    Assert-True -Condition (Test-Path -LiteralPath (Join-Path $repoRoot $relativePath)) -Message "Required artifact exists: $relativePath"
}

Assert-True -Condition (-not (Test-Path -LiteralPath (Join-Path $repoRoot 'docs\m0'))) -Message 'Milestone artifacts are organized by durable domain, not docs/m0'

$contractPath = Join-Path $repoRoot 'contracts\product\m0-contracts.json'
$schemaPath = Join-Path $repoRoot 'contracts\schemas\m0-contracts.schema.json'
$contract = Get-Content -Raw -LiteralPath $contractPath | ConvertFrom-Json
$schema = Get-Content -Raw -LiteralPath $schemaPath | ConvertFrom-Json

Assert-True -Condition ($contract.contract_version -match '^\d+\.\d+\.\d+$') -Message 'Contract version is semantic'
Assert-True -Condition ($contract.status -eq 'candidate') -Message 'Contract remains candidate until human M0 sign-off'
Assert-True -Condition ($schema.'$schema' -eq 'https://json-schema.org/draft/2020-12/schema') -Message 'Schema declares JSON Schema 2020-12'
Assert-ExactSet -Actual $contract.launch_scope.languages -Expected @('python', 'cpp', 'java') -Message 'Launch languages are exactly Python, C++, and Java'
Assert-ExactSet -Actual $contract.launch_scope.goal_tracks -Expected @('foundations', 'interview', 'competitive') -Message 'Launch tracks are exactly Foundations, Interview, and Competitive'
Assert-ExactSet -Actual $contract.launch_scope.session_minutes -Expected @(20, 30, 45, 60, 90) -Message 'Session budgets match the PRD'
Assert-True -Condition ($contract.launch_scope.minimum_days_per_week -eq 3) -Message 'Minimum weekly commitment is fixed at three days'
Assert-ExactSet -Actual $contract.goal_templates.id -Expected @('foundations', 'interview', 'competitive') -Message 'Exactly three goal templates exist'
Assert-ExactSet -Actual $contract.policy_profiles.id -Expected @('foundations', 'interview', 'competitive') -Message 'Each track has one policy profile'

$templateFieldsValid = @($contract.goal_templates | Where-Object {
    $_.required_fields.Count -lt 6 -or
    $_.required_fields -notcontains 'language' -or
    $_.required_fields -notcontains 'target_outcome' -or
    $_.required_fields -notcontains 'target_date' -or
    $_.required_fields -notcontains 'days_per_week' -or
    $_.required_fields -notcontains 'minutes_per_session' -or
    $_.required_fields -notcontains 'timezone'
}).Count -eq 0
Assert-True -Condition $templateFieldsValid -Message 'Every goal template includes the common confirmation fields'

$routeIds = @($contract.routing_rules.id)
$routePriorities = @($contract.routing_rules.priority)
Assert-True -Condition ($routeIds.Count -ge 8) -Message 'Routing policy covers all minimum launch outcomes'
Assert-True -Condition (($routeIds | Sort-Object -Unique).Count -eq $routeIds.Count) -Message 'Routing rule IDs are unique'
Assert-True -Condition (($routePriorities | Sort-Object -Unique).Count -eq $routePriorities.Count) -Message 'Routing priorities are unique'
Assert-True -Condition (@($contract.routing_rules | Where-Object { -not $_.reason_code }).Count -eq 0) -Message 'Every routing outcome has a stable reason code'
Assert-True -Condition (@($contract.routing_rules | Where-Object { $_.reason_code -eq 'foundation_prerequisites_required' }).Count -eq 1) -Message 'Low-readiness interview/competitive learners receive a Foundations bridge'
Assert-True -Condition (@($contract.routing_rules | Where-Object { $_.reason_code -eq 'competitive_target_not_released' }).Count -eq 1) -Message 'Unreleased competitive coverage produces an explicit waitlist result'

$metricIds = @($contract.metrics.id)
Assert-True -Condition ($metricIds.Count -ge 6) -Message 'Core outcome and guardrail metrics are defined'
Assert-True -Condition (($metricIds | Sort-Object -Unique).Count -eq $metricIds.Count) -Message 'Metric IDs are unique'
Assert-True -Condition (@($contract.metrics | Where-Object { -not $_.numerator -or -not $_.denominator -or -not $_.target }).Count -eq 0) -Message 'Every metric has numerator, denominator, and target'

Assert-True -Condition ($contract.mastery_authority.owner -eq 'deterministic_policy_engine') -Message 'Mastery authority is deterministic'
Assert-True -Condition ($contract.mastery_authority.llm_write_access -eq $false) -Message 'LLM has no mastery write access'
Assert-True -Condition ($contract.mastery_authority.passive_activity_changes_mastery -eq $false) -Message 'Passive activity cannot change mastery'
Assert-True -Condition ($contract.llm_authority.default_state -eq 'disabled') -Message 'LLM capability defaults disabled'
Assert-True -Condition ($contract.llm_authority.forbidden_roles -contains 'access_assessment_solutions') -Message 'LLM cannot access assessment solutions'
Assert-True -Condition ($contract.llm_authority.failure_behavior -eq 'deterministic_or_curated_fallback') -Message 'LLM failure has a non-LLM fallback'
Assert-True -Condition ($contract.decision_invariants.Count -ge 7) -Message 'Decision invariants are explicitly frozen'

$adrFiles = @(Get-ChildItem -LiteralPath (Join-Path $repoRoot 'docs\architecture\adr') -File -Filter '*.md')
Assert-True -Condition ($adrFiles.Count -ge 6) -Message 'At least six architecture decisions are independently reviewable'
foreach ($adrFile in $adrFiles) {
    $adrContent = Get-Content -Raw -LiteralPath $adrFile.FullName
    Assert-True -Condition ($adrContent -match '(?m)^- \*\*Status:\*\* (Proposed|Accepted|Superseded|Rejected)$') -Message "ADR has valid status: $($adrFile.Name)"
    Assert-True -Condition ($adrContent -match '(?m)^## Decision$') -Message "ADR has a decision: $($adrFile.Name)"
    Assert-True -Condition ($adrContent -match '(?m)^## Consequences$') -Message "ADR records consequences: $($adrFile.Name)"
    Assert-True -Condition ($adrContent -match '(?m)^## Verification$') -Message "ADR has verification: $($adrFile.Name)"
}

$threatContent = Get-Content -Raw -LiteralPath (Join-Path $repoRoot 'docs\security\threat-model.md')
$threatIds = [regex]::Matches($threatContent, '\| T-[0-9]{3} \|') | ForEach-Object { $_.Value.Trim('| ').Trim() }
Assert-True -Condition ($threatIds.Count -ge 25) -Message 'Threat register contains at least 25 concrete threats'
Assert-True -Condition (($threatIds | Sort-Object -Unique).Count -eq $threatIds.Count) -Message 'Threat IDs are unique'
Assert-True -Condition ($threatContent -match 'no outbound network' -and $threatContent -match 'no cloud/application credentials') -Message 'Execution isolation forbids network and credentials'
Assert-True -Condition ($threatContent -match 'Privacy/legal decisions still requiring accountable review') -Message 'Unresolved privacy/legal decisions are not hidden'

$gateContent = Get-Content -Raw -LiteralPath (Join-Path $repoRoot 'docs\delivery\milestones\m0-gate.md')
Assert-True -Condition ($gateContent -match '\*\*Decision:\*\* NOT YET PASSED') -Message 'M0 is not falsely marked complete before pilots/sign-off'
Assert-True -Condition ($gateContent -match 'five valid sessions each') -Message 'Gate requires five users per track'

$prototypeHtml = Get-Content -Raw -LiteralPath (Join-Path $repoRoot 'prototypes\concierge\index.html')
$prototypeApp = Get-Content -Raw -LiteralPath (Join-Path $repoRoot 'prototypes\concierge\app.mjs')
foreach ($screen in @('welcome', 'goal', 'route', 'diagnostic', 'plan', 'practice', 'evidence', 'recovery', 'complete')) {
    Assert-True -Condition ($prototypeHtml -match ('data-screen="' + [regex]::Escape($screen) + '"')) -Message "Prototype contains required screen: $screen"
}
Assert-True -Condition ($prototypeHtml -match 'Skip to main content') -Message 'Prototype has a keyboard skip link'
Assert-True -Condition ($prototypeHtml -match 'no data saved' -and $prototypeHtml -match 'does not create an account') -Message 'Prototype discloses research and data limitations'
Assert-True -Condition ($prototypeApp -match "from './model.mjs'") -Message 'Prototype UI uses the tested deterministic model'

$allTextFiles = @((Get-Item -LiteralPath (Join-Path $repoRoot 'README.md'))) + @(
    'docs', 'contracts', 'prototypes', 'scripts' | ForEach-Object {
        Get-ChildItem -LiteralPath (Join-Path $repoRoot $_) -Recurse -File |
            Where-Object { $_.Extension -in @('.md', '.json', '.ps1') }
    }
)
foreach ($file in $allTextFiles) {
    if ($file.FullName -ne $MyInvocation.MyCommand.Path) {
        $content = Get-Content -Raw -LiteralPath $file.FullName
        Assert-True -Condition ($content -notmatch '\b(TODO|TBD|FIXME|XXX)\b') -Message "No unresolved placeholder token: $($file.FullName.Substring($repoRoot.Length + 1))"
    }
    if ($file.Extension -eq '.md') {
        Resolve-LocalMarkdownLinks -MarkdownPath $file.FullName
    }
}

Write-Host "M0 contract validation: $($script:Passes.Count) passed, $($script:Failures.Count) failed"
foreach ($pass in $script:Passes) {
    Write-Host "[PASS] $pass"
}

if ($script:Failures.Count -gt 0) {
    foreach ($failure in $script:Failures) {
        Write-Error "[FAIL] $failure" -ErrorAction Continue
    }
    exit 1
}

Write-Host '[PASS] All automated M0 document and contract checks passed.'
exit 0
