#include "bellhop-data-loader.h"
#include "channel-gate.h"
#include "link-quality.h"
#include <cmath>
#include <cstdio>
#include <memory>
using namespace elqtp;
int main(int argc,char**argv){
  auto ld=std::make_shared<BellhopDataLoader>(std::string(argv[1])+"/TL_grid_extended_january.csv",
                                              std::string(argv[1])+"/SNR_grid_extended_january.csv",Season::January);
  ChannelGate g(ld);
  printf("beyond-grid and shallow queries (c_lin non-finite => reward R=+/-inf branch):\n");
  for(double r:{5900.0,6000.0,6100.0,7000.0,8500.0,12000.0})
    for(double z:{5.0,50.0}){
      ChannelSample s=g.queryRangeDepth(r,z); double cl=cLin(s.snr_db,400,2);
      printf("  r=%6.0f z=%4.1f valid=%d nearPR=%d snr=%9.3f c_lin=%-12g %s\n",r,z,(int)s.valid,(int)s.nearPressureRelease,s.snr_db,cl,
             std::isfinite(cl)?"":"<-- NON-FINITE");
    }
  // which invalid cells exist inside the grid?
  long npr=0,inv=0; double zmin=1e9,zmax=-1e9;
  for(double r=0;r<=6000;r+=5) for(double z=5;z<=500;z+=5){
    ChannelSample s=g.queryRangeDepth(r,z);
    if(s.nearPressureRelease){++npr; if(z<zmin)zmin=z; if(z>zmax)zmax=z;}
    else if(!s.valid) ++inv;
  }
  printf("in-grid: nearPR cells=%ld (depths %.0f-%.0f m)  other invalid=%ld\n",npr,zmin,zmax,inv);
}
