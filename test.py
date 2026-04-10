import os
import sys
sys.path.append(os.path.abspath("."))
from compiler.pipeline import CompilerPipeline

code = '''
function fibonacci(num) {
    let num1 = 0;
    let num2 = 1;
    let sum;
    if (num === 1) {
        return num1;
    } else if (num === 2) {
        return num2;
    } else {
        for (let i = 3; i <= num; i++) {
            sum = num1 + num2;
            num1 = num2;
            num2 = sum;
        }
        return num2;
    }
}
console.log("Fibonacci(5): " + fibonacci(5));
'''
with open("artifacts/temp_source.js", "w") as f:
    f.write(code)

p = CompilerPipeline("javascript", "python")
res = p.compile(code, "artifacts/temp_source.js")
print(res)
