/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * SOTA analytical underwater acoustic link model used by Phase 1.
 *
 * Formulas (not invented):
 *  - Thorp absorption as used by Liu et al., IEEE IoTJ 2026 (LQARP), eq. (2)
 *    and Stojanovic, ACM MC2R, 2007.
 *  - Practical spreading k=1.5: Stojanovic & Preisig, IEEE Comm. Mag., 2009.
 *  - Wenz ambient-noise components: LQARP eqs. (4)–(8), after Stojanovic & Preisig 2009.
 *  - Passive sonar equation: SNR = SL - TL - NL + DI (Urick).
 *  - BPSK packet success: LQARP eqs. (36)–(38) with M=2.
 *  - Acoustic Doppler: f_d = f_c * v_radial / c, c = 1500 m/s.
 *
 * Honest limit: this is an analytical connectivity model, not Bellhop/sea-trial CSI.
 * A constant multipath margin stands in for coherent multipath until a TL table exists.
 */
#ifndef PHASE1_SOTA_ACOUSTIC_LINK_H
#define PHASE1_SOTA_ACOUSTIC_LINK_H

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <limits>

namespace phase1 {

struct AcousticLinkConfig
{
  double fcKhz = 24.0;          // LQARP Table II
  double bandwidthHz = 1000.0;  // matches 1000 bit/s BPSK, Table II
  double spreadingK = 1.5;      // practical spreading (Stojanovic)
  double slDb = 185.0;          // LQARP Table II source level
  double diDb = 0.0;
  double shippingS = 0.2;       // LQARP Table II
  double windMs = 2.0;          // LQARP Table II
  double snrThresholdDb = 8.68; // LQARP Table II / footnote 3
  double multipathMarginDb = 30.0; // proxy for unmodeled coherent multipath
  double soundSpeed = 1500.0;
  uint32_t packetBits = 400;    // LQARP Table II
  uint32_t constellationM = 2;  // BPSK
};

inline double ThorpAbsorptionDbPerKm (double fKhz)
{
  const double f2 = fKhz * fKhz;
  return 0.11 * f2 / (1.0 + f2)
         + 44.0 * f2 / (4100.0 + f2)
         + 2.75e-4 * f2
         + 0.003;
}

inline double UrickTransmissionLossDb (double distanceM, const AcousticLinkConfig &cfg)
{
  const double d = std::max (distanceM, 1.0);
  const double spreading = 10.0 * cfg.spreadingK * std::log10 (d);
  const double absorption = ThorpAbsorptionDbPerKm (cfg.fcKhz) * (d / 1000.0);
  return spreading + absorption + cfg.multipathMarginDb;
}

inline double WenzNoisePsdLinear (double fKhz, double shippingS, double windMs)
{
  const double ntDb = 17.0 - 30.0 * std::log10 (fKhz);
  const double nsDb = 40.0 + 20.0 * (shippingS - 0.5) + 26.0 * std::log10 (fKhz)
                      - 60.0 * std::log10 (fKhz + 0.03);
  const double nwDb = 50.0 + 7.5 * std::sqrt (windMs) + 20.0 * std::log10 (fKhz)
                      - 40.0 * std::log10 (fKhz + 0.4);
  const double nthDb = -15.0 + 20.0 * std::log10 (fKhz);
  auto lin = [] (double db) { return std::pow (10.0, db / 10.0); };
  return lin (ntDb) + lin (nsDb) + lin (nwDb) + lin (nthDb);
}

inline double NoiseLevelDb (const AcousticLinkConfig &cfg)
{
  const double n0 = WenzNoisePsdLinear (cfg.fcKhz, cfg.shippingS, cfg.windMs);
  return 10.0 * std::log10 (n0 * cfg.bandwidthHz);
}

inline double SnrDb (double distanceM, const AcousticLinkConfig &cfg)
{
  const double tl = UrickTransmissionLossDb (distanceM, cfg);
  const double nl = NoiseLevelDb (cfg);
  return cfg.slDb - tl - nl + cfg.diDb;
}

inline bool LinkIsDecodable (double distanceM, const AcousticLinkConfig &cfg)
{
  return SnrDb (distanceM, cfg) >= cfg.snrThresholdDb;
}

inline double BpskBitErrorRate (double snrDb)
{
  // LQARP (36) with M=2: pe = 0.5 * erfc(sqrt(SNR_lin))
  const double snrLin = std::pow (10.0, snrDb / 10.0);
  return 0.5 * std::erfc (std::sqrt (std::max (snrLin, 0.0)));
}

inline double PacketSuccessProbability (double snrDb, const AcousticLinkConfig &cfg)
{
  const double pe = std::min (0.5, std::max (0.0, BpskBitErrorRate (snrDb)));
  return std::pow (1.0 - pe, static_cast<double> (cfg.packetBits));
}

inline double DopplerHz (double radialRelativeMs, const AcousticLinkConfig &cfg)
{
  return (cfg.fcKhz * 1000.0) * radialRelativeMs / cfg.soundSpeed;
}

inline double Distance3D (double x1, double y1, double z1, double x2, double y2, double z2)
{
  const double dx = x1 - x2;
  const double dy = y1 - y2;
  const double dz = z1 - z2;
  return std::sqrt (dx * dx + dy * dy + dz * dz);
}

inline double RadialRelativeSpeed (double x1, double y1, double z1,
                                   double vx1, double vy1, double vz1,
                                   double x2, double y2, double z2,
                                   double vx2, double vy2, double vz2)
{
  const double dx = x2 - x1;
  const double dy = y2 - y1;
  const double dz = z2 - z1;
  const double r = std::sqrt (dx * dx + dy * dy + dz * dz);
  if (r < 1e-6)
    {
      return 0.0;
    }
  const double dvx = vx2 - vx1;
  const double dvy = vy2 - vy1;
  const double dvz = vz2 - vz1;
  return (dx * dvx + dy * dvy + dz * dvz) / r;
}

inline double RangeAtSnrThreshold (const AcousticLinkConfig &cfg)
{
  double lo = 1.0;
  double hi = 50000.0;
  for (int i = 0; i < 60; ++i)
    {
      const double mid = 0.5 * (lo + hi);
      if (SnrDb (mid, cfg) >= cfg.snrThresholdDb)
        {
          lo = mid;
        }
      else
        {
          hi = mid;
        }
    }
  return 0.5 * (lo + hi);
}

/** d(TL)/dd in dB per metre. */
inline double TransmissionLossGradientDbPerM (double distanceM, const AcousticLinkConfig &cfg)
{
  const double d = std::max (distanceM, 1.0);
  const double spreading = 10.0 * cfg.spreadingK / (d * std::log (10.0));
  const double absorption = ThorpAbsorptionDbPerKm (cfg.fcKhz) / 1000.0;
  return spreading + absorption;
}

/**
 * Remaining useful time of a link.
 * vRadialOpening > 0 means range is increasing.
 * snrDotDbPerSec is EWMA SNR slope at the receiver (dB/s).
 */
inline double PredictedHoldTimeSec (double rangeM,
                                    double vRadialOpening,
                                    double snrDb,
                                    double snrDotDbPerSec,
                                    double rangeStarM,
                                    const AcousticLinkConfig &cfg)
{
  double tGeom = 1.0e9;
  if (vRadialOpening > 0.02)
    {
      if (rangeM >= rangeStarM)
        {
          tGeom = 0.0;
        }
      else
        {
          tGeom = (rangeStarM - rangeM) / vRadialOpening;
        }
    }

  double tSnr = 1.0e9;
  if (snrDb < cfg.snrThresholdDb)
    {
      tSnr = 0.0;
    }
  else if (snrDotDbPerSec < -1.0e-3)
    {
      tSnr = (snrDb - cfg.snrThresholdDb) / (-snrDotDbPerSec);
    }
  else if (vRadialOpening > 0.02)
    {
      const double snrDotGeom = -TransmissionLossGradientDbPerM (rangeM, cfg) * vRadialOpening;
      if (snrDotGeom < -1.0e-3)
        {
          tSnr = (snrDb - cfg.snrThresholdDb) / (-snrDotGeom);
        }
    }

  return std::min (300.0, std::min (tGeom, tSnr));
}

} // namespace phase1

#endif
