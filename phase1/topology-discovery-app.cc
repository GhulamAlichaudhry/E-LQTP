/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#include "topology-discovery-app.h"
#include "hello-routing.h"
#include "meandering-current-mobility.h"

#include "ns3/abort.h"
#include "ns3/aqua-sim-address.h"
#include "ns3/aqua-sim-net-device.h"
#include "ns3/double.h"
#include "ns3/header.h"
#include "ns3/log.h"
#include "ns3/mobility-model.h"
#include "ns3/random-variable-stream.h"
#include "ns3/simulator.h"
#include "ns3/string.h"
#include "ns3/uinteger.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace ns3 {

NS_LOG_COMPONENT_DEFINE ("TopologyDiscoveryApp");
NS_OBJECT_ENSURE_REGISTERED (TopologyDiscoveryApp);
NS_OBJECT_ENSURE_REGISTERED (HelloBeaconHeader);

static void
WriteFloat (Buffer::Iterator &i, float v)
{
  uint32_t u = 0;
  std::memcpy (&u, &v, sizeof (u));
  i.WriteHtonU32 (u);
}

static float
ReadFloat (Buffer::Iterator &i)
{
  uint32_t u = i.ReadNtohU32 ();
  float v = 0;
  std::memcpy (&v, &u, sizeof (v));
  return v;
}

HelloBeaconHeader::HelloBeaconHeader ()
  : m_src (0), m_seq (0),
    m_x (0), m_y (0), m_z (0),
    m_vx (0), m_vy (0), m_vz (0)
{
}

TypeId
HelloBeaconHeader::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::HelloBeaconHeader")
    .SetParent<Header> ()
    .AddConstructor<HelloBeaconHeader> ()
  ;
  return tid;
}

TypeId
HelloBeaconHeader::GetInstanceTypeId (void) const
{
  return GetTypeId ();
}

void
HelloBeaconHeader::Print (std::ostream &os) const
{
  os << "hello src=" << m_src << " seq=" << m_seq;
}

uint32_t
HelloBeaconHeader::GetSerializedSize (void) const
{
  return 2 + 2 + 6 * 4; // 28 bytes
}

void
HelloBeaconHeader::Serialize (Buffer::Iterator start) const
{
  start.WriteHtonU16 (m_src);
  start.WriteHtonU16 (m_seq);
  WriteFloat (start, m_x);
  WriteFloat (start, m_y);
  WriteFloat (start, m_z);
  WriteFloat (start, m_vx);
  WriteFloat (start, m_vy);
  WriteFloat (start, m_vz);
}

uint32_t
HelloBeaconHeader::Deserialize (Buffer::Iterator start)
{
  m_src = start.ReadNtohU16 ();
  m_seq = start.ReadNtohU16 ();
  m_x = ReadFloat (start);
  m_y = ReadFloat (start);
  m_z = ReadFloat (start);
  m_vx = ReadFloat (start);
  m_vy = ReadFloat (start);
  m_vz = ReadFloat (start);
  return GetSerializedSize ();
}

TypeId
TopologyDiscoveryApp::GetTypeId (void)
{
  static TypeId tid = TypeId ("ns3::TopologyDiscoveryApp")
    .SetParent<Application> ()
    .SetGroupName ("Applications")
    .AddConstructor<TopologyDiscoveryApp> ()
  ;
  return tid;
}

TopologyDiscoveryApp::TopologyDiscoveryApp ()
  : m_id (0),
    m_role ("auv"),
    m_beaconMode ("periodic"),
    m_beaconInterval (Seconds (5.0)),
    m_tMin (Seconds (2.0)),
    m_tMax (Seconds (20.0)),
    m_neighborTimeout (Seconds (15.0)),
    m_ewmaLambda (0.35),
    m_snrDeltaDb (3.0),
    m_moveDeltaM (80.0),
    m_rangeStarM (5000.0),
    m_slotSec (0.0),
    m_slotPending (false),
    m_lastBeacon (Seconds (-1e9)),
    m_lastBeaconPos (0, 0, 0),
    m_lastBeaconSnrToUsv (-1e9),
    m_seq (0),
    m_beaconsSent (0),
    m_controlBits (0),
    m_hellosRx (0),
    m_snrDrops (0),
    m_bpskDrops (0)
{
}

