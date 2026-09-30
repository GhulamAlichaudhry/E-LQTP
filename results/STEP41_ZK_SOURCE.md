# Step 41: Where does z_k come from?

No ε₀ change. No trigger rewrite. This is the architecture
question only.

**Answer: (a).** Every dt=1 s tick, for every directed pair (i,j),
z_k is a Bellhop query at the nodes’ **true current positions**.
It does not wait for a broadcast, a data packet, or overhearing.

---

## Code path

`ElqtpProtocol::tick` (every pair, every step):

```713:715:contrib/elqtp/model/elqtp-protocol.cc
            predictPair(i, j, step);
            const ChannelSample z = linkSample(i, j);
            updatePair(i, j, z.snr_db);
```

`linkSample` is a truth query on the protocol node list:

```185:193:contrib/elqtp/model/elqtp-protocol.cc
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
```

`queryLink` uses horizontal range of those coordinates:

```43:49:contrib/elqtp/model/channel-gate.cc
ChannelGate::queryLink(...)
{
    const double rangeM = horizontalRangeM(txX, txY, rxX, rxY);
    const double depthM = depthQueryM(rxZ);
    return loader_->query(rangeM, depthM);
}
```

In the Scenario II harness those coordinates **are** ns-3
ground truth. `Pipeline::OnTick` copies mobility poses into the
protocol **before** `tick`:

```
SweepExits → SyncPoses → proto->tick(dt)
```

`SyncPoses` writes `MobilityModel::GetPosition()` / `GetVelocity()`
into `setKinematics`. There is no “last heard position” and no
communication predicate on this path.

`updatePair` then always consumes that z_k (unless NaN): median
window, e_k = z_tilde − x[6], Kalman update with H = [0…0 1].
ZOH / `zohHeard` is written only **after** the innovation, and
only if Broadcast_k already fired. Measurement does not depend
on it.

SPEC 2.3 already said “actual current range/depth, not the
predicted one.” The Step 41 sentence now states that this query
runs every dt, not at HELLO events.

---

## What this implies (not a fix)

Predicted SNR `h = x[6]` is the EKF’s range-propagated lookup
(`predictPair`: hypot(x[0],x[1]) → Bellhop). Measured z_k is
Bellhop at **true** range. The innovation is therefore

e_k ≈ SNR(true range) − SNR(EKF-predicted range)

plus the 1 s of F-propagation since the last update.

Because a measurement of true range arrives every second, the
Kalman update pulls the **radial** position toward truth every
tick. Step 35’s 31 m range lock (and 898 m *tangential* walk)
is exactly that: the observable axis is healed; the rest is
not. Velocity error (~1.5 m/s) never accumulates in e_k. A
1 s slip at 0.06 dB/m is 0.12 dB; then the truth measurement
wipes it.

So e_k **cannot** encode “my velocity / ZOH is wrong,” for any
ε₀. Lowering ε₀ would threshold numerical leftovers near zero
(Step 37: max |e_k| = 0.37 dB, typical 0.006 dB), not a
physical velocity-error signal. The usable signal in Step 40
was *un-wiped* divergence over 20–60 s — a quantity this
estimator never forms.

That is (a), confirmed. The open-loop forecast vs observed-SNR
redesign is a SPEC 2.2/2.4 change; it is **not** implemented
here.
