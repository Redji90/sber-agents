@echo off
setlocal
set "SOURCE=C:\.ssh\immers-vm.pem"
set "DEST=%USERPROFILE%\.ssh\immers-vm.pem"

if not exist "%USERPROFILE%\.ssh" mkdir "%USERPROFILE%\.ssh"

copy /Y "%SOURCE%" "%DEST%" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo Key copied successfully
    icacls "%DEST%" /inheritance:r /grant:r "%USERNAME%:(R)" >nul 2>&1
    echo Permissions set
    echo You can now use: ssh -i "%DEST%" ubuntu@195.209.210.171
) else (
    echo Failed to copy key. Trying with elevated permissions...
    echo Please run this script as Administrator or check file permissions.
)

