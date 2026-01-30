Add-Type -AssemblyName System.Drawing

$assetsDir = Join-Path (Get-Item .).FullName "installer\assets"
if (-not (Test-Path $assetsDir)) { New-Item -ItemType Directory -Path $assetsDir }

function Create-Bitmap {
  param(
    [string]$Path,
    [int]$Width,
    [int]$Height,
    [System.Drawing.Color]$Color,
    [string]$Text
  )

  $bmp = New-Object System.Drawing.Bitmap($Width, $Height)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $brush = New-Object System.Drawing.SolidBrush($Color)
  $g.FillRectangle($brush, 0, 0, $Width, $Height)
    
  if ($Text) {
    $font = New-Object System.Drawing.Font("Arial", 12)
    $textBrush = [System.Drawing.Brushes]::White
    $sf = New-Object System.Drawing.StringFormat
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $g.DrawString($Text, $font, $textBrush, ($Width / 2), ($Height / 2), $sf)
  }

  $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Bmp)
  $g.Dispose()
  $bmp.Dispose()
  Write-Host "Created $Path"
}

# Create Wizard Images
Create-Bitmap -Path (Join-Path $assetsDir "wizard_small.bmp") -Width 55 -Height 58 -Color ([System.Drawing.Color]::DarkBlue) -Text "sisRUA"
Create-Bitmap -Path (Join-Path $assetsDir "wizard_large.bmp") -Width 164 -Height 314 -Color ([System.Drawing.Color]::DarkBlue) -Text "sisRUA Installer"

# Create a Dummy Icon (Just a small BMP renamed to ICO for placeholder - Inno might accept it or we use a hack)
# Proper ICO creation is complex in pure PS without external libs, so we will try to make a 32x32 BMP and save as ICO. 
# Note: Real ICO has a header. If Inno Setup rejects this, we might need a real .ico file.
# For now, let's try to create a proper icon using System.Drawing.Icon.FromHandle if possible, or just a BMP.
try {
  $bmpIcon = New-Object System.Drawing.Bitmap(32, 32)
  $gIcon = [System.Drawing.Graphics]::FromImage($bmpIcon)
  $gIcon.FillRectangle([System.Drawing.Brushes]::Blue, 0, 0, 32, 32)
  $gIcon.FillEllipse([System.Drawing.Brushes]::White, 4, 4, 24, 24)
    
  # Convert to Icon
  $hIcon = $bmpIcon.GetHicon()
  $icon = [System.Drawing.Icon]::FromHandle($hIcon)
    
  $iconPath = Join-Path $assetsDir "sisrua_installer.ico"
  $fs = New-Object System.IO.FileStream($iconPath, [System.IO.FileMode]::Create)
  $icon.Save($fs)
  $fs.Close()
    
  Write-Host "Created $iconPath"
}
catch {
  Write-Warning "Failed to generate ICO: $_"
}
