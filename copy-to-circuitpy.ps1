# CIRCUITPYドライブを自動検出し、code.pyをコピーするスクリプト
# コピー先が見つからなければ中止

$source = Join-Path $PSScriptRoot "code.py"
$targetFile = "code.py"

# CIRCUITPYドライブをラベルで探す
$drive = Get-Volume | Where-Object { $_.FileSystemLabel -eq "CIRCUITPY" } | Select-Object -First 1

if ($null -eq $drive) {
    Write-Host "CIRCUITPYドライブが見つかりません。コピーを中止します。"
    exit 1
}

 $target = "$($drive.DriveLetter):\$targetFile"
Copy-Item -Path $source -Destination $target -Force
Write-Host "code.py を $target にコピーしました。"

# adafruit_ht16k33 フォルダを lib ディレクトリにコピー
$srcLib = Join-Path $PSScriptRoot ".venv\Lib\site-packages\adafruit_ht16k33"
$dstLib = "$($drive.DriveLetter):\lib\adafruit_ht16k33"
if (Test-Path $srcLib) {
    Copy-Item -Path $srcLib -Destination $dstLib -Recurse -Force
    Write-Host "adafruit_ht16k33 を $dstLib にコピーしました。"
} else {
    Write-Host "adafruit_ht16k33 フォルダが見つかりません。"
}
