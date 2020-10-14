\* Bay_Assignment *\
Minimize
obj_fun: 8500 X_A10_1 + 5540 X_A10_2 + 10880 X_A10_3 + 425 X_A1_1 + 277 X_A1_2
 + 544 X_A1_3 + 425 X_A2_1 + 277 X_A2_2 + 544 X_A2_3 + 1275 X_A3_1
 + 831 X_A3_2 + 1632 X_A3_3 + 1275 X_A4_1 + 831 X_A4_2 + 1632 X_A4_3
 + 2125 X_A5_1 + 1385 X_A5_2 + 2720 X_A5_3 + 2125 X_A6_1 + 1385 X_A6_2
 + 2720 X_A6_3 + 2975 X_A7_1 + 1939 X_A7_2 + 3808 X_A7_3 + 8500 X_A8_1
 + 5540 X_A8_2 + 10880 X_A8_3 + 8500 X_A9_1 + 5540 X_A9_2 + 10880 X_A9_3
 + 850 X_B1_1 + 554 X_B1_2 + 1088 X_B1_3 + 850 X_B2_1 + 554 X_B2_2
 + 1088 X_B2_3 + 2337.5 X_B3_1 + 1523.5 X_B3_2 + 2992 X_B3_3 + 2337.5 X_B4_1
 + 1523.5 X_B4_2 + 2992 X_B4_3 + 3612.5 X_B5_1 + 2354.5 X_B5_2 + 4624 X_B5_3
Subject To
Assignment_Constraint:1: X_B1_1 + X_B2_1 = 1
Assignment_Constraint:2: X_B1_2 + X_B2_2 + X_B3_2 + X_B4_2 + X_B5_2 = 1
Assignment_Constraint:3: X_B1_3 + X_B2_3 = 1
Bay_Constraint:B3_1: X_B3_1 = 0
Bay_Constraint:B3_3: X_B3_3 = 0
Bay_Constraint:B4_1: X_B4_1 = 0
Bay_Constraint:B4_3: X_B4_3 = 0
Bay_Constraint:B5_1: X_B5_1 = 0
Bay_Constraint:B5_3: X_B5_3 = 0
Terminal_Constraint:A10_1: X_A10_1 = 0
Terminal_Constraint:A10_2: X_A10_2 = 0
Terminal_Constraint:A10_3: X_A10_3 = 0
Terminal_Constraint:A1_1: X_A1_1 = 0
Terminal_Constraint:A1_2: X_A1_2 = 0
Terminal_Constraint:A1_3: X_A1_3 = 0
Terminal_Constraint:A2_1: X_A2_1 = 0
Terminal_Constraint:A2_2: X_A2_2 = 0
Terminal_Constraint:A2_3: X_A2_3 = 0
Terminal_Constraint:A3_1: X_A3_1 = 0
Terminal_Constraint:A3_2: X_A3_2 = 0
Terminal_Constraint:A3_3: X_A3_3 = 0
Terminal_Constraint:A4_1: X_A4_1 = 0
Terminal_Constraint:A4_2: X_A4_2 = 0
Terminal_Constraint:A4_3: X_A4_3 = 0
Terminal_Constraint:A5_1: X_A5_1 = 0
Terminal_Constraint:A5_2: X_A5_2 = 0
Terminal_Constraint:A5_3: X_A5_3 = 0
Terminal_Constraint:A6_1: X_A6_1 = 0
Terminal_Constraint:A6_2: X_A6_2 = 0
Terminal_Constraint:A6_3: X_A6_3 = 0
Terminal_Constraint:A7_1: X_A7_1 = 0
Terminal_Constraint:A7_2: X_A7_2 = 0
Terminal_Constraint:A7_3: X_A7_3 = 0
Terminal_Constraint:A8_1: X_A8_1 = 0
Terminal_Constraint:A8_2: X_A8_2 = 0
Terminal_Constraint:A8_3: X_A8_3 = 0
Terminal_Constraint:A9_1: X_A9_1 = 0
Terminal_Constraint:A9_2: X_A9_2 = 0
Terminal_Constraint:A9_3: X_A9_3 = 0
TimeSlot_Constraint:B1_1_2: X_B1_1 + X_B1_2 <= 1
TimeSlot_Constraint:B1_1_3: X_B1_1 + X_B1_3 <= 1
TimeSlot_Constraint:B1_2_3: X_B1_2 + X_B1_3 <= 1
TimeSlot_Constraint:B2_1_2: X_B2_1 + X_B2_2 <= 1
TimeSlot_Constraint:B2_1_3: X_B2_1 + X_B2_3 <= 1
TimeSlot_Constraint:B2_2_3: X_B2_2 + X_B2_3 <= 1
Binaries
X_A10_1
X_A10_2
X_A10_3
X_A1_1
X_A1_2
X_A1_3
X_A2_1
X_A2_2
X_A2_3
X_A3_1
X_A3_2
X_A3_3
X_A4_1
X_A4_2
X_A4_3
X_A5_1
X_A5_2
X_A5_3
X_A6_1
X_A6_2
X_A6_3
X_A7_1
X_A7_2
X_A7_3
X_A8_1
X_A8_2
X_A8_3
X_A9_1
X_A9_2
X_A9_3
X_B1_1
X_B1_2
X_B1_3
X_B2_1
X_B2_2
X_B2_3
X_B3_1
X_B3_2
X_B3_3
X_B4_1
X_B4_2
X_B4_3
X_B5_1
X_B5_2
X_B5_3
End
