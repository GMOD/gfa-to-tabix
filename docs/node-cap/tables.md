Node counts where the median time to paint passes 1, 5 and 30 s (an estimate between the two windows that
straddle it, or the windows when one of them did not draw), and the first window that drew nothing

| layout | reader | 1 s chr22 | 1 s MHC | 5 s chr22 | 5 s MHC | 30 s chr22 | 30 s MHC | fails chr22 | fails MHC |
|---|---|---|---|---|---|---|---|---|---|
| FMMM | BandageJS | ~11,000 | ~6,300 | ~65,000 | ~30,000 | ~257,000 | ~107,000 | 1,199,754, aborts | 973,240, aborts |
| FMMM | plugin | ~10,000 | ~6,100 | ~57,000 | ~29,000 | ~236,000 | ~105,000 | 1,199,754, aborts | 973,240, aborts |
| stress | BandageJS | ~11,000 | ~7,400 | ~37,000 | ~21,000 | ~112,000 | 36,182-157,896 | 1,199,754, nothing in 300 s | 157,896, nothing in 300 s |
| stress | plugin | ~9,600 | ~6,300 | ~37,000 | ~21,000 | ~108,000 | 36,182-157,896 | 1,199,754, nothing in 300 s | 157,896, nothing in 300 s |
| tube map | BandageJS | ~24,000 | ~16,000 | ~68,000 | ~41,000 | ~158,000 | ~101,000 | 1,199,754, crashes | 277,560, crashes |
| tube map | plugin | ~26,000 | ~16,000 | ~71,000 | ~41,000 | ~150,000 | ~96,000 | 1,199,754, crashes | 277,560, crashes |
| ordered | BandageJS | ~14,000 | ~10,000 | ~50,000 | ~30,000 | ~127,000 | ~88,000 | 1,199,754, nothing in 300 s | 277,560, nothing in 300 s |
| ordered | plugin | ~12,000 | ~10,000 | ~60,000 | ~25,000 | 106,634-321,044 | ~76,000 | 321,044, view fails | 277,560, view fails |
| walk rows | BandageJS | ~71,000 | ~70,000 | ~307,000 | ~310,000 | ~1,199,000 | never | none | none |
| walk rows | plugin | ~145,000 | ~140,000 | ~515,000 | ~709,000 | never | never | none | none |

The windows (node counts) on either side of each crossing

| layout | reader | | 1 s | 5 s | 30 s |
|---|---|---|---|---|---|
| FMMM | BandageJS | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| FMMM | BandageJS | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| FMMM | plugin | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| FMMM | plugin | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| stress | BandageJS | chr22 | 8,656-29,912 | 29,912-54,096 | 106,634-321,044 |
| stress | BandageJS | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| stress | plugin | chr22 | 8,656-29,912 | 29,912-54,096 | 106,634-321,044 |
| stress | plugin | MHC | 5,095-8,451 | 8,451-36,182 | 36,182-157,896 |
| tube map | BandageJS | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| tube map | BandageJS | MHC | 8,451-36,182 | 36,182-157,896 | 36,182-157,896 |
| tube map | plugin | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| tube map | plugin | MHC | 8,451-36,182 | 36,182-157,896 | 36,182-157,896 |
| ordered | BandageJS | chr22 | 8,656-29,912 | 29,912-54,096 | 106,634-321,044 |
| ordered | BandageJS | MHC | 8,451-36,182 | 8,451-36,182 | 36,182-157,896 |
| ordered | plugin | chr22 | 8,656-29,912 | 54,096-106,634 | 106,634-321,044 |
| ordered | plugin | MHC | 8,451-36,182 | 8,451-36,182 | 36,182-157,896 |
| walk rows | BandageJS | chr22 | 54,096-106,634 | 106,634-321,044 | 321,044-1,199,754 |
| walk rows | BandageJS | MHC | 36,182-157,896 | 277,560-973,240 | never |
| walk rows | plugin | chr22 | 106,634-321,044 | 321,044-1,199,754 | never |
| walk rows | plugin | MHC | 36,182-157,896 | 277,560-973,240 | never |

