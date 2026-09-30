# Step 59: Scenario III radial vs tangential v_rel (kinematics only)

seed=20260921 N=40 T=1.200000e+02 s dt=1 V_eddy=2.000000e+00 R_core=2.000000e+03 zeta=0.95 sigma_z=0 (permanent, SPEC Part 9)
eddy centre=(3.000000e+03,3.000000e+03) CCW Rankine-capped. Sink fixed. v_cmd=0.
placement t=0: n_core(r<R)=13 n_outer(r>=R)=27 / 40

Radial = |(v_b-v_a)·rhat| (range-rate; H_k / SNR observes this).
Tangential = |v_rel - v_radial rhat| (perpendicular; unobservable).
Solid-body core: mean-flow (v_b-v_a) is identically perpendicular to r_ij (unit test 22g).

=== PASS A: full Gauss-Markov (sigma_xy=1, sigma_z=0) ===
all AUV-AUV pair-ticks
  |v_rel|           n=94380 mean=2.917097e+00 median=2.825223e+00 p25=1.837163e+00 p75=3.872482e+00 min=6.680685e-03 max=8.894174e+00
  |v_rel_radial|    n=94380 mean=1.058151e+00 median=8.766231e-01 p25=4.085482e-01 p75=1.527013e+00 min=5.272232e-19 max=5.967890e+00
  |v_rel_tangential| n=94380 mean=2.537986e+00 median=2.434566e+00 p25=1.314492e+00 p75=3.592671e+00 min=1.923856e-03 max=8.853825e+00
  frac |v_rad|>0.1=9.373278e-01  >0.5=6.982729e-01  >1.0=4.456982e-01
both-in-core (r_i,r_j < R)
  |v_rel|           n=9438 mean=2.618110e+00 median=2.455404e+00 p25=1.619432e+00 p75=3.482748e+00 min=6.680685e-03 max=7.522502e+00
  |v_rel_radial|    n=9438 mean=9.997377e-01 median=8.004788e-01 p25=3.706615e-01 p75=1.428636e+00 min=5.272232e-19 max=5.967890e+00
  |v_rel_tangential| n=9438 mean=2.252972e+00 median=2.113885e+00 p25=1.174231e+00 p75=3.159041e+00 min=2.345494e-03 max=7.145638e+00
  frac |v_rad|>0.1=9.290104e-01  >0.5=6.738716e-01  >1.0=4.075016e-01
mixed (one in core, one outer)
  |v_rel|           n=42471 mean=2.830083e+00 median=2.739903e+00 p25=1.803653e+00 p75=3.748849e+00 min=3.204681e-02 max=8.623341e+00
  |v_rel_radial|    n=42471 mean=1.094858e+00 median=9.178134e-01 p25=4.275936e-01 p75=1.577147e+00 min=8.318015e-05 max=5.887040e+00
  |v_rel_tangential| n=42471 mean=2.414544e+00 median=2.307477e+00 p25=1.209125e+00 p75=3.438777e+00 min=1.923856e-03 max=8.527593e+00
  frac |v_rad|>0.1=9.400297e-01  >0.5=7.117798e-01  >1.0=4.643639e-01
both-outer (r_i,r_j >= R)
  |v_rel|           n=42471 mean=3.070553e+00 median=3.008017e+00 p25=1.940984e+00 p75=4.055121e+00 min=1.022584e-02 max=8.894174e+00
  |v_rel_radial|    n=42471 mean=1.034424e+00 median=8.531177e-01 p25=3.970172e-01 p75=1.497909e+00 min=1.462810e-05 max=5.251739e+00
  |v_rel_tangential| n=42471 mean=2.724765e+00 median=2.658154e+00 p25=1.471563e+00 p75=3.811318e+00 min=2.923469e-03 max=8.853825e+00
  frac |v_rad|>0.1=9.364743e-01  >0.5=6.901886e-01  >1.0=4.355207e-01

