# API 키 보안 강화 스크립트
# API Key Security Hardening Script

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "API 키 보안 강화" -ForegroundColor Cyan
Write-Host "API Key Security Hardening" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ProjectRoot = Split-Path -Parent $PSScriptRoot

# ============================================================================
# 1. Google Cloud Console에서 키 제한 설정 가이드
# ============================================================================
Write-Host "[1/5] Google Cloud Console 키 제한 설정 가이드..." -ForegroundColor Green
Write-Host ""
Write-Host "Google Cloud Console에서 다음 제한을 설정하세요:" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. API 키 제한:" -ForegroundColor White
Write-Host "   - https://console.cloud.google.com/apis/credentials" -ForegroundColor Cyan
Write-Host "   - 키 선택 → 'API 제한' → '키 제한' 선택" -ForegroundColor White
Write-Host "   - 'Generative Language API'만 허용" -ForegroundColor White
Write-Host ""
Write-Host "2. 애플리케이션 제한:" -ForegroundColor White
Write-Host "   - '애플리케이션 제한' → 'IP 주소' 선택" -ForegroundColor White
Write-Host "   - 서버 IP 주소 추가 (배포 서버 IP)" -ForegroundColor White
Write-Host "   - 또는 'HTTP 리퍼러' 선택 (웹 애플리케이션인 경우)" -ForegroundColor White
Write-Host ""
Write-Host "3. 키 이름 변경:" -ForegroundColor White
Write-Host "   - 키 이름을 명확하게 설정 (예: 'SC2-Bot-Production')" -ForegroundColor White
Write-Host ""

# ============================================================================
# 2. 키 사용 모니터링 설정
# ============================================================================
Write-Host "[2/5] 키 사용 모니터링 설정..." -ForegroundColor Green

$monitoringScript = @"
# API 키 사용 모니터링 스크립트
import os
import json
from datetime import datetime
from pathlib import Path

def log_api_key_usage(api_name, success=True, error=None):
    '''API 키 사용 로그 기록'''
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / 'api_key_usage.json'
    
    # 기존 로그 읽기
    if log_file.exists():
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = json.load(f)
    else:
        logs = []
    
    # 새 로그 추가
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'api': api_name,
        'success': success,
        'error': str(error) if error else None
    }
    
    logs.append(log_entry)
    
    # 최근 1000개만 유지
    if len(logs) > 1000:
        logs = logs[-1000:]
    
    # 로그 저장
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)
"@

$monitoringFile = Join-Path $ProjectRoot "tools\api_key_monitoring.py"
$monitoringScript | Set-Content $monitoringFile
Write-Host "  ? API 키 모니터링 스크립트 생성: tools\api_key_monitoring.py" -ForegroundColor Green

Write-Host ""

# ============================================================================
# 3. 키 로테이션 스케줄 설정
# ============================================================================
Write-Host "[3/5] 키 로테이션 스케줄 설정..." -ForegroundColor Green

$rotationGuide = @"
# API 키 로테이션 가이드

## 권장 로테이션 주기
- 프로덕션 키: 90일마다
- 개발 키: 180일마다
- 테스트 키: 필요시

## 로테이션 체크리스트
1. 새 키 생성
2. 새 키 테스트
3. 모든 환경에 새 키 배포
4. 옛 키 비활성화 (삭제하지 않음, 30일 후 삭제)
5. 옛 키 사용 중지 확인
6. 옛 키 삭제
"@

$rotationFile = Join-Path $ProjectRoot "docs\API_KEY_ROTATION_SCHEDULE.md"
$rotationGuide | Set-Content $rotationFile
Write-Host "  ? 키 로테이션 가이드 생성: docs\API_KEY_ROTATION_SCHEDULE.md" -ForegroundColor Green

Write-Host ""

# ============================================================================
# 4. 키 접근 제어 설정
# ============================================================================
Write-Host "[4/5] 키 접근 제어 설정..." -ForegroundColor Green

$accessControlScript = @"
# API 키 접근 제어 설정
import os
from pathlib import Path
from typing import Optional

class ApiKeyAccessControl:
    '''API 키 접근 제어 클래스'''
    
    def __init__(self):
        self.allowed_ips = self._load_allowed_ips()
        self.allowed_domains = self._load_allowed_domains()
    
    def _load_allowed_ips(self) -> list:
        '''허용된 IP 주소 목록 로드'''
        config_file = Path('config') / 'allowed_ips.txt'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return []
    
    def _load_allowed_domains(self) -> list:
        '''허용된 도메인 목록 로드'''
        config_file = Path('config') / 'allowed_domains.txt'
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return []
    
    def is_allowed(self, ip: Optional[str] = None, domain: Optional[str] = None) -> bool:
        '''접근이 허용되었는지 확인'''
        if ip and self.allowed_ips:
            return ip in self.allowed_ips
        if domain and self.allowed_domains:
            return domain in self.allowed_domains
        return True  # 제한이 없으면 허용
"@

