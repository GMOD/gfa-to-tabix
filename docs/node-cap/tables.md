Time to paint, median (B BandageJS, P the plugin)

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 199 ms | 369 ms | 176 ms | 383 ms | 54 ms | 273 ms | 134 ms | 355 ms |  |  |
| chr22 220 kb | 5,143 | 516 ms | 540 ms | 477 ms | 602 ms | 158 ms | 276 ms | 332 ms | 605 ms |  |  |
| chr22 370 kb | 8,656 | 787 ms | 847 ms | 699 ms | 887 ms | 232 ms | 258 ms | 529 ms | 758 ms |  |  |
| chr22 1.1 Mb | 29,912 | 2.7 s | 3.0 s | 3.5 s | 3.8 s | 1.4 s | 1.2 s | 2.6 s | 2.0 s |  |  |
| chr22 2 Mb | 54,096 | 4.0 s | 4.6 s | 9.2 s | 8.2 s | 3.2 s | 3.0 s | 5.6 s | 4.2 s |  |  |
| chr22 3.6 Mb | 106,634 | 9.6 s | 11.0 s | 27.5 s | 29.5 s | 12.5 s | 10.9 s | 21.2 s | 13.9 s |  |  |
| chr22 10 Mb | 321,044 | 40.1 s | 44.1 s | 228.7 s | 244.5 s | 142.5 s | 139.3 s | 195.5 s | fails |  |  |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  |  |  |
| chr6 17 kb | 1,084 | 295 ms | 384 ms | 210 ms | 391 ms | 66 ms | 295 ms | 156 ms | 358 ms |  |  |
| chr6 90 kb | 5,095 | 834 ms | 849 ms | 687 ms | 861 ms | 220 ms | 258 ms | 418 ms | 547 ms |  |  |
| chr6 150 kb | 8,451 | 1.3 s | 1.4 s | 1.1 s | 1.2 s | 370 ms | 335 ms | 734 ms | 697 ms |  |  |
| chr6 400 kb | 36,182 | 6.1 s | 6.4 s | 12.0 s | 11.8 s | 3.8 s | 3.8 s | 6.6 s | 9.8 s |  |  |
| chr6 1.8 Mb | 157,896 | 52.2 s | 54.4 s | > 300 s | > 300 s | 73.3 s | 84.3 s | 81.9 s | 90.5 s |  |  |
| chr6 5.5 Mb | 277,560 | 72.0 s | 73.9 s |  |  | crash | crash |  |  |  |  |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  |  |  |

Longest main-thread task before the paint, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 83 ms | 114 ms | 89 ms | 114 ms | 63 ms | 0 ms | 119 ms | 94 ms |  |  |
| chr22 220 kb | 5,143 | 199 ms | 234 ms | 278 ms | 328 ms | 168 ms | 104 ms | 320 ms | 226 ms |  |  |
| chr22 370 kb | 8,656 | 254 ms | 349 ms | 438 ms | 515 ms | 263 ms | 175 ms | 509 ms | 343 ms |  |  |
| chr22 1.1 Mb | 29,912 | 772 ms | 1.1 s | 2.7 s | 3.1 s | 1.5 s | 1.1 s | 2.6 s | 1.7 s |  |  |
| chr22 2 Mb | 54,096 | 1.3 s | 2.1 s | 7.9 s | 7.0 s | 3.3 s | 2.9 s | 5.7 s | 3.5 s |  |  |
| chr22 3.6 Mb | 106,634 | 3.0 s | 4.3 s | 25.0 s | 27.0 s | 12.9 s | 10.9 s | 21.4 s | 13.8 s |  |  |
| chr22 10 Mb | 321,044 | 11.1 s | 15.8 s | 217.5 s | 235.2 s | 143.2 s | 139.2 s | 194.8 s | fails |  |  |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  |  |  |
| chr6 17 kb | 1,084 | 114 ms | 131 ms | 120 ms | 122 ms | 74 ms | 0 ms | 140 ms | 107 ms |  |  |
| chr6 90 kb | 5,095 | 234 ms | 295 ms | 428 ms | 514 ms | 235 ms | 132 ms | 402 ms | 272 ms |  |  |
| chr6 150 kb | 8,451 | 319 ms | 442 ms | 803 ms | 935 ms | 397 ms | 239 ms | 709 ms | 450 ms |  |  |
| chr6 400 kb | 36,182 | 1.2 s | 1.5 s | 10.7 s | 10.7 s | 3.9 s | 1.8 s | 6.6 s | 5.7 s |  |  |
| chr6 1.8 Mb | 157,896 | 10.5 s | 18.1 s | > 300 s | > 300 s | 73.7 s | 44.4 s | 81.1 s | 90.2 s |  |  |
| chr6 5.5 Mb | 277,560 | 13.3 s | 20.5 s |  |  | crash | crash |  |  |  |  |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  |  |  |

