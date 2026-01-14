# ? Android models 폴더 제외 규칙 수정 완료

**작성일**: 2026-01-14  
**문제**: `app/src/main/java/com/wickedzerg/mobilegcs/models/` 경로가 `.gitignore`에 의해 제외됨  
**해결**: `.gitignore` 규칙 수정하여 Android 소스 코드 models 폴더는 포함되도록 변경

---

## ? 문제 원인

`wicked_zerg_challenger/.gitignore` 파일의 56번째 줄에 `models/` 규칙이 있어서, AI/ML 모델 파일을 제외하기 위한 목적이었지만 Android 앱의 소스 코드 폴더(`app/src/main/java/com/wickedzerg/mobilegcs/models/`)도 함께 제외되었습니다.

---

## ? 해결 방법

### 1. 상위 `.gitignore` 수정

`wicked_zerg_challenger/.gitignore` 파일에서 Android 소스 코드 경로를 예외 처리:

```gitignore
# Models & Checkpoints (AI/ML model files only)
# ----------------------------------------------
# Exclude AI model files, but NOT Android source code models folder
*.pt
*.pth
*.h5
*.ckpt
*.pb
*.onnx
*.tflite
# Exclude model directories (but allow Android source code)
# IMPORTANT: Exclude models/ directories EXCEPT Android source code
# Android source code models folder must be explicitly allowed BEFORE models/ rule
!monitoring/mobile_app_android/app/src/main/java/com/wickedzerg/mobilegcs/models/
!monitoring/mobile_app_android/app/src/main/java/com/wickedzerg/mobilegcs/models/**
!monitoring/mobile_app_android/app/src/main/kotlin/com/wickedzerg/mobilegcs/models/
!monitoring/mobile_app_android/app/src/main/kotlin/com/wickedzerg/mobilegcs/models/**
# Now exclude other models/ directories
models/
```

### 2. Android 프로젝트 `.gitignore` 수정

`wicked_zerg_challenger/monitoring/mobile_app_android/.gitignore` 파일에도 예외 규칙 추가:

```gitignore
# Allow source code models folder (override parent .gitignore)
# Note: This explicitly includes the models folder for Android source code
!app/src/main/java/com/wickedzerg/mobilegcs/models/
!app/src/main/java/com/wickedzerg/mobilegcs/models/**
!app/src/main/kotlin/com/wickedzerg/mobilegcs/models/
!app/src/main/kotlin/com/wickedzerg/mobilegcs/models/**
```

---

## ? 확인 방법

```bash
# models 폴더가 제외되는지 확인
git check-ignore -v wicked_zerg_challenger/monitoring/mobile_app_android/app/src/main/java/com/wickedzerg/mobilegcs/models/

# 출력이 없으면 정상 (제외되지 않음)
# 출력이 있으면 여전히 제외되고 있음
```

---

## ? 참고사항

- Git의 `.gitignore` 규칙은 상위 디렉토리에서 하위 디렉토리로 적용됩니다
- 예외 규칙(`!`)은 제외 규칙(`models/`) **이전**에 위치해야 합니다
- Android 소스 코드의 models 폴더는 Kotlin/Java 파일을 포함하므로 Git에 포함되어야 합니다
- AI/ML 모델 파일(`*.pt`, `*.pth` 등)은 계속 제외됩니다

---

**마지막 업데이트**: 2026-01-14
