@echo off
REM SuperLocalMemory V2 - Windows CLI Wrapper (CMD variant)
REM Copyright (c) 2026 Varun Pratap Bhardwaj
REM Licensed under MIT License
REM
REM This is a simplified wrapper that calls slm.bat
REM Exists for compatibility with systems that prefer .cmd over .bat

call "%~dp0slm.bat" %*
exit /b %ERRORLEVEL%
