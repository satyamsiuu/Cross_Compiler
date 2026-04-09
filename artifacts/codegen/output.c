#include <stdio.h>

int main() {
    int i, sum, x, y;

    x = 10;
    y = 20;
    sum = (x + y);
    printf("%d\n", sum);
    if ((sum > 25)) {
        printf("%s\n", "big");
    } else {
        printf("%s\n", "small");
    }
    i = 0;
    while ((i < 5)) {
        printf("%d\n", i);
        i = (i + 1);
    }

    return 0;
}