Time to paint, median (B BandageJS, P the plugin)

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 199 ms | 369 ms | 176 ms | 383 ms | 54 ms | 273 ms | 134 ms | 355 ms | 75 ms | 318 ms |
| chr22 220 kb | 5,143 | 516 ms | 540 ms | 477 ms | 602 ms | 158 ms | 276 ms | 332 ms | 605 ms | 147 ms | 301 ms |
| chr22 370 kb | 8,656 | 787 ms | 847 ms | 699 ms | 887 ms | 232 ms | 258 ms | 529 ms | 758 ms | 219 ms | 278 ms |
| chr22 1.1 Mb | 29,912 | 2.7 s | 3.0 s | 3.5 s | 3.8 s | 1.4 s | 1.2 s | 2.6 s | 2.0 s | 471 ms | 298 ms |
| chr22 2 Mb | 54,096 | 4.0 s | 4.6 s | 9.2 s | 8.2 s | 3.2 s | 3.0 s | 5.6 s | 4.2 s | 785 ms | 425 ms |
| chr22 3.6 Mb | 106,634 | 9.6 s | 11.0 s | 27.5 s | 29.5 s | 12.5 s | 10.9 s | 21.2 s | 13.9 s | 1.5 s | 711 ms |
| chr22 10 Mb | 321,044 | 40.1 s | 44.1 s | 228.7 s | 244.5 s | 142.5 s | 275.7 s | 195.5 s | fails | 5.3 s | 2.4 s |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 30.0 s | 18.8 s |
| chr6 17 kb | 1,084 | 295 ms | 384 ms | 210 ms | 391 ms | 66 ms | 295 ms | 156 ms | 358 ms | 69 ms | 281 ms |
| chr6 90 kb | 5,095 | 834 ms | 849 ms | 687 ms | 861 ms | 220 ms | 258 ms | 418 ms | 547 ms | 143 ms | 287 ms |
| chr6 150 kb | 8,451 | 1.3 s | 1.4 s | 1.1 s | 1.2 s | 370 ms | 335 ms | 734 ms | 697 ms | 201 ms | 286 ms |
| chr6 400 kb | 36,182 | 6.2 s | 6.4 s | 12.0 s | 11.8 s | 3.8 s | 3.8 s | 6.6 s | 9.8 s | 537 ms | 358 ms |
| chr6 1.8 Mb | 157,896 | 52.9 s | 54.4 s | > 300 s | > 300 s | 73.3 s | 84.3 s | 81.9 s | 90.6 s | 2.1 s | 1.1 s |
| chr6 5.5 Mb | 277,560 | 84.2 s | 73.9 s |  |  | crash | crash | > 300 s | fails | 4.4 s | 2.0 s |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 20.6 s | 6.8 s |

Longest main-thread task before the paint, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 83 ms | 114 ms | 89 ms | 114 ms | 63 ms | 0 ms | 119 ms | 94 ms | 78 ms | 53 ms |
| chr22 220 kb | 5,143 | 199 ms | 234 ms | 278 ms | 328 ms | 168 ms | 104 ms | 320 ms | 226 ms | 170 ms | 68 ms |
| chr22 370 kb | 8,656 | 254 ms | 349 ms | 438 ms | 515 ms | 263 ms | 175 ms | 509 ms | 343 ms | 251 ms | 91 ms |
| chr22 1.1 Mb | 29,912 | 772 ms | 1.1 s | 2.7 s | 3.1 s | 1.5 s | 1.1 s | 2.6 s | 1.7 s | 581 ms | 145 ms |
| chr22 2 Mb | 54,096 | 1.3 s | 2.1 s | 7.9 s | 7.0 s | 3.3 s | 2.9 s | 5.7 s | 3.5 s | 968 ms | 403 ms |
| chr22 3.6 Mb | 106,634 | 3.0 s | 4.3 s | 25.0 s | 27.0 s | 12.9 s | 10.9 s | 21.4 s | 13.8 s | 1.8 s | 691 ms |
| chr22 10 Mb | 321,044 | 11.1 s | 15.8 s | 217.5 s | 235.2 s | 143.2 s | 145.8 s | 194.8 s | fails | 5.9 s | 2.4 s |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 34.0 s | 18.9 s |
| chr6 17 kb | 1,084 | 114 ms | 131 ms | 120 ms | 122 ms | 74 ms | 0 ms | 140 ms | 107 ms | 81 ms | 58 ms |
| chr6 90 kb | 5,095 | 234 ms | 295 ms | 428 ms | 514 ms | 235 ms | 132 ms | 402 ms | 272 ms | 167 ms | 75 ms |
| chr6 150 kb | 8,451 | 319 ms | 442 ms | 803 ms | 935 ms | 397 ms | 239 ms | 709 ms | 450 ms | 239 ms | 90 ms |
| chr6 400 kb | 36,182 | 1.2 s | 1.5 s | 10.7 s | 10.7 s | 3.9 s | 1.8 s | 6.6 s | 5.7 s | 625 ms | 192 ms |
| chr6 1.8 Mb | 157,896 | 10.6 s | 18.1 s | > 300 s | > 300 s | 73.7 s | 44.4 s | 81.1 s | 90.4 s | 2.5 s | 1.1 s |
| chr6 5.5 Mb | 277,560 | 14.2 s | 20.5 s |  |  | crash | crash | > 300 s | fails | 5.0 s | 2.0 s |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 23.6 s | 6.8 s |

