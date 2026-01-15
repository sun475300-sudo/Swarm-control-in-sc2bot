#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
<#
.SYNOPSIS
    Git 커밋 전 민감한 정보 검사 스크립트
    
.DESCRIPTION
    커밋 전에 민감한 정보(API 키, 비밀번호 등)가 포함되지 않았는지 검사합니다.
    이 스크립트는 Git pre-commit hook로 사용하거나 수동으로 실행할 수 있습니다.
    
.EXAMPLE
    .\pre_commit_security_check.ps1
    
.NOTES
    이 스크립트는 커밋 전에 자동으로 실행되어 민감한 정보를 차단합니다.
#>

$ErrorActionPreference = "Stop"

Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "🔒 Git 커밋 전 민감한 정보 검사" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""

# 검사할 패턴들
$sensitivePatterns = @(
    # API 키 패턴
    "AIzaSy[A-Za-z0-9_-]{35}",  # Google API Key
    "sk-[A-Za-z0-9]{32,}",      # OpenAI API Key
    "xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,32}",  # Slack Token
    "[0-9a-f]{32}",             # 일반적인 32자리 해시 (API 키 가능성)
    "[0-9a-f]{40}",             # 40자리 해시 (GitHub token 등)
    
    # 비밀번호 패턴 (간단한 패턴)
    "password\s*[:=]\s*['\""]?[^'\""\s]{8,}",  # password: "value"
    "passwd\s*[:=]\s*['\""]?[^'\""\s]{8,}",    # passwd: "value"
    "secret\s*[:=]\s*['\""]?[^'\""\s]{8,}",    # secret: "value"
    "token\s*[:=]\s*['\""]?[^'\""\s]{20,}",     # token: "value"
    
    # 실제 API 키 (이미 제거된 것으로 알려진 키)
    "***REDACTED_GEMINI_KEY***",
)

# 검사할 파일 확장자
$fileExtensions = @("*.py", "*.kt", "*.java", "*.js", "*.ts", "*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.sh", "*.ps1", "*.bat")

# 검사 결과
$foundIssues = @()
$checkedFiles = 0

Write-Host "📁 스테이징된 파일 검사 중..." -ForegroundColor Yellow
Write-Host ""

# Git 스테이징된 파일 가져오기
try {
    $stagedFiles = git diff --cached --name-only --diff-filter=ACM
} catch {
    Write-Host "⚠️  Git 저장소가 아니거나 스테이징된 파일이 없습니다." -ForegroundColor Yellow
    Write-Host "   모든 파일을 검사합니다..." -ForegroundColor Yellow
    $stagedFiles = @()
}

# 스테이징된 파일이 없으면 모든 파일 검사
if (-not $stagedFiles) {
    Write-Host "📁 모든 파일 검사 중..." -ForegroundColor Yellow
    Write-Host ""
    
    foreach ($ext in $fileExtensions) {
        $files = Get-ChildItem -Path . -Filter $ext -Recurse -ErrorAction SilentlyContinue | 
                 Where-Object { $_.FullName -notmatch '\.git|node_modules|venv|__pycache__|\.gradle|build' }
        
        foreach ($file in $files) {
            $checkedFiles++
            $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
            
            if ($content) {
                foreach ($pattern in $sensitivePatterns) {
                    if ($content -match $pattern) {
                        $lineNumber = ($content -split "`n").IndexOf(($content -split "`n" | Where-Object { $_ -match $pattern } | Select-Object -First 1)) + 1
                        $foundIssues += [PSCustomObject]@{
                            File = $file.FullName
                            Pattern = $pattern
                            Line = $lineNumber
                        }
                    }
                }
            }
        }
    }
} else {
    # 스테이징된 파일만 검사
    foreach ($filePath in $stagedFiles) {
        if (Test-Path $filePath) {
            $file = Get-Item $filePath
            $checkedFiles++
            
            # 특정 확장자만 검사
            $shouldCheck = $false
            foreach ($ext in $fileExtensions) {
                if ($file.Name -like $ext) {
                    $shouldCheck = $true
                    break
                }
            }
            
            if ($shouldCheck) {
                $content = Get-Content $file.FullName -Raw -ErrorAction SilentlyContinue
                
                if ($content) {
                    foreach ($pattern in $sensitivePatterns) {
                        if ($content -match $pattern) {
                            $lines = $content -split "`n"
                            $matchingLine = $lines | Where-Object { $_ -match $pattern } | Select-Object -First 1
                            $lineNumber = [Array]::IndexOf($lines, $matchingLine) + 1
                            
                            $foundIssues += [PSCustomObject]@{
                                File = $file.FullName
                                Pattern = $pattern
                                Line = $lineNumber
                                Preview = ($matchingLine -replace $pattern, "[REDACTED]").Substring(0, [Math]::Min(80, ($matchingLine -replace $pattern, "[REDACTED]").Length))
                            }
                        }
                    }
                }
            }
        }
    }
}

Write-Host ""
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host "검사 결과" -ForegroundColor Cyan
Write-Host "=" * 70 -ForegroundColor Cyan
Write-Host ""
Write-Host "검사한 파일 수: $checkedFiles" -ForegroundColor White
Write-Host ""

if ($foundIssues.Count -gt 0) {
    Write-Host "🚨 민감한 정보가 발견되었습니다!" -ForegroundColor Red
    Write-Host ""
    
    foreach ($issue in $foundIssues) {
        Write-Host "  파일: $($issue.File)" -ForegroundColor Yellow
        Write-Host "  패턴: $($issue.Pattern)" -ForegroundColor Yellow
        Write-Host "  라인: $($issue.Line)" -ForegroundColor Yellow
        if ($issue.Preview) {
            Write-Host "  미리보기: $($issue.Preview)" -ForegroundColor Gray
        }
        Write-Host ""
    }
    
    Write-Host "=" * 70 -ForegroundColor Red
    Write-Host "❌ 커밋이 차단되었습니다!" -ForegroundColor Red
    Write-Host "=" * 70 -ForegroundColor Red
    Write-Host ""
    Write-Host "조치 사항:" -ForegroundColor Yellow
    Write-Host "  1. 위 파일들에서 민감한 정보를 제거하세요" -ForegroundColor White
    Write-Host "  2. 플레이스홀더로 대체하세요 (예: [YOUR_API_KEY])" -ForegroundColor White
    Write-Host "  3. 환경 변수나 설정 파일을 사용하세요" -ForegroundColor White
    Write-Host "  4. 다시 검사 후 커밋하세요" -ForegroundColor White
    Write-Host ""
    
    exit 1
} else {
    Write-Host "✅ 민감한 정보가 발견되지 않았습니다." -ForegroundColor Green
    Write-Host ""
    Write-Host "안전하게 커밋할 수 있습니다." -ForegroundColor Green
    Write-Host ""
    
    exit 0
}
