#include <stdio.h>

int main() {
    int i, sum, x, y, t2, t3, t4;

    x = 10;
    y = 20;
    sum = 30;
    printf("%d\n", 30);
    t2 = 1;
    if (t2) {
        printf("%s\n", "big");
    } else {
        printf("%s\n", "small");
    }
    i = 0;
    while (1) {
        t3 = (i < 5);
        if (!t3) break;
        printf("%d\n", i);
        t4 = (i + 1);
        i = t4;
    }

    return 0;
}
