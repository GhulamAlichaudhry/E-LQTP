// elqtp-protocol.h
//
// E-LQTP (SPEC.md Part 2) on top of the LQARP baseline. Same
// ChannelGate / kBerFloor as LqarpProtocol. beta_1=0, beta_2=0 and
// a trigger that never fires recover LQARP exactly.

#ifndef ELQTP_ELQTP_PROTOCOL_H
#define ELQTP_ELQTP_PROTOCOL_H

#include "lqarp-protocol.h"

#include <array>
#include <cstdint>
#include <deque>
#include <limits>
#include <vector>

namespace elqtp {

enum class BroadcastMode {
    EventTriggered, // SPEC 2.4
    FixedPeriodic   // Section 4.3 ablation: Broadcast_k every T_ctrl
};

// Caps lambda*sqrt(S_k) on the event trigger. Equals sqrt(rMeas):
// the original heuristic scale, used because P_forecast is never
// measurement-corrected and would otherwise inflate epsilon_k
// without bound (SPEC 2.3 addendum, Step 45 Option B).
constexpr double kSCapDb = 2.0;

struct ElqtpConfig : LqarpConfig {
    double beta_1 = 0.0;             // default identity; SWEPT at run time
    double beta_2 = 0.0;             // default identity; SWEPT at run time
    double epsilon_0 = 2.0;          // Step 46; 70-80% ZOH-init contour
    double s_cap = kSCapDb;          // dB; min(sqrt(S_k), s_cap)
    double lambda = 1.0;             // first-pass
    uint32_t W_mp = 3;               // first-pass median window
    uint32_t W = 5;                  // first-pass persistence window
    double rho = 0.6;                // first-pass
    double dt = 1.0;                 // EKF predict step (s)
    double fdRangeM = 10.0;          // finite-difference range (m)
    double qPos = 1.0;               // process noise, position
    double qVel = 0.1;               // process noise, velocity
    double qSnr = 1.0;               // process noise, SNR
    double rMeas = 4.0;              // measurement noise R_k (dB^2)
    BroadcastMode broadcastMode = BroadcastMode::EventTriggered;
    double T_ctrl = 5.0;             // first-pass periodic ablation (s)
    // 0 = energy_j_zoh moves only with a pose HELLO. >0 = overwrite
    // energy_j_zoh on this grid without touching pose or velocity.
    double energyRefreshS = 0.0;
    // 0 = full-precision residual on that beacon. 8 or 16 = uniform
    // quantizer over [0, E_ini]. Addressing is a separate field.
    int energyQuantBits = 0;
    int energyAddrBits = 8;
    // Step 5: a HELLO / energy beacon from j writes i's hold for j only if
    // i demodulates it (ChannelGate::receptionOk on j->i). false restores
    // the pre-Step-5 network-wide write (diagnostic A/B only).
    bool helloRxGate = true;
};

struct ElqtpReward {
    double c_lin = 0.0;
    double c_pred = 0.0;
    double c_ene = 0.0;
    double c_del = 0.0;
    double c_drift = 0.0;
    double c_nei = 0.0;
    double v_rel = 0.0;
    double e_k = 0.0;
    double R = 0.0;
};

// Per-neighbor EKF (7-dim: p_ij, pdot_ij, SNR_ij).
struct NeighborEkf {
    std::array<double, 7> x{};
    std::array<double, 49> P{}; // row-major 7x7
    // SPEC 2.2 addendum: open-loop forecast, predict-only, never updated.
    std::array<double, 7> xForecast{};
    std::array<double, 49> PForecast{};
    std::deque<double> zWindow;
    std::deque<int> exceedHist; // 1 if |e_m^{trigger}| >= epsilon_m
    double e_k = 0.0;
    double e_km1 = 0.0;
    double epsilon_k = 0.0;
    double S_k = 0.0;
    // SPEC 2.3 addendum: forecast-vs-truth innovation (trigger only).
    double eTrigger = 0.0;
    double STrigger = 0.0;
    double epsilonTrigger = 0.0;
    // Running maxima for Step 44 (diagnostic; not used by the trigger).
    double maxAbsETrigger = 0.0;
    double maxAbsETriggerUnheard = 0.0;
    double maxEpsilonTriggerUnheard = 0.0;
    int broadcast_k = 0;
    double vx_j_zoh = 0.0;
    double vy_j_zoh = 0.0;
    double vz_j_zoh = 0.0;
    // Last HELLO's pose and residual energy. Routing filters read these,
    // not the live MobilityModel copy in nodes_[j].
    double x_j_zoh = 0.0;
    double y_j_zoh = 0.0;
    double z_j_zoh = 0.0;
    double energy_j_zoh = 0.0;
    double query_z_j_zoh = 0.0; // Bellhop receiver depth at that HELLO
    bool initialized = false;
    // SPEC 2.1: pdot_j is last received broadcast. False until the
    // first Broadcast_k=1 (or periodic HELLO) copies neighbor velocity.
    bool zohHeard = false;
    double lastZohTime = std::numeric_limits<double>::quiet_NaN ();
    double firstBroadcastTime = std::numeric_limits<double>::quiet_NaN ();
    uint64_t nBroadcastRising = 0;
    // Received-only z_k: set when a packet from j is demodulated at i
    // (ChannelGate::receptionOk on the j->i link). tick() runs
    // updatePair only on the next tick after such a reception, with the
    // SNR sampled at that reception; otherwise both tracks predict only.
    bool rxPending = false;
    double zRxPending = std::numeric_limits<double>::quiet_NaN ();
    uint64_t nRx = 0;
};

class ElqtpProtocol {
public:
    ElqtpProtocol(ChannelGate& gate,
                  ElqtpConfig cfg,
                  std::vector<LqarpNode> nodes);

