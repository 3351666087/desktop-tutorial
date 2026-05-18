$ErrorActionPreference = "Stop"

$driverDir = Join-Path $env:TEMP "cp210x_universal_windows_driver"
$zip = Join-Path $env:TEMP "CP210x_Universal_Windows_Driver.zip"
$inf = Join-Path $driverDir "silabser.inf"

if (!(Test-Path $inf)) {
  New-Item -ItemType Directory -Force -Path $driverDir | Out-Null
  Invoke-WebRequest -Uri "https://www.silabs.com/documents/public/software/CP210x_Universal_Windows_Driver.zip" -OutFile $zip
  Expand-Archive -Path $zip -DestinationPath $driverDir -Force
}

Write-Host "Installing Silicon Labs CP210x driver from:"
Write-Host $driverDir
pnputil /add-driver "$driverDir\*.inf" /subdirs /install

Write-Host ""
Write-Host "Driver install command finished. Unplug/replug the ESP32 if COM port does not appear immediately."
Start-Sleep -Seconds 3
