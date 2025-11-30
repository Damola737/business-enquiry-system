Param(
    [string]$Root = "$PSScriptRoot"
)

Write-Host "Organizing Python files into package structure..." -ForegroundColor Cyan

# Ensure structure exists
& (Join-Path $Root "01_init_structure.ps1") -Root $Root | Out-Null

$map = @{
    "base_agent.py"          = "agents\base_agent.py"
    "orchestrator.py"        = "agents\orchestrator.py"
    "classifier.py"          = "agents\classifier.py"
    "research_agent.py"      = "agents\research_agent.py"
    "qa_agent.py"            = "agents\qa_agent.py"
    "response_generator.py"  = "agents\response_generator.py"
    "sales_agent.py"         = "agents\specialists\sales_agent.py"
    "technical_agent.py"     = "agents\specialists\technical_agent.py"
    "demo_run.py"            = "scripts\demo_run.py"
}

foreach ($key in $map.Keys) {
    $src = Join-Path $Root $key
    $dst = Join-Path $Root $map[$key]
    if (Test-Path $src) {
        $dstDir = Split-Path $dst -Parent
        if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Force -Path $dstDir | Out-Null }
        Move-Item -Path $src -Destination $dst -Force
        Write-Host ("Moved {0} -> {1}" -f $key, $map[$key])
    } else {
        Write-Host ("Skip (missing): {0}" -f $key) -ForegroundColor DarkYellow
    }
}

Write-Host "Organization complete."
