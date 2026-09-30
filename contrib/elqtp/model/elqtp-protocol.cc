// elqtp-protocol.cc
//
// E-LQTP SPEC.md Part 2. BER floor comes only from link-quality.cc.

#include "elqtp-protocol.h"

#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>
#include <vector>

namespace elqtp {
namespace {

constexpr int kDim = 7;

int
idx(int r, int c)
{
    return r * kDim + c;
}

void
zero49(std::array<double, 49>& a)
{
    a.fill(0.0);
}

void
ident49(std::array<double, 49>& a)
{
    zero49(a);
    for (int i = 0; i < kDim; ++i) {
        a[static_cast<size_t>(idx(i, i))] = 1.0;
    }
}

void
mul49(const std::array<double, 49>& A,
      const std::array<double, 49>& B,
      std::array<double, 49>& C)
{
    zero49(C);
    for (int r = 0; r < kDim; ++r) {
        for (int c = 0; c < kDim; ++c) {
            double s = 0.0;
            for (int k = 0; k < kDim; ++k) {
                s += A[static_cast<size_t>(idx(r, k))] * B[static_cast<size_t>(idx(k, c))];
            }
            C[static_cast<size_t>(idx(r, c))] = s;
        }
    }
}

void
transpose49(const std::array<double, 49>& A, std::array<double, 49>& At)
{
    for (int r = 0; r < kDim; ++r) {
        for (int c = 0; c < kDim; ++c) {
            At[static_cast<size_t>(idx(c, r))] = A[static_cast<size_t>(idx(r, c))];
        }
    }
}

double
medianCopy(std::deque<double> w)
{
    if (w.empty()) {
        return std::numeric_limits<double>::quiet_NaN();
    }
    std::sort(w.begin(), w.end());
    const size_t n = w.size();
    if (n % 2 == 1) {
        return w[n / 2];
    }
    return 0.5 * (w[n / 2 - 1] + w[n / 2]);
}

} // namespace

ElqtpProtocol::ElqtpProtocol(ChannelGate& gate,
                             ElqtpConfig cfg,
                             std::vector<LqarpNode> nodes)
    : gate_(&gate),
      cfg_(cfg),
      nodes_(std::move(nodes)),
      rRangeM_(cfg.rRangeM)
{
    if (nodes_.empty()) {
        throw std::runtime_error("ElqtpProtocol: empty node list");
    }
    for (size_t i = 0; i < nodes_.size(); ++i) {
        nodes_[i].id = static_cast<uint32_t>(i);
    }
    if (!std::isfinite(rRangeM_)) {
        rRangeM_ = gate_->rangeAtSnrThreshold();
    }
    const size_t n = nodes_.size();
    Q_.assign(n, std::vector<double>(n, 0.0));
    ekf_.assign(n, std::vector<NeighborEkf>(n));
    helloSuppressed_.assign(n, 0);
    bootstrapSuppressed_.assign(n, 0);
    prevBroadcast_.assign(n * n, 0);
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            if (i != j) {
                initEkf(i, j);
            }
        }
    }
    // Fixed-periodic ablation (SPEC Part 4): first control round at t=0.
    if (cfg_.broadcastMode == BroadcastMode::FixedPeriodic) {
        emitPeriodicControl();
        nextPeriodicTime_ = cfg_.T_ctrl;
    }
    if (cfg_.energyRefreshS > 0.0) {
        nextEnergyRefresh_ = cfg_.energyRefreshS;
    }
}

void
ElqtpProtocol::checkIndex(uint32_t i) const
{
    if (i >= nodes_.size()) {
        throw std::out_of_range("ElqtpProtocol: node index out of range");
    }
}

NeighborEkf&
ElqtpProtocol::slot(uint32_t i, uint32_t j)
{
    checkIndex(i);
    checkIndex(j);
    return ekf_[i][j];
}

const NeighborEkf&
ElqtpProtocol::slot(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    return ekf_[i][j];
}

const NeighborEkf&
ElqtpProtocol::ekf(uint32_t i, uint32_t j) const
{
    return slot(i, j);
}

void
ElqtpProtocol::initEkf(uint32_t i, uint32_t j)
{
    NeighborEkf& s = ekf_[i][j];
    const LqarpNode& a = nodes_[i];
    const LqarpNode& b = nodes_[j];
    s.x[0] = a.x - b.x;
    s.x[1] = a.y - b.y;
    s.x[2] = a.z - b.z;
    // SPEC 2.1: pdot_j is the last received broadcast, ZOH between
    // broadcasts. No packet has arrived yet, so ZOH starts at 0.
    // Copying true neighbor velocity here would make constant-drift
    // Scenario II a process-model match and silence the trigger.
    s.vx_j_zoh = 0.0;
    s.vy_j_zoh = 0.0;
    s.vz_j_zoh = 0.0;
    s.x[3] = a.vx - s.vx_j_zoh;
    s.x[4] = a.vy - s.vy_j_zoh;
    s.x[5] = a.vz - s.vz_j_zoh;
    // SNR state matches the measurement path (queryDepthM / acousticZ),
    // not kinematic z. The sink's towed transducer is acousticZ=50 m.
    s.x[6] = linkSample(i, j).snr_db;
    ident49(s.P);
    for (int k = 0; k < 3; ++k) {
        s.P[static_cast<size_t>(idx(k, k))] = 10.0;
        s.P[static_cast<size_t>(idx(k + 3, k + 3))] = 1.0;
    }
    s.P[static_cast<size_t>(idx(6, 6))] = 4.0;
    s.e_k = 0.0;
    s.e_km1 = 0.0;
    s.epsilon_k = cfg_.epsilon_0;
    s.S_k = cfg_.rMeas;
    s.xForecast = s.x;
    s.PForecast = s.P;
    s.eTrigger = 0.0;
    s.STrigger = cfg_.rMeas;
    s.epsilonTrigger = cfg_.epsilon_0;
    s.maxAbsETrigger = 0.0;
    s.maxAbsETriggerUnheard = 0.0;
    s.maxEpsilonTriggerUnheard = cfg_.epsilon_0;
    s.broadcast_k = 0;
    s.initialized = true;
    s.zohHeard = false;
    s.lastZohTime = std::numeric_limits<double>::quiet_NaN();
    s.firstBroadcastTime = std::numeric_limits<double>::quiet_NaN();
    s.nBroadcastRising = 0;
}

