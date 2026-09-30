// Pre-Step-5 ElqtpProtocol::quantizeEnergy, copied verbatim (the UB shift),
// checked against the fixed ldexp version over a dense sweep of [0, E_ini].
#include <cmath>
#include <cstdio>
#include <cstdlib>
static double pre(double joules, int bits, double eIni) {
    if (bits <= 0) return joules;
    if (!(eIni > 0.0) || !std::isfinite(joules)) return joules;
    double e = joules; if (e < 0.0) e = 0.0; if (e > eIni) e = eIni;
    const double levels = static_cast<double>((1u << static_cast<unsigned>(bits)) - 1u);
    const double code = std::round(e / eIni * levels);
    return code * eIni / levels;
}
static double fixed_(double joules, int bits, double eIni) {
    double e = joules; if (e < 0.0) e = 0.0; if (e > eIni) e = eIni;
    const double levels = std::ldexp(1.0, bits) - 1.0;
    return std::round(e / eIni * levels) * eIni / levels;
}
int main(int argc, char** argv) {
    const double eIni = 10000.0; const long N = 1000000;
    int nb = argc - 1;
    printf("bits  levels(pre)  nonfinite  max|pre-E|(J)  step/2(J)  within_step/2  pre==fixed  distinct_codes\n");
    for (int a = 1; a < argc; ++a) {
        volatile int bits = atoi(argv[a]);              // runtime value, as in the simulator
        const double lev = (double)((1u << (unsigned)bits) - 1u);
        long nonfinite = 0, mismatch = 0; double maxerr = 0; long distinct = 0; double last = NAN;
        for (long k = 0; k <= N + 2; ++k) {
            double E = (k <= N) ? eIni * k / N : (k == N + 1 ? -1.0 : eIni + 1.0);   // + out-of-range edges
            double q = pre(E, bits, eIni), f = fixed_(E, bits, eIni);
            if (!std::isfinite(q)) { ++nonfinite; continue; }
            double Ec = E < 0 ? 0 : (E > eIni ? eIni : E);
            maxerr = std::fmax(maxerr, std::fabs(q - Ec));
            if (q != f) ++mismatch;
            if (k <= N && q != last) { ++distinct; last = q; }
        }
        double half = (lev > 0) ? eIni / lev / 2 : NAN;
        printf("%4d %12.0f %10ld %14.6g %10.4g %14s %11s %14ld\n", (int)bits, lev, nonfinite, maxerr, half,
               nonfinite ? "-" : (maxerr <= half + 1e-9 ? "yes" : "NO"), mismatch ? "NO" : "yes", distinct);
    }
}
