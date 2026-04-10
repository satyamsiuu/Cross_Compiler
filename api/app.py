from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import io
import json
import glob

# Add parent dir to PYTHONPATH so backend can import compiler mapping
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# Force the working directory to the project root so "artifacts/..." paths resolve no matter where the user runs the script from!
os.chdir(PROJECT_ROOT)

from compiler.pipeline import CompilerPipeline
from compiler.errors import CompilerError

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend')
app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
CORS(app)  # Allow frontend to make requests

@app.route('/')
def index():
    return app.send_static_file('index.html')

def load_artifacts_from_dir(result_obj=None):
    artifacts = {}
    for phase, fpath in [
        ("preprocessed", "preprocess/cleaned_source.txt"),
        ("tokens", "lexer/tokens.json"),
        ("ast", "parser/ast.json"),
        ("symbols", "semantic/symbol_table.json"),
        ("ir", "ir/ir.json"),
        ("optimized_ir", "optimizer/ir_after.json")
    ]:
        full_path = os.path.join("artifacts", fpath)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                artifacts[phase] = f.read()
        else:
            artifacts[phase] = "Not generated."

    # Read the generated code output natively
    if result_obj and result_obj.get("output_path") and os.path.exists(result_obj.get("output_path")):
        with open(result_obj.get("output_path"), "r") as f:
            artifacts["output_code"] = f.read()
    else:
        # Fallback to wildcard search
        matched = glob.glob("artifacts/codegen/output.*")
        if matched:
            with open(matched[0], "r") as f:
                artifacts["output_code"] = f.read()
        else:
            artifacts["output_code"] = "Error generating target code."
    return artifacts

@app.route('/api/compile', methods=['POST'])
def compile_code():
    data = request.json
    source_code = data.get('source_code', '')
    source_lang = data.get('source_lang', 'cpp')
    target_lang = data.get('target_lang', 'python')
    test_input = data.get('test_input', '')
    validate = data.get('validate', False)

    # We map "temp_source" for UI processing
    ext_map = {"python": ".py", "c": ".c", "cpp": ".cpp", "javascript": ".js"}
    source_path = f"artifacts/temp_source{ext_map.get(source_lang, '.txt')}"
    
    with open(source_path, "w") as f:
        f.write(source_code)

    # Clean old artifacts to prevent loading stale files on failure
    for old_file in [
        "lexer/tokens.json", "parser/ast.json", "semantic/symbol_table.json", 
        "ir/ir.json", "optimizer/ir_after.json", "validation/validation_report.json"
    ]:
        p = os.path.join("artifacts", old_file)
        if os.path.exists(p):
            os.remove(p)
            
    for old_out in glob.glob("artifacts/codegen/output.*"):
        os.remove(old_out)

    pipeline = CompilerPipeline(
        source_lang=source_lang,
        target_lang=target_lang,
        verbose=False
    )

    try:
        # Run pipeline natively bypassing stdin blocks safely
        result = pipeline.compile(
            source_code=source_code, 
            source_path=source_path, 
            validate=validate, 
            input_data=test_input if test_input else ""
        )
        
        artifacts = load_artifacts_from_dir(result)

        return jsonify({
            "status": "success",
            "phases": result["phases"],
            "validation": result.get("validation"),
            "artifacts": artifacts
        })

    except CompilerError as e:
        return jsonify({
            "status": "error",
            "phase": e.phase,
            "message": e.message,
            "line": e.line,
            "column": e.column,
            "phases": getattr(e, 'phases_state', {}), # We can track it through pipeline dynamically, but we'll manage in JS
            "artifacts": load_artifacts_from_dir()
        }), 400
    except Exception as e:
        return jsonify({
            "status": "fatal",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5000)
