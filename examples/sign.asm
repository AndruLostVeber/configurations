; Три исходных значения по адресам 300–302.
load r0, 300
load r1, -12
write r1, 0, r0
load r1, 0
write r1, 1, r0
load r1, 27
write r1, 2, r0

; Знаки сохраняются отдельно по адресам 310–312.
load r3, 310
sgn r0, r15
write r15, 0, r3
load r2, 301
sgn r2, r15
write r15, 1, r3
load r2, 302
sgn r2, r15
write r15, 2, r3
