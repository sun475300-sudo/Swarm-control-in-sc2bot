#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Git 히스토리에서 API 키 제거 스크립트
    
.DESCRIPTION
    Git 히스토리에서 특정 API 키를 제거합니다.
    git filter-branch를 사용하여 모든 커밋에서 API 키를 제거합니다.
    
.PARAMETER ApiKey
    제거할 API 키
    
.EXAMPLE
    .\remove_api_key_from_git_history.ps1 -ApiKey 
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$ApiKey
)

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Yellow
Write-Host "Git 히스토리에서 API 키 제거" -ForegroundColor Yellow
Write-Host "=" * 70 -ForegroundColor Yellow
Write-Host ""

# 현재 브랜치 확인
$currentBranch = git rev-parse --abbrev-ref HEAD
Write-Host "현재 브랜치: $currentBranch" -ForegroundColor Cyan
Write-Host ""

# 경고 메시지
Write-Host "⚠️  경고: 이 작업은 Git 히스토리를 다시 작성합니다!" -ForegroundColor Red
Write-Host "⚠️  이미 푸시된 커밋을 수정하면 force push가 필요합니다!" -ForegroundColor Red
Write-Host "⚠️  다른 사람과 공유하는 저장소라면 문제가 될 수 있습니다!" -ForegroundColor Red
Write-Host ""

$confirm = Read-Host "계속하시겠습니까? (yes/no)"
if ($confirm -ne "yes") {
    Write-Host "작업이 취소되었습니다." -ForegroundColor Yellow
    exit 0
}

Write-Host ""
Write-Host "API 키가 포함된 커밋 검색 중..." -ForegroundColor Cyan

# API 키가 포함된 커밋 찾기
$commits = git log --all --source --full-history -S $ApiKey --oneline
if ($commits) {
    Write-Host "다음 커밋에서 API 키가 발견되었습니다:" -ForegroundColor Yellow
    $commits | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
} else {
    Write-Host "API 키가 포함된 커밋을 찾을 수 없습니다." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Git 히스토리에서 API 키 제거 중..." -ForegroundColor Cyan

# 백업 브랜치 생성
$backupBranch = "backup-before-api-key-removal-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
Write-Host "백업 브랜치 생성: $backupBranch" -ForegroundColor Cyan
git branch $backupBranch

# git filter-branch를 사용하여 API 키 제거
# 모든 파일에서 API 키를 빈 문자열로 교체
$script = @"
#!/bin/sh
git ls-files -z | xargs -0 sed -i 's/$ApiKey/[API_KEY_REMOVED]/g'
"@

# 임시 스크립트 파일 생성
$tempScript = Join-Path $env:TEMP "git-filter-api-key-$(Get-Date -Format 'yyyyMMdd-HHmmss').sh"
$script | Out-File -FilePath $tempScript -Encoding UTF8

try {
    # git filter-branch 실행
    Write-Host "git filter-branch 실행 중..." -ForegroundColor Cyan
    Write-Host "이 작업은 시간이 걸릴 수 있습니다..." -ForegroundColor Yellow
    
    # Windows에서 git filter-branch를 실행하기 위해 WSL 또는 Git Bash 필요
    # PowerShell에서는 직접 실행이 어려우므로, 사용자에게 수동 실행 가이드 제공
    Write-Host ""
    Write-Host "=" * 70 -ForegroundColor Yellow
    Write-Host "수동 실행 가이드" -ForegroundColor Yellow
    Write-Host "=" * 70 -ForegroundColor Yellow
    Write-Host ""
    Write-Host "다음 명령어를 Git Bash 또는 WSL에서 실행하세요:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  git filter-branch --force --index-filter \`" -ForegroundColor White
    Write-Host "    'git ls-files -z | xargs -0 sed -i \"s/$ApiKey/[API_KEY_REMOVED]/g\"' \`" -ForegroundColor White
    Write-Host "    --prune-empty --tag-name-filter cat -- --all" -ForegroundColor White
    Write-Host ""
    Write-Host "또는 BFG Repo-Cleaner 사용 (더 빠름):" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  1. BFG 다운로드: https://rtyley.github.io/bfg-repo-cleaner/" -ForegroundColor White
    Write-Host "  2. 실행: java -jar bfg.jar --replace-text passwords.txt" -ForegroundColor White
    Write-Host "     (passwords.txt에 $ApiKey 포함)" -ForegroundColor White
    Write-Host "  3. 정리: git reflog expire --expire=now --all && git gc --prune=now --aggressive" -ForegroundColor White
    Write-Host ""
    Write-Host "작업 완료 후:" -ForegroundColor Cyan
    Write-Host "  git push --force --all" -ForegroundColor White
    Write-Host "  git push --force --tags" -ForegroundColor White
    Write-Host ""
    
} finally {
    # 임시 파일 정리
    if (Test-Path $tempScript) {
        Remove-Item $tempScript -Force
    }
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Yellow
Write-Host "작업 완료" -ForegroundColor Yellow
Write-Host "=" * 70 -ForegroundColor Yellow
Write-Host ""
Write-Host "백업 브랜치: $backupBranch" -ForegroundColor Green
Write-Host "문제가 발생하면 다음 명령어로 복구할 수 있습니다:" -ForegroundColor Cyan
Write-Host "  git reset --hard $backupBranch" -ForegroundColor White
Write-Host ""