    const ElqtpConfig& config() const { return cfg_; }
    const std::vector<LqarpNode>& nodes() const { return nodes_; }
    double rRangeM() const { return rRangeM_; }

    // Part 1.2 three-condition set (c_nei still uses this, SPEC 2.8).
    std::vector<uint32_t> lqarpCandidateSet(uint32_t i) const;

    // I_ELQTP = N_range ∩ N_SNR ∩ N_depth ∩ N_stab
    std::vector<uint32_t> candidateSet(uint32_t i) const;
    bool inNRange(uint32_t i, uint32_t j) const;
    bool inNSnr(uint32_t i, uint32_t j) const;
    bool inNDepth(uint32_t i, uint32_t j) const;
    bool inNStab(uint32_t i, uint32_t j) const;

    uint32_t numberSj(uint32_t j) const; // |I_LQARP(s_j)|

    // SPEC 2.1
    void relativeState(uint32_t i, uint32_t j,
                       double& pijx, double& pijy, double& pijz,
                       double& vijx, double& vijy, double& vijz) const;
    double vRel(uint32_t i, uint32_t j) const;

    static double sigmoid(double u);

    // SPEC 2.6–2.7 (c_lin uses the shared BER floor).
    double cPred(uint32_t i, uint32_t j) const;
    double cDrift(uint32_t i, uint32_t j) const;

    ElqtpReward reward(uint32_t i, uint32_t j) const;

    double qValue(uint32_t i, uint32_t j) const;
    void updateQ(uint32_t i, uint32_t j);
    void learnFrom(uint32_t i);
    void learnFrom(uint32_t i, const std::vector<uint32_t>& actions);
    int nextHop(uint32_t i) const;
    int nextHop(uint32_t i, const std::vector<uint32_t>& actions) const;

    // SPEC 1.5. D = N_range ∩ N_SNR (no N_depth, no N_stab).
    // I(s_j) in the two-hop filter is I_ELQTP.
    std::vector<uint32_t> detourSet(uint32_t i) const;
    std::vector<uint32_t> detourTargets(uint32_t i,
                                        uint32_t sinkId,
                                        const std::vector<uint32_t>& visited) const;

    // EKF tick: predict, measure, median, innovation, trigger, update.
    void tick(double dt);

    double simTime() const { return simTime_; }
    // Event/periodic HELLOs plus one-time bootstrap discoveries.
    // Position-trigger HELLOs plus bootstrap. Energy-only beacons are excluded.
    uint64_t controlTxCount() const { return eventHelloCount_ + bootstrapHelloCount_; }
    uint64_t eventHelloCount() const { return eventHelloCount_; }
    uint64_t bootstrapHelloCount() const { return bootstrapHelloCount_; }
    uint64_t energyHelloCount() const { return energyHelloCount_; }
    int energyBeaconBits() const
    {
        if (!(cfg_.energyRefreshS > 0.0)) {
            return 0;
        }
        return cfg_.energyQuantBits + cfg_.energyAddrBits;
    }
    uint64_t broadcastKOnes() const { return broadcastKOnes_; }
    uint64_t broadcastRising() const { return broadcastRising_; }
    uint64_t nanMeasCount() const { return nanMeasCount_; }
    double maxAbsInnovation() const { return maxAbsInnovation_; }
    double maxAbsTriggerInnovation() const { return maxAbsTriggerInnovation_; }

    const NeighborEkf& ekf(uint32_t i, uint32_t j) const;
    bool zohHeard(uint32_t i, uint32_t j) const;
    double lastZohTime(uint32_t i, uint32_t j) const;