ChannelSample
ElqtpProtocol::linkSample(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    const LqarpNode& a = nodes_[i];
    const LqarpNode& b = nodes_[j];
    return gate_->queryLink(a.x, a.y, a.queryDepthM(),
                            b.x, b.y, b.queryDepthM());
}

bool
ElqtpProtocol::noteReceptionImpl(uint32_t rx, uint32_t tx) const
{
    if (rx == tx) {
        return false;
    }
    checkIndex(rx);
    checkIndex(tx);
    // Same reception condition as a data hop (tx -> rx): valid sample,
    // not near pressure release, SNR >= threshold.
    if (!gate_->receptionOk(linkSample(tx, rx))) {
        return false;
    }
    NeighborEkf& s = ekf_[rx][tx];
    s.rxPending = true;
    // z_k keeps the EKF's measurement convention for pair (rx, tx)
    // (same argument order as h / initEkf), sampled at reception time.
    s.zRxPending = linkSample(rx, tx).snr_db;
    ++s.nRx;
    ++receptionCount_;
    return true;
}

bool
ElqtpProtocol::helloReaches(uint32_t rx, uint32_t tx) const
{
    if (!cfg_.helloRxGate) {
        return true;
    }
    // Same reception condition as a data hop and as noteReceptionImpl.
    return gate_->receptionOk(linkSample(tx, rx));
}

bool
ElqtpProtocol::noteReception(uint32_t rx, uint32_t tx)
{
    return noteReceptionImpl(rx, tx);
}

void
ElqtpProtocol::broadcastFrom(uint32_t tx)
{
    for (uint32_t rx = 0; rx < nodes_.size(); ++rx) {
        if (rx != tx) {
            noteReceptionImpl(rx, tx);
        }
    }
}

bool
ElqtpProtocol::liveInRange(uint32_t i, uint32_t j) const
{
    if (i == j) {
        return false;
    }
    const LqarpNode& a = nodes_[i];
    const LqarpNode& b = nodes_[j];
    return ChannelGate::distance3D(a.x, a.y, a.z, b.x, b.y, b.z) < rRangeM_;
}

bool
ElqtpProtocol::liveInSnr(uint32_t i, uint32_t j) const
{
    if (i == j) {
        return false;
    }
    return !gate_->sampleFailsCandidateSnr(linkSample(i, j));
}

void
ElqtpProtocol::noteBootstrap(uint32_t i, uint32_t j) const
{
    if (i == j) {
        return;
    }
    checkIndex(i);
    checkIndex(j);
    if (bootstrapSuppressed_[j]) {
        return;
    }
    NeighborEkf& s = ekf_[i][j];
    if (s.zohHeard) {
        return;
    }
    // Same live gate as LQARP/RLOR noteDiscovery: N_range ∩ N_SNR.
    // N_depth is applied later to the stored z, so a deeper neighbor
    // is kept for the detour set. Not a Broadcast_k refresh.
    if (!(liveInRange(i, j) && liveInSnr(i, j))) {
        return;
    }
    ingestBroadcastVelocity(s, i, j, nodes_[j].vx, nodes_[j].vy, nodes_[j].vz);
    ++bootstrapHelloCount_;
    noteReceptionImpl(i, j);
}

bool
ElqtpProtocol::inNRange(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    if (i == j) {
        return false;
    }
    noteBootstrap(i, j);
    const NeighborEkf& s = slot(i, j);
    if (!s.zohHeard) {
        return false;
    }
    const LqarpNode& a = nodes_[i];
    return ChannelGate::distance3D(a.x, a.y, a.z,
                                   s.x_j_zoh, s.y_j_zoh, s.z_j_zoh) < rRangeM_;
}

