@echo OFF

pyinstaller --noconsole --onefile  %1%

move /Y dist\*.exe .\
del /F *.spec 

rmdir /Q /S dist build
