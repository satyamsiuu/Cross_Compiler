// Sample C program — basic arithmetic and control flow
#include <stdio.h>

int main() {
    int x = 10;
    int y = 20;
    int sum = x + y;

    // Print the sum
    printf("%d\n", sum);

    /* Multi-line comment:
       This tests if/else */
    if (sum > 25) {
        printf("big\n");
    } else {
        printf("small\n");
    }

    // While loop
    int i = 0;
    while (i < 5) {
        printf("%d\n", i);
        i = i + 1;
    }

    return 0;
}
