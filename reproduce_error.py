from compiler.lexer import Lexer
from compiler.parser import Parser
import json

code = """
#include <stdio.h>

int main() {
    int num;
    printf("Enter a number: ");
    scanf("%d", &num);
    return 0;
}
"""

try:
    lexer = Lexer("c")
    tokens = lexer.tokenize(code)
    print("TOKENS:")
    for t in tokens:
        print(t)
    
    parser = Parser("c")
    ast = parser.parse(tokens)
    print("\nAST successfully generated")
except Exception as e:
    print(f"\nERROR: {e}")
