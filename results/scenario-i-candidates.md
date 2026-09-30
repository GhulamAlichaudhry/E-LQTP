# Step 25: is N_range / N_depth still binding at sink z_ac=50.000 m?

Same 15 Step-22 placements. Directed pairs from each AUV. I = N_range ∩ N_SNR ∩ N_depth. D = N_range ∩ N_SNR (RLOR's I). r_range from the January 50 m crossing.

| N | seed | r_range | AUV-AUV |D|/pairs | |I|/pairs | N_depth drop | AUV-all |I| mean | |D| mean | I={sink} only | has AUV in I |
|---|------|---------|----------------|-----------|--------------|--------------|---------|---------------|---------------|
| 20 | 20260921 | 5125 | 0.853 | 0.426 | 0.500 | 9.100 | 17.200 | 1/20 | 19/20 |
| 20 | 20260922 | 5125 | 0.858 | 0.429 | 0.500 | 9.150 | 17.300 | 1/20 | 19/20 |
| 20 | 20260923 | 5125 | 0.858 | 0.429 | 0.500 | 9.150 | 17.300 | 1/20 | 19/20 |
| 20 | 20260924 | 5125 | 0.926 | 0.463 | 0.500 | 9.800 | 18.600 | 1/20 | 19/20 |
| 20 | 20260925 | 5125 | 0.968 | 0.484 | 0.500 | 10.200 | 19.400 | 1/20 | 19/20 |
| 40 | 20260921 | 5125 | 0.878 | 0.438 | 0.501 | 18.075 | 35.250 | 1/40 | 39/40 |
| 40 | 20260922 | 5125 | 0.904 | 0.452 | 0.500 | 18.625 | 36.250 | 1/40 | 39/40 |
| 40 | 20260923 | 5125 | 0.879 | 0.440 | 0.500 | 18.150 | 35.300 | 2/40 | 38/40 |
| 40 | 20260924 | 5125 | 0.939 | 0.469 | 0.500 | 19.300 | 37.625 | 1/40 | 39/40 |
| 40 | 20260925 | 5125 | 0.958 | 0.479 | 0.500 | 19.675 | 38.350 | 1/40 | 39/40 |
| 60 | 20260921 | 5125 | 0.881 | 0.440 | 0.501 | 26.967 | 53.000 | 1/60 | 59/60 |
| 60 | 20260922 | 5125 | 0.910 | 0.455 | 0.500 | 27.833 | 54.667 | 1/60 | 59/60 |
| 60 | 20260923 | 5125 | 0.888 | 0.444 | 0.500 | 27.200 | 53.400 | 2/60 | 58/60 |
| 60 | 20260924 | 5125 | 0.946 | 0.473 | 0.500 | 28.900 | 56.800 | 1/60 | 59/60 |
| 60 | 20260925 | 5125 | 0.925 | 0.462 | 0.500 | 28.283 | 55.600 | 1/60 | 59/60 |

Per-N means (5 seeds):

| N | AUV-AUV |D| frac | |I| frac | N_depth drop of D | N_range fail frac | I={sink} only | has AUV in I |
|---|----------------|---------|-------------------|-------------------|---------------|---------------|
| 20 | 0.893 | 0.446 | 0.500 | 0.106 | 0.050 | 0.950 |
| 40 | 0.912 | 0.456 | 0.500 | 0.087 | 0.030 | 0.970 |
| 60 | 0.910 | 0.455 | 0.500 | 0.089 | 0.020 | 0.980 |

N_depth drop = 1 - |I_AUV-AUV| / |D_AUV-AUV|: fraction of range∩SNR AUV-AUV pairs that N_depth removes (shallower-only). A value near 0.5 is the random-depth expectation and means N_depth is still doing real work. I={sink} only is the fraction of AUVs whose candidate set is exactly the sink — true single-hop-only sources. has AUV in I is the fraction with at least one AUV (not just the sink) in I, i.e. a multi-hop option.
