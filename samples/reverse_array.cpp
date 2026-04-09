#include <iostream>
using namespace std;

int main() {
    int n;
    
    // Input size of array
    cout << "Enter size of array: ";
    cin >> n;
    
    int arr[n];
    
    // Input array elements
    cout << "Enter " << n << " elements: ";
    for(int i = 0; i < n; i++) {
        cin >> arr[i];
    }
    
    // Reverse the array using logic (swap)
    int left = 0, right = n - 1;
    while(left < right) {
        int temp = arr[left];
        arr[left] = arr[right];
        arr[right] = temp;
        
        left++;
        right--;
    }
    
    // Print reversed array and calculate sum
    int sum = 0;
    cout << "Reversed array: ";
    for(int i = 0; i < n; i++) {
        cout << arr[i] << " ";
        sum += arr[i];
    }
    
    cout << endl;
    cout << "Sum of all elements: " << sum << endl;
     
    return 0;
}
