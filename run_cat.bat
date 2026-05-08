@echo off
cd /d "%~dp0"
echo === iGamePet LCD5A Cat Animation ===
echo.
echo [1/3] Generating cat animation...
python generate_pet.py --frames 30 --output output\pet.pak
if %errorlevel% neq 0 goto :fail
echo.
echo [2/3] Uploading to LCD5A...
python -c "import os,clr;exec(open('lcd_display.py').read().split('def main')[0]);lcd=LCD5AController();lcd.connect();lcd.upload_and_play(r'%cd%\output\pet.pak','catwalk');lcd.close()"
if %errorlevel% neq 0 goto :fail
echo.
echo [3/3] Done! Check the mini screen.
pause
goto :eof

:fail
echo.
echo [FAIL] Something went wrong.
pause
exit /b 1
