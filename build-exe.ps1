#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build Windows installer EXE for SuperLocalMemory V2

.DESCRIPTION
    This script builds a Windows installer using Inno Setup.
    Can be run on Windows with Inno Setup installed, or via Docker on any platform.

    Copyright (c) 2026 Varun Pratap Bhardwaj
    Licensed under MIT License
    Repository: https://github.com/varun369/SuperLocalMemoryV2

    ATTRIBUTION REQUIRED: This notice must be preserved in all copies.

.PARAMETER Method
    Build method: "innosetup" (native Windows), "docker" (cross-platform), or "both"

.PARAMETER Clean
    Clean build artifacts before building

.PARAMETER SkipTests
    Skip pre-build tests

.EXAMPLE
    .\build-exe.ps1 -Method innosetup
    Build using local Inno Setup installation (Windows only)

.EXAMPLE
    .\build-exe.ps1 -Method docker
    Build using Docker (works on macOS/Linux/Windows)

.EXAMPLE
    .\build-exe.ps1 -Method both -Clean
    Build using both methods and clean first
#>

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("innosetup", "docker", "both")]
    [string]$Method = "docker",

    [Parameter(Mandatory=$false)]
    [switch]$Clean,

    [Parameter(Mandatory=$false)]
    [switch]$SkipTests
)

# Configuration
$Version = "2.1.0"
$AppName = "SuperLocalMemory"
$OutputDir = "dist"
$OutputExe = "SuperLocalMemory-Setup-v$Version-windows.exe"
$InnoSetupScript = "installer.iss"

# Colors for output
function Write-Success {
    param([string]$Message)
    Write-Host "✓ $Message" -ForegroundColor Green
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "✗ $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ $Message" -ForegroundColor Cyan
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Host "⚠ $Message" -ForegroundColor Yellow
}

# Banner
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  SuperLocalMemory V2 - Windows Installer Builder" -ForegroundColor Magenta
Write-Host "  Version: $Version" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

# Check prerequisites
Write-Info "Checking prerequisites..."

# Check if running in repo root
if (-not (Test-Path "installer.iss")) {
    Write-Error-Custom "Must run from repository root directory"
    Write-Error-Custom "Expected file: installer.iss"
    exit 1
}
Write-Success "Repository structure validated"

# Check Git
try {
    $gitVersion = git --version
    Write-Success "Git: $gitVersion"
} catch {
    Write-Warning-Custom "Git not found (optional)"
}

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python: $pythonVersion"
} catch {
    Write-Warning-Custom "Python not found (tests will be skipped)"
    $SkipTests = $true
}

# Clean build artifacts
if ($Clean) {
    Write-Info "Cleaning build artifacts..."
    if (Test-Path $OutputDir) {
        Remove-Item -Recurse -Force $OutputDir
        Write-Success "Removed $OutputDir directory"
    }
}

# Create output directory
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir | Out-Null
    Write-Success "Created $OutputDir directory"
}

# Create necessary assets if missing
Write-Info "Preparing assets..."

$AssetsDir = "assets"
if (-not (Test-Path $AssetsDir)) {
    New-Item -ItemType Directory -Path $AssetsDir | Out-Null
}

# Create placeholder icon if missing
if (-not (Test-Path "$AssetsDir/icon.ico")) {
    Write-Warning-Custom "Icon file missing: $AssetsDir/icon.ico"
    Write-Info "Creating placeholder icon..."
    # Note: In production, add proper icon creation here
    Write-Warning-Custom "Using default Windows icon (add custom icon later)"
}

# Create installer info files
Write-Info "Creating installer documentation..."

$WinReadme = @"
SuperLocalMemory V2.1.0 - Windows Installation
==============================================

Thank you for installing SuperLocalMemory V2!

This installer will:
1. Copy all necessary files to your system
2. Install Python modules to %USERPROFILE%\.claude-memory\
3. Configure MCP integration for supported IDEs
4. Install universal skills for AI tools
5. Add 'slm' command to your system PATH

System Requirements:
--------------------
• Windows 10 or higher (64-bit)
• Python 3.8 or higher
• 100 MB disk space
• Internet connection (for Python packages)

After Installation:
-------------------
1. Open Command Prompt or PowerShell
2. Run: slm status
3. Test: slm remember "Test memory"
4. Search: slm recall "test"

Documentation:
--------------
• GitHub: https://github.com/varun369/SuperLocalMemoryV2
• Wiki: https://github.com/varun369/SuperLocalMemoryV2/wiki
• Issues: https://github.com/varun369/SuperLocalMemoryV2/issues

