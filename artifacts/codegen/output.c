#include <stdio.h>

int fibonacci(int num) {
    num1 = 0;
    num2 = 1;
    if ((num == 1)) {
        return num1;
    } else {
        if ((num == 2)) {
            return num2;
        } else {
            i = 3;
            while ((i <= num)) {
                sum = (num1 + num2);
                num1 = num2;
                num2 = sum;
                i = (i + 1);
            }
            return num2;
        }
    }
    return;
}
int main() {
    int i, num1, num2, sum;

    t6 = fibonacci(5);
    printf("%d\n", ("Fibonacci(5): " + t6));
    t8 = fibonacci(8);
    printf("%d\n", ("Fibonacci(8): " + t8));

    return 0;
}