$accessControlFile = Join-Path $ProjectRoot "tools\api_key_access_control.py"
$accessControlScript | Set-Content $accessControlFile
Write-Host "  ? 키 접근 제어 스크립트 생성: tools\api_key_access_control.py" -ForegroundColor Green

# config 디렉토리 생성
$configDir = Join-Path $ProjectRoot "config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

# 허용된 IP 예제 파일
$allowedIpsFile = Join-Path $configDir "allowed_ips.txt.example"
@(
    "# 허용된 IP 주소 목록",
    "# 한 줄에 하나씩 IP 주소 입력",
    "# 예:",
    "# 192.168.1.100",
    "# 10.0.0.50"
) | Set-Content $allowedIpsFile

# 허용된 도메인 예제 파일
$allowedDomainsFile = Join-Path $configDir "allowed_domains.txt.example"
@(
    "# 허용된 도메인 목록",
    "# 한 줄에 하나씩 도메인 입력",
    "# 예:",
    "# example.com",
    "# *.example.com"
) | Set-Content $allowedDomainsFile

Write-Host "  ? 접근 제어 설정 파일 생성됨" -ForegroundColor Green

Write-Host ""

# ============================================================================
# 5. 키 사용량 제한 설정
# ============================================================================
Write-Host "[5/5] 키 사용량 제한 설정..." -ForegroundColor Green

$usageLimitScript = @"
# API 키 사용량 제한 설정
import time
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
import json

class ApiKeyUsageLimiter:
    '''API 키 사용량 제한 클래스'''
    
    def __init__(self, daily_limit: int = 1000, hourly_limit: int = 100):
        self.daily_limit = daily_limit
        self.hourly_limit = hourly_limit
        self.usage_file = Path('logs') / 'api_key_usage_limits.json'
        self._load_usage()
    
    def _load_usage(self):
        '''사용량 로드'''
        if self.usage_file.exists():
            with open(self.usage_file, 'r', encoding='utf-8') as f:
                self.usage = json.load(f)
        else:
            self.usage = defaultdict(int)
    
    def _save_usage(self):
        '''사용량 저장'''
        self.usage_file.parent.mkdir(exist_ok=True)
        with open(self.usage_file, 'w', encoding='utf-8') as f:
            json.dump(dict(self.usage), f, indent=2)
    
    def can_make_request(self) -> tuple[bool, str]:
        '''요청 가능한지 확인'''
        now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%Y-%m-%d-%H')
        
        daily_count = self.usage.get(date_key, 0)
        hourly_count = self.usage.get(hour_key, 0)
        
        if daily_count >= self.daily_limit:
            return False, f"일일 사용량 제한 초과 ({daily_count}/{self.daily_limit})"
        
        if hourly_count >= self.hourly_limit:
            return False, f"시간당 사용량 제한 초과 ({hourly_count}/{self.hourly_limit})"
        
        return True, ""
    
    def record_request(self):
        '''요청 기록'''
        now = datetime.now()
        date_key = now.strftime('%Y-%m-%d')
        hour_key = now.strftime('%Y-%m-%d-%H')
        
        self.usage[date_key] = self.usage.get(date_key, 0) + 1
        self.usage[hour_key] = self.usage.get(hour_key, 0) + 1
        
        # 오래된 데이터 정리 (30일 이상)
        cutoff_date = (now - timedelta(days=30)).strftime('%Y-%m-%d')
        self.usage = {k: v for k, v in self.usage.items() if k >= cutoff_date}
        
        self._save_usage()
"@

$usageLimitFile = Join-Path $ProjectRoot "tools\api_key_usage_limiter.py"
$usageLimitScript | Set-Content $usageLimitFile
Write-Host "  ? 키 사용량 제한 스크립트 생성: tools\api_key_usage_limiter.py" -ForegroundColor Green

Write-Host ""

# ============================================================================
# 요약
# ============================================================================
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "생성된 파일:" -ForegroundColor Cyan
Write-Host "  1. tools\api_key_monitoring.py - 키 사용 모니터링" -ForegroundColor White
Write-Host "  2. tools\api_key_access_control.py - 접근 제어" -ForegroundColor White
Write-Host "  3. tools\api_key_usage_limiter.py - 사용량 제한" -ForegroundColor White
Write-Host "  4. config\allowed_ips.txt.example - 허용 IP 예제" -ForegroundColor White
Write-Host "  5. config\allowed_domains.txt.example - 허용 도메인 예제" -ForegroundColor White
Write-Host "  6. docs\API_KEY_ROTATION_SCHEDULE.md - 로테이션 가이드" -ForegroundColor White
Write-Host ""

Write-Host "다음 단계:" -ForegroundColor Cyan
Write-Host "  1. Google Cloud Console에서 키 제한 설정" -ForegroundColor White
Write-Host "  2. config\allowed_ips.txt 생성 (필요한 경우)" -ForegroundColor White
Write-Host "  3. config\allowed_domains.txt 생성 (필요한 경우)" -ForegroundColor White
Write-Host "  4. 키 사용 모니터링 활성화" -ForegroundColor White
Write-Host "  5. 키 사용량 제한 설정" -ForegroundColor White
Write-Host ""
