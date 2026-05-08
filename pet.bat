@echo off
cd /d "%~dp0"
:menu
cls
echo ===========================================
echo   iGamePet - LCD5A Mini Screen Controller
echo ===========================================
echo.
echo   [1] Cat animation (pet)
echo   [2] Display text
echo   [3] Live text (real-time typing)
echo   [4] Show default animation
echo   [5] List files
echo   [6] Upload a GIF
echo   [7] Switch between files
echo   [8] Delete a file
echo   [0] Exit
echo.
set /p choice="Choose: "

if "%choice%"=="1" goto :cat
if "%choice%"=="2" goto :text
if "%choice%"=="3" goto :live
if "%choice%"=="4" goto :default
if "%choice%"=="5" goto :list
if "%choice%"=="6" goto :upload
if "%choice%"=="7" goto :switch
if "%choice%"=="8" goto :delete
if "%choice%"=="0" exit /b 0
goto :menu

:cat
python generate_pet.py --frames 30 --output output\pet.pak
python lcd_display.py upload output\pet.pak catwalk
pause
goto :menu

:text
set /p text="Text to display: "
python lcd_display.py text "%text%"
pause
goto :menu

:live
python lcd_display.py live
pause
goto :menu

:default
python lcd_display.py play IMG1.gif
pause
goto :menu

:list
python lcd_display.py list
pause
goto :menu

:upload
set /p gif="GIF file path: "
python lcd_display.py upload "%gif%"
pause
goto :menu

:switch
python lcd_display.py switch
pause
goto :menu

:delete
python lcd_display.py delete
pause
goto :menu
