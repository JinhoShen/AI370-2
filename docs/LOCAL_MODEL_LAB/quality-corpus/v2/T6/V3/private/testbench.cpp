#include <cstdint>
#include <cstdio>
std::uint32_t invert32(std::uint32_t input);
int main(){
  if(invert32(0x0f0f0f0fu)!=0xf0f0f0f0u){std::fprintf(stderr,"mismatch 0f0f0f0f\n");return 1;}
  if(invert32(0xdeadbeefu)!=0x21524110u){std::fprintf(stderr,"mismatch deadbeef\n");return 1;}
  if(invert32(0x13579bdfu)!=0xeca86420u){std::fprintf(stderr,"mismatch 13579bdf\n");return 1;}
  if(invert32(0x2468ace0u)!=0xdb97531fu){std::fprintf(stderr,"mismatch 2468ace0\n");return 1;}
  std::puts("QUALITY_T6_CSIM_PASS checks=4");return 0;
}