bool
ElqtpProtocol::inNSnr(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    if (i == j) {
        return false;
    }
    noteBootstrap(i, j);
    const NeighborEkf& s = slot(i, j);
    if (!s.zohHeard) {
        return false;
    }
    const LqarpNode& a = nodes_[i];
    const ChannelSample sample = gate_->queryLink(a.x, a.y, a.queryDepthM(),
                                                  s.x_j_zoh, s.y_j_zoh,
                                                  s.query_z_j_zoh);
    if (gate_->sampleFailsCandidateSnr(sample)) {
        return false;
    }
    // Step 7: the reward path reads the LIVE sample (linkSample), so a pair
    // whose live query has no defined SNR — it has drifted outside the Bellhop
    // envelope since its last HELLO — is not in N_SNR under SPEC Part 1.2 and
    // must not reach the reward as a candidate. Only channel *definedness* is
    // tested against the live pose; the SNR_threshold comparison stays on the
    // held sample above, which is what the staleness model is about.
    if (!gate_->sampleHasDefinedSnr(linkSample(i, j))) {
        return false;
    }
    return true;
}

bool
ElqtpProtocol::inNDepth(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    if (i == j) {
        return false;
    }
    noteBootstrap(i, j);
    const NeighborEkf& s = slot(i, j);
    if (!s.zohHeard) {
        return false;
    }
    return (nodes_[i].z - s.z_j_zoh) > 0.0;
}

bool
ElqtpProtocol::inNStab(uint32_t i, uint32_t j) const
{
    if (i == j) {
        return false;
    }
    const NeighborEkf& s = slot(i, j);
    // N_stab = { Broadcast_k = 0  OR  |e_k| < epsilon_k }
    return s.broadcast_k == 0 || std::fabs(s.e_k) < s.epsilon_k;
}

std::vector<uint32_t>
ElqtpProtocol::lqarpCandidateSet(uint32_t i) const
{
    checkIndex(i);
    std::vector<uint32_t> I;
    for (uint32_t j = 0; j < nodes_.size(); ++j) {
        if (inNRange(i, j) && inNSnr(i, j) && inNDepth(i, j)) {
            I.push_back(j);
        }
    }
    return I;
}

std::vector<uint32_t>
ElqtpProtocol::candidateSet(uint32_t i) const
{
    checkIndex(i);
    std::vector<uint32_t> I;
    for (uint32_t j = 0; j < nodes_.size(); ++j) {
        if (inNRange(i, j) && inNSnr(i, j) && inNDepth(i, j) && inNStab(i, j)) {
            I.push_back(j);
        }
    }
    return I;
}

uint32_t
ElqtpProtocol::numberSj(uint32_t j) const
{
    // SPEC 2.8: c_nei unchanged from Part 1.3, so |I_LQARP(s_j)|.
    return static_cast<uint32_t>(lqarpCandidateSet(j).size());
}

void
ElqtpProtocol::relativeState(uint32_t i, uint32_t j,
                             double& pijx, double& pijy, double& pijz,
                             double& vijx, double& vijy, double& vijz) const
{
    checkIndex(i);
    checkIndex(j);
    const LqarpNode& a = nodes_[i];
    const LqarpNode& b = nodes_[j];
    const NeighborEkf& s = slot(i, j);
    pijx = a.x - b.x;
    pijy = a.y - b.y;
    pijz = a.z - b.z;
    vijx = a.vx - s.vx_j_zoh;
    vijy = a.vy - s.vy_j_zoh;
    vijz = a.vz - s.vz_j_zoh;
}

double
ElqtpProtocol::vRel(uint32_t i, uint32_t j) const
{
    double px, py, pz, vx, vy, vz;
    relativeState(i, j, px, py, pz, vx, vy, vz);
    const double n = std::sqrt(px * px + py * py + pz * pz);
    if (n < 1e-12) {
        return 0.0;
    }
    return (vx * px + vy * py + vz * pz) / n;
}

double
ElqtpProtocol::sigmoid(double u)
{
    return 1.0 / (1.0 + std::exp(-u));
}

double
ElqtpProtocol::cPred(uint32_t i, uint32_t j) const
{
    const ChannelSample s = linkSample(i, j);
    const double clin = elqtp::cLin(s.snr_db, cfg_.packetBits, cfg_.constellationM);
    const NeighborEkf& st = slot(i, j);
    const double excess = std::max(0.0, st.e_k - st.e_km1);
    return clin + cfg_.beta_1 * excess;
}

double
ElqtpProtocol::cDrift(uint32_t i, uint32_t j) const
{
    noteBootstrap(i, j);
    const NeighborEkf& s = slot(i, j);
    // No bootstrap and no HELLO yet: do not read nodes_[j] depth or energy.
    if (!s.zohHeard) {
        return 0.0;
    }
    const double c_del = LqarpProtocol::cDel(s.energy_j_zoh, cfg_.eIni,
                                             nodes_[i].z, s.z_j_zoh);
    const double vr = vRel(i, j);
    return c_del * (1.0 + cfg_.beta_2 * sigmoid(-vr));
}

