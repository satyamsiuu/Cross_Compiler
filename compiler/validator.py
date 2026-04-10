import subprocess
import tempfile
import os
import json

from compiler.errors import CompilerError

class ValidationError(CompilerError):
    def __init__(self, message):
        super().__init__("Validation", "ValidationError", message)


class Validator:
    def run_code(self, code_path, lang, test_input=""):
        try:
            if lang == "python":
                result = subprocess.run(
                    ["python", code_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    input=test_input
                )

            elif lang == "javascript":
                result = subprocess.run(
                    ["node", code_path],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    input=test_input
                )

            elif lang in ["c", "cpp"]:
                compiler = "gcc" if lang == "c" else "g++"
                binary = code_path + ".out"

                subprocess.run([compiler, code_path, "-o", binary], check=True)

                result = subprocess.run(
                    [binary],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    input=test_input
                )

            else:
                raise ValidationError(f"Unsupported language: {lang}")

            return result.stdout.strip()

        except Exception as e:
            raise ValidationError(str(e))


    def validate(self, source_path, source_lang, generated_code, target_lang, interactive=False, input_data=None):
        import sys
        ext_map = {"python": ".py", "c": ".c", "cpp": ".cpp", "javascript": ".js"}
        suffix = ext_map.get(target_lang, ".txt")
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(generated_code.encode())
            temp_path = temp.name

        test_input = ""
        if interactive:
            if input_data is not None:
                if str(input_data).strip() == "":
                    raise ValidationError("This program requires Interactive Input. Please provide test inputs cleanly in the GUI.")
                test_input = input_data
                print("[validator] Interactive program detected. Using provided test inputs from API.")
            else:
                print("\n[validator] Interactive program detected. Please provide test inputs.")
                print("[validator] (Type your inputs, press Enter, then press Ctrl+D on Unix or Ctrl+Z on Windows to finish):")
                test_input = sys.stdin.read()
                print("[validator] Input captured. Proceeding with validation...")

        try:
            source_output = self.run_code(source_path, source_lang, test_input)
            target_output = self.run_code(temp_path, target_lang, test_input)

            match = source_output == target_output
            if not match:
                # Fallback to formatting-agnostic matching
                match = source_output.split() == target_output.split()

            result = {
                "passed": match,
                "source_output": source_output,
                "target_output": target_output,
                "match": match
            }

            os.makedirs("artifacts/validation", exist_ok=True)

            with open("artifacts/validation/validation_report.json", "w") as f:
                json.dump(result, f, indent=4)

            return result

        finally:
            os.remove(temp_path)