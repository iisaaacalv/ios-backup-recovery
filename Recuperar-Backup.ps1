<#
================================================================
  iOS Backup Recovery  -  Recuperar-Backup.ps1
  https://github.com/<tu-usuario>/ios-backup-recovery

  RECUPERADOR DE BACKUP iOS  (iTunes / Finder)
  Extrae archivos de una copia de seguridad sin restaurar nada.
  Se salta los archivos corruptos automaticamente.

  Licencia: MIT
  Uso solo sobre backups propios o con autorizacion del propietario.
================================================================
  USO:
    1. Click derecho sobre el archivo -> "Ejecutar con PowerShell"
       (o abre PowerShell y ejecuta: .\Recuperar-Backup.ps1)
    2. Indica la ruta de la carpeta del backup.
    3. Elige en el menu que quieres sacar.
================================================================
#>

# --- Permite ejecutar aunque la politica lo bloquee (solo esta sesion) ---
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force -ErrorAction SilentlyContinue

$ErrorActionPreference = "Stop"

function Pausa { Write-Host ""; Read-Host "Pulsa ENTER para continuar" | Out-Null }

# ----------------------------------------------------------------
#  Localizar sqlite3.exe
# ----------------------------------------------------------------
function Get-Sqlite {
    # 1) En el PATH
    $cmd = Get-Command sqlite3.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    # 2) Junto a este script
    $local = Join-Path $PSScriptRoot "sqlite3.exe"
    if (Test-Path $local) { return $local }
    return $null
}

# ----------------------------------------------------------------
#  Lee el Manifest.db. Si no hay sqlite3.exe, usa fallback .NET
# ----------------------------------------------------------------
function Get-Files-Sqlite {
    param($SqliteExe, $DbPath, $Filter)
    $query = "SELECT fileID, relativePath FROM Files WHERE $Filter;"
    $rows = & $SqliteExe -separator "|" $DbPath $query
    $result = @()
    foreach ($r in $rows) {
        $p = $r -split '\|', 2
        if ($p.Count -eq 2 -and $p[0]) {
            $result += [PSCustomObject]@{ fileID = $p[0].Trim(); relativePath = $p[1] }
        }
    }
    return $result
}

# ----------------------------------------------------------------
#  Copia los archivos a la carpeta de salida, por tipo
# ----------------------------------------------------------------
function Extraer {
    param($Files, $BackupDir, $OutDir, $Etiqueta)

    if ($Files.Count -eq 0) {
        Write-Host "  No se encontraron archivos de tipo: $Etiqueta" -ForegroundColor Yellow
        return
    }

    $destino = Join-Path $OutDir $Etiqueta
    New-Item -ItemType Directory -Force -Path $destino | Out-Null

    $ok = 0; $fallos = 0; $total = $Files.Count; $i = 0
    foreach ($f in $Files) {
        $i++
        $fid = $f.fileID
        if ($fid.Length -lt 2) { continue }
        $sub = $fid.Substring(0,2)
        $src = Join-Path (Join-Path $BackupDir $sub) $fid

        $nombre = Split-Path $f.relativePath -Leaf
        if ([string]::IsNullOrWhiteSpace($nombre)) { $nombre = $fid }
        # prefijo del hash para que no se pisen nombres repetidos
        $nombreFinal = "$($fid.Substring(0,8))_$nombre"
        $dst = Join-Path $destino $nombreFinal

        Write-Progress -Activity "Extrayendo $Etiqueta" -Status "$i de $total" -PercentComplete (($i/$total)*100)

        if (Test-Path $src) {
            try {
                Copy-Item -LiteralPath $src -Destination $dst -Force
                $ok++
            } catch {
                $fallos++   # archivo corrupto o ilegible -> se salta
            }
        } else {
            $fallos++
        }
    }
    Write-Progress -Activity "Extrayendo $Etiqueta" -Completed
    Write-Host "  $Etiqueta -> recuperados: $ok / $total  (saltados: $fallos)" -ForegroundColor Green
}

# ----------------------------------------------------------------
#  Filtros SQL por categoria
# ----------------------------------------------------------------
$FILTROS = @{
    "Documentos" = "relativePath LIKE '%.pdf' OR relativePath LIKE '%.doc%' OR relativePath LIKE '%.ppt%' OR relativePath LIKE '%.xls%' OR relativePath LIKE '%.txt' OR relativePath LIKE '%.rtf' OR relativePath LIKE '%.pages' OR relativePath LIKE '%.numbers' OR relativePath LIKE '%.key' OR relativePath LIKE '%.csv'"
    "Fotos"      = "relativePath LIKE '%.jpg' OR relativePath LIKE '%.jpeg' OR relativePath LIKE '%.png' OR relativePath LIKE '%.heic' OR relativePath LIKE '%.gif' OR relativePath LIKE '%.bmp' OR relativePath LIKE '%.tiff' OR relativePath LIKE '%.webp'"
    "Videos"     = "relativePath LIKE '%.mov' OR relativePath LIKE '%.mp4' OR relativePath LIKE '%.m4v' OR relativePath LIKE '%.avi' OR relativePath LIKE '%.3gp' OR relativePath LIKE '%.hevc'"
    "Audio"      = "relativePath LIKE '%.m4a' OR relativePath LIKE '%.mp3' OR relativePath LIKE '%.wav' OR relativePath LIKE '%.aac' OR relativePath LIKE '%.caf'"
}