ElqtpReward
ElqtpProtocol::reward(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    ElqtpReward out;
    noteBootstrap(i, j);
    const NeighborEkf& hj = slot(i, j);
    const double eJ = hj.zohHeard ? hj.energy_j_zoh : 0.0;
    const double zJ = hj.zohHeard ? hj.z_j_zoh : 0.0;

    const auto I = candidateSet(i);
    double eSum = 0.0;
    for (uint32_t k : I) {
        eSum += slot(i, k).energy_j_zoh;
    }
    const double eAvg = I.empty() ? 0.0 : eSum / static_cast<double>(I.size());

    const ChannelSample s = linkSample(i, j);
    out.c_lin = elqtp::cLin(s.snr_db, cfg_.packetBits, cfg_.constellationM);
    out.e_k = hj.e_k;
    out.c_pred = cPred(i, j);
    out.c_ene = LqarpProtocol::cEne(eJ, eAvg, cfg_.eIni);
    out.c_del = LqarpProtocol::cDel(eJ, cfg_.eIni, nodes_[i].z, zJ);
    out.v_rel = vRel(i, j);
    out.c_drift = cDrift(i, j);
    out.c_nei = LqarpProtocol::cNei(numberSj(j));

    const double num = out.c_ene * out.c_drift * out.c_nei;
    if (num == 0.0) {
        out.R = 0.0;
    } else if (out.c_pred == 0.0 || !std::isfinite(out.c_pred)) {
        out.R = std::copysign(std::numeric_limits<double>::infinity(), num);
    } else {
        out.R = num / out.c_pred;
    }
    return out;
}

double
ElqtpProtocol::qValue(uint32_t i, uint32_t j) const
{
    checkIndex(i);
    checkIndex(j);
    return Q_[i][j];
}

void
ElqtpProtocol::updateQ(uint32_t i, uint32_t j)
{
    checkIndex(i);
    checkIndex(j);
    const ElqtpReward rw = reward(i, j);
    double maxNext = 0.0;
    const auto I_j = candidateSet(j);
    if (!I_j.empty()) {
        maxNext = Q_[j][I_j.front()];
        for (uint32_t a : I_j) {
            maxNext = std::max(maxNext, Q_[j][a]);
        }
    }
    Q_[i][j] = (1.0 - cfg_.alpha) * Q_[i][j]
               + cfg_.alpha * (rw.R + cfg_.gamma * maxNext);
}

void
ElqtpProtocol::learnFrom(uint32_t i)
{
    learnFrom(i, candidateSet(i));
}

void
ElqtpProtocol::learnFrom(uint32_t i, const std::vector<uint32_t>& actions)
{
    for (uint32_t j : actions) {
        updateQ(i, j);
    }
}

int
ElqtpProtocol::nextHop(uint32_t i) const
{
    return nextHop(i, candidateSet(i));
}

int
ElqtpProtocol::nextHop(uint32_t i, const std::vector<uint32_t>& actions) const
{
    if (actions.empty()) {
        return -1;
    }
    uint32_t best = actions.front();
    double bestQ = Q_[i][best];
    for (uint32_t j : actions) {
        const double q = Q_[i][j];
        if (q > bestQ || (q == bestQ && j < best)) {
            bestQ = q;
            best = j;
        }
    }
    return static_cast<int>(best);
}

bool
ElqtpProtocol::peekFilter(uint32_t i, uint32_t j, FilterPeek& out) const
{
    checkIndex(i);
    checkIndex(j);
    out = FilterPeek{};
    if (i == j) {
        return false;
    }
    const NeighborEkf& s = slot(i, j);
    const LqarpNode& a = nodes_[i];
    const LqarpNode& b = nodes_[j];
    out.heard = s.zohHeard;
    out.lastZohS = s.lastZohTime;
    out.absE = std::fabs(s.e_k);
    out.epsilon = s.epsilon_k;
    out.broadcast = s.broadcast_k;
    out.stab = s.broadcast_k == 0 || std::fabs(s.e_k) < s.epsilon_k;
    out.heldX = s.x_j_zoh;
    out.heldY = s.y_j_zoh;
    out.heldZ = s.z_j_zoh;
    out.heldE = s.energy_j_zoh;
    out.heldQueryZ = s.query_z_j_zoh;
    out.energyGapJ = b.energy - (s.zohHeard ? s.energy_j_zoh : 0.0);
    if (!s.zohHeard) {
        return true;
    }
    out.poseErrM = ChannelGate::distance3D(b.x, b.y, b.z,
                                           s.x_j_zoh, s.y_j_zoh, s.z_j_zoh);
    out.range = ChannelGate::distance3D(a.x, a.y, a.z,
                                        s.x_j_zoh, s.y_j_zoh, s.z_j_zoh) < rRangeM_;
    const ChannelSample sample = gate_->queryLink(a.x, a.y, a.queryDepthM(),
                                                  s.x_j_zoh, s.y_j_zoh,
                                                  s.query_z_j_zoh);
    out.snr = !gate_->sampleFailsCandidateSnr(sample);
    out.depth = (a.z - s.z_j_zoh) > 0.0;
    return true;
}

std::vector<uint32_t>
ElqtpProtocol::detourSet(uint32_t i) const
{
    checkIndex(i);
    std::vector<uint32_t> D;
    for (uint32_t j = 0; j < nodes_.size(); ++j) {
        if (inNRange(i, j) && inNSnr(i, j)) {
            D.push_back(j);
        }
    }
    return D;
}

