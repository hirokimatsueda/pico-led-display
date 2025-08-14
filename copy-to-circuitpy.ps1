# CIRCUITPYドライブを自動検出し、必要なファイル・ディレクトリをコピーするスクリプト
# -WithLib オプション指定時のみ lib のコピーを行う

param(
    [switch]$WithLib
)

# 設定
$DRIVE_LABEL = "CIRCUITPY"
$SOURCE_PATHS = @{
    Code = "code.py"
    Games = "games"
    VenvLibs = ".venv\Lib\site-packages"
}

$LIB_ITEMS = @(
    @{ Type = "Directory"; Name = "adafruit_ht16k33" }
    @{ Type = "File"; Name = "adafruit_debouncer.py" }
    @{ Type = "File"; Name = "adafruit_ticks.py" }
)

# ヘルパー関数
function Find-CircuitPyDrive {
    $drive = Get-Volume | Where-Object { $_.FileSystemLabel -eq $DRIVE_LABEL } | Select-Object -First 1
    if ($null -eq $drive) {
        Write-Host "CIRCUITPYドライブが見つかりません。コピーを中止します。" -ForegroundColor Red
        exit 1
    }
    return "$($drive.DriveLetter):\"
}

function Copy-ItemSafely {
    param(
        [string]$Source,
        [string]$Destination,
        [switch]$Recurse,
        [string]$ItemName
    )
    
    if (Test-Path $Source) {
        Copy-Item -Path $Source -Destination $Destination -Recurse:$Recurse -Force
        Write-Host "$ItemName を $Destination にコピーしました。" -ForegroundColor Green
    } else {
        Write-Host "$ItemName が見つかりません。処理を中止します。" -ForegroundColor Red
        exit 1
    }
}

function New-DirectoryIfNotExists {
    param([string]$Path)
    
    if (-not (Test-Path $Path)) {
        New-Item -Path $Path -ItemType Directory | Out-Null
    }
}

function Copy-DirectoryContents {
    param(
        [string]$SourceDir,
        [string]$DestinationDir,
        [string[]]$ExcludeItems = @(".mypy_cache")
    )
    
    if (-not (Test-Path $SourceDir)) {
        Write-Host "$SourceDir が見つかりません。処理を中止します。" -ForegroundColor Red
        exit 1
    }
    
    New-DirectoryIfNotExists -Path $DestinationDir
    
    Get-ChildItem -Path $SourceDir | 
        Where-Object { $_.Name -notin $ExcludeItems } | 
        ForEach-Object {
            $src = $_.FullName
            $dst = Join-Path $DestinationDir $_.Name
            Copy-Item -Path $src -Destination $dst -Recurse -Force
        }
}

# メイン処理
try {
    # CIRCUITPYドライブを検出
    $targetDrive = Find-CircuitPyDrive
    Write-Host "CIRCUITPYドライブを検出: $targetDrive" -ForegroundColor Cyan

    # code.py のコピー
    $sourceCode = Join-Path $PSScriptRoot $SOURCE_PATHS.Code
    $targetCode = Join-Path $targetDrive "code.py"
    Copy-ItemSafely -Source $sourceCode -Destination $targetCode -ItemName "code.py"

    # games ディレクトリのコピー
    $sourceGames = Join-Path $PSScriptRoot $SOURCE_PATHS.Games
    $targetGames = Join-Path $targetDrive "games"
    
    Copy-DirectoryContents -SourceDir $sourceGames -DestinationDir $targetGames
    Write-Host "games ディレクトリの中身を $targetGames にコピーしました。" -ForegroundColor Green

    # -WithLib オプション処理
    if ($WithLib) {
        Write-Host "ライブラリファイルのコピーを開始します..." -ForegroundColor Cyan
        
        $targetLib = Join-Path $targetDrive "lib"
        New-DirectoryIfNotExists -Path $targetLib
        
        $venvLibPath = Join-Path $PSScriptRoot $SOURCE_PATHS.VenvLibs
        
        foreach ($item in $LIB_ITEMS) {
            $sourcePath = Join-Path $venvLibPath $item.Name
            
            if ($item.Type -eq "Directory") {
                $targetPath = Join-Path $targetLib $item.Name
                Copy-DirectoryContents -SourceDir $sourcePath -DestinationDir $targetPath
                Write-Host "$($item.Name) の中身を $targetPath にコピーしました。" -ForegroundColor Green
            } else {
                $targetPath = Join-Path $targetLib $item.Name
                Copy-ItemSafely -Source $sourcePath -Destination $targetPath -ItemName $item.Name
            }
        }
    }

    Write-Host "`nデプロイ処理が完了しました。" -ForegroundColor Green
    
} catch {
    Write-Host "エラーが発生しました: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}