# ================================================================
#  INICIO
# ================================================================
Clear-Host
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "   RECUPERADOR DE BACKUP iOS" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# --- sqlite3.exe ---
$sqlite = Get-Sqlite
if (-not $sqlite) {
    Write-Host "AVISO: no encontre sqlite3.exe." -ForegroundColor Yellow
    Write-Host "Descargalo de https://www.sqlite.org/download.html (sqlite-tools para Windows),"
    Write-Host "descomprime y deja 'sqlite3.exe' en la MISMA carpeta que este script."
    Write-Host ""
    Pausa
    exit
}
Write-Host "sqlite3.exe encontrado: $sqlite" -ForegroundColor Green
Write-Host ""

# --- Ruta del backup ---
Write-Host "Arrastra aqui la carpeta del backup (la que tiene el nombre largo / UDID"
Write-Host "y contiene Manifest.db), o pega la ruta y pulsa ENTER:"
$BackupDir = (Read-Host "Ruta").Trim('"').Trim()

if (-not (Test-Path $BackupDir)) {
    Write-Host "Esa ruta no existe." -ForegroundColor Red; Pausa; exit
}

$DbPath = Join-Path $BackupDir "Manifest.db"
if (-not (Test-Path $DbPath)) {
    # quiza apuntaron a la carpeta padre: busca el UDID dentro
    $sub = Get-ChildItem -Path $BackupDir -Directory -ErrorAction SilentlyContinue |
           Where-Object { Test-Path (Join-Path $_.FullName "Manifest.db") } |
           Select-Object -First 1
    if ($sub) {
        $BackupDir = $sub.FullName
        $DbPath = Join-Path $BackupDir "Manifest.db"
        Write-Host "Backup detectado en: $BackupDir" -ForegroundColor Green
    } else {
        Write-Host "No encuentro Manifest.db en esa carpeta." -ForegroundColor Red; Pausa; exit
    }
}

# --- Comprobar cifrado ---
$manifestPlist = Join-Path $BackupDir "Manifest.plist"
if (Test-Path $manifestPlist) {
    $contenido = Get-Content $manifestPlist -Raw -ErrorAction SilentlyContinue
    if ($contenido -match "IsEncrypted") {
        # en plist binario/xml el valor true aparece como <true/> tras la clave
        $idx = $contenido.IndexOf("IsEncrypted")
        $trozo = $contenido.Substring($idx, [Math]::Min(60, $contenido.Length - $idx))
        if ($trozo -match "true") {
            Write-Host ""
            Write-Host "*** ATENCION: el backup parece CIFRADO. ***" -ForegroundColor Red
            Write-Host "Sin la contrasena no se pueden extraer los archivos." -ForegroundColor Red
            Write-Host "Si conoces la contrasena, conviene usar una herramienta que descifre"
            Write-Host "(iMazing / iBackup Viewer Pro), porque los datos estan cifrados en disco."
            Write-Host ""
            $seguir = Read-Host "Intentar de todos modos? (s/n)"
            if ($seguir -ne "s") { exit }
        }
    }
}

# --- Carpeta de salida ---
$OutDir = Join-Path ([Environment]::GetFolderPath("Desktop")) "Recuperado_Backup"
Write-Host ""
Write-Host "Los archivos se guardaran en: $OutDir" -ForegroundColor Cyan

# ================================================================
#  MENU
# ================================================================
function Menu {
    Write-Host ""
    Write-Host "================ QUE QUIERES SACAR? ================" -ForegroundColor Cyan
    Write-Host "  1) Documentos (Word, PDF, PPT, Excel, txt...)"
    Write-Host "  2) Fotos (jpg, png, heic...)"
    Write-Host "  3) Videos (mov, mp4...)"
    Write-Host "  4) Audio (m4a, mp3...)"
    Write-Host "  5) TODO (documentos + fotos + videos + audio)"
    Write-Host "  6) Contar cuantos hay de cada tipo (sin extraer)"
    Write-Host "  0) Salir"
    Write-Host "===================================================="
}

while ($true) {
    Menu
    $op = (Read-Host "Opcion").Trim()

    switch ($op) {
        "1" { $f = Get-Files-Sqlite $sqlite $DbPath $FILTROS["Documentos"]; Extraer $f $BackupDir $OutDir "Documentos"; Pausa }
        "2" { $f = Get-Files-Sqlite $sqlite $DbPath $FILTROS["Fotos"];      Extraer $f $BackupDir $OutDir "Fotos"; Pausa }
        "3" { $f = Get-Files-Sqlite $sqlite $DbPath $FILTROS["Videos"];     Extraer $f $BackupDir $OutDir "Videos"; Pausa }
        "4" { $f = Get-Files-Sqlite $sqlite $DbPath $FILTROS["Audio"];      Extraer $f $BackupDir $OutDir "Audio"; Pausa }
        "5" {
            foreach ($cat in @("Documentos","Fotos","Videos","Audio")) {
                $f = Get-Files-Sqlite $sqlite $DbPath $FILTROS[$cat]
                Extraer $f $BackupDir $OutDir $cat
            }
            Write-Host ""
            Write-Host "TODO LISTO. Revisa: $OutDir" -ForegroundColor Green
            Pausa
        }
        "6" {
            Write-Host ""
            foreach ($cat in @("Documentos","Fotos","Videos","Audio")) {
                $f = Get-Files-Sqlite $sqlite $DbPath $FILTROS[$cat]
                Write-Host ("  {0,-12}: {1}" -f $cat, $f.Count) -ForegroundColor Cyan
            }
            Pausa
        }
        "0" { Write-Host "Hasta luego."; break }
        default { Write-Host "Opcion no valida." -ForegroundColor Yellow }
    }
}