std::vector<uint32_t>
ElqtpProtocol::detourTargets(uint32_t i,
                             uint32_t sinkId,
                             const std::vector<uint32_t>& visited) const
{
    std::vector<uint32_t> T;
    for (uint32_t j : detourSet(i)) {
        if (LqarpProtocol::containsId(visited, j)) {
            continue;
        }
        if (j == sinkId) {
            T.push_back(j);
            continue;
        }
        bool onwardI = false;
        for (uint32_t k : candidateSet(j)) {
            if (!LqarpProtocol::containsId(visited, k)) {
                onwardI = true;
                break;
            }
        }
        if (onwardI) {
            T.push_back(j);
            continue;
        }
        bool onwardD = false;
        for (uint32_t k : detourSet(j)) {
            if (!LqarpProtocol::containsId(visited, k)) {
                onwardD = true;
                break;
            }
        }
        if (onwardD) {
            T.push_back(j);
        }
    }
    return T;
}

double
ElqtpProtocol::triggerEpsilon(double S) const
{
    // SPEC 2.3 addendum Option B:
    // epsilon_k = epsilon_0 + lambda * min(sqrt(S_k), s_cap)
    const double sTerm = (S > 0.0) ? std::sqrt(S) : 0.0;
    return cfg_.epsilon_0 + cfg_.lambda * std::min(sTerm, cfg_.s_cap);
}

double
ElqtpProtocol::dSnrDRange(double rangeM, double receiverZ) const
{
    const double h = cfg_.fdRangeM;
    const ChannelSample lo = gate_->queryRangeDepth(std::max(0.0, rangeM - h), receiverZ);
    const ChannelSample hi = gate_->queryRangeDepth(rangeM + h, receiverZ);
    if (!std::isfinite(lo.snr_db) || !std::isfinite(hi.snr_db)) {
        return 0.0;
    }
    const double denom = (rangeM + h) - std::max(0.0, rangeM - h);
    if (denom <= 0.0) {
        return 0.0;
    }
    return (hi.snr_db - lo.snr_db) / denom;
}

void
ElqtpProtocol::applyPredict(std::array<double, 7>& x,
                            std::array<double, 49>& P,
                            double dt,
                            double zRx)
{
    std::array<double, 7> xp = x;
    xp[0] = x[0] + dt * x[3];
    xp[1] = x[1] + dt * x[4];
    xp[2] = x[2] + dt * x[5];
    xp[3] = x[3];
    xp[4] = x[4];
    xp[5] = x[5];

    const double range = std::hypot(xp[0], xp[1]);
    // Bellhop SNR is (horizontal range, receiver acoustic depth).
    // Reconstructing kinematic z_j = z_i - p_ij_z misses acousticZ
    // (sink transducer at 50 m vs hull at 5 m).
    const ChannelSample pred = gate_->queryRangeDepth(range, zRx);
    if (std::isfinite(pred.snr_db)) {
        xp[6] = pred.snr_db;
    }
    // else keep last finite SNR; out-of-envelope is not interpolated.

    std::array<double, 49> F;
    ident49(F);
    F[static_cast<size_t>(idx(0, 3))] = dt;
    F[static_cast<size_t>(idx(1, 4))] = dt;
    F[static_cast<size_t>(idx(2, 5))] = dt;

    const double dsnr_dr = dSnrDRange(range, zRx);
    if (range > 1e-9 && std::isfinite(dsnr_dr)) {
        F[static_cast<size_t>(idx(6, 0))] = dsnr_dr * (xp[0] / range);
        F[static_cast<size_t>(idx(6, 1))] = dsnr_dr * (xp[1] / range);
    }
    F[static_cast<size_t>(idx(6, 6))] = 0.0; // SNR fully recomputed from pose

    std::array<double, 49> Ft, FP, FPFt;
    transpose49(F, Ft);
    mul49(F, P, FP);
    mul49(FP, Ft, FPFt);
    for (int k = 0; k < 3; ++k) {
        FPFt[static_cast<size_t>(idx(k, k))] += cfg_.qPos;
        FPFt[static_cast<size_t>(idx(k + 3, k + 3))] += cfg_.qVel;
    }
    FPFt[static_cast<size_t>(idx(6, 6))] += cfg_.qSnr;
    x = xp;
    P = FPFt;
}

void
ElqtpProtocol::predictPair(uint32_t i, uint32_t j, double dt)
{
    NeighborEkf& s = slot(i, j);
    applyPredict(s.x, s.P, dt, nodes_[j].queryDepthM());
}

void
ElqtpProtocol::predictForecast(uint32_t i, uint32_t j, double dt)
{
    NeighborEkf& s = slot(i, j);
    applyPredict(s.xForecast, s.PForecast, dt, nodes_[j].queryDepthM());
}

void
ElqtpProtocol::resetForecast(NeighborEkf& s) const
{
    s.xForecast = s.x;
    s.PForecast = s.P;
}

void
ElqtpProtocol::ingestBroadcastVelocity(NeighborEkf& s, uint32_t i, uint32_t j,
                                       double vx_j, double vy_j, double vz_j) const
{
    // SPEC 2.1: pdot_j is the received ground-truth broadcast, not an
    // EKF inference. Overwrite x[3:5] = pdot_i - pdot_j. Leave p_ij
    // and SNR (x[0:2], x[6]) as the range-corrected estimate.
    // Position and energy are copied at the same event. Routing reads
    // those holds; the EKF measurement path still uses linkSample.
    const LqarpNode& b = nodes_[j];
    s.vx_j_zoh = vx_j;
    s.vy_j_zoh = vy_j;
    s.vz_j_zoh = vz_j;
    s.x_j_zoh = b.x;
    s.y_j_zoh = b.y;
    s.z_j_zoh = b.z;
    s.energy_j_zoh = b.energy;
    s.query_z_j_zoh = b.queryDepthM();
    s.zohHeard = true;
    s.lastZohTime = simTime_;
    s.x[3] = nodes_[i].vx - vx_j;
    s.x[4] = nodes_[i].vy - vy_j;
    s.x[5] = nodes_[i].vz - vz_j;
    resetForecast(s);
}

