# Step 56: RLOR one-hop confirmation (not a new experiment)

seed=20260921 N=40 v=2.000000e+00 m/s azimuth=5.968155e+00 rad sink_ac_z=5.000000e+01 m. I_RLOR = N_range ∩ N_SNR. NextHop = argmax P_succ, ties → smallest id (sink is 0).

## t=0.000000e+00 s  (displacement=0.000000e+00 m)
id |I| nextHop P_succ(sink) SNR(sink) bestAUV P_succ(AUV) SNR(AUV)
  1 |39| nh=0 P_sink=9.999996e-01 SNR_sink=4.627770e+01 alt=2 P_alt=9.999996e-01 SNR_alt=2.967982e+01
  2 |40| nh=0 P_sink=9.999996e-01 SNR_sink=4.531806e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.889618e+01
  3 |31| nh=0 P_sink=9.999996e-01 SNR_sink=2.877980e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.074048e+01
  4 |33| nh=0 P_sink=9.999996e-01 SNR_sink=2.918514e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.952742e+01
  5 |36| nh=0 P_sink=9.999996e-01 SNR_sink=3.205703e+01 alt=1 P_alt=9.999996e-01 SNR_alt=4.183912e+01
  6 |31| nh=0 P_sink=9.999996e-01 SNR_sink=1.986016e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.372719e+01
  7 |38| nh=0 P_sink=9.999996e-01 SNR_sink=3.459569e+01 alt=1 P_alt=9.999996e-01 SNR_alt=3.669016e+01
  8 |39| nh=0 P_sink=9.999996e-01 SNR_sink=3.953362e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.909844e+01
  40 |38| nh=0 P_sink=9.999996e-01 SNR_sink=4.049284e+01 alt=1 P_alt=9.999996e-01 SNR_alt=3.493063e+01
  sink_in_I=40/40 empty_I=0 nextHop_sink=40 nextHop_AUV=0 nextHop_none=0 has_AUV_alt=40
  P_succ(sink)>P_succ(best AUV)=0  P_succ tie=40  of those, SNR_sink>=SNR_alt=23

## t=3.000000e+02 s  (displacement=6.000000e+02 m)
id |I| nextHop P_succ(sink) SNR(sink) bestAUV P_succ(AUV) SNR(AUV)
  1 |39| nh=0 P_sink=9.999996e-01 SNR_sink=4.885577e+01 alt=2 P_alt=9.999996e-01 SNR_alt=2.967982e+01
  2 |40| nh=0 P_sink=9.999996e-01 SNR_sink=3.987407e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.889618e+01
  3 |31| nh=0 P_sink=9.999996e-01 SNR_sink=1.933266e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.074048e+01
  4 |33| nh=0 P_sink=9.999996e-01 SNR_sink=1.937432e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.952742e+01
  5 |36| nh=0 P_sink=9.999996e-01 SNR_sink=3.610516e+01 alt=1 P_alt=9.999996e-01 SNR_alt=4.183912e+01
  6 |31| nh=0 P_sink=9.999996e-01 SNR_sink=1.571493e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.372719e+01
  7 |38| nh=0 P_sink=9.999996e-01 SNR_sink=3.185626e+01 alt=1 P_alt=9.999996e-01 SNR_alt=3.669016e+01
  8 |39| nh=0 P_sink=9.999996e-01 SNR_sink=4.039680e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.909844e+01
  40 |38| nh=0 P_sink=9.999996e-01 SNR_sink=4.665280e+01 alt=1 P_alt=9.999996e-01 SNR_alt=3.493063e+01
  sink_in_I=40/40 empty_I=0 nextHop_sink=40 nextHop_AUV=0 nextHop_none=0 has_AUV_alt=40
  P_succ(sink)>P_succ(best AUV)=0  P_succ tie=40  of those, SNR_sink>=SNR_alt=19

## t=6.000000e+02 s  (displacement=1.200000e+03 m)
id |I| nextHop P_succ(sink) SNR(sink) bestAUV P_succ(AUV) SNR(AUV)
  1 |39| nh=0 P_sink=9.999996e-01 SNR_sink=4.754620e+01 alt=2 P_alt=9.999996e-01 SNR_alt=2.967982e+01
  2 |40| nh=0 P_sink=9.999996e-01 SNR_sink=3.368357e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.889618e+01
  3 |31| nh=0 P_sink=9.999996e-01 SNR_sink=1.743957e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.074048e+01
  4 |33| nh=0 P_sink=9.999996e-01 SNR_sink=1.753827e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.952742e+01
  5 |36| nh=0 P_sink=9.999996e-01 SNR_sink=3.882910e+01 alt=1 P_alt=9.999996e-01 SNR_alt=4.183912e+01
  6 |31| nh=0 P_sink=9.999996e-01 SNR_sink=1.304292e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.372719e+01
  7 |38| nh=0 P_sink=9.999996e-01 SNR_sink=3.055021e+01 alt=1 P_alt=9.999996e-01 SNR_alt=3.669016e+01
  8 |39| nh=0 P_sink=9.999996e-01 SNR_sink=3.930776e+01 alt=1 P_alt=9.999996e-01 SNR_alt=2.909844e+01
  40 |38| nh=0 P_sink=9.999996e-01 SNR_sink=4.972768e+01 alt=1 P_alt=9.999996e-01 SNR_alt=3.493063e+01
  sink_in_I=39/40 empty_I=0 nextHop_sink=39 nextHop_AUV=1 nextHop_none=0 has_AUV_alt=40
  P_succ(sink)>P_succ(best AUV)=0  P_succ tie=39  of those, SNR_sink>=SNR_alt=16

