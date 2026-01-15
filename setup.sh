#!/bin/bash
# Swarm Control in SC2Bot - Linux/macOS Setup Script
# 자동 설치 스크립트

set -e  # 오류 발생 시 중단

echo "======================================================================"
echo "Swarm Control in SC2Bot - Linux/macOS Setup"
echo "======================================================================"
echo ""

# Python 버전 확인
echo "1. Python 버전 확인 중..."
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo "   ? Python이 설치되어 있지 않습니다."
    echo "   https://www.python.org/downloads/ 에서 Python 3.10+를 설치하세요."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1)
echo "   $PYTHON_VERSION"

# Python 3.10 이상 확인
VERSION_CHECK=$($PYTHON_CMD -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)" 2>&1)
if [ $? -ne 0 ]; then
    echo "   ??  Python 3.10 이상이 필요합니다."
    exit 1
fi

# 가상 환경 생성
echo ""
echo "2. 가상 환경 생성 중..."
if [ -d ".venv" ]; then
    echo "   가상 환경이 이미 존재합니다. 스킵합니다."
else
    $PYTHON_CMD -m venv .venv
    if [ $? -ne 0 ]; then
        echo "   ? 가상 환경 생성 실패"
        exit 1
    fi
    echo "   ? 가상 환경 생성 완료"
fi

# 가상 환경 활성화
echo ""
echo "3. 가상 환경 활성화 중..."
source .venv/bin/activate

# pip 업그레이드
echo ""
echo "4. pip 업그레이드 중..."
$PIP_CMD install --upgrade pip > /dev/null 2>&1 || echo "   ??  pip 업그레이드 실패 (계속 진행)"

# 의존성 설치
echo ""
echo "5. 의존성 설치 중..."
echo "   (이 작업은 몇 분이 걸릴 수 있습니다)"

if [ -f "wicked_zerg_challenger/requirements.txt" ]; then
    cd wicked_zerg_challenger
    $PIP_CMD install -r requirements.txt
    cd ..
    
    if [ $? -ne 0 ]; then
        echo "   ??  일부 의존성 설치 실패 (수동 설치 필요)"
    else
        echo "   ? 의존성 설치 완료"
    fi
else
    echo "   ? requirements.txt 파일을 찾을 수 없습니다."
    exit 1
fi

# 환경 변수 파일 설정
echo ""
echo "6. 환경 변수 파일 설정 중..."
if [ -f "wicked_zerg_challenger/api_keys/.env.example" ]; then
    if [ ! -f "wicked_zerg_challenger/.env" ]; then
        cp "wicked_zerg_challenger/api_keys/.env.example" "wicked_zerg_challenger/.env"
        echo "   ? .env 파일 생성 완료"
        echo "   ??  wicked_zerg_challenger/.env 파일을 편집하여 API 키를 설정하세요."
    else
        echo "   .env 파일이 이미 존재합니다."
    fi
else
    echo "   ??  .env.example 파일을 찾을 수 없습니다. (선택사항)"
fi

# 설치 확인
echo ""
echo "7. 설치 확인 중..."
ERRORS=()

if $PYTHON_CMD -c "import sc2" 2>/dev/null; then
    echo "   ? SC2 library"
else
    ERRORS+=("sc2")
fi

if $PYTHON_CMD -c "import torch" 2>/dev/null; then
    echo "   ? PyTorch"
else
    ERRORS+=("torch")
fi

# 최종 메시지
echo ""
echo "======================================================================"
if [ ${#ERRORS[@]} -eq 0 ]; then
    echo "? 설치 완료!"
    echo ""
    echo "다음 단계:"
    echo "  1. .env 파일 설정: wicked_zerg_challenger/.env"
    echo "  2. 게임 실행: python run.py"
    echo ""
    echo "자세한 내용은 SETUP.md를 참조하세요."
else
    echo "??  설치 완료 (일부 오류 발생)"
    echo ""
    echo "설치되지 않은 패키지:"
    for error in "${ERRORS[@]}"; do
        echo "  - $error"
    done
    echo ""
    echo "수동으로 설치하세요:"
    echo "  pip install ${ERRORS[*]}"
fi
echo "======================================================================"
