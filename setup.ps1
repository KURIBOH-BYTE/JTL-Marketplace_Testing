# Richtet die Testumgebung auf dem DEV-Server ein. Einmal aufrufen:
#
#   powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Legt ein venv in .venv an und installiert, was die Werkzeuge brauchen.
#
# Für den ersten Test (tools\hello_jtl.py) ist das NICHT nötig – der läuft mit
# System-Python und ohne Zusatzpakete, weil er auf sqlcmd.exe zurückfällt.
# Dieses Skript ist für den vollen Werkzeugkasten.
#
# Ein venv lässt sich nicht vorbauen und mitliefern: es enthält absolute Pfade
# und plattformspezifische Binärdateien. pyodbc ist eine kompilierte
# Erweiterung und muss als Windows-Rad installiert werden.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Python suchen ===" -ForegroundColor Cyan
$python = $null
foreach ($candidate in @("py", "python", "python3")) {
    try {
        $version = & $candidate --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            $python = $candidate
            Write-Host "  $candidate -> $version"
            break
        }
    } catch { }
}
if (-not $python) {
    Write-Host "Kein Python gefunden." -ForegroundColor Red
    Write-Host "Von python.org installieren und dabei 'Add Python to PATH' ankreuzen."
    exit 1
}

Write-Host "`n=== venv anlegen ===" -ForegroundColor Cyan
if (Test-Path ".venv") {
    Write-Host "  .venv existiert schon, wird weiterverwendet"
} else {
    & $python -m venv .venv
    Write-Host "  .venv angelegt"
}
$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "venv unvollstaendig: $venvPython fehlt" -ForegroundColor Red
    exit 1
}

Write-Host "`n=== Pakete installieren ===" -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip --quiet
& $venvPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "`nInstallation fehlgeschlagen." -ForegroundColor Red
    Write-Host "Kein Internet auf dem Server? Dann auf einem Rechner mit"
    Write-Host "Verbindung die Raeder herunterladen und mitnehmen:"
    Write-Host "  pip download -r requirements.txt --only-binary :all: ``"
    Write-Host "    --platform win_amd64 --python-version 3.12 -d wheels"
    Write-Host "Und hier:"
    Write-Host "  .venv\Scripts\pip install --no-index --find-links wheels -r requirements.txt"
    exit 1
}

Write-Host "`n=== Middleware suchen ===" -ForegroundColor Cyan
# build_import.py braucht das andere Repository. Liegen beide nebeneinander,
# findet es sich von selbst.
$middleware = Join-Path (Split-Path $PSScriptRoot -Parent) "JTL-Marketplace-Integration\jtl-integration"
if (Test-Path (Join-Path $middleware "src\jtl_integration")) {
    Write-Host "  gefunden: $middleware"
    Write-Host "  Abhaengigkeiten der Middleware dazu installieren..."
    & $venvPython -m pip install -r (Join-Path $middleware "requirements.txt")
} else {
    Write-Host "  nicht gefunden." -ForegroundColor Yellow
    Write-Host "  Nur fuer build_import.py noetig. Dann das Repository daneben klonen:"
    Write-Host "    git clone https://github.com/KURIBOH-BYTE/JTL-Marketplace-Integration.git"
}

Write-Host "`n=== Konfiguration ===" -ForegroundColor Cyan
if (Test-Path "config.ini") {
    Write-Host "  config.ini existiert schon"
} else {
    Copy-Item "config.example.ini" "config.ini"
    Write-Host "  config.ini aus der Vorlage angelegt"
    Write-Host "  Jetzt ausfuellen:  notepad config.ini" -ForegroundColor Yellow
    Write-Host "  Fuer den Lesezugriff genuegt die Windows-Anmeldung -"
    Write-Host "  dann user und password leer lassen."
}

Write-Host "`n=== Fertig ===" -ForegroundColor Green
Write-Host "Erster Test (braucht nichts davon, laeuft auch mit System-Python):"
Write-Host "  .venv\Scripts\python tools\hello_jtl.py" -ForegroundColor White
Write-Host ""
Write-Host "Versuchsplan: README.md"
