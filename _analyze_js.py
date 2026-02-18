"""Analyze JS file for brace/paren balance issues."""
import sys

filepath = r'C:\Users\sun47\.openclaw\workspace\discord_voice_chat_jarvis.js'
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

depth_b = 0  # braces {}
depth_p = 0  # parens ()
in_str = None
escape_next = False

for i, line in enumerate(lines, 1):
    for j in range(len(line)):
        ch = line[j]

        if escape_next:
            escape_next = False
            continue

        if ch == '\\':
            escape_next = True
            continue

        if in_str == 'backtick':
            if ch == '`':
                in_str = None
            # Skip template expression tracking for simplicity
            continue
        elif in_str is not None:
            if ch == in_str:
                in_str = None
            continue

        # Not in string
        if ch == '"':
            in_str = '"'
        elif ch == "'":
            in_str = "'"
        elif ch == '`':
            in_str = 'backtick'
        elif ch == '/' and j+1 < len(line):
            # Skip comments
            if line[j+1] == '/':
                break  # rest of line is comment
            elif line[j+1] == '*':
                pass  # TODO: multi-line comments, skip for now
        elif ch == '{':
            depth_b += 1
        elif ch == '}':
            depth_b -= 1
        elif ch == '(':
            depth_p += 1
        elif ch == ')':
            depth_p -= 1

    if depth_p < 0 or depth_b < 0:
        print(f'Line {i}: braces={depth_b} parens={depth_p} *** NEGATIVE ***')
        print(f'  -> {line.rstrip()[:120]}')
    elif i % 1000 == 0:
        print(f'Line {i}: braces={depth_b} parens={depth_p}')

print(f'\nFinal (line {len(lines)}): braces={depth_b} parens={depth_p}')
