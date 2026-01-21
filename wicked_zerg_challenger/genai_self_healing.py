# -*- coding: utf-8 -*-
"""
Gen-AI Self-Healing System - �ڰ� ���� �ý��� ����ȭ

CRITICAL IMPROVEMENT:
1. ���� �ڵ� ���� �ܰ� ��ȭ (ast.parse() ���� �˻�)
2. �н� ������ ���� (�ڿ� ȿ��, ���� ȿ�� ����)
3. �ڵ� ����ȭ ���� ���� (�ߺ� ����, ��ȿ������ ��������� ����)
"""

import ast
import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("[WARNING] google.generativeai not available")


class GenAISelfHealing:
    """
    Generative AI ��� �ڰ� ���� �ý���
    
    Gemini API�� ����Ͽ� ���� �м�, ��ġ ����, �ڵ� ������ �����մϴ�.
    """
    
    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        """
        Args:
            api_key: Gemini API Ű (������ ȯ�溯������ ������)
            model_name: ����� �� �̸�
        """
        self.model_name = model_name
        self.model = None
        
        if GENAI_AVAILABLE:
            try:
                if api_key is None:
                    # ȯ�溯�� �Ǵ� ���Ͽ��� API Ű ��������
                    api_key = os.environ.get("GEMINI_API_KEY")
                    if api_key is None:
                        api_key_path = Path(__file__).parent / "api_keys" / "GEMINI_API_KEY.txt"
                        if api_key_path.exists():
                            api_key = api_key_path.read_text().strip()
                
                if api_key:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel(model_name)
            except Exception as e:
                print(f"[WARNING] Failed to initialize Gemini: {e}")
    
    def analyze_error(self, error: Exception, context: Dict, source_code: Optional[str] = None) -> Dict:
        """
        ���� �м� �� ��ġ ����
        
        CRITICAL IMPROVEMENT: �ڵ� ���� �ܰ� ��ȭ
        
        Args:
            error: �߻��� ����
            context: ���� ���ؽ�Ʈ (���ϸ�, ���� ��ȣ ��)
            source_code: �ҽ� �ڵ� (���û���)
            
        Returns:
            �м� ��� ��ųʸ�
        """
        if not self.model:
            return {
                "success": False,
                "error": "Gemini model not available",
                "patch_code": None
            }
        
        try:
            # ������Ʈ ����
            prompt = self._generate_error_analysis_prompt(error, context, source_code)
            
            # Gemini API ȣ��
            response = self.model.generate_content(prompt)
            
            # ���� �Ľ�
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # ��ġ �ڵ� ����
            patch_code = self._extract_patch_code(response_text)
            
            # ��ġ �ڵ� ����
            validation_result = self._validate_patch_code(patch_code)
            
            return {
                "success": True,
                "analysis": response_text,
                "patch_code": patch_code,
                "validation": validation_result
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "patch_code": None
            }
    
    def _generate_error_analysis_prompt(self, error: Exception, context: Dict, source_code: Optional[str]) -> str:
        """���� �м� ������Ʈ ����"""
        prompt = f"""
���� �м� �� ��ġ ������ ��û�մϴ�.

���� ����:
- ���� Ÿ��: {type(error).__name__}
- ���� �޽���: {str(error)}
- ����: {context.get('file', 'Unknown')}
- ����: {context.get('line', 'Unknown')}

"""
        if source_code:
            prompt += f"""
���� �ҽ� �ڵ�:
```python
{source_code}
```

"""
        prompt += """
��û ����:
1. ������ ���� �м�
2. ������ �ڵ� ���� (Python �ڵ常, �ּ� ����)
3. ���� ���� ����

���� ����:
```python
# ������ �ڵ�
...
```

����:
...
"""
<<<<<<< Current (Your changes)
        return prompt
    
    def _extract_patch_code(self, response_text: str) -> str:
        """���信�� ��ġ �ڵ� ����"""
        # �ڵ� ���� ã��
        if "```python" in response_text:
            start = response_text.find("```python") + len("```python")
            end = response_text.find("```", start)
            if end > start:
                return response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + len("```")
            end = response_text.find("```", start)
            if end > start:
                return response_text[start:end].strip()
        
        return ""
    
    def _validate_patch_code(self, patch_code: str) -> Dict[str, Any]:
        """
        ��ġ �ڵ� ����
        
        CRITICAL IMPROVEMENT: ast.parse()�� ���� ���� ���� �˻�
        
        Args:
            patch_code: ������ �ڵ�
            
        Returns:
            ���� ��� ��ųʸ�
        """
        result = {
            "syntax_valid": False,
            "errors": [],
            "warnings": [],
            "nested_loops": 0,
            "inefficient_comprehensions": []
        }
        
        if not patch_code:
            result["errors"].append("Empty patch code")
            return result
        
        try:
            # 1. ���� �˻�
            try:
                tree = ast.parse(patch_code)
                result["syntax_valid"] = True
            except SyntaxError as e:
                result["errors"].append(f"Syntax error: {e}")
                return result
            
            # 2. �ߺ� ���� ����
            result["nested_loops"] = self._detect_nested_loops(tree)
            if result["nested_loops"] > 2:
                result["warnings"].append(f"Deep nested loops detected: {result['nested_loops']} levels")
            
            # 3. ��ȿ������ ��������� ����
            result["inefficient_comprehensions"] = self._detect_inefficient_comprehensions(tree)
            if result["inefficient_comprehensions"]:
                result["warnings"].append(f"Inefficient comprehensions: {len(result['inefficient_comprehensions'])} found")
        
        except Exception as e:
            result["errors"].append(f"Validation error: {e}")
        
        return result
    
    def _detect_nested_loops(self, tree: ast.AST) -> int:
        """�ߺ� ���� ���� ����"""
        class LoopDepthVisitor(ast.NodeVisitor):
            def __init__(self):
                self.max_depth = 0
                self.current_depth = 0
            
            def visit_For(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
            
            def visit_While(self, node):
                self.current_depth += 1
                self.max_depth = max(self.max_depth, self.current_depth)
                self.generic_visit(node)
                self.current_depth -= 1
        
        visitor = LoopDepthVisitor()
        visitor.visit(tree)
        return visitor.max_depth
    
    def _detect_inefficient_comprehensions(self, tree: ast.AST) -> List[str]:
        """��ȿ������ ��������� ����"""
        class ComprehensionVisitor(ast.NodeVisitor):
            def __init__(self):
                self.inefficient = []
            
            def visit_ListComp(self, node):
                # ��ø�� ��������� ����
                for generator in node.generators:
                    if isinstance(generator.iter, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                        self.inefficient.append("Nested comprehension detected")
                self.generic_visit(node)
            
            def visit_DictComp(self, node):
                for generator in node.generators:
                    if isinstance(generator.iter, (ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                        self.inefficient.append("Nested comprehension detected")
                self.generic_visit(node)
        
        visitor = ComprehensionVisitor()
        visitor.visit(tree)
        return visitor.inefficient
    
    def filter_training_data(self, replay_data: List[Dict], min_resource_efficiency: float = 0.7, min_combat_efficiency: float = 0.6) -> List[Dict]:
        """
        �н� ������ ����
        
        CRITICAL IMPROVEMENT: �¸��� ���� �߿����� ȿ���� ���� �����͸� ����
        
        Args:
            replay_data: ���÷��� ������ ����Ʈ
            min_resource_efficiency: �ּ� �ڿ� ȿ�� (0.0 ~ 1.0)
            min_combat_efficiency: �ּ� ���� ȿ�� (0.0 ~ 1.0)
            
        Returns:
            ������ ������ ����Ʈ
        """
        filtered = []
        
        for data in replay_data:
            # �¸��� ���Ӹ� ����
            if not data.get("victory", False):
                continue
            
            # �ڿ� ȿ�� ���
            resource_efficiency = self._calculate_resource_efficiency(data)
            if resource_efficiency < min_resource_efficiency:
                continue
            
            # ���� ȿ�� ���
            combat_efficiency = self._calculate_combat_efficiency(data)
            if combat_efficiency < min_combat_efficiency:
                continue
            
            # ȿ�� ���� �߰�
            data["resource_efficiency"] = resource_efficiency
            data["combat_efficiency"] = combat_efficiency
            
            filtered.append(data)
        
        return filtered
    
    def _calculate_resource_efficiency(self, data: Dict) -> float:
        """�ڿ� ȿ�� ���"""
        try:
            # �ڿ� �������� �Һ� ��
            minerals_collected = data.get("minerals_collected", 0)
            minerals_spent = data.get("minerals_spent", 0)
            
            if minerals_collected == 0:
                return 0.0
            
            # ������ �ڿ� �� �Һ��� ����
            efficiency = min(1.0, minerals_spent / minerals_collected)
            
            return efficiency
        
        except Exception:
            return 0.5  # �⺻��
    
    def _calculate_combat_efficiency(self, data: Dict) -> float:
        """���� ȿ�� ���"""
        try:
            # ���� �·�
            battles_won = data.get("battles_won", 0)
            battles_total = data.get("battles_total", 1)
            
            if battles_total == 0:
                return 0.0
            
            win_rate = battles_won / battles_total
            
            # �ս� ���� ����
            units_lost = data.get("units_lost", 0)
            units_killed = data.get("units_killed", 1)
            
            loss_ratio = units_lost / units_killed if units_killed > 0 else 1.0
            
            # �·��� ���� �ս��� ������ ȿ�� ����
            efficiency = win_rate * (1.0 - min(1.0, loss_ratio * 0.5))
            
            return efficiency
        
        except Exception:
            return 0.5  # �⺻��
=======



 if source_files:

     prompt += "SOURCE CODE (relevant section):\n"

 for file_path, code in source_files.items():

     prompt += f"\n--- {file_path} ---\n"

 prompt += code

     prompt += "\n"



     prompt += """

Please analyze the error and provide a fix in the following JSON format:

{

    "description": "Brief description of the fix",

    "file_path": "path/to/file.py",

    "old_code": "the problematic code section",

    "new_code": "the fixed code section",

    "confidence": 0.0-1.0,

    "reasoning": "Explanation of why this fix should work"

}



IMPORTANT:
# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

- Only suggest fixes that are clearly correct based on the error

- Be conservative with confidence scores

- Provide complete, runnable code blocks

- Preserve code structure and indentation

"""



 return prompt



def _parse_gemini_response(self, response_text: str, error_context: ErrorContext) -> Optional[PatchSuggestion]:

    """Gemini ÀÀ´ä ÆÄ½Ì"""

 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass

 # JSON ÄÚµå ºí·Ï ÃßÃâ

     if '```json' in response_text:

         pass

     pass

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
     json_start = response_text.find('```json') + 7

     json_end = response_text.find('```', json_start)

 json_str = response_text[json_start:json_end].strip()

     elif '```' in response_text:

         pass

     json_start = response_text.find('```') + 3

     json_end = response_text.find('```', json_start)

 json_str = response_text[json_start:json_end].strip()

 else:

     pass

 # JSONÀÌ ¾øÀ¸¸é ÀüÃ¼ ÅØ½ºÆ®¸¦ JSONÀ¸·Î ½Ãµµ

 json_str = response_text.strip()



 # JSON ÆÄ½Ì

 patch_data = json.loads(json_str)



 return PatchSuggestion(

     description = patch_data.get('description', 'No description'),

     file_path = patch_data.get('file_path', error_context.file_path or 'unknown'),
# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

    old_code = patch_data.get('old_code', ''),

    new_code = patch_data.get('new_code', ''),

    confidence = float(patch_data.get('confidence', 0.5)),

    reasoning = patch_data.get('reasoning', 'No reasoning provided')

 )

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토


 except (json.JSONDecodeError, KeyError, ValueError) as e:

     logger.warning(f"[SELF-HEALING] Failed to parse Gemini response: {e}")

     logger.debug(f"[SELF-HEALING] Response text: {response_text[:500]}")

 return None



def _save_patch_suggestion(self, error_context: ErrorContext, patch: PatchSuggestion):

    """ÆÐÄ¡ Á¦¾ÈÀ» ÆÄÀÏ¿¡ ÀúÀå"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    patch_file = self.log_dir / f"patch_{timestamp}.json"



 patch_data = {
# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

    "timestamp": timestamp,

    "error_context": asdict(error_context),

    "patch_suggestion": asdict(patch),

 }



 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass

     with open(patch_file, 'w', encoding='utf-8') as f:

 json.dump(patch_data, f, indent = 2, ensure_ascii = False)

     logger.info(f"[SELF-HEALING] Patch suggestion saved to {patch_file}")

 except Exception as e:

     logger.error(f"[SELF-HEALING] Failed to save patch suggestion: {e}")

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토


def apply_patch(self, patch: PatchSuggestion) -> bool:

    """
# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

 ÆÐÄ¡ Àû¿ë (ÁÖÀÇ: ÀÚµ¿ ÆÐÄ¡´Â À§ÇèÇÒ ¼ö ÀÖÀ½)



 Args:

 patch: Àû¿ëÇÒ ÆÐÄ¡ Á¦¾È



 Returns:

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
 ¼º°ø ¿©ºÎ

     """

 if not self.enable_auto_patch:

     pass

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
     logger.warning("[SELF-HEALING] Auto-patch is disabled. Patch suggestion saved but not applied.")

 return False

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토


 if patch.confidence < 0.7:

     logger.warning(f"[SELF-HEALING] Patch confidence too low ({patch.confidence}), not applying")

 return False



 try:
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass
 pass

 except Exception:
     pass
     pass

 file_path = Path(patch.file_path)

 if not file_path.exists():

     logger.error(f"[SELF-HEALING] File not found: {file_path}")

 return False



 # ÆÄÀÏ ¹é¾÷

     backup_path = file_path.with_suffix(f"{file_path.suffix}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

     with open(file_path, 'r', encoding='utf-8') as f:

 original_content = f.read()

     with open(backup_path, 'w', encoding='utf-8') as f:

 f.write(original_content)


# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

 # ÆÐÄ¡ Àû¿ë

 if patch.old_code in original_content:

     pass

 new_content = original_content.replace(patch.old_code, patch.new_code)

 # TODO: 중복 코드 블록 - 공통 함수로 추출 검토
     with open(file_path, 'w', encoding='utf-8') as f:

 f.write(new_content)

     logger.info(f"[SELF-HEALING] Patch applied to {file_path} (backup: {backup_path})")

 return True

 else:

     logger.warning(f"[SELF-HEALING] Old code not found in file, patch not applied")

 return False



 except Exception as e:

     logger.error(f"[SELF-HEALING] Failed to apply patch: {e}")
# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

 logger.debug(traceback.format_exc())

 return False

    def validate_code_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        코드 구문 검증 (SyntaxError 체크)
        
        Gemini가 생성한 코드를 적용하기 전에 구문 오류를 사전에 검사
        
        Args:
            code: 검증할 코드 문자열
            
        Returns:
            (is_valid, error_message) 튜플
        """
        import ast
        
        try:
            # AST 파싱으로 구문 오류 검사
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            error_msg = f"SyntaxError at line {e.lineno}: {e.msg}"
            if e.text:
                error_msg += f"\nCode: {e.text.strip()}"
            return False, error_msg
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def filter_training_data(self, replay_data: List[Dict], 
                           min_resource_efficiency: float = 0.7,
                           min_combat_win_rate: float = 0.5) -> List[Dict]:
        """
        학습 데이터 선별
        
        승리한 게임 중에서도 자원 효율이나 교전 승률이 특정 기준 이상인 데이터만 엄선
        
        Args:
            replay_data: 리플레이 데이터 리스트
            min_resource_efficiency: 최소 자원 효율 (0.0 ~ 1.0)
            min_combat_win_rate: 최소 교전 승률 (0.0 ~ 1.0)
            
        Returns:
            선별된 리플레이 데이터 리스트
        """
        filtered = []
        
        for replay in replay_data:
            # 승리한 게임만 필터링
            if not replay.get('won', False):
                continue
            
            # 자원 효율 계산
            resources_spent = replay.get('resources_spent', 0)
            resources_gathered = replay.get('resources_gathered', 0)
            if resources_gathered > 0:
                resource_efficiency = resources_spent / resources_gathered
            else:
                resource_efficiency = 0.0
            
            # 교전 승률 계산
            engagements_won = replay.get('engagements_won', 0)
            total_engagements = replay.get('total_engagements', 1)
            combat_win_rate = engagements_won / total_engagements if total_engagements > 0 else 0.0
            
            # 기준 이상인 데이터만 선별
            if resource_efficiency >= min_resource_efficiency and combat_win_rate >= min_combat_win_rate:
                filtered.append(replay)
        
        return filtered
    
    def static_analysis_optimization(self, file_path: Path) -> List[Dict[str, Any]]:
        """
        정적 분석을 통한 코드 최적화 감지
        
        성능에 영향을 주는 중복 루프나 비효율적인 리스트 컴프리헨션을 감지
        
        Args:
            file_path: 분석할 파일 경로
            
        Returns:
            최적화 제안 리스트
        """
        import ast
        
        suggestions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                lines = content.splitlines()
            
            # AST 파싱
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                return suggestions  # 구문 오류가 있으면 분석 불가
            
            # 1. 중복 루프 감지
            for node in ast.walk(tree):
                if isinstance(node, ast.For):
                    # 중첩된 for 루프 확인
                    nested_fors = [n for n in ast.walk(node) if isinstance(n, ast.For) and n != node]
                    if nested_fors:
                        suggestions.append({
                            'type': 'nested_loop',
                            'line': node.lineno,
                            'message': f'Nested for loops detected at line {node.lineno}. Consider using itertools.product() or vectorization.',
                            'severity': 'medium'
                        })
            
            # 2. 비효율적인 리스트 컴프리헨션 감지
            for i, line in enumerate(lines, 1):
                # 중첩된 리스트 컴프리헨션
                if line.count('[') >= 3 and 'for' in line and 'in' in line:
                    # 간단한 휴리스틱: 너무 복잡한 컴프리헨션
                    if line.count('for') >= 2:
                        suggestions.append({
                            'type': 'complex_comprehension',
                            'line': i,
                            'message': f'Complex nested list comprehension at line {i}. Consider breaking into multiple steps for readability and performance.',
                            'severity': 'low'
                        })
                
                # 리스트 컴프리헨션 내부의 함수 호출
                if '[' in line and 'for' in line and '(' in line:
                    # 함수 호출이 있는 컴프리헨션은 map() 사용 고려
                    if line.count('(') > line.count('['):
                        suggestions.append({
                            'type': 'function_in_comprehension',
                            'line': i,
                            'message': f'Function calls in list comprehension at line {i}. Consider using map() for better performance.',
                            'severity': 'low'
                        })
            
            # 3. 중복 코드 블록 감지 (간단한 버전)
            line_hashes = {}
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if len(stripped) > 20:  # 충분히 긴 라인만
                    line_hash = hash(stripped)
                    if line_hash in line_hashes:
                        # 같은 라인이 반복됨
                        prev_line = line_hashes[line_hash]
                        suggestions.append({
                            'type': 'duplicate_code',
                            'line': i,
                            'message': f'Duplicate code detected at line {i} (similar to line {prev_line}). Consider extracting to a function.',
                            'severity': 'medium'
                        })
                    else:
                        line_hashes[line_hash] = i
        
        except Exception as e:
            logger.warning(f"[STATIC_ANALYSIS] Error analyzing {file_path}: {e}")
        
        return suggestions


# TODO: 중복 코드 블록 - 공통 함수로 추출 검토


# 전역 인스턴스 (선택적 사용)

_global_self_healing: Optional[GenAISelfHealing] = None




# TODO: 중복 코드 블록 - 공통 함수로 추출 검토

def get_self_healing() -> Optional[GenAISelfHealing]:

    """Àü¿ª Self-Healing ÀÎ½ºÅÏ½º °¡Á®¿À±â"""

 return _global_self_healing





# TODO: 중복 코드 블록 - 공통 함수로 추출 검토
def init_self_healing(

 api_key: Optional[str] = None,

 enable_auto_patch: bool = False

# TODO: 중복 코드 블록 - 공통 함수로 추출 검토
) -> GenAISelfHealing:

    """

 Àü¿ª Self-Healing ÀÎ½ºÅÏ½º ÃÊ±âÈ­



 Args:

 api_key: Google Gemini API Å°

 enable_auto_patch: ÀÚµ¿ ÆÐÄ¡ Àû¿ë ¿©ºÎ (±âº»°ª: False)



 Returns:

 GenAISelfHealing ÀÎ½ºÅÏ½º

    """

 global _global_self_healing

 _global_self_healing = GenAISelfHealing(

 api_key = api_key,

 enable_auto_patch = enable_auto_patch

 )

 return _global_self_healing
>>>>>>> Incoming (Background Agent changes)
