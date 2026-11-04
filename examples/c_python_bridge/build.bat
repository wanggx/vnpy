@echo off
setlocal
set VCVARS="C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
call %VCVARS%
cl /nologo /LD /O2 /utf-8 /W3 work.c /Fe:work.dll
if %ERRORLEVEL% NEQ 0 exit /b 1
echo Built work.dll
dir work.dll
