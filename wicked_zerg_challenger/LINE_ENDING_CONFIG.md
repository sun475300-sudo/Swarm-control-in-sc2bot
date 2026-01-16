# Line Ending 설정 완료

**작성일**: 2026-01-16

## 설정 개요

프로젝트의 line ending을 통일하여 Git diff에서 발생하는 CRLF/LF 경고를 방지했습니다.

## 설정 내용

### 1. `.gitattributes` 파일 생성

프로젝트 루트에 `.gitattributes` 파일을 생성하여 파일 타입별 line ending 규칙을 설정했습니다:

- **Python 파일** (`.py`): LF
- **Markdown 파일** (`.md`): LF
- **JSON/YAML/Config 파일**: LF
- **JavaScript/TypeScript/HTML/CSS**: LF
- **Windows 배치 파일** (`.bat`, `.cmd`, `.ps1`): CRLF
- **바이너리 파일**: binary로 처리

### 2. Git 설정 변경

```bash
git config --local core.autocrlf input
git config --local core.eol lf
```

- `core.autocrlf input`: 체크아웃 시 변환하지 않음 (Unix 스타일)
- `core.eol lf`: 기본 line ending을 LF로 설정

### 3. 파일 재정규화

```bash
git add --renormalize .
```

모든 파일의 line ending을 `.gitattributes` 규칙에 맞게 재정규화했습니다.

## 효과

1. **일관된 Line Ending**: 모든 텍스트 파일이 일관된 line ending을 사용
2. **Diff 경고 제거**: CRLF/LF 변경으로 인한 Git diff 경고 방지
3. **크로스 플랫폼 호환성**: Unix/Linux와 Windows 모두에서 정상 작동

## 참고 사항

- Windows 배치 파일 (`.bat`, `.cmd`, `.ps1`)은 CRLF를 사용합니다 (Windows 호환성)
- 나머지 모든 텍스트 파일은 LF를 사용합니다 (Unix/Linux 표준)
- Git은 자동으로 `.gitattributes` 규칙에 따라 line ending을 변환합니다

## 다음 단계

변경사항을 커밋하면 line ending 설정이 적용됩니다:

```bash
git add .gitattributes
git commit -m "Configure line endings"
```
