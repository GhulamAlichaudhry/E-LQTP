# Step 63: Kalman (e_k - e_{k-1}) sign persistence

seed=20260921 N=40 T=1.200000e+02 s dt=1 V_eddy=2.000000e+00 R_core=2.000000e+03 zeta=0.95 sigma_xy=1 sigma_z=0
Same GM / placement as Step 61. Live ElqtpProtocol EKF: e_k = z_tilde - h(x_hat) (SPEC 2.3 / 2.6), NOT e_k^{trigger}.
Directed AUV-AUV pairs (c_pred is per directed slot). Analyse k=2..T (k=1 has e_{k-1}=0 ctor init).
Event trigger on (epsilon_0=2, s_cap=2) so HELLO / velocity write matches Scenario III. beta_1 does not enter e_k.
n_directed=1560 n_ticks_used=119

same-sign run duration of (e_k - e_{k-1}) (s): n=26904 mean=6.703390e+00 median=4.000000e+00 p25=1.000000e+00 p75=9.000000e+00 min=1.000000e+00 max=8.900000e+01
frac ticks de>0 (beta_1 binds)=4.846746e-01 de<0=4.868186e-01 zero/nan=2.850679e-02  (nan=4)
sign flips n=25380 pairs_that_flip=1514/1560  pos_runs=13415 neg_runs=13489
sign ACF tau_1/e=4.043432e+00 s
  ACF[0]=1.000000e+00 ACF[1]=7.161134e-01 ACF[2]=5.793611e-01 ACF[5]=2.897180e-01 ACF[10]=6.038574e-02 ACF[20]=-4.763777e-02 ACF[40]=-5.664617e-02
  |e_k - e_{k-1}| n=185636 mean=3.606420e-02 median=1.352336e-02 p25=4.942142e-03 p75=3.465500e-02 min=0.000000e+00 max=5.321304e+00
  max(0, de) when de>0 n=89975 mean=3.723405e-02 median=1.438723e-02 p25=5.564850e-03 p75=3.593450e-02 min=1.037749e-07 max=3.485257e+00

PAIR_1_2 Kalman (t, e_k, de=e_k-e_{k-1}, sign(de))
  t=0.000000e+00 e_k=nan de=nan sign=0
  t=1.000000e+01 e_k=-1.135168e-01 de=2.421229e-02 sign=1
  t=2.000000e+01 e_k=7.480148e-02 de=1.195837e-02 sign=1
  t=3.000000e+01 e_k=3.598459e-02 de=-1.291157e-02 sign=-1
  t=4.000000e+01 e_k=3.553428e-02 de=1.360214e-03 sign=1
  t=5.000000e+01 e_k=2.685093e-02 de=-6.730617e-03 sign=-1
  t=6.000000e+01 e_k=-5.730020e-02 de=3.465891e-03 sign=1
  t=7.000000e+01 e_k=2.688809e-01 de=2.014295e-02 sign=1
  t=8.000000e+01 e_k=1.682199e-01 de=8.704054e-03 sign=1
  t=9.000000e+01 e_k=-2.391266e-01 de=1.649390e-01 sign=1
  t=1.000000e+02 e_k=2.085800e+00 de=7.020040e-01 sign=1
  t=1.100000e+02 e_k=8.483799e-01 de=1.262603e+00 sign=1
  t=1.200000e+02 e_k=7.110731e-01 de=7.456202e-01 sign=1
Compare to Step 61 radial-sign: median run 3.0 s, p25=1.0 s, tau_1/e=10.4 s, hop flight 2.03 s.
