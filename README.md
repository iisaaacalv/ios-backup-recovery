# iOS Backup Recovery

<img width="610" height="192" alt="image" src="https://github.com/user-attachments/assets/30c31a09-dcc3-42fc-ae0f-a47fe28d9c11" />

Herramientas para **extraer archivos de una copia de seguridad de iOS** (iTunes / Finder) sin restaurar el dispositivo.

Útil cuando la restauración nativa falla por un archivo corrupto (el típico proceso que se queda atascado a mitad). Una copia de iOS no es un único bloque monolítico: es un sistema de archivos indexado en una base de datos SQLite (`Manifest.db`) que mapea cada archivo (renombrado a un hash) con su ruta y nombre real. Estas herramientas leen ese índice y copian los archivos **uno a uno**, saltándose los corruptos, así recuperas todo lo que está intacto aunque la restauración completa se abortara.

## Dos versiones

Este repo incluye dos herramientas. Elige según tu caso:

| | `Recuperar-Backup.ps1` | `recuperar_backup.py` |
|---|---|---|
| Lenguaje | PowerShell (nativo en Windows) | Python 3 |
| Backups **sin cifrar** | ✅ | ✅ |
| Backups **cifrados** | ❌ | ✅ (pide la contraseña y descifra) |
| Dependencias | solo `sqlite3.exe` | `pip install -r requirements.txt` |
| Ideal para | Windows, sin instalar nada pesado | cualquier SO, y obligatoria si el backup está cifrado |

**En resumen:** si el backup **no** está cifrado y estás en Windows, la versión PowerShell es la vía más rápida (no necesita Python). Si el backup **está cifrado** —o prefieres Python— usa `recuperar_backup.py`.

> ¿No sabes si está cifrado? Ambas herramientas lo detectan al abrir el backup y te avisan.

## Qué hacen (ambas)

Menú interactivo con varias opciones:

- **Por categoría:** documentos, fotos, vídeos, audio, o todo junto.
- **Árbol completo:** extrae todo el backup reconstruyendo la estructura real de carpetas (`domain` + ruta original). Incluye archivos de sistema y datos internos de apps.
- **Solo mis datos:** extrae el contenido de usuario (fotos, vídeos, documentos, apuntes, audio...) reconstruyendo carpetas, pero filtrando dominios de sistema y basura técnica (cachés, bases de datos internas, plists, logs, cookies). Es la opción recomendada para el 90% de los casos.
- **Contador:** cuenta cuántos archivos hay de cada tipo sin extraer nada.

Características comunes: detección automática de la carpeta del backup (UDID), aviso si está cifrado, y salto de archivos corruptos/ilegibles sin interrumpir el proceso (al final indica `recuperados / total` y cuántos se saltaron).

## Ruta habitual del backup

Windows:
```
C:\Users\<usuario>\AppData\Roaming\Apple Computer\MobileSync\Backup\<UDID>\
```
macOS:
```
~/Library/Application Support/MobileSync/Backup/<UDID>/
```

> **Antes de nada:** copia la carpeta del backup a tu disco y trabaja sobre la copia, nunca sobre el original (pendrive / unidad de origen).

---

## Uso · versión PowerShell (sin cifrar, Windows)

1. Descarga `sqlite3.exe` de [sqlite.org/download.html](https://www.sqlite.org/download.html) (paquete *sqlite-tools* para Windows x64) y déjalo en la misma carpeta que el script.
2. Click derecho en `Recuperar-Backup.ps1` → **Ejecutar con PowerShell** (o `.\Recuperar-Backup.ps1` en una terminal).
3. Indica la ruta del backup y elige una opción del menú.

> Si PowerShell bloquea la ejecución: `Set-ExecutionPolicy -Scope Process Bypass`

## Uso · versión Python (cifrados y sin cifrar)

1. Instala las dependencias:
   ```
   pip install -r requirements.txt
   ```
   (`colorama` para los colores; `iphone_backup_decrypt` solo hace falta para backups cifrados.)
2. Ejecuta:
   ```
   python recuperar_backup.py
   ```
3. Indica la ruta del backup. Si está cifrado, te pedirá la contraseña que se usó al crear la copia y descifrará automáticamente.

Los archivos recuperados se guardan en `Escritorio/Recuperado_Backup/`, ordenados por categoría o por estructura de carpetas según la opción.

## Limitaciones

- **Backups cifrados sin contraseña:** si el backup está cifrado y no se conoce la contraseña, los datos **no** se pueden recuperar. El cifrado de Apple está diseñado para eso; no existe forma de saltárselo. La contraseña del backup no es el código de desbloqueo del dispositivo.
- Los archivos extraídos por categoría se nombran con un prefijo del hash para evitar colisiones; en los modos de árbol se respeta el nombre y ruta original.

## Aviso legal

Estas herramientas están pensadas para recuperar **datos propios** o de un dispositivo sobre el que se tiene autorización expresa del propietario. El uso para acceder a información de terceros sin consentimiento puede ser ilegal. El autor no se responsabiliza del mal uso.

## Licencia

MIT. Ver [LICENSE](LICENSE).
