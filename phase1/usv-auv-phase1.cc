/* -*- Mode:C++; c-file-style:"gnu"; indent-tabs-mode:nil; -*- */
/*
 * Phase 1: USV–AUV topology discovery and link-quality assessment.
 *
 * Paper-experiment slice (not routing):
 *  - HELLOs contend on Aqua-Sim unslotted ALOHA (AckOn=0)
 *  - 12-node inner/outer layout that requires 2-hop paths
 *  - per-seed randomized placement, thrust, and Caruso current
 *
 * Ground-truth connectivity uses the SOTA sonar equation so we can score
 * precision/recall, detection delay, stale neighbors, and control overhead
 * against a 2 kbps-class budget.
 */
#include "hello-routing.h"
#include "data-header.h"
#include "meandering-current-mobility.h"
#include "sota-acoustic-link.h"
#include "topology-discovery-app.h"

#include "ns3/aqua-sim-ng-module.h"
#include "ns3/core-module.h"
#include "ns3/double.h"
#include "ns3/integer.h"
#include "ns3/mobility-module.h"
#include "ns3/network-module.h"

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <functional>
#include <iomanip>
#include <iostream>
#include <map>
#include <queue>
#include <set>
#include <sstream>
#include <vector>

using namespace ns3;

NS_LOG_COMPONENT_DEFINE ("UsvAuvPhase1");

struct PairKey
{
  uint32_t a;
  uint32_t b;
  bool operator< (const PairKey &o) const
  {
    return a < o.a || (a == o.a && b < o.b);
  }
};

struct HoldSample
{
  double t;
  double hold;
};

struct HopStats
{
  uint32_t n1 = 0;
  uint32_t n2plus = 0;
  uint32_t unreachable = 0;
  uint32_t diameter = 0;
};

static std::string
JoinPath (std::string dir, std::string file)
{
  if (dir.empty ())
    {
      return file;
    }
  if (dir.back () != '/')
    {
      dir.push_back ('/');
    }
  return dir + file;
}

static HopStats
ComputeHops (const std::vector<std::vector<uint32_t>> &adj)
{
  HopStats st;
  const uint32_t n = adj.size ();
  for (uint32_t s = 0; s < n; ++s)
    {
      std::vector<int> dist (n, -1);
      std::queue<uint32_t> q;
      dist[s] = 0;
      q.push (s);
      while (!q.empty ())
        {
          const uint32_t u = q.front ();
          q.pop ();
          for (uint32_t v : adj[u])
            {
              if (dist[v] < 0)
                {
                  dist[v] = dist[u] + 1;
                  q.push (v);
                }
            }
        }
      for (uint32_t t = 0; t < n; ++t)
        {
          if (t == s)
            {
              continue;
            }
          if (dist[t] < 0)
            {
              st.unreachable++;
            }
          else
            {
              st.diameter = std::max (st.diameter, static_cast<uint32_t> (dist[t]));
              if (dist[t] == 1)
                {
                  st.n1++;
                }
              else
                {
                  st.n2plus++;
                }
            }
        }
    }
  return st;
}

static uint64_t g_phyCollisions = 0;

static void
OnPhyCollision (void)
{
  g_phyCollisions++;
}

