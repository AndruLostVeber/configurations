; Подготовка массива по адресам 1000–1004.
load r0, 1000
load r1, 19
write r1, 0, r0
load r1, -23
write r1, 1, r0
load r1, 0
write r1, 2, r0
load r1, 8388607
write r1, 3, r0
load r1, -8388608
write r1, 4, r0

; Копирование в область 1008–1012.
load r2, 1008
read r15, 1000
write r15, 0, r2
read r15, 1001
write r15, 1, r2
read r15, 1002
write r15, 2, r2
read r15, 1003
write r15, 3, r2
read r15, 1004
write r15, 4, r2
