Add-Type -AssemblyName System.Drawing
foreach ($file in Get-ChildItem 'img\lecturecard_*.jpg') {
    $img = [System.Drawing.Image]::FromFile($file.FullName)
    Write-Host "$($file.Name): $($img.Width)x$($img.Height)"
    $img.Dispose()
}
