$Server = "60.10.230.156"
$Port = "2950"
$User = "root"
$Key = ".\KeyPair-6e51.pem"
$RemoteBase = "/root/test_2"

if (!(Test-Path $Key)) {
    Write-Host "Warning: $Key not found." -ForegroundColor Yellow
}

$FilesToUpload = @(
    @("agent.py", "$RemoteBase/agent.py"),
    @("system_prompt.txt", "$RemoteBase/system_prompt.txt"),
    @("templates\index_new.html", "$RemoteBase/templates/index_new.html")
)

foreach ($Pair in $FilesToUpload) {
    $LocalFile = $Pair[0]
    $RemotePath = $Pair[1]
    
    if (Test-Path $LocalFile) {
        Write-Host "Uploading $LocalFile to $RemotePath..." -ForegroundColor Cyan
        # Using StrictHostKeyChecking=no to avoid prompts
        scp -o "StrictHostKeyChecking=no" -P $Port -i $Key $LocalFile "${User}@${Server}:${RemotePath}"
        if ($LASTEXITCODE -eq 0) {
             Write-Host "Success: $LocalFile uploaded." -ForegroundColor Green
        } else {
             Write-Host "Error: Failed to upload $LocalFile. Exit code: $LASTEXITCODE" -ForegroundColor Red
        }
    } else {
        Write-Host "Error: Local file $LocalFile not found." -ForegroundColor Red
    }
}

Write-Host "Attempting to restart flask-app.service..." -ForegroundColor Cyan
ssh -o "StrictHostKeyChecking=no" -p $Port -i $Key ${User}@${Server} "systemctl restart flask-app.service"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Service restarted successfully." -ForegroundColor Green
} else {
    Write-Host "Warning: Failed to restart flask-app.service (Exit code: $LASTEXITCODE)." -ForegroundColor Yellow
    Write-Host "Trying to check if python process is running..."
    ssh -o "StrictHostKeyChecking=no" -p $Port -i $Key ${User}@${Server} "ps aux | grep app.py"
}