void
ElqtpProtocol::updatePair(uint32_t i, uint32_t j, double z_k)
{
    NeighborEkf& s = slot(i, j);
    if (!std::isfinite(z_k)) {
        ++nanMeasCount_;
        // Out of Bellhop envelope: no measurement, do not fire.
        if (cfg_.broadcastMode == BroadcastMode::EventTriggered) {
            s.broadcast_k = 0;
        }
        return;
    }
    s.zWindow.push_back(z_k);
    while (s.zWindow.size() > cfg_.W_mp) {
        s.zWindow.pop_front();
    }
    const double z_tilde = medianCopy(s.zWindow);
    const double h = s.x[6];
    s.e_km1 = s.e_k;
    s.e_k = z_tilde - h;
    if (std::isfinite(s.e_k)) {
        maxAbsInnovation_ = std::max(maxAbsInnovation_, std::fabs(s.e_k));
    }

    s.S_k = s.P[static_cast<size_t>(idx(6, 6))] + cfg_.rMeas;
    if (!(s.S_k > 0.0)) {
        s.S_k = cfg_.rMeas;
    }
    s.epsilon_k = cfg_.epsilon_0 + cfg_.lambda * std::sqrt(s.S_k);

    // SPEC 2.3 addendum: e_k^{trigger} = z_k - h(x_forecast). z_k is the
    // SNR sampled at the last reception from j (received-only). Kalman e_k / S_k / epsilon_k above
    // stay on x_hat for the EKF update and c_pred.
    const double hForecast = s.xForecast[6];
    s.eTrigger = z_k - hForecast;
    s.STrigger = s.PForecast[static_cast<size_t>(idx(6, 6))] + cfg_.rMeas;
    if (!(s.STrigger > 0.0)) {
        s.STrigger = cfg_.rMeas;
    }
    s.epsilonTrigger = triggerEpsilon(s.STrigger);
    if (std::isfinite(s.eTrigger)) {
        const double ae = std::fabs(s.eTrigger);
        maxAbsTriggerInnovation_ = std::max(maxAbsTriggerInnovation_, ae);
        s.maxAbsETrigger = std::max(s.maxAbsETrigger, ae);
        // Unheard window includes the tick that first sets zohHeard
        // (the innovation that would have caused the fire).
        if (!s.zohHeard) {
            s.maxAbsETriggerUnheard = std::max(s.maxAbsETriggerUnheard, ae);
            if (std::isfinite(s.epsilonTrigger)) {
                s.maxEpsilonTriggerUnheard = std::max(s.maxEpsilonTriggerUnheard,
                                                      s.epsilonTrigger);
            }
        }
    }

    const bool exceed = std::fabs(s.eTrigger) >= s.epsilonTrigger;
    s.exceedHist.push_back(exceed ? 1 : 0);
    while (s.exceedHist.size() > cfg_.W) {
        s.exceedHist.pop_front();
    }

    // Part 2.4 event trigger is skipped in FixedPeriodic mode (SPEC Part 4);
    // Broadcast_k is set on the T_ctrl grid in tick() instead. Parts 2.1–2.3
    // and the EKF update below are unchanged.
    if (cfg_.broadcastMode == BroadcastMode::EventTriggered) {
        recomputeBroadcast(i, j);
    }

    // EKF update on SNR measurement z_tilde. H = [0..0 1].
    const double S = s.S_k;
    std::array<double, 7> K{};
    for (int r = 0; r < kDim; ++r) {
        K[static_cast<size_t>(r)] = s.P[static_cast<size_t>(idx(r, 6))] / S;
    }
    const double innov = z_tilde - h;
    for (int r = 0; r < kDim; ++r) {
        s.x[static_cast<size_t>(r)] += K[static_cast<size_t>(r)] * innov;
    }
    // P <- (I - K H) P
    std::array<double, 49> KH;
    zero49(KH);
    for (int r = 0; r < kDim; ++r) {
        KH[static_cast<size_t>(idx(r, 6))] = K[static_cast<size_t>(r)];
    }
    std::array<double, 49> Iminus;
    ident49(Iminus);
    for (int r = 0; r < kDim; ++r) {
        for (int c = 0; c < kDim; ++c) {
            Iminus[static_cast<size_t>(idx(r, c))] -= KH[static_cast<size_t>(idx(r, c))];
        }
    }
    std::array<double, 49> Pnew;
    mul49(Iminus, s.P, Pnew);
    s.P = Pnew;

    // After the Kalman update: write received pdot_j into x[3:5] as
    // ground-truth relative velocity, then reset the forecast. Doing
    // this after the update stops the filter from blending the write
    // back toward the stale EKF velocity on the same tick.
    if (cfg_.broadcastMode == BroadcastMode::EventTriggered && s.broadcast_k == 1
        && !helloSuppressed_[j] && helloReaches(i, j)) {
        ingestBroadcastVelocity(s, i, j, nodes_[j].vx, nodes_[j].vy, nodes_[j].vz);
    }
}

