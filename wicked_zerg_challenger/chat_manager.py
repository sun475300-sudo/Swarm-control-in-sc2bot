# -*- coding: utf-8 -*-
"""Compatibility shim.

과거에는 chat_manager_utf8.ChatManager 를 re-export 했지만 해당 모듈이
삭제되어 이 쉼은 사실상 비어 있다. 외부에서 이 모듈을 import 하더라도
이름이 나타나지 않도록 __all__ 도 비워 둔다. ChatManager 가 필요할
경우 새 구현을 여기에 추가하거나 별도 모듈로 옮기자.
"""

__all__: list = []
