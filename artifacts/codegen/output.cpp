#include <iostream>
using namespace std;

int main() {
    int i, num;

    cout << "Enter a number: ";
    cin >> num;
    cout << "Multiplication Table of " << num << ":" << endl;
    i = 1;
    while ((i <= 10)) {
        cout << num << " x " << i << " = " << (num * i) << endl;
        i = (i + 1);
    }
    return 0;
}
