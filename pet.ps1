# iGamePet - LCD5A PowerShell console
param()

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $scriptDir

function Menu {
    Clear-Host
    Write-Host "===========================================" -ForegroundColor Cyan
    Write-Host "  iGamePet - LCD5A Mini Screen Controller" -ForegroundColor Cyan
    Write-Host "===========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  [1] Cat animation"
    Write-Host "  [2] Display text"
    Write-Host "  [3] Live text (real-time typing)"
    Write-Host "  [4] Show default animation"
    Write-Host "  [5] List files"
    Write-Host "  [6] Upload GIF"
    Write-Host "  [7] Switch between files"
    Write-Host "  [8] Delete a file"
    Write-Host "  [0] Exit"
    Write-Host ""
}

do {
    Menu
    $choice = Read-Host "Choose"
    switch ($choice) {
        "1" {
            python generate_pet.py --frames 30 --output output\pet.pak
            python lcd_display.py upload output\pet.pak catwalk
            pause
        }
        "2" {
            $text = Read-Host "Text"
            python lcd_display.py text $text
            pause
        }
        "3" {
            python lcd_display.py live
            pause
        }
        "4" {
            python lcd_display.py play IMG1.gif
            pause
        }
        "5" {
            python lcd_display.py list
            pause
        }
        "6" {
            $gif = Read-Host "GIF file path"
            python lcd_display.py upload $gif
            pause
        }
        "7" {
            python lcd_display.py switch
            pause
        }
        "8" {
            python lcd_display.py list
            $name = Read-Host "File name to delete"
            python lcd_display.py delete $name
            pause
        }
    }
} while ($choice -ne "0")

Pop-Location