TopologyDiscoveryApp::~TopologyDiscoveryApp ()
{
}

void
TopologyDiscoveryApp::Configure (uint32_t id,
                                 std::string role,
                                 std::string beaconMode,
                                 phase1::AcousticLinkConfig link,
                                 Time beaconInterval,
                                 Time tMin,
                                 Time tMax,
                                 Time neighborTimeout,
                                 double ewmaLambda,
                                 double snrDeltaDb,
                                 double moveDeltaM)
{
  m_id = id;
  m_role = role;
  m_beaconMode = beaconMode;
  m_link = link;
  m_beaconInterval = beaconInterval;
  m_tMin = tMin;
  m_tMax = tMax;
  m_neighborTimeout = neighborTimeout;
  m_ewmaLambda = ewmaLambda;
  m_snrDeltaDb = snrDeltaDb;
  m_moveDeltaM = moveDeltaM;
  m_rangeStarM = phase1::RangeAtSnrThreshold (m_link);
}

void
TopologyDiscoveryApp::SetSlotSec (double slotSec)
{
  m_slotSec = std::max (0.0, slotSec);
}

void
TopologyDiscoveryApp::SetPeers (std::vector<Ptr<TopologyDiscoveryApp>> peers)
{
  m_peers = peers;
}

Vector
TopologyDiscoveryApp::MyPosition (void) const
{
  return GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
}

Vector
TopologyDiscoveryApp::MyVelocity (void) const
{
  return GetNode ()->GetObject<MobilityModel> ()->GetVelocity ();
}

void
TopologyDiscoveryApp::StartApplication (void)
{
  m_rng = CreateObject<UniformRandomVariable> ();
  m_lastBeaconPos = MyPosition ();
  m_dev = DynamicCast<AquaSimNetDevice> (GetNode ()->GetDevice (0));
  NS_ABORT_MSG_IF (m_dev == nullptr, "TopologyDiscoveryApp: missing AquaSimNetDevice");
  Ptr<AquaSimHelloRouting> rt = DynamicCast<AquaSimHelloRouting> (m_dev->GetRouting ());
  NS_ABORT_MSG_IF (rt == nullptr, "TopologyDiscoveryApp: routing is not AquaSimHelloRouting");
  rt->SetRxCallback (MakeCallback (&TopologyDiscoveryApp::HandleMacPacket, this));

  Time jitter = MilliSeconds (m_rng->GetInteger (20, 1800) + m_id * 17);
  if (m_slotSec > 1e-6)
    {
      jitter = Seconds (m_rng->GetValue (0.0, m_slotSec));
    }
  m_event = Simulator::Schedule (jitter, &TopologyDiscoveryApp::ConsiderBeacon, this);
}

void
TopologyDiscoveryApp::StopApplication (void)
{
  m_event.Cancel ();
}

