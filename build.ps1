<#
build.ps1 - configure and build Trivia-Doku with optional vcpkg toolchain

Usage:
  .\scripts\build.ps1               # uses $env:VCPKG_ROOT or C:\vcpkg
  .\scripts\build.ps1 -VcpkgRoot D:\tools\vcpkg
#>

param(
    [string]$VcpkgRoot = $env:VCPKG_ROOT
)

if (-not $VcpkgRoot -or $VcpkgRoot -eq "") {
    $VcpkgRoot = "C:\vcpkg"
}

# Always run from the repository root (one level up from this script).
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $repoRoot
try {
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
} finally {
    Pop-Location
}
