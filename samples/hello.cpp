// Sample C++ program — basic arithmetic and control flow
#include <iostream>
using namespace std;

int main() {
    int x = 10;
    int y = 20;
    int sum = x + y;

    // Print the sum
    cout << sum << endl;

    /* Multi-line comment:
       This tests if/else */
    if (sum > 25) {
        cout << "big" << endl;
    } else {
        cout << "small" << endl;
    }

    // While loop
    int i = 0;
    while (i < 5) {
        cout << i << endl;
        i = i + 1LL;
    }

    return 0;
}