=== PASS B: mean-flow only (sigma=0; Rankine geometry alone) ===
all AUV-AUV pair-ticks
  |v_rel|           n=94380 mean=2.377211e+00 median=2.469243e+00 p25=1.520198e+00 p75=3.320724e+00 min=1.758101e-03 max=3.999710e+00
  |v_rel_radial|    n=94380 mean=2.195621e-01 median=1.701228e-01 p25=6.035751e-02 p75=3.319080e-01 min=5.272232e-19 max=9.929956e-01
  |v_rel_tangential| n=94380 mean=2.349669e+00 median=2.460932e+00 p25=1.479076e+00 p75=3.317654e+00 min=9.827818e-04 max=3.999710e+00
  frac |v_rad|>0.1=6.513456e-01  >0.5=9.277389e-02  >1.0=0.000000e+00
both-in-core (r_i,r_j < R)
  |v_rel|           n=9438 mean=1.931165e+00 median=2.016051e+00 p25=1.198769e+00 p75=2.557349e+00 min=3.216866e-01 max=3.488736e+00
  |v_rel_radial|    n=9438 mean=3.204618e-02 median=3.395127e-02 p25=1.642485e-02 p75=4.560591e-02 min=5.272232e-19 max=6.953965e-02
  |v_rel_tangential| n=9438 mean=1.930877e+00 median=2.015782e+00 p25=1.198556e+00 p75=2.556895e+00 min=3.216774e-01 max=3.488042e+00
  frac |v_rad|>0.1=0.000000e+00  >0.5=0.000000e+00  >1.0=0.000000e+00
mixed (one in core, one outer)
  |v_rel|           n=42471 mean=2.280351e+00 median=2.358930e+00 p25=1.490495e+00 p75=3.047407e+00 min=1.997963e-01 max=3.915779e+00
  |v_rel_radial|    n=42471 mean=2.708262e-01 median=2.480391e-01 p25=1.175490e-01 p75=3.867149e-01 min=1.810028e-05 max=9.760289e-01
  |v_rel_tangential| n=42471 mean=2.247543e+00 median=2.321361e+00 p25=1.418591e+00 p75=3.021018e+00 min=1.563680e-01 max=3.915149e+00
  frac |v_rad|>0.1=7.937181e-01  >0.5=1.131125e-01  >1.0=0.000000e+00
both-outer (r_i,r_j >= R)
  |v_rel|           n=42471 mean=2.573192e+00 median=2.834467e+00 p25=1.641800e+00 p75=3.699133e+00 min=1.758101e-03 max=3.999710e+00
  |v_rel_radial|    n=42471 mean=2.099681e-01 median=1.579158e-01 p25=6.733688e-02 p75=2.978857e-01 min=9.765631e-06 max=9.929956e-01
  |v_rel_tangential| n=42471 mean=2.544859e+00 median=2.834431e+00 p25=1.614029e+00 p75=3.693577e+00 min=9.827818e-04 max=3.999710e+00
  frac |v_rad|>0.1=6.537167e-01  >0.5=9.305173e-02  >1.0=0.000000e+00

