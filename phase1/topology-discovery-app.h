/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef PHASE1_TOPOLOGY_DISCOVERY_APP_H
#define PHASE1_TOPOLOGY_DISCOVERY_APP_H

#include "sota-acoustic-link.h"

#include "ns3/application.h"
#include "ns3/event-id.h"
#include "ns3/header.h"
#include "ns3/nstime.h"
#include "ns3/packet.h"
#include "ns3/ptr.h"
#include "ns3/random-variable-stream.h"
#include "ns3/vector.h"

#include <cstdint>
#include <map>
#include <set>
#include <string>
#include <vector>

namespace ns3 {

class Node;
class AquaSimNetDevice;

struct NeighborRecord
{
  uint32_t id = 0;
  double lastSnrDb = -1e9;
  double ewmaSnrDb = -1e9;
  double prevEwmaSnrDb = -1e9;
  double snrDotDbPerSec = 0.0;
  double lastPsucc = 0.0;
  double lastDopplerHz = 0.0;
  double lastRangeM = 0.0;
  double lastVrad = 0.0;
  double predictedHoldS = 1.0e9;
  double lastHeard = -1.0;
  Vector lastPos;
  uint32_t rxCount = 0;
  uint32_t missCount = 0;
};

struct BeaconEvent
{
  uint32_t src = 0;
  Vector srcPos;
  Vector srcVel;
  uint32_t seq = 0;
  double snrDb = 0.0;
  double psucc = 0.0;
  double dopplerHz = 0.0;
  double rangeM = 0.0;
  double vRadial = 0.0;
};

/** Compact HELLO payload: identity, kinematics, padded to LQARP 50-byte packets. */
class HelloBeaconHeader : public Header
{
public:
  static TypeId GetTypeId (void);
  HelloBeaconHeader ();
  virtual TypeId GetInstanceTypeId (void) const;
  virtual void Print (std::ostream &os) const;
  virtual uint32_t GetSerializedSize (void) const;
  virtual void Serialize (Buffer::Iterator start) const;
  virtual uint32_t Deserialize (Buffer::Iterator start);

  void SetSrc (uint16_t v) { m_src = v; }
  void SetSeq (uint16_t v) { m_seq = v; }
  void SetPos (Vector p) { m_x = p.x; m_y = p.y; m_z = p.z; }
  void SetVel (Vector v) { m_vx = v.x; m_vy = v.y; m_vz = v.z; }
  uint16_t GetSrc (void) const { return m_src; }
  uint16_t GetSeq (void) const { return m_seq; }
  Vector GetPos (void) const { return Vector (m_x, m_y, m_z); }
  Vector GetVel (void) const { return Vector (m_vx, m_vy, m_vz); }

private:
  uint16_t m_src;
  uint16_t m_seq;
  float m_x, m_y, m_z;
  float m_vx, m_vy, m_vz;
};

/**
 * Distributed topology discovery.
 *
 * Beacon policies:
 *  - periodic: HELLO every BeaconInterval
 *  - event: send-on-delta with hysteresis (Heemels/Johansson/Tabuada-style
 *    event-triggered control), plus a keep-alive cap Tmax
 *
 * Transmit path: Aqua-Sim ALOHA broadcast (collisions live in the PHY).
 * Decode uses the SOTA sonar-equation SNR gate, not geometric range.
 */
class TopologyDiscoveryApp : public Application
{
public:
  static TypeId GetTypeId (void);
  TopologyDiscoveryApp ();
  virtual ~TopologyDiscoveryApp ();

  void Configure (uint32_t id,
                  std::string role,
                  std::string beaconMode,
                  phase1::AcousticLinkConfig link,
                  Time beaconInterval,
                  Time tMin,
                  Time tMax,
                  Time neighborTimeout,
                  double ewmaLambda,
                  double snrDeltaDb,
                  double moveDeltaM);

  void SetPeers (std::vector<Ptr<TopologyDiscoveryApp>> peers);
  void SetSlotSec (double slotSec);
  const std::vector<Ptr<TopologyDiscoveryApp>> & Peers (void) const { return m_peers; }

  uint32_t GetId (void) const { return m_id; }
  std::string GetRole (void) const { return m_role; }
  uint64_t BeaconsSent (void) const { return m_beaconsSent; }
  uint64_t ControlBits (void) const { return m_controlBits; }
  uint64_t HellosRx (void) const { return m_hellosRx; }
  uint64_t SnrDrops (void) const { return m_snrDrops; }
  uint64_t BpskDrops (void) const { return m_bpskDrops; }
  std::map<uint32_t, NeighborRecord> NeighborsAlive (Time now) const;
  std::set<uint32_t> NeighborIdsAlive (Time now) const;

  void HandleMacPacket (Ptr<Packet> packet);

private:
  virtual void StartApplication (void);
  virtual void StopApplication (void);

  void ConsiderBeacon (void);
  void EmitBeacon (void);
  void TransmitBeacon (void);
  void ReceiveBeacon (BeaconEvent ev);
  Vector MyPosition (void) const;
  Vector MyVelocity (void) const;

  uint32_t m_id;
  std::string m_role;
  std::string m_beaconMode;
  phase1::AcousticLinkConfig m_link;
  Time m_beaconInterval;
  Time m_tMin;
  Time m_tMax;
  Time m_neighborTimeout;
  double m_ewmaLambda;
  double m_snrDeltaDb;
  double m_moveDeltaM;
  double m_rangeStarM;
  double m_slotSec;
  bool m_slotPending;

  Time m_lastBeacon;
  Vector m_lastBeaconPos;
  double m_lastBeaconSnrToUsv;
  uint32_t m_seq;
  uint64_t m_beaconsSent;
  uint64_t m_controlBits;
  uint64_t m_hellosRx;
  uint64_t m_snrDrops;
  uint64_t m_bpskDrops;
  EventId m_event;
  std::vector<Ptr<TopologyDiscoveryApp>> m_peers;
  std::map<uint32_t, NeighborRecord> m_table;
  Ptr<UniformRandomVariable> m_rng;
  Ptr<AquaSimNetDevice> m_dev;
};

} // namespace ns3

#endif
