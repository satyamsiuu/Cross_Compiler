console.log("Enter size of array: ");
let n = parseInt(prompt("Input:") || "0");
let arr = new Array(n).fill(0);
console.log("Enter ", n, " elements: ");
let i = 0;
while ((i < n)) {
    let t2 = parseInt(prompt("Input:") || "0");
    arr[i] = t2;
    i = (i + 1);
}
let left = 0;
let right = (n - 1);
while ((left < right)) {
    let t6 = arr[left];
    let temp = t6;
    let t7 = arr[right];
    arr[left] = t7;
    arr[right] = temp;
    left = (left + 1);
    right = (right - 1);
}
let sum = 0;
console.log("Reversed array: ");
i = 0;
while ((i < n)) {
    let t11 = arr[i];
    console.log(t11, " ");
    let t12 = arr[i];
    sum = (sum + t12);
    i = (i + 1);
}
console.log();
console.log("Sum of all elements: ", sum);
