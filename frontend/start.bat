@echo off
title The First 10 Minutes - Local Web App
echo ========================================================
echo   The First 10 Minutes - Crisis Decision Demo
echo ========================================================
echo Starting local web server. The browser will open shortly...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0server.ps1"
