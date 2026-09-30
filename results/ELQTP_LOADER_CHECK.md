# BellhopDataLoader check (ns-3.41 contrib/elqtp)

Compiled as `contrib/elqtp` against NS-3.41 + Aqua-Sim-NG `0fbc166`.
Library: `build/lib/libns3.41-elqtp-optimized.so`.

```bash
cd opt/ns-allinone-3.41/ns-3.41
./ns3 run "bellhop-data-loader-check --dataDir=/workspace/data/channel_db"
```

January CSV load **8.45 ms**, July **8.32 ms**. Constructor loads once;
`query()` only interpolates.

| Check | Result | Actual |
| --- | --- | --- |
| Jan `query(1000, 50)` vs TL 58.87 / SNR 50.35 | PASS | TL=58.87307234 SNR=50.35195475 valid=true |
| Jan `query(4000, 50)` vicinity of ~18 dB SNR | PASS | TL=90.90265690 SNR=18.32237019 valid=true |
| Jan `query(0, 50)` valid=false | PASS | TL=nan SNR=nan valid=false |
| Jan `query(2500, 0)` valid=false (header claim) | **FAIL** | TL=117.02902148 SNR=-7.80399440 **valid=true** |
| Jan `query(6000, 500)` valid grid edge | PASS | TL=101.95852004 SNR=7.26650704 valid=true |
| Jan `query(6500, 250)` valid=false (out of envelope) | PASS | valid=false (clamped TL/SNR still filled from 6 km edge) |
| Jul `query(4525, 50)` SNR ~ 8.03 | PASS | TL=101.19232854 SNR=8.03269855 valid=true |
| Exact grid node (1000, 50) matches CSV | PASS | same bits as CSV |
| Midpoint range 1012.5 m = average of 1000 and 1025 | PASS | TL=59.04565122 SNR=50.17937587 |

The depth=0 failure is a header/implementation mismatch, not a
compile bug. `loadGrid()` does not force depth=0 cells to NaN; the
CSV stores finite TL/SNR there. Left unpatched.

Source change vs the attached files: `#include <tuple>` and
`#include <cctype>` only.
