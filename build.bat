@echo off
echo [INFO] Instalando dependencias necesarias...
pip install --upgrade pip
pip install -r requirements.txt

echo [INFO] Generando ejecutable autocontenido (.exe) con PyInstaller...
pyinstaller --noconfirm --onedir --clean --name "NetworkMapperTool" src/main.py

echo [INFO] ¡Compilación finalizada! El ejecutable se encuentra en la carpeta dist/NetworkMapperTool/NetworkMapperTool.exe
pause
