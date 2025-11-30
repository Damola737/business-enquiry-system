Param(
    [string]$Root = "$PSScriptRoot"
)

Write-Host "Initializing project structure under $Root ..." -ForegroundColor Cyan

$dirs = @(
    "agents",
    "agents\specialists",
    "config",
    "knowledge_base\business_data",
    "logs",
    "scripts",
    "tests"
)

foreach ($d in $dirs) {
    $path = Join-Path $Root $d
    if (-not (Test-Path $path)) {
        New-Item -ItemType Directory -Force -Path $path | Out-Null
        Write-Host "Created $path"
    }
}

# __init__.py to make packages
New-Item -ItemType File -Force -Path (Join-Path $Root "agents\__init__.py") | Out-Null
New-Item -ItemType File -Force -Path (Join-Path $Root "agents\specialists\__init__.py") | Out-Null

# Seed requirements.txt if missing
$reqPath = Join-Path $Root "requirements.txt"
if (-not (Test-Path $reqPath)) {
@"
pyautogen>=0.2.27,<0.3
pyautogen[retrievechat]>=0.2.27,<0.3
chromadb>=0.4.24
pypdf>=4.2.0
unstructured>=0.15.0
python-dotenv>=1.0.1
pydantic>=2.8.2
tenacity>=8.4.2
"@ | Set-Content -Path $reqPath -Encoding UTF8
    Write-Host "Wrote requirements.txt"
}

# Seed config/llm_config.json if missing
$configPath = Join-Path $Root "config\llm_config.json"
if (-not (Test-Path $configPath)) {
@"
{
  "llm_config": {
    "config_list": [
      { "model": "gpt-4o-mini", "api_key": "${OPENAI_API_KEY}" }
    ],
    "temperature": 0.2,
    "timeout": 60
  },
  "group_chat_config": {
    "max_round": 20,
    "speaker_selection_method": "auto"
  }
}
"@ | Set-Content -Path $configPath -Encoding UTF8
    Write-Host "Wrote config\llm_config.json"
}

# Seed a sample KB doc
$kbDoc = Join-Path $Root "knowledge_base\business_data\getting_started.txt"
if (-not (Test-Path $kbDoc)) {
@"
TechCorp Solutions - Getting Started
- Sign up at https://techcorp.com/signup
- Configure your workspace
- Invite your team
- Explore analytics
"@ | Set-Content -Path $kbDoc -Encoding UTF8
    Write-Host "Seeded sample knowledge base doc"
}

Write-Host "Done."
