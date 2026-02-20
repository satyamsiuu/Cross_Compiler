"""
Phase 1: Preprocessor
- Remove comments
- Normalize whitespace
- Preserve line numbers
"""


class Preprocessor:
    def __init__(self, language: str):
        self.language = language

    def process(self, source: str) -> str:
        """Remove comments and normalize whitespace."""
        if self.language in ("c", "cpp", "javascript"):
            source = self._remove_c_style_comments(source)
        elif self.language == "python":
            source = self._remove_python_comments(source)

        # Normalize trailing whitespace per line, preserve blank lines for line numbers
        lines = source.split("\n")
        lines = [line.rstrip() for line in lines]

        # Remove trailing blank lines only
        while lines and lines[-1] == "":
            lines.pop()

        return "\n".join(lines)

    def _remove_c_style_comments(self, source: str) -> str:
        """Remove // and /* */ comments while preserving line numbers."""
        result = []
        i = 0
        in_string = False
        string_char = None

        while i < len(source):
            # Handle string literals — don't remove comment-like chars inside strings
            if not in_string and source[i] in ('"', "'"):
                in_string = True
                string_char = source[i]
                result.append(source[i])
                i += 1
            elif in_string:
                if source[i] == '\\' and i + 1 < len(source):
                    result.append(source[i])
                    result.append(source[i + 1])
                    i += 2
                elif source[i] == string_char:
                    in_string = False
                    result.append(source[i])
                    i += 1
                else:
                    result.append(source[i])
                    i += 1
            # Single-line comment
            elif source[i] == '/' and i + 1 < len(source) and source[i + 1] == '/':
                # Skip until end of line
                while i < len(source) and source[i] != '\n':
                    i += 1
            # Multi-line comment
            elif source[i] == '/' and i + 1 < len(source) and source[i + 1] == '*':
                i += 2
                while i + 1 < len(source) and not (source[i] == '*' and source[i + 1] == '/'):
                    if source[i] == '\n':
                        result.append('\n')  # Preserve line numbers
                    i += 1
                if i + 1 < len(source):
                    i += 2  # Skip */
            else:
                result.append(source[i])
                i += 1

        return "".join(result)

    def _remove_python_comments(self, source: str) -> str:
        """Remove # comments while preserving line numbers and strings."""
        result = []
        i = 0
        in_string = False
        string_char = None
        triple_string = False

        while i < len(source):
            # Handle triple-quoted strings
            if not in_string and i + 2 < len(source) and source[i:i+3] in ('"""', "'''"):
                in_string = True
                triple_string = True
                string_char = source[i:i+3]
                result.append(source[i:i+3])
                i += 3
            elif in_string and triple_string and i + 2 < len(source) and source[i:i+3] == string_char:
                in_string = False
                triple_string = False
                result.append(source[i:i+3])
                i += 3
            # Handle regular strings
            elif not in_string and source[i] in ('"', "'"):
                in_string = True
                string_char = source[i]
                triple_string = False
                result.append(source[i])
                i += 1
            elif in_string and not triple_string:
                if source[i] == '\\' and i + 1 < len(source):
                    result.append(source[i])
                    result.append(source[i + 1])
                    i += 2
                elif source[i] == string_char:
                    in_string = False
                    result.append(source[i])
                    i += 1
                else:
                    result.append(source[i])
                    i += 1
            elif in_string and triple_string:
                result.append(source[i])
                i += 1
            # Comment
            elif source[i] == '#':
                while i < len(source) and source[i] != '\n':
                    i += 1
            else:
                result.append(source[i])
                i += 1

        return "".join(result)