void
TopologyDiscoveryApp::ConsiderBeacon (void)
{
  const Time now = Simulator::Now ();
  bool send = false;
  if (m_beaconMode == "periodic")
    {
      send = true;
      const Time jitter = MilliSeconds (m_rng->GetInteger (0, 400));
      m_event = Simulator::Schedule (m_beaconInterval + jitter, &TopologyDiscoveryApp::ConsiderBeacon, this);
    }
  else
    {
      const Time since = now - m_lastBeacon;
      const Vector pos = MyPosition ();
      const double moved = phase1::Distance3D (pos.x, pos.y, pos.z,
                                               m_lastBeaconPos.x, m_lastBeaconPos.y, m_lastBeaconPos.z);
      double snrToUsv = m_lastBeaconSnrToUsv;
      double holdToUsv = 1.0e9;
      for (auto const &peer : m_peers)
        {
          if (peer->GetRole () != "usv")
            {
              continue;
            }
          const Vector u = peer->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
          const Vector uv = peer->GetNode ()->GetObject<MobilityModel> ()->GetVelocity ();
          const Vector meV = MyVelocity ();
          const double d = phase1::Distance3D (pos.x, pos.y, pos.z, u.x, u.y, u.z);
          snrToUsv = phase1::SnrDb (d, m_link);
          const double vrad = phase1::RadialRelativeSpeed (pos.x, pos.y, pos.z, meV.x, meV.y, meV.z,
                                                           u.x, u.y, u.z, uv.x, uv.y, uv.z);
          holdToUsv = phase1::PredictedHoldTimeSec (d, vrad, snrToUsv, 0.0, m_rangeStarM, m_link);
          break;
        }
      const bool linkedToUsv = snrToUsv >= m_link.snrThresholdDb;
      const bool deltaSnr = linkedToUsv
                            && std::fabs (snrToUsv - m_lastBeaconSnrToUsv) >= m_snrDeltaDb;
      const bool deltaMove = moved >= m_moveDeltaM;
      // Fade HELLO only while the USV link is still decodable. Outer-ring
      // nodes sit beyond R* so holdToUsv=0; they must not beacon every Tmin.
      const bool fadeWarn = linkedToUsv
                            && holdToUsv < std::max (2.0 * m_tMin.GetSeconds (),
                                                    0.5 * m_tMax.GetSeconds ());
      if (since >= m_tMax)
        {
          send = true;
        }
      else if (since >= m_tMin && (deltaSnr || deltaMove || fadeWarn))
        {
          send = true;
        }
      m_event = Simulator::Schedule (m_tMin, &TopologyDiscoveryApp::ConsiderBeacon, this);
    }

  if (send)
    {
      EmitBeacon ();
    }
}

void
TopologyDiscoveryApp::EmitBeacon (void)
{
  if (m_slotSec > 1e-6)
    {
      if (m_slotPending)
        {
          return;
        }
      const double now = Simulator::Now ().GetSeconds ();
      const double slot = std::ceil ((now + 1e-9) / m_slotSec) * m_slotSec;
      const double wait = slot - now;
      if (wait > 1e-6)
        {
          m_slotPending = true;
          Simulator::Schedule (Seconds (wait), &TopologyDiscoveryApp::TransmitBeacon, this);
          return;
        }
    }
  TransmitBeacon ();
}

void
TopologyDiscoveryApp::TransmitBeacon (void)
{
  m_slotPending = false;
  const Vector pos = MyPosition ();
  const Vector vel = MyVelocity ();
  m_seq++;
  m_beaconsSent++;
  m_controlBits += m_link.packetBits;
  m_lastBeacon = Simulator::Now ();
  m_lastBeaconPos = pos;

  for (auto const &peer : m_peers)
    {
      if (peer->GetRole () == "usv")
        {
          const Vector u = peer->GetNode ()->GetObject<MobilityModel> ()->GetPosition ();
          const double d = phase1::Distance3D (pos.x, pos.y, pos.z, u.x, u.y, u.z);
          m_lastBeaconSnrToUsv = phase1::SnrDb (d, m_link);
          break;
        }
    }

  HelloBeaconHeader hdr;
  hdr.SetSrc (static_cast<uint16_t> (m_id));
  hdr.SetSeq (static_cast<uint16_t> (m_seq));
  hdr.SetPos (pos);
  hdr.SetVel (vel);

  const uint32_t want = std::max (hdr.GetSerializedSize (), m_link.packetBits / 8);
  const uint32_t pad = (want > hdr.GetSerializedSize ()) ? (want - hdr.GetSerializedSize ()) : 0;
  Ptr<Packet> pkt = Create<Packet> (pad);
  pkt->AddHeader (hdr);
  m_dev->Send (pkt, AquaSimAddress::GetBroadcast (), 0);
}

