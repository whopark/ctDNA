@echo off
REM Build ctDNA.exe standalone executable
REM Prerequisites: pip install pyinstaller requests python-docx

echo === ctDNA Annotation Pipeline — Build ===

REM Install build dependencies if missing
pip install pyinstaller requests python-docx >nul 2>&1

REM Clean previous build
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM Build using spec file
pyinstaller ctdna.spec

if exist dist\ctDNA.exe (
    echo.
    echo === Build successful! ===
    echo Output: dist\ctDNA.exe
    echo.
    echo NOTE: On first run, kb.json will be copied next to the exe
    echo       for read/write access. template.docx is bundled inside.
) else (
    echo.
    echo === Build FAILED — check errors above ===
    exit /b 1
)