Copyright (c) 2026 Varun Pratap Bhardwaj
Licensed under MIT License
"@

$PostInstall = @"
SuperLocalMemory V2.1.0 - Installation Complete!
================================================

Installation successful!

Location: %USERPROFILE%\.claude-memory\
CLI Command: slm

Quick Start:
------------
1. Open a NEW Command Prompt or PowerShell window
   (Required for PATH changes to take effect)

2. Verify installation:
   > slm status

3. Store your first memory:
   > slm remember "React is my preferred framework" --tags frontend

4. Search memories:
   > slm recall "React"

5. Launch dashboard (optional):
   > powershell -ExecutionPolicy Bypass -File start-dashboard.ps1

Integrated IDEs:
----------------
SuperLocalMemory is now available in:
✓ Claude Desktop (restart to see @SuperLocalMemory)
✓ Cursor (restart IDE)
✓ Windsurf (restart IDE)
✓ Continue.dev (use /slm-* skills)
✓ Cody (use custom commands)
✓ And 6 more tools...

Troubleshooting:
----------------
• 'slm' not found: Open NEW terminal window
• Python errors: Ensure Python 3.8+ is installed
• Permission errors: Run PowerShell as Administrator

Documentation: https://github.com/varun369/SuperLocalMemoryV2/wiki
Support: https://github.com/varun369/SuperLocalMemoryV2/issues

Copyright (c) 2026 Varun Pratap Bhardwaj
"@

$DocsDir = "docs"
if (-not (Test-Path $DocsDir)) {
    New-Item -ItemType Directory -Path $DocsDir | Out-Null
}

Set-Content -Path "$DocsDir/WINDOWS-INSTALL-README.txt" -Value $WinReadme -Encoding UTF8
Set-Content -Path "$DocsDir/WINDOWS-POST-INSTALL.txt" -Value $PostInstall -Encoding UTF8
Write-Success "Created installer documentation"

# Run tests (unless skipped)
if (-not $SkipTests) {
    Write-Info "Running pre-build tests..."

    # Basic file checks
    $RequiredFiles = @(
        "install.ps1",
        "src/memory_store_v2.py",
        "mcp_server.py",
        "LICENSE",
        "README.md"
    )

    $AllFilesExist = $true
    foreach ($file in $RequiredFiles) {
        if (Test-Path $file) {
            Write-Success "Found: $file"
        } else {
            Write-Error-Custom "Missing: $file"
            $AllFilesExist = $false
        }
    }

    if (-not $AllFilesExist) {
        Write-Error-Custom "Required files missing. Aborting build."
        exit 1
    }
} else {
    Write-Warning-Custom "Skipping tests (--SkipTests flag)"
}

# Build with Inno Setup (Windows native)
function Build-WithInnoSetup {
    Write-Info "Building with Inno Setup (native Windows)..."

    # Find Inno Setup
    $InnoSetupPaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 5\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 5\ISCC.exe"
    )

    $ISCC = $null
    foreach ($path in $InnoSetupPaths) {
        if (Test-Path $path) {
            $ISCC = $path
            break
        }
    }

    if (-not $ISCC) {
        Write-Error-Custom "Inno Setup not found!"
        Write-Info "Download from: https://jrsoftware.org/isdl.php"
        Write-Info "Expected locations:"
        foreach ($path in $InnoSetupPaths) {
            Write-Info "  - $path"
        }
        return $false
    }

    Write-Success "Found Inno Setup: $ISCC"

    # Compile installer
    Write-Info "Compiling installer..."
    $Process = Start-Process -FilePath $ISCC -ArgumentList $InnoSetupScript -Wait -PassThru -NoNewWindow

    if ($Process.ExitCode -eq 0) {
        Write-Success "Inno Setup compilation successful"

        # Check output
        $OutputPath = Join-Path $OutputDir $OutputExe
        if (Test-Path $OutputPath) {
            $FileSize = (Get-Item $OutputPath).Length / 1MB
            Write-Success "Created: $OutputPath ($([math]::Round($FileSize, 2)) MB)"
            return $true
        } else {
            Write-Error-Custom "Output file not found: $OutputPath"
            return $false
        }
    } else {
        Write-Error-Custom "Inno Setup compilation failed with exit code: $($Process.ExitCode)"
        return $false
    }
}

