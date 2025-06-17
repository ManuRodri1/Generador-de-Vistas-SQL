
🧠 Generador Automático de Vistas SQL para Power BI

Esta herramienta ha sido diseñada para profesionales de Business Intelligence que trabajan con modelos estructurados en Power BI y necesitan generar vistas SQL de forma rápida, organizada y dinámica.

🚀 ¿Qué hace esta herramienta?

- 🔌 Se conecta a tu base de datos SQL Server.
- 📋 Permite seleccionar múltiples **tablas principales** y **tablas relacionadas**.
- 🔗 Crea automáticamente las relaciones (`JOIN`) entre ellas.
- 🧱 Genera la vista SQL y te la muestra en pantalla.
- 📝 Puedes guardar la vista directamente en tu base de datos o copiar el código SQL.
- 🛠️ También puedes **modificar vistas ya creadas** de forma visual.


💻 Requisitos

- Python 3.8 o superior
- SQL Server (con ODBC configurado)
- Librerías:
  - `pyodbc`
  - `tkinter` (incluido con Python)
  - `ttkthemes`

Instalación de dependencias:
```bash
pip install pyodbc ttkthemes
