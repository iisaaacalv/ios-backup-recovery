# iOS Backup Recovery

Herramienta en PowerShell para **extraer archivos de una copia de seguridad de iOS** (iTunes / Finder) sin restaurar el dispositivo.

Útil cuando la restauración nativa falla por un archivo corrupto (el típico error que se queda atascado a mitad de proceso). Una copia de seguridad de iOS no es un único bloque monolítico: es un sistema de archivos indexado en una base de datos SQLite (`Manifest.db`). Esta herramienta lee ese índice y copia los archivos **uno a uno**, saltándose los corruptos, de modo que recuperas todo lo que está intacto aunque la restauración completa se abortara.

## Características

- Menú interactivo con varias opciones de extracción:
  - Por categoría: documentos, fotos, vídeos, audio, o todo junto.
  - **Árbol completo:** extrae todo el backup reconstruyendo la estructura real de carpetas (`domain` + ruta original). Incluye archivos de sistema y datos internos de apps.
  - **Solo mis datos:** extrae el contenido de usuario (fotos, vídeos, documentos, apuntes, audio...) reconstruyendo carpetas, pero filtrando dominios de sistema y basura técnica (cachés, bases de datos internas, plists, logs).
  - Contador: cuenta cuántos archivos hay de cada tipo sin extraer nada.
- Detecta automáticamente la carpeta del backup (UDID) aunque apuntes a la carpeta padre.
- Avisa si el backup está cifrado.
- Se salta los archivos corruptos o ilegibles sin interrumpir el proceso.
- Organiza la salida y evita colisiones de nombres.

## Requisitos

- Windows 10 / 11 con PowerShell (incluido por defecto).
- `sqlite3.exe` — descárgalo de [sqlite.org/download.html](https://www.sqlite.org/download.html) (paquete *sqlite-tools* para Windows x64) y déjalo en la misma carpeta que el script.

## Uso

1. Copia la carpeta del backup a tu disco duro (no trabajes sobre el pendrive / unidad original).

   Ruta habitual del backup en Windows:
   ```
   C:\Users\<usuario>\AppData\Roaming\Apple Computer\MobileSync\Backup\<UDID>\
   ```

2. Coloca `sqlite3.exe` junto a `Recuperar-Backup.ps1`.

3. Click derecho en el script → **Ejecutar con PowerShell**
   (o desde una terminal: `.\Recuperar-Backup.ps1`).

4. Indica la ruta del backup y elige una opción del menú.

Los archivos recuperados se guardan en `Escritorio\Recuperado_Backup\`, ordenados por tipo.

> Si PowerShell bloquea la ejecución, lanza primero:
> `Set-ExecutionPolicy -Scope Process Bypass`

## Limitaciones

- **Backups cifrados:** sin la contraseña no es posible extraer los datos (están cifrados en disco). Para esos casos hace falta una herramienta que descifre conociendo la contraseña.
- Los archivos de fotos/vídeos se recuperan con el nombre original del backup, no necesariamente con una fecha legible.

## Aviso legal

Esta herramienta está pensada para recuperar **datos propios** o de un dispositivo sobre el que se tiene autorización expresa del propietario. El uso para acceder a información de terceros sin consentimiento puede ser ilegal. El autor no se responsabiliza del mal uso.

## Licencia

MIT. Ver [LICENSE](LICENSE).
