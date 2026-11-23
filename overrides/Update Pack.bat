@echo off
rem Updates this Adventures of Fairytale instance from GitHub. Add -Schedule after the .ps1 to update automatically at sign-in.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0aof-update.ps1" %*
pause