A wheel zoom to its next painted frame, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 56 ms | 55 ms | 59 ms | 53 ms | 40 ms | 52 ms | 63 ms | 52 ms |  |  |
| chr22 220 kb | 5,143 | 73 ms | 180 ms | 77 ms | 199 ms | 52 ms | 44 ms | 79 ms | 203 ms |  |  |
| chr22 370 kb | 8,656 | 79 ms | 209 ms | 81 ms | 208 ms | 53 ms | 32 ms | 71 ms | 200 ms |  |  |
| chr22 1.1 Mb | 29,912 | 146 ms | 655 ms | 155 ms | 468 ms | 167 ms | 31 ms | 1.4 s | 429 ms |  |  |
| chr22 2 Mb | 54,096 | 653 ms | 556 ms | 2.2 s | 679 ms | 230 ms | 21 ms | 2.4 s | 627 ms |  |  |
| chr22 3.6 Mb | 106,634 | 1.3 s | 1.3 s | 8.9 s | 1.4 s | 929 ms | 52 ms | 9.4 s | 36 ms |  |  |
| chr22 10 Mb | 321,044 | 5.2 s | 3.7 s | 79.9 s | 4.1 s | 8.9 s | 205 ms | 102.8 s | fails |  |  |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  |  |  |
| chr6 17 kb | 1,084 | 61 ms | 50 ms | 55 ms | 84 ms | 41 ms | 50 ms | 62 ms | 69 ms |  |  |
| chr6 90 kb | 5,095 | 80 ms | 191 ms | 100 ms | 199 ms | 62 ms | 50 ms | 80 ms | 207 ms |  |  |
| chr6 150 kb | 8,451 | 86 ms | 252 ms | 115 ms | 250 ms | 79 ms | 47 ms | 108 ms | 231 ms |  |  |
| chr6 400 kb | 36,182 | dies | 617 ms | 3.4 s | 824 ms | 912 ms | 51 ms | 3.5 s | 745 ms |  |  |
| chr6 1.8 Mb | 157,896 | dies | 10.5 s | > 300 s | > 300 s | 16.3 s | 170 ms | 43.1 s | 1.5 s |  |  |
| chr6 5.5 Mb | 277,560 | dies | 11.4 s |  |  | crash | crash |  |  |  |  |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  |  |  |

A 60 px drag to its next painted frame, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 66 ms | 40 ms | 52 ms | 39 ms | 45 ms | 47 ms | 67 ms | 38 ms |  |  |
| chr22 220 kb | 5,143 | 55 ms | 52 ms | 77 ms | 52 ms | 40 ms | 47 ms | 76 ms | 56 ms |  |  |
| chr22 370 kb | 8,656 | 72 ms | 57 ms | 71 ms | 91 ms | 35 ms | 46 ms | 75 ms | 99 ms |  |  |
| chr22 1.1 Mb | 29,912 | 126 ms | 106 ms | 144 ms | 128 ms | 131 ms | 45 ms | 166 ms | 136 ms |  |  |
| chr22 2 Mb | 54,096 | 197 ms | 151 ms | 210 ms | 196 ms | 209 ms | 44 ms | 207 ms | 320 ms |  |  |
| chr22 3.6 Mb | 106,634 | 301 ms | 334 ms | 795 ms | 363 ms | 811 ms | 41 ms | 346 ms | 326 ms |  |  |
| chr22 10 Mb | 321,044 | 2.2 s | 954 ms | 2.2 s | 1.0 s | 7.7 s | 57 ms | 1.9 s | fails |  |  |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  |  |  |
| chr6 17 kb | 1,084 | 61 ms | 40 ms | 56 ms | 39 ms | 44 ms | 47 ms | 61 ms | 39 ms |  |  |
| chr6 90 kb | 5,095 | 100 ms | 98 ms | 111 ms | 93 ms | 56 ms | 46 ms | 75 ms | 88 ms |  |  |
| chr6 150 kb | 8,451 | 83 ms | 107 ms | 94 ms | 96 ms | 72 ms | 46 ms | 94 ms | 99 ms |  |  |
| chr6 400 kb | 36,182 | dies | 165 ms | 269 ms | 239 ms | 705 ms | 43 ms | 319 ms | 244 ms |  |  |
| chr6 1.8 Mb | 157,896 | dies | 12.2 s | > 300 s | > 300 s | 14.4 s | 54 ms | 2.8 s | 1.2 s |  |  |
| chr6 5.5 Mb | 277,560 | dies | 2.7 s |  |  | crash | crash |  |  |  |  |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  |  |  |