void
ElqtpProtocol::recomputeBroadcast(uint32_t i, uint32_t j)
{
    NeighborEkf& s = slot(i, j);
    const bool now = std::fabs(s.eTrigger) >= s.epsilonTrigger;
    double frac = 0.0;
    if (!s.exceedHist.empty()) {
        int sum = 0;
        for (int v : s.exceedHist) {
            sum += v;
        }
        frac = static_cast<double>(sum) / static_cast<double>(s.exceedHist.size());
    }
    s.broadcast_k = (now && frac >= cfg_.rho) ? 1 : 0;
}

void
ElqtpProtocol::emitPeriodicControl()
{
    // One control packet per node; every neighbor ZOH-updates that node's
    // velocity. Isolates timing from the Part 2.4 persistence gate.
    for (uint32_t i = 0; i < nodes_.size(); ++i) {
        for (uint32_t j = 0; j < nodes_.size(); ++j) {
            if (i == j) {
                continue;
            }
            NeighborEkf& s = ekf_[i][j];
            // j's HELLO refreshes i's hold only if i demodulates it.
            if (!helloReaches(i, j)) {
                s.broadcast_k = 0;
                continue;
            }
            s.broadcast_k = 1;
            if (!helloSuppressed_[j]) {
                ingestBroadcastVelocity(s, i, j, nodes_[j].vx, nodes_[j].vy, nodes_[j].vz);
            }
        }
    }
    eventHelloCount_ += static_cast<uint64_t>(nodes_.size());
    for (uint32_t j = 0; j < nodes_.size(); ++j) {
        broadcastFrom(j);
    }
}

void
ElqtpProtocol::refreshEnergyOnly()
{
    // Pose and velocity holds stay on the persistence-gated HELLO.
    // The beacon carries a quantized residual, not the full double.
    for (uint32_t i = 0; i < nodes_.size(); ++i) {
        for (uint32_t j = 0; j < nodes_.size(); ++j) {
            if (i == j) {
                continue;
            }
            NeighborEkf& s = ekf_[i][j];
            if (!s.zohHeard || !helloReaches(i, j)) {
                continue;
            }
            s.energy_j_zoh = quantizeEnergy(nodes_[j].energy);
        }
    }
    energyHelloCount_ += static_cast<uint64_t>(nodes_.size());
    for (uint32_t j = 0; j < nodes_.size(); ++j) {
        broadcastFrom(j);
    }
}

double
ElqtpProtocol::quantizeEnergy(double joules) const
{
    const int bits = cfg_.energyQuantBits;
    if (bits <= 0) {
        return joules;
    }
    const double eIni = cfg_.eIni;
    if (!(eIni > 0.0) || !std::isfinite(joules)) {
        return joules;
    }
    double e = joules;
    if (e < 0.0) {
        e = 0.0;
    }
    if (e > eIni) {
        e = eIni;
    }
    // 2^bits - 1 in double: exact for bits <= 53. (1u << 32) is undefined
    // behaviour and gave levels = 0, i.e. NaN, at the 32-bit design point.
    if (bits > 53) {
        throw std::invalid_argument("energyQuantBits must be <= 53");
    }
    const double levels = std::ldexp(1.0, bits) - 1.0;
    const double code = std::round(e / eIni * levels);
    return code * eIni / levels;
}

void
ElqtpProtocol::clearBroadcastFlags()
{
    for (uint32_t i = 0; i < nodes_.size(); ++i) {
        for (uint32_t j = 0; j < nodes_.size(); ++j) {
            if (i != j) {
                ekf_[i][j].broadcast_k = 0;
            }
        }
    }
}

void
ElqtpProtocol::countEventControlTx()
{
    // SPEC 2.4: node j transmits one HELLO on a 0→1 rising edge of
    // Broadcast_k(i,j) for any neighbor i. Persisted Broadcast_k=1
    // does not re-announce.
    const size_t n = nodes_.size();
    if (prevBroadcast_.size() != n * n) {
        prevBroadcast_.assign(n * n, 0);
    }
    for (uint32_t j = 0; j < n; ++j) {
        bool rising = false;
        for (uint32_t i = 0; i < n; ++i) {
            if (i == j) {
                continue;
            }
            const int now = ekf_[i][j].broadcast_k;
            const int prev = prevBroadcast_[i * n + j];
            if (now == 1 && prev != 1) {
                rising = true;
                break;
            }
        }
        if (rising) {
            ++eventHelloCount_;
            broadcastFrom(j);
        }
    }
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            prevBroadcast_[i * n + j] = ekf_[i][j].broadcast_k;
        }
    }
}