# Build with Docker (cross-platform)
function Build-WithDocker {
    Write-Info "Building with Docker (cross-platform)..."

    # Check Docker
    try {
        $dockerVersion = docker --version
        Write-Success "Docker: $dockerVersion"
    } catch {
        Write-Error-Custom "Docker not found!"
        Write-Info "Install Docker Desktop: https://www.docker.com/products/docker-desktop"
        return $false
    }

    # Create Dockerfile for Inno Setup
    $DockerfilePath = "Dockerfile.innosetup"
    $DockerfileContent = @"
# Dockerfile for building Windows installers with Inno Setup
# Uses Wine to run Inno Setup on Linux/macOS

FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies
RUN apt-get update && apt-get install -y \
    wine \
    wine64 \
    wget \
    xvfb \
    cabextract \
    && rm -rf /var/lib/apt/lists/*

# Download and install Inno Setup
WORKDIR /tmp
RUN wget -q "https://jrsoftware.org/download.php/is.exe?site=2" -O innosetup-installer.exe && \
    xvfb-run wine innosetup-installer.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- && \
    rm innosetup-installer.exe

# Set working directory
WORKDIR /build

# Entry point
ENTRYPOINT ["xvfb-run", "wine"]
CMD ["C:\\Program Files (x86)\\Inno Setup 6\\ISCC.exe"]
"@

    Set-Content -Path $DockerfilePath -Value $DockerfileContent -Encoding UTF8
    Write-Success "Created: $DockerfilePath"

    # Build Docker image
    Write-Info "Building Docker image (this may take 5-10 minutes on first run)..."
    docker build -t superlocalmemory-builder -f $DockerfilePath .

    if ($LASTEXITCODE -ne 0) {
        Write-Error-Custom "Docker image build failed"
        return $false
    }
    Write-Success "Docker image built"

    # Run build in Docker
    Write-Info "Running Inno Setup in Docker..."
    docker run --rm `
        -v "${PWD}:/build" `
        -w /build `
        superlocalmemory-builder `
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" `
        installer.iss

    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker build successful"

        # Check output
        $OutputPath = Join-Path $OutputDir $OutputExe
        if (Test-Path $OutputPath) {
            $FileSize = (Get-Item $OutputPath).Length / 1MB
            Write-Success "Created: $OutputPath ($([math]::Round($FileSize, 2)) MB)"
            return $true
        } else {
            Write-Error-Custom "Output file not found: $OutputPath"
            return $false
        }
    } else {
        Write-Error-Custom "Docker build failed"
        return $false
    }
}

# Execute build based on method
$BuildSuccess = $false

if ($Method -eq "innosetup" -or $Method -eq "both") {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  Method 1: Inno Setup (Native Windows)" -ForegroundColor Magenta
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host ""

    $BuildSuccess = Build-WithInnoSetup
}

if ($Method -eq "docker" -or ($Method -eq "both" -and -not $BuildSuccess)) {
    Write-Host ""
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host "  Method 2: Docker (Cross-Platform)" -ForegroundColor Magenta
    Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
    Write-Host ""

    $BuildSuccess = Build-WithDocker
}

# Final summary
Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host "  Build Summary" -ForegroundColor Magenta
Write-Host "═══════════════════════════════════════════════════════════" -ForegroundColor Magenta
Write-Host ""

if ($BuildSuccess) {
    Write-Success "Build completed successfully!"
    Write-Host ""
    Write-Info "Output: $OutputDir/$OutputExe"
    Write-Host ""
    Write-Info "Next steps:"
    Write-Host "  1. Test the installer on a clean Windows VM"
    Write-Host "  2. Upload to GitHub Releases"
    Write-Host "  3. Update download links in README.md"
    Write-Host ""
    Write-Info "Upload command:"
    Write-Host "  gh release upload v$Version $OutputDir/$OutputExe"
    Write-Host ""
} else {
    Write-Error-Custom "Build failed!"
    Write-Host ""
    Write-Info "Troubleshooting:"
    Write-Host "  • For Windows: Install Inno Setup from https://jrsoftware.org/isdl.php"
    Write-Host "  • For macOS/Linux: Ensure Docker is installed and running"
    Write-Host "  • Check build logs above for specific errors"
    Write-Host ""
    exit 1
}

# Checksum
Write-Info "Generating checksums..."
$OutputPath = Join-Path $OutputDir $OutputExe
if (Test-Path $OutputPath) {
    $Hash = Get-FileHash -Path $OutputPath -Algorithm SHA256
    $ChecksumFile = "$OutputPath.sha256"
    Set-Content -Path $ChecksumFile -Value "$($Hash.Hash)  $OutputExe" -Encoding UTF8
    Write-Success "SHA256: $($Hash.Hash)"
    Write-Success "Checksum saved: $ChecksumFile"
}

Write-Host ""
Write-Success "All done!"
Write-Host ""
