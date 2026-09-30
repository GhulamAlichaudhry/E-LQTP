/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "hello-routing.h"
#include "data-header.h"
#include "topology-discovery-app.h"

#include "ns3/aqua-sim-header.h"
#include "ns3/log.h"
#include "ns3/mobility-model.h"
#include "ns3/random-variable-stream.h"
#include "ns3/simulator.h"

#include <algorithm>
#include <limits>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("AquaSimHelloRouting");
NS_OBJECT_ENSURE_REGISTERED (AquaSimHelloRouting);

AquaSimHelloRouting::AquaSimHelloRouting ()
  : m_policy ("none"),
    m_holdMin (8.0),
    m_myId (0),
    m_sinkId (0),
    m_collisionDrops (0),
    m_delivered (0),
    m_dataOrig (0),
    m_dataFwd (0),
    m_dataDeliv (0),
    m_dropNoRoute (0),
    m_dropLoop (0),
    m_staleFwd (0),
    m_dyingFwd (0),
    m_dataSnrDrops (0),
    m_dataBpskDrops (0),
    m_delaySum (0.0),
    m_hopSum (0.0)
{
  m_rng = CreateObject<UniformRandomVariable> ();
}

TypeId
AquaSimHelloRouting::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::AquaSimHelloRouting")
    .SetParent<AquaSimRouting> ()
    .AddConstructor<AquaSimHelloRouting> ()
  ;
  return tid;
}

int64_t
AquaSimHelloRouting::AssignStreams (int64_t stream)
{
  m_rng->SetStream (stream);
  return 1;
}

void
AquaSimHelloRouting::SetRxCallback (Callback<void, Ptr<Packet>> cb)
{
  m_rx = cb;
}

void
AquaSimHelloRouting::SetDiscovery (Ptr<TopologyDiscoveryApp> disc)
{
  m_disc = disc;
}

void
AquaSimHelloRouting::SetPolicy (std::string policy, double holdMinSec)
{
  m_policy = policy;
  m_holdMin = holdMinSec;
}

void
AquaSimHelloRouting::SetLink (phase1::AcousticLinkConfig link)
{
  m_link = link;
}

void
AquaSimHelloRouting::SetAddresses (std::vector<AquaSimAddress> addrs)
{
  m_addrs = addrs;
}

void
AquaSimHelloRouting::SetIds (uint32_t myId, uint32_t sinkId)
{
  m_myId = myId;
  m_sinkId = sinkId;
}

double
AquaSimHelloRouting::TrueSnrTo (uint32_t other) const
{
  if (!m_disc || other >= m_disc->Peers ().size ())
    {
      return -1e9;
    }
  const Vector a = m_disc->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
  const Vector b = m_disc->Peers ()[other]->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
  const double d = phase1::Distance3D (a.x, a.y, a.z, b.x, b.y, b.z);
  return phase1::SnrDb (d, m_link);
}

void
AquaSimHelloRouting::ScoreChosenHop (uint32_t nh)
{
  if (!m_disc || nh >= m_disc->Peers ().size ())
    {
      return;
    }
  const Vector a = m_disc->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
  const Vector av = m_disc->GetNode ()->GetObject<MobilityModel> ()->GetVelocity ();
  const Vector b = m_disc->Peers ()[nh]->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
  const Vector bv = m_disc->Peers ()[nh]->GetNode ()->GetObject<MobilityModel> ()->GetVelocity ();
  const double d = phase1::Distance3D (a.x, a.y, a.z, b.x, b.y, b.z);
  const double snr = phase1::SnrDb (d, m_link);
  const double vrad = phase1::RadialRelativeSpeed (a.x, a.y, a.z, av.x, av.y, av.z,
                                                   b.x, b.y, b.z, bv.x, bv.y, bv.z);
  const double rStar = phase1::RangeAtSnrThreshold (m_link);
  const double hold = phase1::PredictedHoldTimeSec (d, vrad, snr, 0.0, rStar, m_link);
  const double tFlight = d / m_link.soundSpeed
                         + static_cast<double> (m_link.packetBits) / std::max (1.0, m_link.bandwidthHz);
  if (snr < m_link.snrThresholdDb || hold < tFlight)
    {
      m_staleFwd++;
    }
  if (hold < m_holdMin)
    {
      m_dyingFwd++;
    }
}

