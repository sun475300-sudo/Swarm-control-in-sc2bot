# 마크다운 파일 경고 설명

**작성 일시**: 2026-01-16

---

## ? 경고 종류 및 원인

마크다운 파일에서 나타나는 경고는 **기능적 오류가 아닌 스타일 가이드 위반**입니다. 
이것들은 마크다운 린터(markdownlint)가 체크하는 규칙입니다.

### 1. MD022 - Headings should be surrounded by blank lines
**의미**: 헤딩 앞뒤에 빈 줄이 필요합니다.

**예시 (경고 발생)**:
```markdown
## 제목
내용
```

**수정 방법**:
```markdown
## 제목

내용
```

---

### 2. MD032 - Lists should be surrounded by blank lines
**의미**: 리스트 앞뒤에 빈 줄이 필요합니다.

**예시 (경고 발생)**:
```markdown
## 제목
- 항목 1
- 항목 2
내용
```

**수정 방법**:
```markdown
## 제목

- 항목 1
- 항목 2

내용
```

---

### 3. MD031 - Fenced code blocks should be surrounded by blank lines
**의미**: 코드 블록(```) 앞뒤에 빈 줄이 필요합니다.

**예시 (경고 발생)**:
```markdown
설명
```python
code
```
내용
```

**수정 방법**:
```markdown
설명

```python
code
```

내용
```

---

### 4. MD040 - Fenced code blocks should have a language specified
**의미**: 코드 블록에 언어를 지정해야 합니다.

**예시 (경고 발생)**:
```markdown
```
code
```
```

**수정 방법**:
```markdown
```python
code
```
```

---

## ? 현재 발견된 경고

다음 파일들에서 경고가 발견되었습니다:

1. **PROJECT_STRUCTURE_IMPROVEMENT_PLAN.md** - 26개 경고
2. **TRAINING_OPTIMIZATION_GUIDE.md** - 24개 경고
3. **PRE_COMMIT_CHECKLIST.md** - 30개 경고
4. **FINAL_PRE_COMMIT_SUMMARY.md** - 28개 경고

---

## ? 해결 방법

### 옵션 1: 경고 무시 (권장)
이 경고들은 **기능에 영향을 주지 않습니다**. 
마크다운 파일은 정상적으로 렌더링됩니다.

### 옵션 2: 자동 수정
마크다운 린터 도구를 사용하여 자동으로 수정할 수 있습니다:

```bash
# markdownlint-cli 설치
npm install -g markdownlint-cli

# 자동 수정
markdownlint --fix *.md
```

### 옵션 3: 수동 수정
각 경고 위치에 빈 줄을 추가하거나 코드 블록에 언어를 지정합니다.

---

## ? 요약

- **경고는 기능적 오류가 아닙니다**
- **마크다운 파일은 정상적으로 작동합니다**
- **수정은 선택사항입니다** (가독성 향상을 위해 권장)

---

**작성자**: AI Assistant  
**최종 업데이트**: 2026-01-16
