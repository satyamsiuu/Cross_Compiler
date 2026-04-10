process.stdout.write("Enter a number: ");
let num = parseInt(prompt("Input:") || "0");
process.stdout.write(`Multiplication Table of ${num}:` + "\n");
let i = 1;
while ((i <= 10)) {
    process.stdout.write(`${num} x ${i} = ${(num * i)}` + "\n");
    i = (i + 1);
}
return 0;
