import subprocess
import tempfile
import os
import json

class ValidationError(Exception):
    pass


class Validator:
    def run_code(self, code_path, lang):
        try:
            if lang == "python":
                result = subprocess.run(
                    ["python", code_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            elif lang == "javascript":
                result = subprocess.run(
                    ["node", code_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            elif lang in ["c", "cpp"]:
                compiler = "gcc" if lang == "c" else "g++"
                binary = code_path + ".out"

                subprocess.run([compiler, code_path, "-o", binary], check=True)

                result = subprocess.run(
                    [binary],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            else:
                raise ValidationError(f"Unsupported language: {lang}")

            return result.stdout.strip()

        except Exception as e:
            raise ValidationError(str(e))


    def validate(self, source_path, source_lang, generated_code, target_lang):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp:
            temp.write(generated_code.encode())
            temp_path = temp.name

        try:
            source_output = self.run_code(source_path, source_lang)
            target_output = self.run_code(temp_path, target_lang)

            match = source_output == target_output

            result = {
                "passed": match,
                "source_output": source_output,
                "target_output": target_output,
                "match": match
            }

            os.makedirs("artifacts/validation", exist_ok=True)

            with open("artifacts/validation/validation_report.json", "w") as f:
                json.dump(result, f, indent=4)

            if not match:
                raise ValidationError("Outputs do not match")

            return result

        finally:
            os.remove(temp_path)