int
AquaSimHelloRouting::AddrToId (AquaSimAddress a) const
{
  for (uint32_t i = 0; i < m_addrs.size (); ++i)
    {
      if (m_addrs[i] == a)
        {
          return static_cast<int> (i);
        }
    }
  return -1;
}

bool
AquaSimHelloRouting::DataDecodableFrom (AquaSimAddress src)
{
  const int sid = AddrToId (src);
  if (sid < 0)
    {
      return true;
    }
  const double snr = TrueSnrTo (static_cast<uint32_t> (sid));
  if (snr < m_link.snrThresholdDb)
    {
      m_dataSnrDrops++;
      return false;
    }
  const double ps = phase1::PacketSuccessProbability (snr, m_link);
  if (m_rng->GetValue () > ps)
    {
      m_dataBpskDrops++;
      return false;
    }
  return true;
}

int
AquaSimHelloRouting::PickNextHop (uint32_t dstId)
{
  if (!m_disc || m_policy == "none" || dstId >= m_disc->Peers ().size ())
    {
      return -1;
    }
  const Vector me = m_disc->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
  const Vector dst = m_disc->Peers ()[dstId]->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
  const double dMe = phase1::Distance3D (me.x, me.y, me.z, dst.x, dst.y, dst.z);
  const auto table = m_disc->NeighborsAlive (Simulator::Now ());
  const uint32_t n = m_disc->Peers ().size ();
  const bool holdAware = (m_policy == "hold" || m_policy == "oracle");
  const bool depthAware = (m_policy == "depth");

  auto search = [&] (bool enforceHold) {
    int best = -1;
    double bestScore = -1.0e99;
    auto consider = [&] (uint32_t j, double snr, double hold, Vector nj) {
      if (j == m_myId || j >= n)
        {
          return;
        }
      const double dN = phase1::Distance3D (nj.x, nj.y, nj.z, dst.x, dst.y, dst.z);
      const double progress = dMe - dN;
      if (j != dstId && progress < 40.0)
        {
          return;
        }
      if (snr < m_link.snrThresholdDb)
        {
          return;
        }
      if (enforceHold && hold < m_holdMin)
        {
          return;
        }
      double score = snr;
      if (holdAware)
        {
          // ETHA: DBR-like depth toward the surface sink, with a hold-time
          // constraint and SNR as a tie-break (LQARP-style multi-metric,
          // no Q-learning). The sink, if currently decodable, always wins.
          if (j == dstId)
            {
              score = 1.0e6 + snr;
            }
          else
            {
              score = -nj.z + 0.02 * snr + 0.01 * std::min (hold, 120.0);
            }
        }
      else if (depthAware)
        {
          score = -nj.z;
        }
      if (score > bestScore)
        {
          bestScore = score;
          best = static_cast<int> (j);
        }
    };

    if (m_policy == "oracle")
      {
        const Vector meV = m_disc->GetNode ()->GetObject<MobilityModel> ()->GetVelocity ();
        const double rStar = phase1::RangeAtSnrThreshold (m_link);
        for (uint32_t j = 0; j < n; ++j)
          {
            const Vector nj = m_disc->Peers ()[j]->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
            const Vector nv = m_disc->Peers ()[j]->GetNode ()->GetObject<MobilityModel> ()->GetVelocity ();
            const double d = phase1::Distance3D (me.x, me.y, me.z, nj.x, nj.y, nj.z);
            const double snr = phase1::SnrDb (d, m_link);
            const double vrad = phase1::RadialRelativeSpeed (me.x, me.y, me.z, meV.x, meV.y, meV.z,
                                                             nj.x, nj.y, nj.z, nv.x, nv.y, nv.z);
            const double hold = phase1::PredictedHoldTimeSec (d, vrad, snr, 0.0, rStar, m_link);
            consider (j, snr, hold, nj);
          }
      }
    else
      {
        for (auto const &kv : table)
          {
            consider (kv.first, kv.second.ewmaSnrDb, kv.second.predictedHoldS, kv.second.lastPos);
          }
      }
    return best;
  };

  int best = search (holdAware);
  if (best < 0 && holdAware)
    {
      best = search (false);
    }
  return best;
}

