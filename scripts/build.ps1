<#
build.ps1 - build helper for this repository

This script supports two flows:
 - If a CMakeLists.txt is present in the repo root, it runs the original
   CMake + vcpkg toolchain configure/build steps (for C++ projects).
 - Otherwise it assumes a Python project: it creates/uses a `.venv`,
   installs dependencies (if present), and runs tests if a `tests/` dir exists.

Usage:
  .\scripts\build.ps1               # default behavior
  .\scripts\build.ps1 -VcpkgRoot D:\tools\vcpkg  # only used for CMake flow
#>

param(
    [string]$VcpkgRoot = $env:VCPKG_ROOT
)

# Always run from the repository root (one level up from this script).
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $repoRoot
try {
    # If this repo contains a CMakeLists.txt, run the original CMake flow.
    if (Test-Path (Join-Path $repoRoot 'CMakeLists.txt')) {
        if (-not $VcpkgRoot -or $VcpkgRoot -eq "") {
            $VcpkgRoot = "C:\vcpkg"
        }

        $toolchain = Join-Path $VcpkgRoot "scripts\buildsystems\vcpkg.cmake"
        Write-Host "Using vcpkg toolchain: $toolchain"

        if (Test-Path $toolchain) {
            & cmake -B build -S . -DCMAKE_TOOLCHAIN_FILE="$toolchain"
        } else {
            Write-Warning "Toolchain file not found at $toolchain. Running cmake without vcpkg toolchain."
            & cmake -B build -S .
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Error "cmake configure failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }

        Write-Host "Building Release..."
        & cmake --build build --config Release
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Build failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }

        Write-Host "Build succeeded."
        exit 0
    }

    # Python workflow (default for this repo)
    Write-Host "No CMake project detected. Running Python workflow."

    # Find a Python executable
    $pythonCmd = 'python'
    if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
        $pythonCmd = 'python3'
    }
    if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
        Write-Error "Python 3 not found on PATH. Please install Python 3."
        exit 1
    }

    $venvDir = Join-Path $repoRoot '.venv'
    if (-not (Test-Path $venvDir)) {
        Write-Host "Creating virtual environment at $venvDir"
        & $pythonCmd -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create virtual environment."
            exit $LASTEXITCODE
        }
    } else {
        Write-Host "Using existing virtual environment at $venvDir"
    }

    # Locate venv python executable
    $venvPython = Join-Path $venvDir 'Scripts\python.exe'
    if (-not (Test-Path $venvPython)) {
        $venvPython = Join-Path $venvDir 'bin/python'
    }
    if (-not (Test-Path $venvPython)) {
        Write-Error "Virtual environment python not found at expected locations ($venvDir)."
        exit 1
    }

    Write-Host "Upgrading pip, setuptools and wheel in virtual environment..."
    & $venvPython -m pip install --upgrade pip setuptools wheel
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Failed to upgrade pip/tools in virtual environment."
        exit $LASTEXITCODE
    }

    # Install dependencies if available
    if (Test-Path (Join-Path $repoRoot 'requirements.txt')) {
        Write-Host "Installing dependencies from requirements.txt"
        & $venvPython -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install requirements.txt"
            exit $LASTEXITCODE
        }
    } elseif ((Test-Path (Join-Path $repoRoot 'pyproject.toml')) -or (Test-Path (Join-Path $repoRoot 'setup.py'))) {
        Write-Host "Installing package in editable mode"
        & $venvPython -m pip install -e .
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to install package in editable mode."
            exit $LASTEXITCODE
        }
    } else {
        Write-Warning "No requirements.txt, pyproject.toml, or setup.py found. Skipping dependency install."
    }

    # Run tests if present
    if (Test-Path (Join-Path $repoRoot 'tests')) {
        Write-Host "Running tests with pytest..."
        & $venvPython -m pytest -q
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Tests failed with exit code $LASTEXITCODE"
            exit $LASTEXITCODE
        }
        Write-Host "Tests passed."
    } else {
        Write-Host "No tests/ directory found; Python build finished."
    }

    exit 0
} finally {
    Pop-Location
}
