#include <stdio.h>

int main() {
    int num;

    // Taking input from user
    printf("Enter a number: ");
    scanf("%d", &num);

    // Printing table from 1 to 10
    printf("Multiplication Table of %d:\n", num);

    for(int i = 1; i <= 10; i++) {
        printf("%d x %d = %d\n", num, i, num * i);
    }

    return 0;
}
