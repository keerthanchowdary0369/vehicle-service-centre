@echo off
title Vehicle Service Centre
echo ===================================================
echo Starting Vehicle Service Centre Database System...
echo ===================================================
echo.
echo Please leave this black window open while using the website. 
echo You can close it when you are done.
echo.

:: Wait 2 seconds and open browser
start "" "http://127.0.0.1:5000"

:: Start the Flask app
py app.py
pause