void
TopologyDiscoveryApp::HandleMacPacket (Ptr<Packet> packet)
{
  HelloBeaconHeader hdr;
  packet->RemoveHeader (hdr);
  if (hdr.GetSrc () == m_id)
    {
      return;
    }

  const Vector srcPos = hdr.GetPos ();
  const Vector srcVel = hdr.GetVel ();
  const Vector dst = MyPosition ();
  const Vector dstVel = MyVelocity ();
  const double d = phase1::Distance3D (srcPos.x, srcPos.y, srcPos.z, dst.x, dst.y, dst.z);
  const double snr = phase1::SnrDb (d, m_link);
  if (snr < m_link.snrThresholdDb)
    {
      m_snrDrops++;
      return;
    }
  const double vrad = phase1::RadialRelativeSpeed (srcPos.x, srcPos.y, srcPos.z,
                                                   srcVel.x, srcVel.y, srcVel.z,
                                                   dst.x, dst.y, dst.z,
                                                   dstVel.x, dstVel.y, dstVel.z);
  BeaconEvent ev;
  ev.src = hdr.GetSrc ();
  ev.srcPos = srcPos;
  ev.srcVel = srcVel;
  ev.seq = hdr.GetSeq ();
  ev.snrDb = snr;
  ev.psucc = phase1::PacketSuccessProbability (snr, m_link);
  ev.dopplerHz = phase1::DopplerHz (vrad, m_link);
  ev.rangeM = d;
  ev.vRadial = vrad;
  if (m_rng->GetValue () > ev.psucc)
    {
      m_bpskDrops++;
      return;
    }
  ReceiveBeacon (ev);
}

void
TopologyDiscoveryApp::ReceiveBeacon (BeaconEvent ev)
{
  const double now = Simulator::Now ().GetSeconds ();
  NeighborRecord &rec = m_table[ev.src];
  rec.id = ev.src;
  rec.lastSnrDb = ev.snrDb;
  if (rec.rxCount == 0)
    {
      rec.ewmaSnrDb = ev.snrDb;
      rec.prevEwmaSnrDb = ev.snrDb;
      rec.snrDotDbPerSec = 0.0;
    }
  else
    {
      rec.prevEwmaSnrDb = rec.ewmaSnrDb;
      rec.ewmaSnrDb = (1.0 - m_ewmaLambda) * rec.ewmaSnrDb + m_ewmaLambda * ev.snrDb;
      const double dt = std::max (0.2, now - rec.lastHeard);
      rec.snrDotDbPerSec = (rec.ewmaSnrDb - rec.prevEwmaSnrDb) / dt;
    }
  rec.lastPsucc = ev.psucc;
  rec.lastDopplerHz = ev.dopplerHz;
  rec.lastRangeM = ev.rangeM;
  rec.lastVrad = ev.vRadial;
  rec.lastPos = ev.srcPos;
  rec.predictedHoldS = phase1::PredictedHoldTimeSec (ev.rangeM, ev.vRadial, rec.ewmaSnrDb,
                                                     rec.snrDotDbPerSec, m_rangeStarM, m_link);
  rec.lastHeard = now;
  rec.rxCount++;
  m_hellosRx++;
}

std::map<uint32_t, NeighborRecord>
TopologyDiscoveryApp::NeighborsAlive (Time now) const
{
  std::map<uint32_t, NeighborRecord> live;
  const double t = now.GetSeconds ();
  const double base = (m_beaconMode == "event")
                      ? 2.0 * m_tMax.GetSeconds ()
                      : 3.0 * m_beaconInterval.GetSeconds ();
  for (auto const &kv : m_table)
    {
      const NeighborRecord &rec = kv.second;
      double tout = base;
      if (rec.predictedHoldS < tout)
        {
          tout = std::max (5.0, rec.predictedHoldS + 4.0);
        }
      if (rec.ewmaSnrDb < m_link.snrThresholdDb + 3.0 && rec.snrDotDbPerSec < 0.0)
        {
          tout = std::min (tout, 8.0);
        }
      if (t - rec.lastHeard <= tout)
        {
          live[kv.first] = rec;
        }
    }
  return live;
}

std::set<uint32_t>
TopologyDiscoveryApp::NeighborIdsAlive (Time now) const
{
  std::set<uint32_t> ids;
  for (auto const &kv : NeighborsAlive (now))
    {
      ids.insert (kv.first);
    }
  return ids;
}

} // namespace ns3
