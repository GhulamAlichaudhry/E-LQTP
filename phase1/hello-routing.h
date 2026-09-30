/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
#ifndef PHASE1_HELLO_ROUTING_H
#define PHASE1_HELLO_ROUTING_H

#include "sota-acoustic-link.h"

#include "ns3/aqua-sim-address.h"
#include "ns3/aqua-sim-routing.h"
#include "ns3/callback.h"
#include "ns3/packet.h"
#include "ns3/random-variable-stream.h"

#include <cstdint>
#include <set>
#include <string>
#include <utility>
#include <vector>

namespace ns3 {

class TopologyDiscoveryApp;

/**
 * 1-hop HELLO broadcast plus optional unicast data toward the USV.
 * Dummy routing would flood; this never forwards HELLOs.
 */
class AquaSimHelloRouting : public AquaSimRouting
{
public:
  static TypeId GetTypeId (void);
  AquaSimHelloRouting ();
  virtual bool Recv (Ptr<Packet> packet, const Address &dest, uint16_t protocolNumber);
  virtual int64_t AssignStreams (int64_t stream);

  void SetRxCallback (Callback<void, Ptr<Packet>> cb);
  void SetDiscovery (Ptr<TopologyDiscoveryApp> disc);
  void SetPolicy (std::string policy, double holdMinSec);
  void SetLink (phase1::AcousticLinkConfig link);
  void SetAddresses (std::vector<AquaSimAddress> addrs);
  void SetIds (uint32_t myId, uint32_t sinkId);

  uint64_t CollisionDrops (void) const { return m_collisionDrops; }
  uint64_t Delivered (void) const { return m_delivered; }
  uint64_t DataOriginated (void) const { return m_dataOrig; }
  uint64_t DataForwarded (void) const { return m_dataFwd; }
  uint64_t DataDelivered (void) const { return m_dataDeliv; }
  uint64_t DropNoRoute (void) const { return m_dropNoRoute; }
  uint64_t DropLoop (void) const { return m_dropLoop; }
  uint64_t StaleForwards (void) const { return m_staleFwd; }
  uint64_t DyingForwards (void) const { return m_dyingFwd; }
  uint64_t DataSnrDrops (void) const { return m_dataSnrDrops; }
  uint64_t DataBpskDrops (void) const { return m_dataBpskDrops; }
  double DelaySumS (void) const { return m_delaySum; }
  double HopSum (void) const { return m_hopSum; }

private:
  int PickNextHop (uint32_t dstId);
  double TrueSnrTo (uint32_t other) const;
  void ScoreChosenHop (uint32_t nh);
  int AddrToId (AquaSimAddress a) const;
  bool DataDecodableFrom (AquaSimAddress src);

  Callback<void, Ptr<Packet>> m_rx;
  Ptr<TopologyDiscoveryApp> m_disc;
  std::string m_policy;
  double m_holdMin;
  phase1::AcousticLinkConfig m_link;
  std::vector<AquaSimAddress> m_addrs;
  uint32_t m_myId;
  uint32_t m_sinkId;
  uint64_t m_collisionDrops;
  uint64_t m_delivered;
  uint64_t m_dataOrig;
  uint64_t m_dataFwd;
  uint64_t m_dataDeliv;
  uint64_t m_dropNoRoute;
  uint64_t m_dropLoop;
  uint64_t m_staleFwd;
  uint64_t m_dyingFwd;
  uint64_t m_dataSnrDrops;
  uint64_t m_dataBpskDrops;
  double m_delaySum;
  double m_hopSum;
  std::set<std::pair<uint16_t, uint16_t>> m_seen;
  Ptr<UniformRandomVariable> m_rng;
};

} // namespace ns3

#endif
