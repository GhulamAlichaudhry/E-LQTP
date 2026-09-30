// elqtp-run-config.h
//
// Runtime (no-rebuild) experiment knobs. ElqtpProtocol already takes
// ElqtpConfig by value; this parser is how a single built binary
// accepts beta_1 / beta_2 / epsilon_0 / W / W_mp / ... as CLI flags
// or a key=value file. Unit tests construct ElqtpConfig themselves
// and do not read this object.

#ifndef ELQTP_ELQTP_RUN_CONFIG_H
#define ELQTP_ELQTP_RUN_CONFIG_H

#include "elqtp-protocol.h"
#include "gauss-markov.h"

#include <iosfwd>
#include <string>
#include <vector>

namespace elqtp {

struct ElqtpRunConfig {
    ElqtpConfig elqtp;
    GaussMarkovConfig gm;
    std::string dataDir = "/workspace/data/channel_db";
    std::string configFile;

    // --key=value or --key value. Unknown keys return false.
    bool applyToken(const std::string& key, const std::string& value);

    // Load key=value / key value lines. '#' comments. Returns false on IO error.
    bool loadFile(const std::string& path, std::string& err);

    // argv[0] skipped. Positional non-flag → dataDir.
    // --config=PATH is applied when seen (later CLI flags override the file).
    static ElqtpRunConfig parseArgv(int argc, char** argv, std::string& err);

    void dump(std::ostream& os) const;
};

std::vector<std::string> sweepFlagNames();

} // namespace elqtp

#endif // ELQTP_ELQTP_RUN_CONFIG_H