void
ElqtpProtocol::tick(double dt)
{
    const size_t n = nodes_.size();
    std::vector<int> prev(n * n, 0);
    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            prev[i * n + j] = ekf_[i][j].broadcast_k;
        }
    }

    const double step = std::isfinite(dt) ? dt : cfg_.dt;
    for (uint32_t i = 0; i < nodes_.size(); ++i) {
        for (uint32_t j = 0; j < nodes_.size(); ++j) {
            if (i == j) {
                continue;
            }
            predictPair(i, j, step);
            predictForecast(i, j, step);
            // Received-only z_k: correct x_hat and sample the trigger only
            // if a packet from j reached i since the last tick. Otherwise
            // both tracks stay predict-only via F_k, and (as for an
            // out-of-envelope sample) no measurement means no fire.
            NeighborEkf& s = ekf_[i][j];
            if (s.rxPending) {
                const double z_k = s.zRxPending;
                s.rxPending = false;
                s.zRxPending = std::numeric_limits<double>::quiet_NaN();
                ++measuredUpdates_;
                updatePair(i, j, z_k);
            } else {
                ++silentPredicts_;
                if (cfg_.broadcastMode == BroadcastMode::EventTriggered) {
                    s.broadcast_k = 0;
                }
            }
        }
    }
    simTime_ += step;
    if (cfg_.broadcastMode == BroadcastMode::FixedPeriodic) {
        bool fired = false;
        const double T = cfg_.T_ctrl;
        while (simTime_ + 1e-12 >= nextPeriodicTime_) {
            emitPeriodicControl();
            fired = true;
            if (!(T > 0.0) || !std::isfinite(T)) {
                break;
            }
            nextPeriodicTime_ += T;
        }
        if (!fired) {
            clearBroadcastFlags();
        }
    } else {
        countEventControlTx();
    }

    if (cfg_.energyRefreshS > 0.0) {
        const double Te = cfg_.energyRefreshS;
        while (simTime_ + 1e-12 >= nextEnergyRefresh_) {
            refreshEnergyOnly();
            if (!(Te > 0.0) || !std::isfinite(Te)) {
                break;
            }
            nextEnergyRefresh_ += Te;
        }
    }

    for (uint32_t i = 0; i < n; ++i) {
        for (uint32_t j = 0; j < n; ++j) {
            if (i == j) {
                continue;
            }
            const int now = ekf_[i][j].broadcast_k;
            if (now == 1) {
                ++broadcastKOnes_;
                if (prev[i * n + j] != 1) {
                    ++broadcastRising_;
                    ++ekf_[i][j].nBroadcastRising;
                    if (!std::isfinite(ekf_[i][j].firstBroadcastTime)) {
                        ekf_[i][j].firstBroadcastTime = simTime_;
                    }
                }
                if (ekf_[i][j].zohHeard) {
                    ekf_[i][j].lastZohTime = simTime_;
                }
            }
        }
    }
}

void
ElqtpProtocol::forceInnovation(uint32_t i, uint32_t j, double e_k, double epsilon_k)
{
    NeighborEkf& s = slot(i, j);
    s.e_km1 = s.e_k;
    s.e_k = e_k;
    s.epsilon_k = epsilon_k;
    // Test 7 drives Broadcast_k through recomputeBroadcast, which now
    // reads e_k^{trigger}. Keep the Kalman pair and the trigger pair
    // in lockstep for the seam.
    s.eTrigger = e_k;
    s.epsilonTrigger = epsilon_k;
}

void
ElqtpProtocol::pushExceedFlag(uint32_t i, uint32_t j, bool exceed)
{
    NeighborEkf& s = slot(i, j);
    s.exceedHist.push_back(exceed ? 1 : 0);
    while (s.exceedHist.size() > cfg_.W) {
        s.exceedHist.pop_front();
    }
}

void
ElqtpProtocol::setNeighborVelocityZoh(uint32_t i, uint32_t j,
                                      double vx, double vy, double vz)
{
    ingestBroadcastVelocity(slot(i, j), i, j, vx, vy, vz);
}

void
ElqtpProtocol::setHelloSuppressed(uint32_t j, bool suppressed)
{
    checkIndex(j);
    helloSuppressed_[j] = suppressed ? 1 : 0;
}

void
ElqtpProtocol::setBootstrapSuppressed(uint32_t j, bool suppressed)
{
    checkIndex(j);
    bootstrapSuppressed_[j] = suppressed ? 1 : 0;
}

void
ElqtpProtocol::setBroadcastK(uint32_t i, uint32_t j, int broadcast_k)
{
    slot(i, j).broadcast_k = broadcast_k ? 1 : 0;
}

void
ElqtpProtocol::flushEventControlTx()
{
    countEventControlTx();
}

bool
ElqtpProtocol::zohHeard(uint32_t i, uint32_t j) const
{
    return slot(i, j).zohHeard;
}

double
ElqtpProtocol::lastZohTime(uint32_t i, uint32_t j) const
{
    return slot(i, j).lastZohTime;
}

void
ElqtpProtocol::setEnergy(uint32_t i, double joules)
{
    checkIndex(i);
    nodes_[i].energy = joules;
}

double
ElqtpProtocol::energy(uint32_t i) const
{
    checkIndex(i);
    return nodes_[i].energy;
}

void
ElqtpProtocol::setKinematics(uint32_t i, double x, double y, double z,
                             double vx, double vy, double vz)
{
    checkIndex(i);
    nodes_[i].x = x;
    nodes_[i].y = y;
    nodes_[i].z = z;
    nodes_[i].vx = vx;
    nodes_[i].vy = vy;
    nodes_[i].vz = vz;
}

} // namespace elqtp
