"""
Source-to-Source Cross Compiler
Entry point - CLI interface
"""
import argparse
import json
import sys
import os

from compiler.pipeline import CompilerPipeline
from compiler.errors import CompilerError


def main():
    parser = argparse.ArgumentParser(
        description="Source-to-Source Cross Compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --source samples/hello.c --from c --to python
  python main.py --source samples/loop.py --from python --to javascript
        """
    )
    parser.add_argument("--source", required=True, help="Path to source file")
    parser.add_argument("--from", dest="source_lang", required=True,
                        choices=["c", "cpp", "python", "javascript"],
                        help="Source language")
    parser.add_argument("--to", dest="target_lang", required=True,
                        choices=["c", "cpp", "python", "javascript"],
                        help="Target language")
    parser.add_argument("--validate", action="store_true",
                        help="Run validation phase (compare outputs)")
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose output")

    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Error: Source file '{args.source}' not found.")
        sys.exit(1)

    with open(args.source, "r") as f:
        source_code = f.read()

    pipeline = CompilerPipeline(
        source_lang=args.source_lang,
        target_lang=args.target_lang,
        verbose=args.verbose
    )

    try:
        result = pipeline.compile(source_code=source_code, source_path=args.source, validate=args.validate)

        print("\n=== Compilation Summary ===")
        for phase, status in result["phases"].items():
            icon = "[OK]" if status == "success" else "[FAIL]" if status == "failed" else "[SKIP]"
            print(f"  {icon} {phase}")

        print("\nArtifacts saved to: artifacts/")
        if args.validate and result.get("validation"):
            print("\n=== Validation Result ===")
            if result["validation"]["passed"]:
                print("  [PASS] Outputs match")
            else:
                print("  [FAIL] Outputs do NOT match")
        print("Compilation successful (implemented phases).")

    except CompilerError as e:
        print(f"\n[FAIL] Compilation failed at phase: {e.phase}")
        print(f"   Error: {e.message}")
        if e.line:
            print(f"   Location: line {e.line}, column {e.column}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
