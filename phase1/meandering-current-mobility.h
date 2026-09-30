/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef PHASE1_MEANDERING_CURRENT_MOBILITY_H
#define PHASE1_MEANDERING_CURRENT_MOBILITY_H

#include "ns3/mobility-model.h"
#include "ns3/nstime.h"
#include "ns3/event-id.h"
#include "ns3/vector.h"

namespace ns3 {

/**
 * Meandering-current mobility after Caruso et al., ACM MobiHoc 2008,
 * plus an optional AUV thrust vector (own propulsion).
 *
 * USVs typically use thrust = 0 (surface drift). AUVs add a bounded
 * swim velocity on top of the current. Depth is held (z thrust only
 * if set). This is a kinematic model, not an ocean GCM.
 */
class MeanderingCurrentMobility : public MobilityModel
{
public:
  static TypeId GetTypeId (void);
  MeanderingCurrentMobility ();
  virtual ~MeanderingCurrentMobility ();

  void SetThrust (Vector thrustMs);
  Vector GetThrust (void) const;
  Vector GetCurrentVelocity (void) const;
  void SetPhaseOffset (double seconds);
  void SetCurrentScale (double u0);

private:
  virtual Vector DoGetPosition (void) const;
  virtual void DoSetPosition (const Vector &position);
  virtual Vector DoGetVelocity (void) const;

  void Advance (void);
  Vector CurrentAt (Vector p, double tSec) const;

  Vector m_position;
  Vector m_thrust;
  double m_dt;
  double m_wavelength;
  double m_phaseSpeed;
  double m_meanderAmp;
  double m_epsilon;
  double m_currentScale;
  double m_phaseOffset;
  EventId m_event;
};

} // namespace ns3

#endif
