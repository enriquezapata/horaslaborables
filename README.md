# Horas laborables

Herramienta en Python que calcula las **horas laborables totales** de un año natural a partir de un fichero YAML: define tu jornada por día de la semana (normal e intensiva), festivos y vacaciones. Los fines de semana no cuentan como laborables.

Incluye una **interfaz gráfica local** (PyQt6) para editar la configuración con controles adecuados a cada dato, validar entradas y ver el detalle del cálculo.

## Requisitos

- Python 3.8 o superior (recomendado instalar desde [python.org](https://www.python.org/downloads/) o el gestor de tu sistema).
- [PyYAML](https://pyyaml.org/) y [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) (se instalan con `requirements.txt` dentro del entorno virtual).

## Instalación

### 1. Clonar el repositorio

```bash
git clone <URL-del-repositorio>.git
cd horaslaborables
```

### 2. Crear el entorno virtual

El proyecto usa un directorio `.venv` en la raíz (ya está ignorado por Git). Desde la carpeta del proyecto:

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si la activación falla por política de ejecución, ejecuta una vez en la misma sesión:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Linux y macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Tras activar el entorno, el prompt suele mostrar `(.venv)`. Para salir del entorno: `deactivate`.

### 3. Comprobar la instalación

```bash
python calcular_horas_laborables.py --help
```

## Uso

Por defecto el script busca el fichero `config_horas_laborables.yml` en el directorio actual. En este repositorio el ejemplo está en `config_horas_laborables_2026.yml`, así que indica la ruta con `-c`:

```bash
python calcular_horas_laborables.py 2026 -c config_horas_laborables_2026.yml
```

Argumentos:

| Argumento | Descripción |
|-----------|-------------|
| `year` | Año a calcular (obligatorio), por ejemplo `2026`. |
| `-c`, `--config` | Ruta al YAML de configuración. Por defecto: `config_horas_laborables.yml`. |

Salida: resumen con horas totales, días laborables computados, días excluidos por festivo/vacaciones y días de fin de semana.

## Interfaz gráfica (local)

Con el entorno virtual activado:

```powershell
python gui_app.py
```

Desde la aplicación puedes definir año (`QSpinBox`), fechas de jornada intensiva (`QDateEdit` con calendario), listas de festivos y vacaciones (rangos en tabla y días sueltos), horas por día (`QDoubleSpinBox`), **Abrir / Guardar YAML**, y ejecutar el cálculo con vista resumen y tabla detallada. El estilo visual está en `gui/resources/style.qss`.

Atajos útiles: **F5** calcular, **Ctrl+O** abrir, **Ctrl+S** guardar, **Ctrl+Q** salir.

### Nota técnica (legibilidad en Windows)

En equipos con **modo oscuro** activo en Windows, Qt puede combinar el tema del sistema con las hojas de estilo (**QSS**) y dejar algunas zonas (áreas con scroll, listas, pestañas) con **fondo muy oscuro y poco contraste**. La aplicación fuerza el estilo **Fusion**, aplica una **paleta clara** en `gui_app.py` y extiende `gui/resources/style.qss` para que fondo y texto sean siempre legibles.

**Fallo resuelto en desarrollo:** al arrancar fallaba `setIconSize()` en la barra de herramientas porque `QStyle.pixelMetric()` devuelve un entero y PyQt6 exige un `QSize` (se construye `QSize(px, px)` a partir de ese valor).

## Formato del YAML de configuración

- **`jornada_intensiva`**: `inicio` y `fin` (fechas `YYYY-MM-DD`) del periodo en que aplican las horas de `horas_laborables.jornada_intensiva`.
- **`vacaciones`**:
  - `rangos`: lista de `{ inicio, fin }` (ambos inclusive).
  - `dias_individuales`: lista de fechas sueltas.
- **`festivos`**: lista de fechas `YYYY-MM-DD` que no son laborables (aunque sea lunes a viernes).
- **`horas_laborables`**:
  - `semana_normal`: horas por día (claves: `lunes` … `domingo`; sábado y domingo suelen ser `0`).
  - `jornada_intensiva`: mismo esquema para el periodo intensivo.

Los nombres de día aceptan variantes con o sin tilde (`miercoles` / `miércoles`, etc.), según el código.

El fichero `config_horas_laborables_2026.yml` es un ejemplo orientativo (Madrid capital 2026, vacaciones de ejemplo). **Debes adaptar festivos, vacaciones y jornada** a tu convenio o calendario real.

## Estructura del repositorio

| Ruta | Descripción |
|------|-------------|
| `calcular_horas_laborables.py` | CLI y lógica (`config_from_raw`, `calcular_horas_laborables`). |
| `gui_app.py` | Arranque de la aplicación gráfica. |
| `gui/main_window.py` | Ventana principal PyQt6 (formularios y validación). |
| `gui/resources/style.qss` | Hojas de estilo Qt. |
| `config_horas_laborables_2026.yml` | Configuración de ejemplo para 2026. |
| `requirements.txt` | Dependencias Python. |
| `.gitignore` | Artefactos locales y entornos virtuales excluidos de Git. |
| `.gitattributes` | Normalización de finales de línea en texto. |
| `scripts/setup_venv.ps1` | Ayuda opcional para crear `.venv` en Windows. |
| `scripts/setup_venv.sh` | Ayuda opcional para crear `.venv` en Linux/macOS. |

## Licencia

Este proyecto se distribuye bajo la **licencia MIT** (texto legal en inglés, habitual para esta licencia):

```
MIT License

Copyright (c) 2026 horaslaborables contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
