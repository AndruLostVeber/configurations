; Инициализация вектора по адресам 1024–1033.
load r0, 1024
load r1, 0
write r1, 0, r0
load r1, 1
write r1, 1, r0
load r1, 2
write r1, 2, r0
load r1, 0
write r1, 3, r0
load r1, 65536
write r1, 4, r0
load r1, 128
write r1, 5, r0
load r1, 0
write r1, 6, r0
load r1, 4096
write r1, 7, r0
load r1, 8388607
write r1, 8, r0
load r1, 4
write r1, 9, r0

; Запись знаков в те же ячейки.
load r2, 1024
sgn r2, r3
write r3, 0, r0
load r2, 1025
sgn r2, r3
write r3, 1, r0
load r2, 1026
sgn r2, r3
write r3, 2, r0
load r2, 1027
sgn r2, r3
write r3, 3, r0
load r2, 1028
sgn r2, r3
write r3, 4, r0
load r2, 1029
sgn r2, r3
write r3, 5, r0
load r2, 1030
sgn r2, r3
write r3, 6, r0
load r2, 1031
sgn r2, r3
write r3, 7, r0
load r2, 1032
sgn r2, r3
write r3, 8, r0
load r2, 1033
sgn r2, r3
write r3, 9, r0