A wheel zoom to its next painted frame, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 56 ms | 55 ms | 59 ms | 53 ms | 40 ms | 52 ms | 63 ms | 52 ms | 45 ms | 48 ms |
| chr22 220 kb | 5,143 | 73 ms | 180 ms | 77 ms | 199 ms | 52 ms | 44 ms | 79 ms | 203 ms | 50 ms | 52 ms |
| chr22 370 kb | 8,656 | 79 ms | 209 ms | 81 ms | 208 ms | 53 ms | 32 ms | 71 ms | 200 ms | 42 ms | 54 ms |
| chr22 1.1 Mb | 29,912 | 146 ms | 655 ms | 155 ms | 468 ms | 167 ms | 31 ms | 1.4 s | 429 ms | 82 ms | 66 ms |
| chr22 2 Mb | 54,096 | 653 ms | 556 ms | 2.2 s | 679 ms | 230 ms | 21 ms | 2.4 s | 627 ms | 114 ms | 149 ms |
| chr22 3.6 Mb | 106,634 | 1.3 s | 1.3 s | 8.9 s | 1.4 s | 929 ms | 52 ms | 9.4 s | 36 ms | 298 ms | 31 ms |
| chr22 10 Mb | 321,044 | 5.2 s | 3.7 s | 79.9 s | 4.1 s | 8.9 s | 201 ms | 102.8 s | fails | 836 ms | 42 ms |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 3.6 s | 747 ms |
| chr6 17 kb | 1,084 | 61 ms | 50 ms | 55 ms | 84 ms | 41 ms | 50 ms | 62 ms | 69 ms | 43 ms | 44 ms |
| chr6 90 kb | 5,095 | 80 ms | 191 ms | 100 ms | 199 ms | 62 ms | 50 ms | 80 ms | 207 ms | 47 ms | 52 ms |
| chr6 150 kb | 8,451 | 86 ms | 252 ms | 115 ms | 250 ms | 79 ms | 47 ms | 108 ms | 231 ms | 55 ms | 53 ms |
| chr6 400 kb | 36,182 | dies | 617 ms | 3.4 s | 824 ms | 912 ms | 51 ms | 3.5 s | 745 ms | 83 ms | 76 ms |
| chr6 1.8 Mb | 157,896 | dies | 10.5 s | > 300 s | > 300 s | 16.3 s | 170 ms | 43.1 s | 2.9 s | 379 ms | 26 ms |
| chr6 5.5 Mb | 277,560 | dies | 11.4 s |  |  | crash | crash | > 300 s | fails | 800 ms | 43 ms |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 2.8 s | 52 ms |

