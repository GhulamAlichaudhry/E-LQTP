# Example run (this machine)

Verified on Ubuntu 24.04.4, g++ 13.3.0, CMake 3.28.3.

| Piece | Result |
| --- | --- |
| NS-3 | 3.41 |
| Aqua-Sim-NG | `0fbc166` (`src/aqua-sim-ng`) |
| Module library | `build/lib/libns3.41-aqua-sim-ng-optimized.so` (3.9 MB) |
| Linked into | `broadcastMAC_example`, `floodtest`, `TrumacTest` |

## BroadcastMAC

```bash
./scripts/run-example.sh
# ./ns3 run "broadcastMAC_example --simStop=8 --nodes=3 --sinks=1"
```

```text
-----------Initializing simulation-----------
Creating Nodes
-----------Running Simulation-----------
fin.
```

Three underwater nodes plus one sink on a line, BroadcastMAC, dummy routing. Simulation time 8 s.

## Underwater ALOHA (`TrumacTest --mac=aloha`)

```bash
./scripts/run-example.sh TrumacTest --seed=0 --psize=100 --nodes=4 --simStop=20 --mac=aloha --rate=120 --dist=120 --algo=0
```

```text
-----------Initializing simulation-----------
Creating Nodes
-----------Running Simulation-----------
Channel Counters= SendUpFromChannel(8) AllRecvers(should be =n*sendup)(32) SchedPhyRecv(24)
Sent Pkts(Source_NetDevice->Stack):
 (NetworkTotal) 8
SendUp Pkts(Sink_RoutingLayer):
 (NetworkTotal) 0
Recv Pkts(@PhyLayer):
 (NetworkTotal) 0
fin.
```

Four nodes, 20 s of sim time: 8 packets entered the acoustic channel. Trace summary (`results_trumac.txt`): 8 originated, 8 PHY TX, 16 collisions.
