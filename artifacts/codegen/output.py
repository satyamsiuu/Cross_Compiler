print("Enter size of array: ")
n = int(input())
arr = [0] * (n)
print("Enter ", n, " elements: ")
i = 0
while (i < n):
    t2 = int(input())
    arr[i] = t2
    i = (i + 1)
left = 0
right = (n - 1)
while (left < right):
    t6 = arr[left]
    temp = t6
    t7 = arr[right]
    arr[left] = t7
    arr[right] = temp
    left = (left + 1)
    right = (right - 1)
sum = 0
print("Reversed array: ")
i = 0
while (i < n):
    t11 = arr[i]
    print(t11, " ")
    t12 = arr[i]
    sum = (sum + t12)
    i = (i + 1)
print()
print("Sum of all elements: ", sum)