PAIR_1_2 full-GM (t, |v_rel|, |v_rad|, |v_tan|, v1, v2)
  t=0.000000e+00 |v_rel|=2.705216e+00 |v_rad|=3.212239e-16 |v_tan|=2.705216e+00 v1=(8.394024e-01,-1.017884e+00) v2=(-5.920220e-01,1.277594e+00)
  t=1.000000e+01 |v_rel|=3.281478e+00 |v_rad|=7.613034e-01 |v_tan|=3.191945e+00 v1=(9.720970e-01,-1.541613e+00) v2=(-1.392093e+00,7.340642e-01)
  t=2.000000e+01 |v_rel|=1.744494e+00 |v_rad|=7.082109e-01 |v_tan|=1.594270e+00 v1=(4.684127e-01,-7.388789e-01) v2=(-9.978233e-01,2.063257e-01)
  t=3.000000e+01 |v_rel|=2.065481e+00 |v_rad|=9.047265e-01 |v_tan|=1.856793e+00 v1=(-2.922486e-01,-1.388906e+00) v2=(-5.642545e-01,6.585864e-01)
  t=4.000000e+01 |v_rel|=2.680098e+00 |v_rad|=3.556476e-01 |v_tan|=2.656396e+00 v1=(1.283180e+00,-1.126527e+00) v2=(-4.940777e-01,8.795340e-01)
  t=5.000000e+01 |v_rel|=2.816056e+00 |v_rad|=1.082896e+00 |v_tan|=2.599520e+00 v1=(5.959790e-02,-1.866358e+00) v2=(-5.203315e-01,8.893362e-01)
  t=6.000000e+01 |v_rel|=1.739167e+00 |v_rad|=1.209607e+00 |v_tan|=1.249621e+00 v1=(-1.101014e-01,-6.578551e-01) v2=(1.668039e-01,1.059126e+00)
  t=7.000000e+01 |v_rel|=2.651896e+00 |v_rad|=1.546314e+00 |v_tan|=2.154405e+00 v1=(-2.314350e-01,-9.808319e-01) v2=(-2.162108e-01,1.671020e+00)
  t=8.000000e+01 |v_rel|=3.103533e+00 |v_rad|=2.222704e-01 |v_tan|=3.095563e+00 v1=(1.030189e+00,-1.162244e+00) v2=(-6.065423e-01,1.474615e+00)
  t=9.000000e+01 |v_rel|=4.257138e+00 |v_rad|=1.843608e+00 |v_tan|=3.837230e+00 v1=(1.467114e+00,-2.145152e+00) v2=(6.426831e-01,2.031394e+00)
  t=1.000000e+02 |v_rel|=5.778494e+00 |v_rad|=4.170481e+00 |v_tan|=3.999760e+00 v1=(-2.209427e-01,-2.280572e+00) v2=(6.317156e-01,3.434668e+00)
  t=1.100000e+02 |v_rel|=4.951994e+00 |v_rad|=4.056586e+00 |v_tan|=2.840133e+00 v1=(2.918582e-01,-1.790700e+00) v2=(1.717251e+00,2.951714e+00)
  t=1.200000e+02 |v_rel|=5.720622e+00 |v_rad|=5.054577e+00 |v_tan|=2.678950e+00 v1=(-8.476886e-01,-2.580711e+00) v2=(1.410605e+00,2.675298e+00)

=== Step 61: signed v_rad persistence (full GM, sigma_xy=1) ===
sign: v_rad<0 closing, v_rad>0 opening (SPEC 2.1). dt=1.000000e+00 s. deadband=1e-12.
n_pairs=780 n_ticks_per_pair=121 n_runs=10923 closing_runs=5404 opening_runs=5519
same-sign run duration (s): n=10923 mean=8.633342e+00 median=3.000000e+00 p25=1.000000e+00 p75=1.000000e+01 min=1.000000e+00 max=1.210000e+02
frac ticks closing=4.901568e-01 opening=5.090167e-01 zero=8.264463e-04
sign flips (nonzero→opposite nonzero) n=10143 pairs_that_flip=779/780
sign ACF tau_1/e=1.043200e+01 s  (first lag ACF < 1/e)
  ACF[0]=1.000000e+00 ACF[1]=7.830885e-01 ACF[2]=6.960169e-01 ACF[5]=5.393907e-01 ACF[10]=3.771011e-01 ACF[20]=2.217733e-01 ACF[40]=6.776330e-02
PAIR_1_2 signed v_rad / sign (every 10 s)
  t=0.000000e+00 v_rad=3.212239e-16 sign=0 run_so_far=1
  t=1.000000e+01 v_rad=-7.613034e-01 sign=-1 run_so_far=10
  t=2.000000e+01 v_rad=-7.082109e-01 sign=-1 run_so_far=20
  t=3.000000e+01 v_rad=9.047265e-01 sign=1 run_so_far=6
  t=4.000000e+01 v_rad=-3.556476e-01 sign=-1 run_so_far=5
  t=5.000000e+01 v_rad=1.082896e+00 sign=1 run_so_far=2
  t=6.000000e+01 v_rad=1.209607e+00 sign=1 run_so_far=12
  t=7.000000e+01 v_rad=1.546314e+00 sign=1 run_so_far=22
  t=8.000000e+01 v_rad=2.222704e-01 sign=1 run_so_far=32
  t=9.000000e+01 v_rad=1.843608e+00 sign=1 run_so_far=42
  t=1.000000e+02 v_rad=4.170481e+00 sign=1 run_so_far=52
  t=1.100000e+02 v_rad=4.056586e+00 sign=1 run_so_far=62
  t=1.200000e+02 v_rad=5.054577e+00 sign=1 run_so_far=72
Inter-hop decision interval: a routing decision is made in Forward() at generation and at every hop arrival. The packet then flies airtime (0.4 s) + range/1500 s. Empirical mean from Step 60 is T_e2e/hops (see STEP61_62 report).
