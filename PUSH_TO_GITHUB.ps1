# Push to GitHub Submission Script
# This script pushes the clean, sanitized build from 'submission_ready' to your new GitHub repository.

$repoUrl = Read-Host "Enter your new GitHub Repository URL (e.g., https://github.com/RohitBharadwaj-rvu/agentic-honeypot-submission.git)"

if (-not $repoUrl) {
    Write-Host "Error: Repository URL is required." -ForegroundColor Red
    exit
}

cd submission_ready
git remote remove origin 2>$null
git remote add origin $repoUrl
git branch -M main
git push -u origin main

Write-Host "Done! Your submission is now live at $repoUrl" -ForegroundColor Green
pause
