#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
================================================================
  iOS Backup Recovery  -  recuperar_backup.py
  https://github.com/TU-USUARIO/ios-backup-recovery

  Extrae archivos de una copia de seguridad de iOS (iTunes/Finder)
  sin restaurar el dispositivo. Funciona con backups cifrados
  (pide la contrasena y descifra) y sin cifrar.

  Se salta los archivos corruptos/ilegibles automaticamente.

  Licencia: MIT
  Uso solo sobre backups propios o con autorizacion del propietario.
================================================================
"""

import os
import sys
import sqlite3
import shutil
import getpass

# ----- Colores: usa colorama si esta, si no, sin color -----
try:
    from colorama import init as _cinit, Fore, Style
    _cinit(autoreset=True)
    C_CYAN = Fore.CYAN
    C_GREEN = Fore.GREEN
    C_YEL = Fore.YELLOW
    C_RED = Fore.RED
    C_MAG = Fore.MAGENTA
    C_DIM = Style.DIM
    C_RST = Style.RESET_ALL
    C_BRIGHT = Style.BRIGHT
except ImportError:
    C_CYAN = C_GREEN = C_YEL = C_RED = C_MAG = C_DIM = C_RST = C_BRIGHT = ""

# La libreria de descifrado es opcional: solo hace falta si el backup esta cifrado
try:
    from iphone_backup_decrypt import EncryptedBackup
    HAY_DESCIFRADO = True
except ImportError:
    HAY_DESCIFRADO = False


BANNER = r"""
  _  ___  ____    ____             _
 (_)/ _ \/ ___|  | __ )  __ _  ___| | ___   _ _ __
 | | | | \___ \  |  _ \ / _` |/ __| |/ / | | | '_ \
 | | |_| |___) | | |_) | (_| | (__|   <| |_| | |_) |
 |_|\___/|____/  |____/ \__,_|\___|_|\_\\__,_| .__/
                                             |_|
        R E C O V E R Y   T O O L
"""


# ----------------------------------------------------------------
#  Filtros (mismos que la version PowerShell, en SQL)
# ----------------------------------------------------------------
EXT = {
    "Documentos": ['.pdf', '.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx',
                   '.txt', '.rtf', '.pages', '.numbers', '.key', '.csv'],
    "Fotos":      ['.jpg', '.jpeg', '.png', '.heic', '.gif', '.bmp', '.tiff', '.webp'],
    "Videos":     ['.mov', '.mp4', '.m4v', '.avi', '.3gp', '.hevc'],
    "Audio":      ['.m4a', '.mp3', '.wav', '.aac', '.caf'],
}


def filtro_categoria(cat):
    """Devuelve la clausula SQL WHERE para una categoria por extension."""
    exts = EXT[cat]
    likes = " OR ".join(f"lower(relativePath) LIKE '%{e}'" for e in exts)
    return f"({likes})"


# excluye sistema y basura tecnica, conserva documentos/media aunque esten en apps
FILTRO_MIS_DATOS = """
domain NOT LIKE 'SystemPreferencesDomain%'
AND domain NOT LIKE 'KeychainDomain%'
AND domain NOT LIKE 'ManagedPreferencesDomain%'
AND domain NOT LIKE 'RootDomain%'
AND domain NOT LIKE 'WirelessDomain%'
AND relativePath NOT LIKE '%Library/Caches/%'
AND relativePath NOT LIKE '%Library/Cookies/%'
AND relativePath NOT LIKE '%Library/Preferences/%'
AND lower(relativePath) NOT LIKE '%.sqlite%'
AND lower(relativePath) NOT LIKE '%.db'
AND lower(relativePath) NOT LIKE '%.plist'
AND lower(relativePath) NOT LIKE '%.log'
AND relativePath != ''
"""


# ----------------------------------------------------------------
#  Utilidades de impresion
# ----------------------------------------------------------------
def info(msg):  print(f"{C_CYAN}{msg}{C_RST}")
def ok(msg):    print(f"{C_GREEN}{msg}{C_RST}")
def warn(msg):  print(f"{C_YEL}{msg}{C_RST}")
def err(msg):   print(f"{C_RED}{msg}{C_RST}")


def pausa():
    input(f"\n{C_DIM}Pulsa ENTER para continuar...{C_RST}")


def limpiar_pantalla():
    os.system("cls" if os.name == "nt" else "clear")


def ruta_segura(domain, relative_path):
    """Construye una ruta de salida valida en cualquier SO."""
    rel = f"{domain}/{relative_path}".replace("/", os.sep).replace("\\", os.sep)
    # caracteres no validos en Windows
    for ch in ':*?"<>|':
        rel = rel.replace(ch, "_")
    return rel


# ================================================================
#  CLASE DE TRABAJO: maneja cifrado y sin cifrar de forma uniforme
# ================================================================
class Backup:
    def __init__(self, ruta):
        self.ruta = ruta
        self.cifrado = False
        self.enc = None          # EncryptedBackup, si esta cifrado
        self.manifest = os.path.join(ruta, "Manifest.db")
        self.detectar_cifrado()

    def detectar_cifrado(self):
        """Lee Manifest.plist para saber si IsEncrypted = true."""
        plist = os.path.join(self.ruta, "Manifest.plist")
        if os.path.exists(plist):
            try:
                with open(plist, "rb") as f:
                    data = f.read()
                idx = data.find(b"IsEncrypted")
                if idx != -1 and b"true" in data[idx:idx + 60]:
                    self.cifrado = True
            except Exception:
                pass

    def abrir(self):
        """Prepara el acceso. Si esta cifrado pide contrasena y descifra."""
        if self.cifrado:
            if not HAY_DESCIFRADO:
                err("El backup esta CIFRADO pero falta la libreria de descifrado.")
                err("Instala con:  pip install iphone_backup_decrypt")
                return False
            warn("\nEste backup esta CIFRADO. Necesito la contrasena que se")
            warn("puso al crear la copia (no es el codigo del dispositivo).")
            for intento in range(3):
                pw = getpass.getpass(f"{C_CYAN}Contrasena del backup: {C_RST}")
                try:
                    self.enc = EncryptedBackup(backup_directory=self.ruta, passphrase=pw)
                    self.enc.test_decryption()
                    ok("Contrasena correcta. Backup descifrado en memoria.")
                    return True
                except Exception:
                    err(f"Contrasena incorrecta ({2 - intento} intentos restantes).")
            err("Demasiados intentos fallidos.")
            return False
        else:
            if not os.path.exists(self.manifest):
                err("No encuentro Manifest.db en esa carpeta.")
                return False
            return True

    def cursor(self):
        """Devuelve un cursor sobre el Manifest.db (descifrado si aplica)."""
        if self.cifrado:
            return self.enc.manifest_db_cursor()
        con = sqlite3.connect(self.manifest)
        return con.cursor()

    def consultar(self, where):
        """Lista de (fileID, domain, relativePath) que cumplen el WHERE."""
        cur = self.cursor()
        q = ("SELECT fileID, domain, relativePath FROM Files "
             "WHERE flags = 1")
        if where:
            q += f" AND ({where})"
        cur.execute(q)
        filas = cur.fetchall()
        return filas

    def copiar_uno(self, file_id, domain, relative_path, destino):
        """Copia/descifra un archivo. Devuelve True si fue bien."""
        try:
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            if self.cifrado:
                # la libreria descifra y escribe directamente
                self.enc.extract_file(relative_path=relative_path,
                                      domain_like=domain,
                                      output_filename=destino)
            else:
                src = os.path.join(self.ruta, file_id[:2], file_id)
                if not os.path.exists(src):
                    return False
                shutil.copy2(src, destino)
            return True
        except Exception:
            return False   # corrupto / ilegible / ruta larga -> se salta


# ================================================================
#  EXTRACCION (comun a categorias y a arbol)
# ================================================================
def extraer(backup, filas, out_dir, etiqueta, por_arbol):
    if not filas:
        warn(f"  No se encontraron archivos para: {etiqueta}")
        return

    raiz = os.path.join(out_dir, etiqueta)
    os.makedirs(raiz, exist_ok=True)

    total = len(filas)
    okc = 0
    fallos = 0
    for i, (file_id, domain, relative_path) in enumerate(filas, 1):
        if por_arbol:
            destino = os.path.join(raiz, ruta_segura(domain, relative_path))
        else:
            nombre = os.path.basename(relative_path) or file_id
            destino = os.path.join(raiz, f"{file_id[:8]}_{nombre}")

        if backup.copiar_uno(file_id, domain, relative_path, destino):
            okc += 1
        else:
            fallos += 1

        # barra de progreso simple
        if i % 25 == 0 or i == total:
            pct = int(i / total * 100)
            sys.stdout.write(f"\r  {etiqueta}: {i}/{total} ({pct}%)   ")
            sys.stdout.flush()

    print()
    ok(f"  {etiqueta} -> recuperados: {okc} / {total}  (saltados: {fallos})")
    info(f"  Guardado en: {raiz}")


# ================================================================
#  MENU
# ================================================================
def menu():
    print(f"\n{C_CYAN}{C_BRIGHT}============== QUE QUIERES SACAR? =============={C_RST}")
    print("  1) Documentos (Word, PDF, PPT, Excel, txt...)")
    print("  2) Fotos (jpg, png, heic...)")
    print("  3) Videos (mov, mp4...)")
    print("  4) Audio (m4a, mp3...)")
    print("  5) TODO (documentos + fotos + videos + audio)")
    print("  6) Contar cuantos hay de cada tipo (sin extraer)")
    print(f"  {C_DIM}-----------------------------------------------{C_RST}")
    print(f"  {C_MAG}7) ARBOL COMPLETO (todo el backup, estructura real){C_RST}")
    print(f"  {C_MAG}8) SOLO MIS DATOS (todo menos sistema y datos de apps){C_RST}")
    print("  0) Salir")
    print(f"{C_CYAN}================================================{C_RST}")


def localizar_backup(ruta):
    """Si la ruta no tiene Manifest.* busca la carpeta UDID dentro."""
    if os.path.exists(os.path.join(ruta, "Manifest.plist")) or \
       os.path.exists(os.path.join(ruta, "Manifest.db")):
        return ruta
    if os.path.isdir(ruta):
        for sub in os.listdir(ruta):
            p = os.path.join(ruta, sub)
            if os.path.isdir(p) and (
                os.path.exists(os.path.join(p, "Manifest.plist")) or
                os.path.exists(os.path.join(p, "Manifest.db"))):
                return p
    return ruta


def main():
    limpiar_pantalla()
    print(f"{C_CYAN}{C_BRIGHT}{BANNER}{C_RST}")
    print(f"{C_DIM}  Recuperacion forense de copias iOS  |  uso autorizado unicamente{C_RST}\n")

    # --- ruta ---
    ruta = input("Arrastra aqui la carpeta del backup (o pega la ruta) y ENTER:\n> ").strip().strip('"')
    if not os.path.isdir(ruta):
        err("Esa ruta no existe o no es una carpeta.")
        pausa(); return

    ruta = localizar_backup(ruta)
    info(f"Backup: {ruta}")

    backup = Backup(ruta)
    if backup.cifrado:
        warn("Estado: CIFRADO")
    else:
        ok("Estado: sin cifrar")

    if not backup.abrir():
        pausa(); return

    out_dir = os.path.join(os.path.expanduser("~"), "Desktop", "Recuperado_Backup")
    # por si no existe Desktop (algunos Windows en otros idiomas)
    if not os.path.isdir(os.path.dirname(out_dir)):
        out_dir = os.path.join(os.path.expanduser("~"), "Recuperado_Backup")
    info(f"Salida: {out_dir}")

    while True:
        menu()
        try:
            op = input("Opcion> ").strip()
        except EOFError:
            break

        if op in ("1", "2", "3", "4"):
            cat = {"1": "Documentos", "2": "Fotos", "3": "Videos", "4": "Audio"}[op]
            filas = backup.consultar(filtro_categoria(cat))
            extraer(backup, filas, out_dir, cat, por_arbol=False)
            pausa()

        elif op == "5":
            for cat in ("Documentos", "Fotos", "Videos", "Audio"):
                filas = backup.consultar(filtro_categoria(cat))
                extraer(backup, filas, out_dir, cat, por_arbol=False)
            ok(f"\nTODO LISTO. Revisa: {out_dir}")
            pausa()

        elif op == "6":
            print()
            for cat in ("Documentos", "Fotos", "Videos", "Audio"):
                n = len(backup.consultar(filtro_categoria(cat)))
                info(f"  {cat:<12}: {n}")
            pausa()

        elif op == "7":
            warn("\nExtrayendo el ARBOL COMPLETO (incluye sistema y datos de apps)...")
            filas = backup.consultar(None)
            extraer(backup, filas, out_dir, "Arbol_Completo", por_arbol=True)
            pausa()

        elif op == "8":
            warn("\nExtrayendo SOLO tus datos (sin sistema ni datos internos de apps)...")
            filas = backup.consultar(FILTRO_MIS_DATOS)
            extraer(backup, filas, out_dir, "Mis_Datos", por_arbol=True)
            pausa()

        elif op == "0":
            ok("Hasta luego.")
            break
        else:
            warn("Opcion no valida.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelado.")