int
main (int argc, char *argv[])
{
  double simStop = 240.0;
  uint32_t nAuv = 11;
  std::string beaconMode = "periodic";
  std::string outDir = "results/phase1";
  double beaconInterval = 5.0;
  double tMin = 5.0;
  double tMax = 25.0;
  double sampleDt = 1.0;
  uint32_t seed = 1;
  bool verboseTraces = false;
  double bitRate = 1000.0;
  std::string macMode = "unslotted";
  double multipathMargin = 30.0;
  std::string fwdPolicy = "none";
  double dataInterval = 12.0;
  double holdMin = 8.0;
  double dataStart = 50.0;

  CommandLine cmd;
  cmd.AddValue ("simStop", "Simulation length (s)", simStop);
  cmd.AddValue ("nAuv", "Number of AUVs (plus one USV)", nAuv);
  cmd.AddValue ("beaconMode", "periodic or event", beaconMode);
  cmd.AddValue ("outDir", "Directory for CSV traces", outDir);
  cmd.AddValue ("beaconInterval", "Periodic HELLO interval (s)", beaconInterval);
  cmd.AddValue ("tMin", "Event-triggered minimum interval (s)", tMin);
  cmd.AddValue ("tMax", "Event-triggered keep-alive (s)", tMax);
  cmd.AddValue ("seed", "RNG seed (placement, current, ALOHA backoff)", seed);
  cmd.AddValue ("verboseTraces", "Write per-link / position CSVs", verboseTraces);
  cmd.AddValue ("bitRate", "ALOHA MAC bit rate (bit/s)", bitRate);
  cmd.AddValue ("mac", "unslotted or slotted ALOHA", macMode);
  cmd.AddValue ("multipathMargin", "Coherent-multipath stand-in (dB), not Bellhop", multipathMargin);
  cmd.AddValue ("fwdPolicy", "none, snr, hold, depth, or oracle next-hop", fwdPolicy);
  cmd.AddValue ("dataInterval", "AUV to USV data interval (s); 0 disables", dataInterval);
  cmd.AddValue ("holdMin", "Hold-aware minimum remaining time (s)", holdMin);
  cmd.AddValue ("dataStart", "First outer-AUV data time (s)", dataStart);
  cmd.Parse (argc, argv);

  if (macMode != "unslotted" && macMode != "slotted")
    {
      std::cerr << "mac must be unslotted or slotted\n";
      return 1;
    }
  if (fwdPolicy != "none" && fwdPolicy != "snr" && fwdPolicy != "hold"
      && fwdPolicy != "oracle" && fwdPolicy != "depth")
    {
      std::cerr << "fwdPolicy must be none, snr, hold, oracle, or depth\n";
      return 1;
    }

  RngSeedManager::SetSeed (seed);
  RngSeedManager::SetRun (1);
  g_phyCollisions = 0;

  phase1::AcousticLinkConfig link;
  link.multipathMarginDb = multipathMargin;
  const double rStar = phase1::RangeAtSnrThreshold (link);
  const double txRange = std::max (rStar * 1.35, 2000.0);
  const double pktBits = static_cast<double> (link.packetBits + 160);
  const double txTime = pktBits / bitRate;
  const double tProp = txRange / link.soundSpeed;
  const double slotSec = (macMode == "slotted") ? (txTime + tProp + 0.05) : 0.0;
  const double macMaxBackoff = (macMode == "slotted") ? 0.0 : 1.5;
  std::filesystem::create_directories (outDir);

  std::cout << "=========== Phase 1: topology discovery ===========\n";
  std::cout << "SOTA stack: Urick+Thorp+Wenz+BPSK, SNR gate "
            << link.snrThresholdDb << " dB\n";
  std::cout << "fc=" << link.fcKhz << " kHz  SL=" << link.slDb
            << " dB  MAC=" << macMode << " ALOHA  bitRate=" << bitRate << " bit/s\n";
  std::cout << "Decodable range R*(SNR=" << link.snrThresholdDb << " dB) = "
            << std::fixed << std::setprecision (1) << rStar << " m"
            << "  multipathMargin=" << multipathMargin << " dB\n";
  if (slotSec > 0.0)
    {
      std::cout << "Slotted ALOHA slot = T_tx + T_prop_max + guard = "
                << std::setprecision (3) << slotSec << " s\n";
    }
  std::cout << "Beacon mode: " << beaconMode << "   AUVs: " << nAuv
            << "   nodes: " << (nAuv + 1) << "   seed: " << seed
            << "   Tmax: " << tMax << " s   fwd: " << fwdPolicy
            << "   simStop: " << simStop << " s\n";
  std::cout << "===================================================\n";

  const uint32_t nNodes = nAuv + 1;
  NodeContainer nodes;
  nodes.Create (nNodes);

  PacketSocketHelper socketHelper;
  socketHelper.Install (nodes);

  AquaSimChannelHelper channel = AquaSimChannelHelper::Default ();
  channel.SetPropagation ("ns3::AquaSimRangePropagation");
  AquaSimHelper asHelper = AquaSimHelper::Default ();
  asHelper.SetChannel (channel.Create ());
  asHelper.SetMac ("ns3::AquaSimAloha",
                   "AckOn", IntegerValue (0),
                   "MinBackoff", DoubleValue (0.0),
                   "MaxBackoff", DoubleValue (macMaxBackoff),
                   "MaxTransmitDistance", DoubleValue (txRange),
                   "BitRate", DoubleValue (bitRate));
  asHelper.SetRouting ("ns3::AquaSimHelloRouting");
  asHelper.SetPhy ("ns3::AquaSimPhyCmn",
                   "Frequency", DoubleValue (link.fcKhz),
                   "PT", DoubleValue (10.0));

  NetDeviceContainer devices;
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      Ptr<AquaSimNetDevice> dev = CreateObject<AquaSimNetDevice> ();
      devices.Add (asHelper.Create (nodes.Get (i), dev));
      dev->GetPhy ()->SetTransRange (txRange);
      dev->GetPhy ()->TraceConnectWithoutContext ("RxColl", MakeCallback (&OnPhyCollision));
      if (dev->GetMac ())
        {
          dev->GetMac ()->AssignStreams (static_cast<int64_t> (seed) * 64 + i);
        }
    }

  Ptr<UniformRandomVariable> urv = CreateObject<UniformRandomVariable> ();
  urv->SetStream (static_cast<int64_t> (seed) * 17);

  const double currentScale = urv->GetValue (0.30, 0.60);
  const double currentPhase = urv->GetValue (0.0, 2500.0);

  std::vector<Vector> initPos (nNodes);
  std::vector<Vector> thrust (nNodes);
  initPos[0] = Vector (urv->GetValue (-80.0, 80.0), urv->GetValue (-80.0, 80.0), 8.0);
  thrust[0] = Vector (0.0, 0.0, 0.0);

  uint32_t nInner = nAuv;
  uint32_t nOuter = 0;
  if (nAuv >= 8)
    {
      nInner = 5;
      nOuter = nAuv - nInner;
    }

  auto placeRing = [&] (uint32_t startIdx, uint32_t count, double rLo, double rHi,
                        double ang0, bool outer, double swimLo, double swimHi) {
    for (uint32_t k = 0; k < count; ++k)
      {
        const uint32_t i = startIdx + k;
        const double ang = ang0 + (2.0 * M_PI * k) / std::max (1u, count)
                           + urv->GetValue (-0.22, 0.22);
        const double r = rStar * urv->GetValue (rLo, rHi);
        const double z = urv->GetValue (40.0, 160.0);
        initPos[i] = Vector (r * std::cos (ang), r * std::sin (ang), z);
        const double towardCenter = outer ? -1.0 : 1.0;
        const double swimRad = urv->GetValue (swimLo, swimHi) * towardCenter;
        const double swimTan = urv->GetValue (-0.35, 0.35);
        thrust[i] = Vector (swimRad * std::cos (ang) - swimTan * std::sin (ang),
                            swimRad * std::sin (ang) + swimTan * std::cos (ang),
                            0.0);
      }
  };

  if (fwdPolicy == "none")
    {
      // Discovery campaign: force R* crossings so links form and break.
      placeRing (1, nInner, 0.94, 0.995, 0.12, false, 1.40, 2.05);
      if (nOuter > 0)
        {
          placeRing (1 + nInner, nOuter, 1.015, 1.08, 0.31, true, 1.40, 2.05);
        }
    }
  else
    {
      // Forwarding campaign: inner ring stays a usable relay; outer needs 2 hops.
      placeRing (1, nInner, 0.62, 0.82, 0.12, false, 0.35, 0.70);
      if (nOuter > 0)
        {
          placeRing (1 + nInner, nOuter, 1.02, 1.10, 0.31, true, 0.90, 1.40);
        }
    }

  for (uint32_t i = 0; i < nNodes; ++i)
    {
      Ptr<MeanderingCurrentMobility> mob = CreateObject<MeanderingCurrentMobility> ();
      mob->SetPosition (initPos[i]);
      mob->SetThrust (thrust[i]);
      mob->SetCurrentScale (currentScale);
      mob->SetPhaseOffset (currentPhase + urv->GetValue (-80.0, 80.0));
      nodes.Get (i)->AggregateObject (mob);
    }

  std::vector<Ptr<TopologyDiscoveryApp>> apps;
  const Time timeout = Seconds ((beaconMode == "event") ? 3.0 * tMax : 3.0 * beaconInterval);
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      Ptr<TopologyDiscoveryApp> app = CreateObject<TopologyDiscoveryApp> ();
      app->Configure (i,
                      (i == 0) ? "usv" : "auv",
                      beaconMode,
                      link,
                      Seconds (beaconInterval),
                      Seconds (tMin),
                      Seconds (tMax),
                      timeout,
                      0.35,
                      4.0,
                      150.0);
      app->SetSlotSec (slotSec);
      nodes.Get (i)->AddApplication (app);
      app->SetStartTime (Seconds (0.1));
      app->SetStopTime (Seconds (simStop));
      apps.push_back (app);
    }
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      apps[i]->SetPeers (apps);
    }

  std::vector<AquaSimAddress> addrs (nNodes);
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      addrs[i] = AquaSimAddress::ConvertFrom (devices.Get (i)->GetAddress ());
    }
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      Ptr<AquaSimNetDevice> adev = DynamicCast<AquaSimNetDevice> (devices.Get (i));
      Ptr<AquaSimHelloRouting> rt = DynamicCast<AquaSimHelloRouting> (adev->GetRouting ());
      rt->SetDiscovery (apps[i]);
      rt->SetPolicy (fwdPolicy, holdMin);
      rt->SetLink (link);
      rt->SetAddresses (addrs);
      rt->SetIds (i, 0);
      rt->AssignStreams (static_cast<int64_t> (seed) * 128 + i + 7);
    }

  if (fwdPolicy != "none" && dataInterval > 0.0)
    {
      for (uint32_t i = 1; i < nNodes; ++i)
        {
          uint32_t seq = 0;
          for (double t = dataStart + 0.4 * static_cast<double> (i);
               t <= simStop - 20.0 + 1e-9;
               t += dataInterval)
            {
              const uint16_t seqCopy = static_cast<uint16_t> (++seq);
              Simulator::Schedule (Seconds (t), [i, seqCopy, &devices, &addrs, link] () {
                DataHeader dh;
                dh.SetSrc (static_cast<uint16_t> (i));
                dh.SetDst (0);
                dh.SetSeq (seqCopy);
                dh.SetHops (0);
                dh.SetTxMs (static_cast<uint32_t> (Simulator::Now ().GetSeconds () * 1000.0));
                const uint32_t want = std::max (dh.GetSerializedSize (), link.packetBits / 8);
                const uint32_t pad = (want > dh.GetSerializedSize ())
                                     ? (want - dh.GetSerializedSize ()) : 0;
                Ptr<Packet> pkt = Create<Packet> (pad);
                pkt->AddHeader (dh);
                devices.Get (i)->Send (pkt, addrs[0], 0);
              });
            }
        }
    }

  std::ofstream metrics (JoinPath (outDir, "awareness_" + beaconMode + ".csv"));
  std::ofstream delayf (JoinPath (outDir, "detection_delay_" + beaconMode + ".csv"));
  std::ofstream summary (JoinPath (outDir, "summary_" + beaconMode + ".txt"));
  std::ofstream metricsLine (JoinPath (outDir, "metrics.csv"));
  std::ofstream links;
  std::ofstream posf;
  std::ofstream predf;
  metrics << "time,true_edges,table_edges,tp,fp,fn,precision,recall,f1,stale,beacons,control_bps,budget_frac,n1hop,n2hop,unreachable,diameter\n";
  delayf << "src,dst,event,t_true,t_disc,delay_s\n";
  if (verboseTraces)
    {
      links.open (JoinPath (outDir, "links_" + beaconMode + ".csv"));
      posf.open (JoinPath (outDir, "positions_" + beaconMode + ".csv"));
      predf.open (JoinPath (outDir, "predictions_" + beaconMode + ".csv"));
      links << "time,src,dst,true_link,discovered,snr_db,ewma_snr_db,psucc,doppler_hz,hold_oracle_s,hold_disc_s,role_src,role_dst\n";
      posf << "time,id,role,x,y,z,vx,vy,vz\n";
      predf << "time,src,dst,true_link,discovered,snr_db,vrad,hold_oracle_s,hold_disc_s\n";
    }

  std::map<PairKey, int> lastTrue;
  std::map<PairKey, int> lastDisc;
  std::map<PairKey, double> tTrueUp;
  std::map<PairKey, double> tTrueDown;
  std::map<PairKey, std::vector<HoldSample>> holdHist;
  std::vector<double> upDelays;
  std::vector<double> downDelays;
  std::vector<double> holdErrs;
  std::vector<double> recSamples;
  std::vector<double> precSamples;
  std::vector<double> f1Samples;
  std::vector<double> trueEdgeSamples;
  std::vector<double> discEdgeSamples;
  std::vector<double> fracMultiSamples;
  std::vector<double> diamSamples;

  std::function<void ()> sample;
  sample = [&] () {
    const Time now = Simulator::Now ();
    const double t = now.GetSeconds ();
    if (t > simStop + 1e-9)
      {
        return;
      }

    auto posOf = [&] (uint32_t i) {
      return nodes.Get (i)->GetObject<MobilityModel> ()->GetPosition ();
    };
    auto velOf = [&] (uint32_t i) {
      return nodes.Get (i)->GetObject<MobilityModel> ()->GetVelocity ();
    };

    if (verboseTraces)
      {
        for (uint32_t i = 0; i < nNodes; ++i)
          {
            const Vector p = posOf (i);
            const Vector v = velOf (i);
            posf << t << "," << i << "," << apps[i]->GetRole () << ","
                 << p.x << "," << p.y << "," << p.z << ","
                 << v.x << "," << v.y << "," << v.z << "\n";
          }
      }

    std::set<PairKey> trueSet;
    std::set<PairKey> discSet;
    std::vector<std::vector<uint32_t>> adj (nNodes);
    for (uint32_t i = 0; i < nNodes; ++i)
      {
        for (uint32_t j = 0; j < nNodes; ++j)
          {
            if (i == j)
              {
                continue;
              }
            const Vector a = posOf (i);
            const Vector b = posOf (j);
            const double d = phase1::Distance3D (a.x, a.y, a.z, b.x, b.y, b.z);
            const double snr = phase1::SnrDb (d, link);
            const bool truth = snr >= link.snrThresholdDb;
            const auto table = apps[i]->NeighborsAlive (now);
            const bool disc = table.count (j) > 0;
            if (truth)
              {
                trueSet.insert ({i, j});
                adj[i].push_back (j);
              }
            if (disc)
              {
                discSet.insert ({i, j});
              }
            const Vector va = velOf (i);
            const Vector vb = velOf (j);
            const double vrad = phase1::RadialRelativeSpeed (a.x, a.y, a.z, va.x, va.y, va.z,
                                                             b.x, b.y, b.z, vb.x, vb.y, vb.z);
            double ewma = disc ? table.at (j).ewmaSnrDb : snr;
            double psucc = phase1::PacketSuccessProbability (snr, link);
            double fd = phase1::DopplerHz (vrad, link);
            const double holdOracle = phase1::PredictedHoldTimeSec (d, vrad, snr, 0.0, rStar, link);
            const double holdDisc = disc ? table.at (j).predictedHoldS : -1.0;
            if (verboseTraces)
              {
                links << t << "," << i << "," << j << "," << truth << "," << disc << ","
                      << snr << "," << ewma << "," << psucc << "," << fd << ","
                      << holdOracle << "," << holdDisc << ","
                      << apps[i]->GetRole () << "," << apps[j]->GetRole () << "\n";
                predf << t << "," << i << "," << j << "," << truth << "," << disc << ","
                      << snr << "," << vrad << "," << holdOracle << "," << holdDisc << "\n";
              }

            PairKey key {i, j};
            if (disc && holdDisc >= 0.0 && holdDisc < 1e8)
              {
                auto &hist = holdHist[key];
                hist.push_back ({t, holdDisc});
                while (!hist.empty () && t - hist.front ().t > 60.0)
                  {
                    hist.erase (hist.begin ());
                  }
              }
            const int tNow = truth ? 1 : 0;
            const int dNow = disc ? 1 : 0;
            if (tNow == 1 && dNow == 0 && !tTrueUp.count (key))
              {
                tTrueUp[key] = t;
              }
            if (lastTrue.count (key) && lastTrue[key] == 1 && tNow == 0)
              {
                tTrueDown[key] = t;
                for (auto const &hs : holdHist[key])
                  {
                    const double actual = t - hs.t;
                    if (actual >= 0.0)
                      {
                        holdErrs.push_back (std::fabs (hs.hold - actual));
                      }
                  }
                holdHist[key].clear ();
              }
            if (lastDisc.count (key) && lastDisc[key] == 0 && dNow == 1 && tTrueUp.count (key))
              {
                const double delay = t - tTrueUp[key];
                upDelays.push_back (delay);
                delayf << i << "," << j << ",link_up," << tTrueUp[key] << "," << t << "," << delay << "\n";
                tTrueUp.erase (key);
              }
            if (lastDisc.count (key) && lastDisc[key] == 1 && dNow == 0 && tTrueDown.count (key))
              {
                const double delay = t - tTrueDown[key];
                downDelays.push_back (delay);
                delayf << i << "," << j << ",link_down," << tTrueDown[key] << "," << t << "," << delay << "\n";
                tTrueDown.erase (key);
              }
            lastTrue[key] = tNow;
            lastDisc[key] = dNow;
          }
      }

    uint32_t tp = 0;
    uint32_t fp = 0;
    uint32_t fn = 0;
    for (auto const &e : discSet)
      {
        if (trueSet.count (e))
          {
            tp++;
          }
        else
          {
            fp++;
          }
      }
    for (auto const &e : trueSet)
      {
        if (!discSet.count (e))
          {
            fn++;
          }
      }
    const double precision = (tp + fp) ? double (tp) / (tp + fp) : 1.0;
    const double recall = (tp + fn) ? double (tp) / (tp + fn) : 1.0;
    const double f1 = (precision + recall) ? 2 * precision * recall / (precision + recall) : 0.0;
    uint64_t beacons = 0;
    uint64_t bits = 0;
    for (auto const &app : apps)
      {
        beacons += app->BeaconsSent ();
        bits += app->ControlBits ();
      }
    const double bps = (t > 0.5) ? bits / t : 0.0;
    const HopStats hops = ComputeHops (adj);
    const uint32_t reach = hops.n1 + hops.n2plus;
    const double fracMulti = reach ? double (hops.n2plus) / reach : 0.0;
    metrics << t << "," << trueSet.size () << "," << discSet.size () << ","
            << tp << "," << fp << "," << fn << ","
            << precision << "," << recall << "," << f1 << ","
            << fp << "," << beacons << "," << bps << "," << (bps / 2000.0) << ","
            << hops.n1 << "," << hops.n2plus << "," << hops.unreachable << ","
            << hops.diameter << "\n";
    if (t >= 20.0)
      {
        recSamples.push_back (recall);
        precSamples.push_back (precision);
        f1Samples.push_back (f1);
        trueEdgeSamples.push_back (static_cast<double> (trueSet.size ()));
        discEdgeSamples.push_back (static_cast<double> (discSet.size ()));
        fracMultiSamples.push_back (fracMulti);
        diamSamples.push_back (static_cast<double> (hops.diameter));
      }

    Simulator::Schedule (Seconds (sampleDt), sample);
  };
  Simulator::Schedule (Seconds (1.0), sample);

  Simulator::Stop (Seconds (simStop));
  Simulator::Run ();

  uint64_t beacons = 0;
  uint64_t bits = 0;
  uint64_t helloRx = 0;
  uint64_t snrDrops = 0;
  uint64_t bpskDrops = 0;
  uint64_t routingColl = 0;
  uint64_t dataOrig = 0;
  uint64_t dataFwd = 0;
  uint64_t dataDeliv = 0;
  uint64_t dropNoRoute = 0;
  uint64_t dropLoop = 0;
  uint64_t staleFwd = 0;
  uint64_t dyingFwd = 0;
  uint64_t dataSnrDrops = 0;
  uint64_t dataBpskDrops = 0;
  double delaySum = 0.0;
  double hopSum = 0.0;
  for (uint32_t i = 0; i < nNodes; ++i)
    {
      beacons += apps[i]->BeaconsSent ();
      bits += apps[i]->ControlBits ();
      helloRx += apps[i]->HellosRx ();
      snrDrops += apps[i]->SnrDrops ();
      bpskDrops += apps[i]->BpskDrops ();
      Ptr<AquaSimNetDevice> dev = DynamicCast<AquaSimNetDevice> (devices.Get (i));
      Ptr<AquaSimHelloRouting> rt = DynamicCast<AquaSimHelloRouting> (dev->GetRouting ());
      if (rt)
        {
          routingColl += rt->CollisionDrops ();
          dataOrig += rt->DataOriginated ();
          dataFwd += rt->DataForwarded ();
          dataDeliv += rt->DataDelivered ();
          dropNoRoute += rt->DropNoRoute ();
          dropLoop += rt->DropLoop ();
          staleFwd += rt->StaleForwards ();
          dyingFwd += rt->DyingForwards ();
          dataSnrDrops += rt->DataSnrDrops ();
          dataBpskDrops += rt->DataBpskDrops ();
          delaySum += rt->DelaySumS ();
          hopSum += rt->HopSum ();
        }
    }
  auto meanOf = [] (const std::vector<double> &v) {
    if (v.empty ())
      {
        return 0.0;
      }
    double s = 0.0;
    for (double x : v)
      {
        s += x;
      }
    return s / v.size ();
  };

  const double meanBps = bits / simStop;
  summary << "Phase 1 topology discovery (ALOHA + scaled topology)\n";
  summary << "beaconMode=" << beaconMode << "\n";
  summary << "seed=" << seed << "\n";
  summary << "nUSV=1 nAUV=" << nAuv << " nNodes=" << nNodes << " simStop=" << simStop << "\n";
  summary << "R_star_m=" << rStar << " txRange_m=" << txRange << "\n";
  summary << "mac=" << macMode << "_ALOHA bitRate=" << bitRate << " AckOn=0 slot_s=" << slotSec << "\n";
  summary << "tMin=" << tMin << " tMax=" << tMax << " beaconInterval=" << beaconInterval << "\n";
  summary << "currentScale=" << currentScale << " currentPhase=" << currentPhase << "\n";
  summary << "fc_kHz=" << link.fcKhz << " SL_dB=" << link.slDb
          << " SNRth_dB=" << link.snrThresholdDb
          << " multipathMargin_dB=" << link.multipathMarginDb << "\n";
  summary << "beacons=" << beacons << "\n";
  summary << "control_bits=" << bits << "\n";
  summary << "mean_control_bps=" << meanBps << "\n";
  summary << "budget_2kbps_frac=" << meanBps / 2000.0 << "\n";
  summary << "hello_rx=" << helloRx << "\n";
  summary << "snr_drops=" << snrDrops << "\n";
  summary << "bpsk_drops=" << bpskDrops << "\n";
  summary << "phy_collisions=" << g_phyCollisions << "\n";
  summary << "routing_collision_drops=" << routingColl << "\n";
  summary << "link_up_events=" << upDelays.size ()
          << " mean_up_delay_s=" << meanOf (upDelays) << "\n";
  summary << "link_down_events=" << downDelays.size ()
          << " mean_down_delay_s=" << meanOf (downDelays) << "\n";
  summary << "mean_precision=" << meanOf (precSamples) << "\n";
  summary << "mean_recall=" << meanOf (recSamples) << "\n";
  summary << "mean_f1=" << meanOf (f1Samples) << "\n";
  summary << "mean_true_edges=" << meanOf (trueEdgeSamples) << "\n";
  summary << "mean_disc_edges=" << meanOf (discEdgeSamples) << "\n";
  summary << "mean_frac_multihop=" << meanOf (fracMultiSamples) << "\n";
  summary << "mean_diameter=" << meanOf (diamSamples) << "\n";
  summary << "hold_mae_s=" << meanOf (holdErrs) << " hold_n=" << holdErrs.size () << "\n";
  const double pdr = dataOrig ? double (dataDeliv) / dataOrig : 0.0;
  const double meanDelay = dataDeliv ? delaySum / dataDeliv : 0.0;
  const double meanHops = dataDeliv ? hopSum / dataDeliv : 0.0;
  const double txJ = 10.0 * (static_cast<double> (link.packetBits) / bitRate)
                     * static_cast<double> (beacons + dataOrig + dataFwd);
  summary << "fwdPolicy=" << fwdPolicy << " holdMin=" << holdMin
          << " dataInterval=" << dataInterval << " dataStart=" << dataStart << "\n";
  summary << "data_orig=" << dataOrig << " data_fwd=" << dataFwd << " data_deliv=" << dataDeliv << "\n";
  summary << "pdr=" << pdr << " mean_e2e_s=" << meanDelay << " mean_hops=" << meanHops << "\n";
  summary << "stale_fwd=" << staleFwd << " dying_fwd=" << dyingFwd
          << " drop_noroute=" << dropNoRoute << " drop_loop=" << dropLoop << "\n";
  summary << "data_snr_drops=" << dataSnrDrops << " data_bpsk_drops=" << dataBpskDrops
          << " tx_energy_J=" << txJ << "\n";
  summary.flush ();

  metricsLine << "seed,mode,n_nodes,beacons,control_bps,budget_frac,precision,recall,f1,"
              << "up_n,up_delay,down_n,down_delay,true_edges,disc_edges,frac_multihop,"
              << "diameter,phy_collisions,hello_rx,snr_drops,bpsk_drops,hold_mae,hold_n,"
              << "mac,tMin,tMax,multipath_margin,r_star_m,slot_s,fwd_policy,data_interval,data_orig,data_fwd,data_deliv,pdr,mean_e2e_s,mean_hops,stale_fwd,dying_fwd,drop_noroute,drop_loop,data_snr_drops,data_bpsk_drops,tx_energy_J\n";
  metricsLine << seed << "," << beaconMode << "," << nNodes << "," << beacons << ","
              << meanBps << "," << (meanBps / 2000.0) << ","
              << meanOf (precSamples) << "," << meanOf (recSamples) << "," << meanOf (f1Samples) << ","
              << upDelays.size () << "," << meanOf (upDelays) << ","
              << downDelays.size () << "," << meanOf (downDelays) << ","
              << meanOf (trueEdgeSamples) << "," << meanOf (discEdgeSamples) << ","
              << meanOf (fracMultiSamples) << "," << meanOf (diamSamples) << ","
              << g_phyCollisions << "," << helloRx << "," << snrDrops << "," << bpskDrops << ","
              << meanOf (holdErrs) << "," << holdErrs.size () << ","
              << macMode << "," << tMin << "," << tMax << "," << multipathMargin << ","
              << rStar << "," << slotSec << ","
              << fwdPolicy << "," << dataInterval << "," << dataOrig << "," << dataFwd << "," << dataDeliv << ","
              << pdr << "," << meanDelay << "," << meanHops << ","
              << staleFwd << "," << dyingFwd << "," << dropNoRoute << "," << dropLoop << ","
              << dataSnrDrops << "," << dataBpskDrops << "," << txJ << "\n";

  std::cout << "beacons=" << beacons
            << "  mean_control_bps=" << meanBps
            << "  2kbps_frac=" << meanBps / 2000.0 << "\n";
  std::cout << "hello_rx=" << helloRx
            << "  phy_collisions=" << g_phyCollisions
            << "  snr_drops=" << snrDrops
            << "  bpsk_drops=" << bpskDrops << "\n";
  std::cout << "precision=" << meanOf (precSamples)
            << "  recall=" << meanOf (recSamples)
            << "  frac_multihop=" << meanOf (fracMultiSamples)
            << "  diameter=" << meanOf (diamSamples) << "\n";
  std::cout << "link_up_events=" << upDelays.size ()
            << "  mean_up_delay_s=" << meanOf (upDelays) << "\n";
  std::cout << "link_down_events=" << downDelays.size ()
            << "  mean_down_delay_s=" << meanOf (downDelays) << "\n";
  std::cout << "hold_mae_s=" << meanOf (holdErrs) << "  n=" << holdErrs.size () << "\n";
  if (fwdPolicy != "none")
    {
      std::cout << "fwd=" << fwdPolicy
                << "  data_orig=" << dataOrig
                << "  deliv=" << dataDeliv
                << "  pdr=" << pdr
                << "  e2e_s=" << meanDelay
                << "  hops=" << meanHops
                << "  stale=" << staleFwd
                << "  dying=" << dyingFwd
                << "  noroute=" << dropNoRoute
                << "  snrDrop=" << dataSnrDrops
                << "  E_J=" << txJ << "\n";
    }
  std::cout << "traces: " << outDir << "\nfin.\n";

  Simulator::Destroy ();
  return 0;
}