    // Test seams for Part 2 unit tests (do not use as protocol API).
    void forceInnovation(uint32_t i, uint32_t j, double e_k, double epsilon_k);
    void pushExceedFlag(uint32_t i, uint32_t j, bool exceed);
    void recomputeBroadcast(uint32_t i, uint32_t j);
    void setNeighborVelocityZoh(uint32_t i, uint32_t j,
                                double vx, double vy, double vz);
    // Skip ingestBroadcastVelocity for neighbor j (event and periodic).
    // Does not block the one-time bootstrap discovery.
    void setHelloSuppressed(uint32_t j, bool suppressed);
    // Skip the one-time bootstrap write for neighbor j. Later
    // broadcast_k / T_ctrl refreshes are unchanged.
    void setBootstrapSuppressed(uint32_t j, bool suppressed);
    void setBroadcastK(uint32_t i, uint32_t j, int broadcast_k);
    void flushEventControlTx();

    ChannelSample linkSample(uint32_t i, uint32_t j) const;

    // Received-only measurement path. Node rx demodulates a packet sent
    // by tx iff ChannelGate::receptionOk(linkSample(tx, rx)). Returns
    // whether it was received. broadcastFrom applies that to every rx.
    bool noteReception(uint32_t rx, uint32_t tx);
    void broadcastFrom(uint32_t tx);
    uint64_t receptionCount() const { return receptionCount_; }
    uint64_t measuredUpdates() const { return measuredUpdates_; }
    uint64_t silentPredicts() const { return silentPredicts_; }

    // Held filters and N_stab only. Does not call noteBootstrap.
    bool peekFilter(uint32_t i, uint32_t j, FilterPeek& out) const;

    void setEnergy(uint32_t i, double joules);
    double energy(uint32_t i) const;
    void setKinematics(uint32_t i, double x, double y, double z,
                       double vx, double vy, double vz);

private:
    ChannelGate* gate_;
    ElqtpConfig cfg_;
    std::vector<LqarpNode> nodes_;
    double rRangeM_;
    std::vector<std::vector<double>> Q_;
    // Mutable so the const candidate-set path can record a one-time
    // bootstrap discovery, the same way LQARP's noteDiscovery writes
    // its frozen neighbor from a const filter.
    mutable std::vector<std::vector<NeighborEkf>> ekf_;
    std::vector<char> helloSuppressed_;
    std::vector<char> bootstrapSuppressed_;
    double simTime_ = 0.0;
    double nextPeriodicTime_ = 0.0;
    uint64_t eventHelloCount_ = 0;
    mutable uint64_t bootstrapHelloCount_ = 0;
    uint64_t energyHelloCount_ = 0;
    double nextEnergyRefresh_ = 0.0;
    uint64_t broadcastKOnes_ = 0;
    uint64_t broadcastRising_ = 0;
    std::vector<int> prevBroadcast_;
    uint64_t nanMeasCount_ = 0;
    double maxAbsInnovation_ = 0.0;
    double maxAbsTriggerInnovation_ = 0.0;
    mutable uint64_t receptionCount_ = 0;
    uint64_t measuredUpdates_ = 0;
    uint64_t silentPredicts_ = 0;
    bool noteReceptionImpl(uint32_t rx, uint32_t tx) const;
    bool helloReaches(uint32_t rx, uint32_t tx) const;

    void checkIndex(uint32_t i) const;
    NeighborEkf& slot(uint32_t i, uint32_t j);
    const NeighborEkf& slot(uint32_t i, uint32_t j) const;
    void initEkf(uint32_t i, uint32_t j);
    void applyPredict(std::array<double, 7>& x,
                      std::array<double, 49>& P,
                      double dt,
                      double zRx);
    void predictPair(uint32_t i, uint32_t j, double dt);
    void predictForecast(uint32_t i, uint32_t j, double dt);
    void resetForecast(NeighborEkf& s) const;
    void ingestBroadcastVelocity(NeighborEkf& s, uint32_t i, uint32_t j,
                                 double vx_j, double vy_j, double vz_j) const;
    // First live N_range ∩ N_SNR. Not a trigger refresh.
    void noteBootstrap(uint32_t i, uint32_t j) const;
    bool liveInRange(uint32_t i, uint32_t j) const;
    bool liveInSnr(uint32_t i, uint32_t j) const;
    void updatePair(uint32_t i, uint32_t j, double z_k);
    double triggerEpsilon(double S) const;
    double dSnrDRange(double rangeM, double receiverZ) const;
    void emitPeriodicControl();
    void refreshEnergyOnly();
    double quantizeEnergy(double joules) const;
    void clearBroadcastFlags();
    void countEventControlTx();
};

} // namespace elqtp

#endif // ELQTP_ELQTP_PROTOCOL_H
