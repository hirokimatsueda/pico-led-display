# pico-sdk (VS Code 拡張が ~/.pico-sdk に入れたもの) を使ってビルドするスクリプト
# 使い方:
#   pwsh -ExecutionPolicy Bypass -File ./firmware-c/build.ps1
#   pwsh -ExecutionPolicy Bypass -File ./firmware-c/build.ps1 -Clean

param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$PicoRoot = Join-Path $HOME ".pico-sdk"
$ProjectDir = $PSScriptRoot
$BuildDir = Join-Path $ProjectDir "build"

function Get-LatestVersionDir {
    param([string]$Path, [string]$Name)

    if (-not (Test-Path $Path)) {
        Write-Host "$Name が見つかりません: $Path" -ForegroundColor Red
        Write-Host "VS Code の Raspberry Pi Pico 拡張機能をインストールしてください。" -ForegroundColor Yellow
        exit 1
    }
    $dir = Get-ChildItem $Path -Directory | Sort-Object Name -Descending | Select-Object -First 1
    if ($null -eq $dir) {
        Write-Host "$Name のバージョンが見つかりません: $Path" -ForegroundColor Red
        exit 1
    }
    return $dir.FullName
}

$SdkPath = Get-LatestVersionDir -Path (Join-Path $PicoRoot "sdk") -Name "pico-sdk"
$ToolchainPath = Get-LatestVersionDir -Path (Join-Path $PicoRoot "toolchain") -Name "ツールチェーン"
$NinjaDir = Get-LatestVersionDir -Path (Join-Path $PicoRoot "ninja") -Name "ninja"
$PicotoolDir = Get-LatestVersionDir -Path (Join-Path $PicoRoot "picotool") -Name "picotool"

$Ninja = Join-Path $NinjaDir "ninja.exe"
$PicotoolCMake = Join-Path $PicotoolDir "picotool"

Write-Host "SDK        : $SdkPath"
Write-Host "Toolchain  : $ToolchainPath"
Write-Host "Ninja      : $Ninja"

if ($Clean -and (Test-Path $BuildDir)) {
    Write-Host "build ディレクトリを削除します" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $BuildDir
}

cmake -S $ProjectDir -B $BuildDir -G Ninja `
    -DCMAKE_MAKE_PROGRAM="$Ninja" `
    -DPICO_SDK_PATH="$SdkPath" `
    -DPICO_TOOLCHAIN_PATH="$ToolchainPath" `
    -Dpicotool_DIR="$PicotoolCMake"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

& $Ninja -C $BuildDir
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Uf2 = Join-Path $BuildDir "pico_led_display.uf2"
$Bin = Join-Path $BuildDir "pico_led_display.bin"
if (Test-Path $Bin) {
    $binSize = (Get-Item $Bin).Length
    Write-Host ""
    Write-Host ("フラッシュ使用量: {0:N0} バイト ({1:N1} KiB / 4 MiB)" -f $binSize, ($binSize / 1KB)) -ForegroundColor Green
    Write-Host "書き込み: BOOTSEL を押しながら接続し、RP2350 ドライブに次をコピー" -ForegroundColor Green
    Write-Host "  $Uf2"
}