bool
AquaSimHelloRouting::Recv (Ptr<Packet> packet, const Address &dest, uint16_t protocolNumber)
{
  (void) protocolNumber;
  AquaSimHeader ash;
  packet->RemoveHeader (ash);
  AquaSimAddress myAddr = AquaSimAddress::ConvertFrom (GetNetDevice ()->GetAddress ());

  if (ash.GetNumForwards () == 0)
    {
      bool isHello = true;
      if (AquaSimAddress::IsMatchingType (dest))
        {
          isHello = (AquaSimAddress::ConvertFrom (dest) == AquaSimAddress::GetBroadcast ());
        }

      ash.SetDirection (AquaSimHeader::DOWN);
      ash.SetNumForwards (1);
      ash.SetSAddr (myAddr);
      ash.SetErrorFlag (false);
      if (isHello)
        {
          ash.SetNextHop (AquaSimAddress::GetBroadcast ());
          ash.SetDAddr (AquaSimAddress::GetBroadcast ());
          packet->AddHeader (ash);
          SendDown (packet, ash.GetNextHop (), Seconds (0));
          return true;
        }

      DataHeader dh;
      packet->RemoveHeader (dh);
      m_dataOrig++;
      const int nh = PickNextHop (dh.GetDst ());
      if (nh < 0 || static_cast<uint32_t> (nh) >= m_addrs.size ())
        {
          m_dropNoRoute++;
          return true;
        }
      ScoreChosenHop (static_cast<uint32_t> (nh));
      dh.SetHops (dh.GetHops () + 1);
      packet->AddHeader (dh);
      ash.SetNextHop (m_addrs[nh]);
      ash.SetDAddr (m_addrs[dh.GetDst ()]);
      packet->AddHeader (ash);
      SendDown (packet, ash.GetNextHop (), Seconds (0));
      return true;
    }

  if (ash.GetErrorFlag ())
    {
      m_collisionDrops++;
      return true;
    }

  if (ash.GetDAddr () == AquaSimAddress::GetBroadcast ())
    {
      m_delivered++;
      if (!m_rx.IsNull ())
        {
          m_rx (packet);
        }
      return true;
    }

  if (!DataDecodableFrom (ash.GetSAddr ()))
    {
      return true;
    }

  DataHeader dh;
  packet->RemoveHeader (dh);
  if (dh.GetDst () == m_myId)
    {
      m_dataDeliv++;
      const double delay = Simulator::Now ().GetSeconds () - 1e-3 * dh.GetTxMs ();
      if (delay > 0.0 && delay < 1.0e6)
        {
          m_delaySum += delay;
        }
      m_hopSum += static_cast<double> (dh.GetHops ());
      return true;
    }

  const auto key = std::make_pair (dh.GetSrc (), dh.GetSeq ());
  if (m_seen.count (key) || dh.GetHops () >= 8)
    {
      m_dropLoop++;
      return true;
    }
  m_seen.insert (key);

  const int nh = PickNextHop (dh.GetDst ());
  if (nh < 0 || static_cast<uint32_t> (nh) >= m_addrs.size ())
    {
      m_dropNoRoute++;
      return true;
    }
  ScoreChosenHop (static_cast<uint32_t> (nh));
  dh.SetHops (dh.GetHops () + 1);
  packet->AddHeader (dh);
  ash.SetDirection (AquaSimHeader::DOWN);
  ash.SetNumForwards (ash.GetNumForwards () + 1);
  ash.SetNextHop (m_addrs[nh]);
  ash.SetSAddr (myAddr);
  ash.SetDAddr (m_addrs[dh.GetDst ()]);
  ash.SetErrorFlag (false);
  packet->AddHeader (ash);
  m_dataFwd++;
  SendDown (packet, ash.GetNextHop (), Seconds (0));
  return true;
}

} // namespace ns3