Renderer peak resident MB, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 278 | 337 | 274 | 340 | 238 | 281 | 261 | 317 |  |  |
| chr22 220 kb | 5,143 | 392 | 454 | 403 | 441 | 288 | 333 | 326 | 405 |  |  |
| chr22 370 kb | 8,656 | 446 | 497 | 455 | 515 | 315 | 366 | 355 | 407 |  |  |
| chr22 1.1 Mb | 29,912 | 659 | 822 | 683 | 785 | 618 | 604 | 457 | 615 |  |  |
| chr22 2 Mb | 54,096 | 1,020 | 1,182 | 969 | 1,151 | 642 | 734 | 603 | 752 |  |  |
| chr22 3.6 Mb | 106,634 | 1,513 | 1,938 | 1,438 | 1,590 | 1,674 | 757 | 846 | 1,054 |  |  |
| chr22 10 Mb | 321,044 | 3,638 | 3,574 | 2,725 | 3,108 | 988 | 5,186 | 2,038 | fails |  |  |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  |  |  |
| chr6 17 kb | 1,084 | 310 | 347 | 300 | 351 | 249 | 287 | 265 | 327 |  |  |
| chr6 90 kb | 5,095 | 452 | 479 | 458 | 474 | 312 | 341 | 331 | 400 |  |  |
| chr6 150 kb | 8,451 | 463 | 576 | 476 | 598 | 381 | 415 | 398 | 451 |  |  |
| chr6 400 kb | 36,182 | dies | 1,076 | 997 | 1,052 | 563 | 1,158 | 736 | 847 |  |  |
| chr6 1.8 Mb | 157,896 | dies | 2,964 | > 300 s | > 300 s | 1,037 | 4,107 | 1,736 | 2,179 |  |  |
| chr6 5.5 Mb | 277,560 | dies | 3,891 |  |  | crash | crash |  |  |  |  |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  |  |  |

Windows: graph-walks 9.0.0's cut in Node, median

| window | reference bp | nodes | of them placeholders | links | steps | cut |
|---|---|---|---|---|---|---|
| chr22 37 kb | 30,000,001-30,037,000 | 971 | 0 | 1,027 | 4,594 | 10 ms |
| chr22 220 kb | 30,000,001-30,220,000 | 5,143 | 0 | 5,529 | 23,853 | 26 ms |
| chr22 370 kb | 30,000,001-30,370,000 | 8,656 | 0 | 9,325 | 40,051 | 32 ms |
| chr22 1.1 Mb | 30,000,001-31,100,000 | 29,912 | 0 | 32,653 | 135,992 | 101 ms |
| chr22 2 Mb | 30,000,001-32,000,000 | 54,096 | 0 | 57,855 | 251,824 | 164 ms |
| chr22 3.6 Mb | 30,000,001-33,600,000 | 106,634 | 0 | 115,197 | 490,414 | 375 ms |
| chr22 10 Mb | 30,000,001-40,000,000 | 321,044 | 317 | 348,617 | 1,456,828 | 1.4 s |
| chr22 32 Mb | 18,000,001-50,000,000 | 1,199,754 | 709 | 1,305,240 | 5,180,750 | 7.0 s |
| chr6 17 kb | 31,000,001-31,017,000 | 1,084 | 0 | 1,245 | 4,637 | 12 ms |
| chr6 90 kb | 31,000,001-31,090,000 | 5,095 | 0 | 5,935 | 21,068 | 24 ms |
| chr6 150 kb | 31,000,001-31,150,000 | 8,451 | 0 | 9,887 | 35,015 | 36 ms |
| chr6 400 kb | 31,000,001-31,400,000 | 36,182 | 2,438 | 44,213 | 139,224 | 136 ms |
| chr6 1.8 Mb | 31,000,001-32,800,000 | 157,896 | 19,364 | 198,574 | 548,007 | 598 ms |
| chr6 5.5 Mb | 31,000,001-36,500,000 | 277,560 | 19,364 | 329,867 | 1,086,121 | 1.1 s |
| chr6 30 Mb | 31,000,001-61,000,000 | 973,240 | 19,364 | 1,087,084 | 4,235,119 | 5.7 s |
