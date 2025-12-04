@echo off

setlocal EnableDelayedExpansion

::: Build and Sign the exe
 C:/Users/Darren/AppData/Local/Programs/Python/Python311/python.exe build.py

signtool sign /a /s MY /n "NGN Management Inc."  /tr http://timestamp.sectigo.com /fd SHA256 /td SHA256 /v dist\SplashUtilities\SplashUtilities.exe

::: Build the installer

makensis splashutilities.nsi

::: Clean up build artifacts
rmdir /q/s build
