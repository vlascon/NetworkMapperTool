# 🌐 Network Mapper & Hardware Inventory Tool

Herramienta avanzada desarrollada en Python para el análisis de redes locales, escaneo de dispositivos, inventario detallado de hardware y generación de reportes visuales interactivos en HTML.

---

## 🚀 Características Principales

1. **🗺️ Escaneo de Red Completo:**
   - Detección automática de puertas de enlace (Gateways) y segmentos de red locales.
   - Escaneo de hosts activos mediante solicitudes ARP / ICMP / Socket.
   - Resolución de nombres de host (*Hostname*) y detección de fabricantes de tarjetas de red (*Vendor* por MAC).

2. **💻 Inventario de Hardware Local:**
   - Recopilación de especificaciones del sistema operativo Windows.
   - Monitoreo de memoria RAM, uso de CPU, almacenamiento en discos y configuración de interfaces de red locales.

3. **🤖 Clasificación Inteligente de Dispositivos:**
   - Categorización automática de los dispositivos encontrados en la red:
     - *ISP Router / Gateway*
     - *Printer* (Impresoras HP, Epson, Brother, Canon, etc.)
     - *Mobile Device* (Smartphones y tablets Apple, Samsung, Xiaomi, etc.)
     - *NAS / Server / Virtual*
     - *Router / Switch / AP*
     - *Computer / Unknown Device*

4. **📊 Reportes Interactivos HTML:**
   - Generación de un informe visual estético (`Mapa_Red_Inventario.html`) con tablas detalladas, tarjetas de resumen y apertura automática en el navegador web predeterminado.

5. **📦 Ejecutable Autocontenido (.exe):**
   - Compilable en un solo paquete portable mediante PyInstaller, sin necesidad de tener Python instalado en las PCs de destino.

---

## 🛠️ Tecnologías y Librerías

- **Python 3.x**
- [`psutil`](https://github.com/giampaolo/psutil): Monitoreo de procesos y utilización del sistema/hardware.
- [`requests`](https://requests.readthedocs.io/): Consultas HTTP (para base de datos MAC/OUI).
- [`rich`](https://github.com/Textualize/rich): Interfaz de consola moderna con colores, paneles y barras de progreso.
- **PyInstaller**: Creación del archivo ejecutable de Windows (`.exe`).

---

## 📥 Descarga del Ejecutable y Versionamiento

Puedes descargar la versión más reciente lista para usar sin instalar dependencias:
1. Dirígete a la sección de **[Releases](../../releases)** del repositorio en GitHub.
2. Descarga el archivo comprimido ZIP correspondiente a la última versión (ej. `NetworkMapperTool-v1.0.0.zip`) o el ejecutable directamente desde los assets de la release.
3. Descomprime y ejecuta `NetworkMapperTool.exe`.

---

## ⚙️ Instalación y Ejecución Local (Código Fuente)

Si prefieres ejecutar el script directamente desde el código fuente:

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/TU_USUARIO/NetworkMapperTool.git
   cd NetworkMapperTool
   ```

2. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la herramienta:**
   ```bash
   python src/main.py
   ```

---

## 🔨 Compilación del Ejecutable (.exe)

Para generar tu propio ejecutable portable utilizando PyInstaller:

Puedes utilizar el script automatizado provisto en la raíz del proyecto:
```cmd
build.bat
```
O bien ejecutar manualmente:
```cmd
pyinstaller --noconfirm --onedir --clean --name "NetworkMapperTool" src/main.py
```
El ejecutable resultante se ubicará en la carpeta `dist/NetworkMapperTool/NetworkMapperTool.exe`.

---

## 📁 Estructura del Proyecto

```text
NetworkMapperTool/
├── src/
│   ├── __init__.py
│   ├── main.py              # Punto de entrada y orquestador CLI (Rich)
│   ├── hardware.py          # Recopilación de especificaciones de hardware (psutil)
│   ├── network_discovery.py # Descubrimiento de red, rutas y ARP
│   ├── classifier.py        # Clasificación de dispositivos y resolución de hostnames
│   └── reporter.py          # Generador de reportes visuales en HTML
├── requirements.txt         # Dependencias del proyecto
├── build.bat                # Script de compilación con PyInstaller
├── NetworkMapperTool.spec   # Configuración de PyInstaller
└── README.md                # Documentación del proyecto
```

---

## 📄 Licencia

Este proyecto es de código abierto y está disponible bajo la licencia [MIT](LICENSE).
