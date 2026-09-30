/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "meandering-current-mobility.h"

#include "ns3/log.h"
#include "ns3/simulator.h"
#include "ns3/double.h"

#include <cmath>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("MeanderingCurrentMobility");
NS_OBJECT_ENSURE_REGISTERED (MeanderingCurrentMobility);

TypeId
MeanderingCurrentMobility::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::MeanderingCurrentMobility")
    .SetParent<MobilityModel> ()
    .SetGroupName ("Mobility")
    .AddConstructor<MeanderingCurrentMobility> ()
    .AddAttribute ("TimeStep", "Integration step.",
                   DoubleValue (0.25),
                   MakeDoubleAccessor (&MeanderingCurrentMobility::m_dt),
                   MakeDoubleChecker<double> (0.01))
    .AddAttribute ("Wavelength", "Meander wavelength (m).",
                   DoubleValue (4000.0),
                   MakeDoubleAccessor (&MeanderingCurrentMobility::m_wavelength),
                   MakeDoubleChecker<double> (1.0))
    .AddAttribute ("PhaseSpeed", "Jet phase speed (m/s).",
                   DoubleValue (0.35),
                   MakeDoubleAccessor (&MeanderingCurrentMobility::m_phaseSpeed),
                   MakeDoubleChecker<double> (0.0))
    .AddAttribute ("MeanderAmplitude", "Meander amplitude (m).",
                   DoubleValue (350.0),
                   MakeDoubleAccessor (&MeanderingCurrentMobility::m_meanderAmp),
                   MakeDoubleChecker<double> (0.0))
    .AddAttribute ("Epsilon", "Meander perturbation (Caruso et al.).",
                   DoubleValue (0.3),
                   MakeDoubleAccessor (&MeanderingCurrentMobility::m_epsilon),
                   MakeDoubleChecker<double> (0.0))
    .AddAttribute ("CurrentScale", "Typical current speed U0 (m/s).",
                   DoubleValue (0.45),
                   MakeDoubleAccessor (&MeanderingCurrentMobility::m_currentScale),
                   MakeDoubleChecker<double> (0.0))
  ;
  return tid;
}

MeanderingCurrentMobility::MeanderingCurrentMobility ()
  : m_position (0, 0, 0),
    m_thrust (0, 0, 0),
    m_dt (0.25),
    m_wavelength (4000.0),
    m_phaseSpeed (0.35),
    m_meanderAmp (350.0),
    m_epsilon (0.3),
    m_currentScale (0.45),
    m_phaseOffset (0.0)
{
  m_event = Simulator::ScheduleNow (&MeanderingCurrentMobility::Advance, this);
}

MeanderingCurrentMobility::~MeanderingCurrentMobility ()
{
  m_event.Cancel ();
}

void
MeanderingCurrentMobility::SetThrust (Vector thrustMs)
{
  m_thrust = thrustMs;
}

Vector
MeanderingCurrentMobility::GetThrust (void) const
{
  return m_thrust;
}

Vector
MeanderingCurrentMobility::GetCurrentVelocity (void) const
{
  return CurrentAt (m_position, Simulator::Now ().GetSeconds ());
}

void
MeanderingCurrentMobility::SetPhaseOffset (double seconds)
{
  m_phaseOffset = seconds;
}

void
MeanderingCurrentMobility::SetCurrentScale (double u0)
{
  m_currentScale = u0;
}

Vector
MeanderingCurrentMobility::CurrentAt (Vector p, double tSec) const
{
  // Nondimensional MCM stream function (Caruso et al., MobiHoc 2008).
  // x' = x/λ, B' = B/λ so tanh() sees O(1) arguments. Velocity scale U0 m/s.
  const double lambda = std::max (m_wavelength, 1.0);
  const double k = 2.0 * M_PI;
  const double omega = 0.4 * m_phaseSpeed * (2.0 * M_PI / lambda);
  const double tEff = tSec + m_phaseOffset;
  const double Bprime = (m_meanderAmp / lambda) * (1.0 + m_epsilon * std::cos (omega * tEff));
  const double xs = (p.x - m_phaseSpeed * tEff) / lambda;
  const double ys = p.y / lambda;
  const double eps = 1e-3;

  auto psi = [&] (double xdim, double ydim) {
    const double s = std::sin (k * xdim);
    const double cph = std::cos (k * xdim);
    const double num = ydim - Bprime * s;
    const double den = std::sqrt (1.0 + k * k * Bprime * Bprime * cph * cph);
    return -std::tanh (num / den);
  };

  const double dpsidy = (psi (xs, ys + eps) - psi (xs, ys - eps)) / (2.0 * eps);
  const double dpsidx = (psi (xs + eps, ys) - psi (xs - eps, ys)) / (2.0 * eps);
  const double u = m_currentScale * dpsidy;
  const double v = -m_currentScale * dpsidx;
  return Vector (u, v, 0.0);
}

void
MeanderingCurrentMobility::Advance (void)
{
  const double t = Simulator::Now ().GetSeconds ();
  const Vector cur = CurrentAt (m_position, t);
  const Vector vel (cur.x + m_thrust.x, cur.y + m_thrust.y, cur.z + m_thrust.z);
  m_position.x += vel.x * m_dt;
  m_position.y += vel.y * m_dt;
  m_position.z += vel.z * m_dt;
  if (m_position.z < 1.0)
    {
      m_position.z = 1.0;
    }
  NotifyCourseChange ();
  m_event = Simulator::Schedule (Seconds (m_dt), &MeanderingCurrentMobility::Advance, this);
}

Vector
MeanderingCurrentMobility::DoGetPosition (void) const
{
  return m_position;
}

void
MeanderingCurrentMobility::DoSetPosition (const Vector &position)
{
  m_position = position;
  NotifyCourseChange ();
}

Vector
MeanderingCurrentMobility::DoGetVelocity (void) const
{
  const Vector cur = GetCurrentVelocity ();
  return Vector (cur.x + m_thrust.x, cur.y + m_thrust.y, cur.z + m_thrust.z);
}

} // namespace ns3
