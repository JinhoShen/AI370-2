#include <cstdint>
#include <cstdio>
std::uint32_t invert32(std::uint32_t input);
int main(){
  if(invert32(0x89abcdefu)!=0x76543210u){std::fprintf(stderr,"mismatch 89abcdef\n");return 1;}
  if(invert32(0x01020304u)!=0xfefdfcfbu){std::fprintf(stderr,"mismatch 01020304\n");return 1;}
  if(invert32(0x80000000u)!=0x7fffffffu){std::fprintf(stderr,"mismatch 80000000\n");return 1;}
  if(invert32(0x55aa55aau)!=0xaa55aa55u){std::fprintf(stderr,"mismatch 55aa55aa\n");return 1;}
  std::puts("QUALITY_T6_CSIM_PASS checks=4");return 0;
}
