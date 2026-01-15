#!/bin/bash
# Git 커밋 전 민감한 정보 검사 스크립트
# 사용법: ./pre_commit_security_check.sh
# 
# 개선 사항:
# - 하드코딩된 실제 API 키 제거 (패턴만 사용)
# - 강화된 오류 처리 및 예외 관리
# - 파일 읽기 실패 시 안전한 처리
# - 더 명확한 오류 메시지

# 오류 발생 시 스크립트를 종료하지 않고 계속 진행 (일부 파일 실패 시에도 검사 계속)
set +e

# 오류 카운터
error_count=0

echo "======================================================================"
echo "🔒 Git 커밋 전 민감한 정보 검사"
echo "======================================================================"
echo ""

# 검사할 패턴들 (하드코딩된 실제 키는 제외, 패턴만 사용)
declare -a patterns=(
    "AIzaSy[A-Za-z0-9_-]{35}"  # Google API Key
    "sk-[A-Za-z0-9]{32,}"      # OpenAI API Key
    "xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[A-Za-z0-9]{24,32}"  # Slack Token
    "[0-9a-f]\{32\}"           # 일반적인 32자리 해시
    "[0-9a-f]\{40\}"           # 40자리 해시
    # 주의: 구체적인 API 키 예시는 스크립트 자체 검사 시 오탐지를 방지하기 위해 제외됨
)

# 검사할 파일 확장자
declare -a extensions=("*.py" "*.kt" "*.java" "*.js" "*.ts" "*.md" "*.txt" "*.json" "*.yaml" "*.yml" "*.sh" "*.ps1" "*.bat")

# 검사 결과
found_issues=0
checked_files=0

echo "📁 스테이징된 파일 검사 중..."
echo ""

# Git 스테이징된 파일 가져오기 (개선된 오류 처리)
staged_files=""
if ! staged_files=$(git diff --cached --name-only --diff-filter=ACM 2>&1); then
    # Git 명령 실패 시 오류 메시지 출력
    if echo "$staged_files" | grep -q "not a git repository\|fatal:"; then
        echo "⚠️  Git 저장소가 아니거나 스테이징된 파일이 없습니다." >&2
    else
        echo "⚠️  Git 명령 실행 중 오류 (무시하고 계속):" >&2
        echo "   $staged_files" >&2
        error_count=$((error_count + 1))
    fi
    staged_files=""
fi

if [ -z "$staged_files" ]; then
    echo "⚠️  Git 저장소가 아니거나 스테이징된 파일이 없습니다."
    echo "   모든 파일을 검사합니다..."
    echo ""
    
    # 모든 파일 검사
    for ext in "${extensions[@]}"; do
        while IFS= read -r -d '' file; do
            # .git, node_modules, venv 등 제외
            if [[ "$file" == *".git"* ]] || [[ "$file" == *"node_modules"* ]] || \
               [[ "$file" == *"venv"* ]] || [[ "$file" == *"__pycache__"* ]] || \
               [[ "$file" == *".gradle"* ]] || [[ "$file" == *"build"* ]]; then
                continue
            fi
            
            checked_files=$((checked_files + 1))
            
            # 파일 읽기 가능 여부 확인
            if [ ! -r "$file" ]; then
                echo "⚠️  파일 읽기 권한 없음 (무시): $file" >&2
                error_count=$((error_count + 1))
                continue
            fi
            
            for pattern in "${patterns[@]}"; do
                # 패턴 매칭 시도 (오류 처리)
                if grep -qE "$pattern" "$file" 2>/dev/null; then
                    line=$(grep -nE "$pattern" "$file" 2>/dev/null | head -1 | cut -d: -f1)
                    if [ -n "$line" ]; then
                        echo "🚨 민감한 정보 발견!"
                        echo "  파일: $file"
                        echo "  패턴: $pattern"
                        echo "  라인: $line"
                        echo ""
                        found_issues=$((found_issues + 1))
                    fi
                elif [ $? -ne 0 ] && [ $? -ne 1 ]; then
                    # grep 오류 (0=발견, 1=미발견, 2=오류)
                    echo "⚠️  패턴 매칭 오류 (무시): $pattern in $file" >&2
                    error_count=$((error_count + 1))
                fi
            done
        done < <(find . -type f -name "$ext" -print0 2>/dev/null)
    done
else
    # 스테이징된 파일만 검사
    while IFS= read -r file_path; do
        if [ -f "$file_path" ]; then
            checked_files=$((checked_files + 1))
            
            # 확장자 확인
            should_check=false
            for ext in "${extensions[@]}"; do
                if [[ "$file_path" == *"${ext#\*}" ]]; then
                    should_check=true
                    break
                fi
            done
            
            if [ "$should_check" = true ]; then
                # 파일 읽기 가능 여부 확인
                if [ ! -r "$file_path" ]; then
                    echo "⚠️  파일 읽기 권한 없음 (무시): $file_path" >&2
                    error_count=$((error_count + 1))
                    continue
                fi
                
                for pattern in "${patterns[@]}"; do
                    # 패턴 매칭 시도 (오류 처리)
                    if grep -qE "$pattern" "$file_path" 2>/dev/null; then
                        line=$(grep -nE "$pattern" "$file_path" 2>/dev/null | head -1 | cut -d: -f1)
                        if [ -n "$line" ]; then
                            preview=$(grep -E "$pattern" "$file_path" 2>/dev/null | head -1 | sed "s/$pattern/[REDACTED]/g" 2>/dev/null | cut -c1-80)
                            
                            echo "🚨 민감한 정보 발견!"
                            echo "  파일: $file_path"
                            echo "  패턴: $pattern"
                            echo "  라인: $line"
                            if [ -n "$preview" ]; then
                                echo "  미리보기: $preview"
                            fi
                            echo ""
                            found_issues=$((found_issues + 1))
                        fi
                    elif [ $? -ne 0 ] && [ $? -ne 1 ]; then
                        # grep 오류 (0=발견, 1=미발견, 2=오류)
                        echo "⚠️  패턴 매칭 오류 (무시): $pattern in $file_path" >&2
                        error_count=$((error_count + 1))
                    fi
                done
            fi
        fi
    done <<< "$staged_files"
fi

echo ""
echo "======================================================================"
echo "검사 결과"
echo "======================================================================"
echo ""
echo "검사한 파일 수: $checked_files"
if [ $error_count -gt 0 ]; then
    echo "처리 중 오류 발생 수: $error_count (무시됨)"
fi
echo ""

if [ $found_issues -gt 0 ]; then
    echo "🚨 민감한 정보가 발견되었습니다!"
    echo ""
    echo "======================================================================"
    echo "❌ 커밋이 차단되었습니다!"
    echo "======================================================================"
    echo ""
    echo "조치 사항:"
    echo "  1. 위 파일들에서 민감한 정보를 제거하세요"
    echo "  2. 플레이스홀더로 대체하세요 (예: [YOUR_API_KEY])"
    echo "  3. 환경 변수나 설정 파일을 사용하세요"
    echo "  4. 다시 검사 후 커밋하세요"
    echo ""
    
    exit 1
else
    echo "✅ 민감한 정보가 발견되지 않았습니다."
    echo ""
    echo "안전하게 커밋할 수 있습니다."
    echo ""
    
    exit 0
fi