A 60 px drag to its next painted frame, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 66 ms | 40 ms | 52 ms | 39 ms | 45 ms | 47 ms | 67 ms | 38 ms | 43 ms | 45 ms |
| chr22 220 kb | 5,143 | 55 ms | 52 ms | 77 ms | 52 ms | 40 ms | 47 ms | 76 ms | 56 ms | 39 ms | 46 ms |
| chr22 370 kb | 8,656 | 72 ms | 57 ms | 71 ms | 91 ms | 35 ms | 46 ms | 75 ms | 99 ms | 36 ms | 44 ms |
| chr22 1.1 Mb | 29,912 | 126 ms | 106 ms | 144 ms | 128 ms | 131 ms | 45 ms | 166 ms | 136 ms | 60 ms | 44 ms |
| chr22 2 Mb | 54,096 | 197 ms | 151 ms | 210 ms | 196 ms | 209 ms | 44 ms | 207 ms | 320 ms | 91 ms | 44 ms |
| chr22 3.6 Mb | 106,634 | 301 ms | 334 ms | 795 ms | 363 ms | 811 ms | 41 ms | 346 ms | 326 ms | 151 ms | 43 ms |
| chr22 10 Mb | 321,044 | 2.2 s | 954 ms | 2.2 s | 1.0 s | 7.7 s | 58 ms | 1.9 s | fails | 353 ms | 39 ms |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 1.3 s | 98 ms |
| chr6 17 kb | 1,084 | 61 ms | 40 ms | 56 ms | 39 ms | 44 ms | 47 ms | 61 ms | 39 ms | 43 ms | 46 ms |
| chr6 90 kb | 5,095 | 100 ms | 98 ms | 111 ms | 93 ms | 56 ms | 46 ms | 75 ms | 88 ms | 41 ms | 44 ms |
| chr6 150 kb | 8,451 | 83 ms | 107 ms | 94 ms | 96 ms | 72 ms | 46 ms | 94 ms | 99 ms | 38 ms | 45 ms |
| chr6 400 kb | 36,182 | dies | 165 ms | 269 ms | 239 ms | 705 ms | 43 ms | 319 ms | 244 ms | 58 ms | 43 ms |
| chr6 1.8 Mb | 157,896 | dies | 12.2 s | > 300 s | > 300 s | 14.4 s | 54 ms | 2.8 s | 1.1 s | 172 ms | 42 ms |
| chr6 5.5 Mb | 277,560 | dies | 2.7 s |  |  | crash | crash | > 300 s | fails | 322 ms | 37 ms |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 1.1 s | 59 ms |

Renderer peak resident MB, median

| window | nodes | FMMM B | FMMM P | stress B | stress P | tube map B | tube map P | ordered B | ordered P | walk rows B | walk rows P |
|---|---|---|---|---|---|---|---|---|---|---|---|
| chr22 37 kb | 971 | 278 | 337 | 274 | 340 | 238 | 281 | 261 | 317 | 239 | 286 |
| chr22 220 kb | 5,143 | 392 | 454 | 403 | 441 | 288 | 333 | 326 | 405 | 314 | 326 |
| chr22 370 kb | 8,656 | 446 | 497 | 455 | 515 | 315 | 366 | 355 | 407 | 329 | 341 |
| chr22 1.1 Mb | 29,912 | 659 | 822 | 683 | 785 | 618 | 604 | 457 | 615 | 435 | 433 |
| chr22 2 Mb | 54,096 | 1,020 | 1,182 | 969 | 1,151 | 642 | 734 | 603 | 752 | 481 | 518 |
| chr22 3.6 Mb | 106,634 | 1,513 | 1,938 | 1,438 | 1,590 | 1,674 | 757 | 846 | 1,054 | 589 | 689 |
| chr22 10 Mb | 321,044 | 3,638 | 3,574 | 2,725 | 3,108 | 988 | 5,186 | 2,038 | fails | 1,385 | 1,226 |
| chr22 32 Mb | 1,199,754 | aborts | aborts | > 300 s | > 300 s | crash | crash | > 300 s |  | 3,288 | 3,766 |
| chr6 17 kb | 1,084 | 310 | 347 | 300 | 351 | 249 | 287 | 265 | 327 | 246 | 288 |
| chr6 90 kb | 5,095 | 452 | 479 | 458 | 474 | 312 | 341 | 331 | 400 | 317 | 332 |
| chr6 150 kb | 8,451 | 463 | 576 | 476 | 598 | 381 | 415 | 398 | 451 | 337 | 346 |
| chr6 400 kb | 36,182 | 804 | 1,076 | 997 | 1,052 | 563 | 1,158 | 736 | 847 | 433 | 494 |
| chr6 1.8 Mb | 157,896 | 2,319 | 2,964 | > 300 s | > 300 s | 1,037 | 4,107 | 1,736 | 2,193 | 737 | 864 |
| chr6 5.5 Mb | 277,560 | 3,261 | 3,891 |  |  | crash | crash | > 300 s | fails | 1,262 | 1,187 |
| chr6 30 Mb | 973,240 | aborts | aborts |  |  |  |  |  |  | 3,115 | 3,211 |

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
