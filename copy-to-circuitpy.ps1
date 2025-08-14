# CIRCUITPYドライブを自動検出し、必要なファイル・ディレクトリをコピーするスクリプト
# -WithLib オプション指定時のみ lib のコピーを行う
# コピー先が見つからなければ中止

param(
    [switch]$WithLib
)

$sourceCode = Join-Path $PSScriptRoot "code.py"
$sourceGames = Join-Path $PSScriptRoot "games"
$targetFile = "code.py"
$targetGames = "games"

# CIRCUITPYドライブをラベルで探す
$drive = Get-Volume | Where-Object { $_.FileSystemLabel -eq "CIRCUITPY" } | Select-Object -First 1

if ($null -eq $drive) {
    Write-Host "CIRCUITPYドライブが見つかりません。コピーを中止します。"
    exit 1
}

$target = "$($drive.DriveLetter):\$targetFile"
Copy-Item -Path $sourceCode -Destination $target -Force
Write-Host "code.py を $target にコピーしました。"

# gamesディレクトリの中身のみをコピー
$dstGames = "$($drive.DriveLetter):\$targetGames"
if (Test-Path $sourceGames) {
    if (-not (Test-Path $dstGames)) {
        New-Item -Path $dstGames -ItemType Directory | Out-Null
    }
    Get-ChildItem -Path $sourceGames | Where-Object { $_.Name -ne ".mypy_cache" } | ForEach-Object {
        $itemName = $_.Name
        $src = Join-Path $sourceGames $itemName
        $dst = Join-Path $dstGames $itemName
        Copy-Item -Path $src -Destination $dst -Recurse -Force
    }
    Write-Host "games ディレクトリの中身を $dstGames にコピーしました。"
} else {
    Write-Host "games ディレクトリが見つかりません。"
}

# -WithLib オプション指定時のみ lib 配下のライブラリをコピー
if ($WithLib) {
    $dstLib = "$($drive.DriveLetter):\lib"
    if (-not (Test-Path $dstLib)) {
        New-Item -Path $dstLib -ItemType Directory | Out-Null
    }

    # adafruit_ht16k33 ディレクトリの中身のみをコピー
    $srcLib = Join-Path $PSScriptRoot ".venv\Lib\site-packages\adafruit_ht16k33"
    if (Test-Path $srcLib) {
        $dstHt16k33 = Join-Path $dstLib "adafruit_ht16k33"
        if (-not (Test-Path $dstHt16k33)) {
            New-Item -Path $dstHt16k33 -ItemType Directory | Out-Null
        }
        Get-ChildItem -Path $srcLib | Where-Object { $_.Name -ne ".mypy_cache" } | ForEach-Object {
            $itemName = $_.Name
            $src = Join-Path $srcLib $itemName
            $dst = Join-Path $dstHt16k33 $itemName
            Copy-Item -Path $src -Destination $dst -Recurse -Force
        }
        Write-Host "adafruit_ht16k33 の中身を $dstHt16k33 にコピーしました。"
    } else {
        Write-Host "adafruit_ht16k33 フォルダが見つかりません。"
    }

    # adafruit_debouncer.py ファイルをコピー
    $srcLib = Join-Path $PSScriptRoot ".venv\Lib\site-packages\adafruit_debouncer.py"
    if (Test-Path $srcLib) {
        $dst = Join-Path $dstLib "adafruit_debouncer.py"
        Copy-Item -Path $srcLib -Destination $dst -Force
        Write-Host "adafruit_debouncer.py を $dst にコピーしました。"
    } else {
        Write-Host "adafruit_debouncer.py ファイルが見つかりません。"
    }

    # adafruit_ticks.py ファイルをコピー
    $srcLib = Join-Path $PSScriptRoot ".venv\Lib\site-packages\adafruit_ticks.py"
    if (Test-Path $srcLib) {
        $dst = Join-Path $dstLib "adafruit_ticks.py"
        Copy-Item -Path $srcLib -Destination $dst -Force
        Write-Host "adafruit_ticks.py を $dst にコピーしました。"
    } else {
        Write-Host "adafruit_ticks.py ファイルが見つかりません。"
    }
}