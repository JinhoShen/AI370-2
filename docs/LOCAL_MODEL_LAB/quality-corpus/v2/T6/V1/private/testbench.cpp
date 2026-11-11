#include <cstdint>
#include <cstdio>
std::uint32_t invert32(std::uint32_t input);
int main(){
  if(invert32(0x12345678u)!=0xedcba987u){std::fprintf(stderr,"mismatch 12345678\n");return 1;}
  if(invert32(0x00000000u)!=0xffffffffu){std::fprintf(stderr,"mismatch 00000000\n");return 1;}
  if(invert32(0xffffffffu)!=0x00000000u){std::fprintf(stderr,"mismatch ffffffff\n");return 1;}
  if(invert32(0xa5a5f00du)!=0x5a5a0ff2u){std::fprintf(stderr,"mismatch a5a5f00d\n");return 1;}
  std::puts("QUALITY_T6_CSIM_PASS checks=4");return 0;
}
