@echo off
chcp 65001 >nul
setlocal

set "SRC=D:\Program Build\CodeVerifier"
set "DST=D:\Program Build\CodeVerifier_cython"

echo ========================================
echo   CodeVerifier Cython Build
echo ========================================

echo.
echo [1/5] Clean target folder...
if exist "%DST%" rd /s /q "%DST%"
mkdir "%DST%"

echo.
echo [2/5] Copy project files...
xcopy "%SRC%\main.py" "%DST%\" /Y >nul
xcopy "%SRC%\app.ico" "%DST%\" /Y >nul
xcopy "%SRC%\CodeVerifier.spec" "%DST%\" /Y >nul
xcopy "%SRC%\core" "%DST%\core\" /E /I /Y >nul
xcopy "%SRC%\ui" "%DST%\ui\" /E /I /Y >nul
xcopy "%SRC%\resources" "%DST%\resources\" /E /I /Y >nul

echo.
echo [3/5] Compile py to pyd...
cd /d "%DST%"
python -c "import os,sys;from setuptools import setup;from Cython.Build import cythonize;py_files=[];[py_files.extend([os.path.join(r,f) for f in fs if f.endswith('.py') and f!='__init__.py' and '__pycache__' not in r]) for r,d,fs in os.walk('core')];[py_files.extend([os.path.join(r,f) for f in fs if f.endswith('.py') and f!='__init__.py' and '__pycache__' not in r]) for r,d,fs in os.walk('ui')];setup(ext_modules=cythonize(py_files,compiler_directives={'language_level':'3'}),script_args=['build_ext','--inplace'])"

if errorlevel 1 (
    echo Build failed!
    pause
    exit /b 1
)

echo.
echo [4/5] Clean temp files...
rd /s /q "%DST%\build" 2>nul
for /r "%DST%\core" %%f in (*.c) do del "%%f"
for /r "%DST%\ui" %%f in (*.c) do del "%%f"

echo.
echo [5/5] PyInstaller packaging...
pyinstaller "%DST%\CodeVerifier.spec" --noconfirm --distpath "%DST%" --workpath "%DST%\build"

rd /s /q "%DST%\build" 2>nul

echo.
echo ========================================
echo   Done!
echo ========================================
pause
