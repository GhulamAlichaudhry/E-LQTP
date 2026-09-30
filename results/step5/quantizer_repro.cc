#include <cmath>
#include <cstdio>
#include <cstdlib>
// Verbatim expression from ElqtpProtocol::quantizeEnergy (elqtp-protocol.cc).
double quantize(double joules, int bits, double eIni) {
    if (bits <= 0) return joules;
    double e = joules; if (e < 0.0) e = 0.0; if (e > eIni) e = eIni;
    const double levels = static_cast<double>((1u << static_cast<unsigned>(bits)) - 1u);
    const double code = std::round(e / eIni * levels);
    return code * eIni / levels;
}
int main(int argc, char** argv) {
    volatile int bits[] = {8, 16, 24, 31, 32};   // volatile: runtime shift, as in the simulator
    for (int b : bits) printf("bits=%2d levels=%.0f  q(9999.9 J)=%.6f\n", b,
        (double)((1u << (unsigned)b) - 1u), quantize(9999.9, b, 10000.0));
}
