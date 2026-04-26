# If you are AI AGENT, IGNORE THIS FILE.

$targetPath = "F:\OnGoinProject\House Plane Generator Projects\fpg-server\app\algorithms\types"
$outputFile = "$targetPath\directory_summary.md"

# Clear the output file before starting
Set-Content -Path $outputFile -Value ""

if (Test-Path $targetPath) {
    # Get only .py files (excluding the .md file itself)
    $pyFiles = Get-ChildItem -Path $targetPath -Filter *.py -File

    foreach ($file in $pyFiles) {
        # 1. Write the absolute path
        Add-Content -Path $outputFile -Value $file.FullName

        # 2. Write the file content
        Get-Content -Path $file.FullName | Add-Content -Path $outputFile

        # 3. Write two empty lines
        Add-Content -Path $outputFile -Value "`n"
        Add-Content -Path $outputFile -Value "`n"
    }
    Write-Host "Done! Results saved to $outputFile"
}
else {
    Write-Error "The directory path does not exist: $targetPath"
}