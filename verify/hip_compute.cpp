#include <hip/hip_runtime.h>
#include <cstdio>
#include <cstring>
#include <cstdlib>
#define CHECK(call) do { hipError_t r=(call); if(r!=hipSuccess){std::fprintf(stderr,"%s: %s\n",#call,hipGetErrorString(r));std::exit(1);} } while(0)
__global__ void compute(unsigned *values){unsigned i=blockIdx.x*blockDim.x+threadIdx.x;values[i]=i*3u+7u;}
int main(){
    hipDeviceProp_t props; CHECK(hipGetDeviceProperties(&props,0));
    std::printf("Device: %s; architecture: %s\n",props.name,props.gcnArchName);
    if(std::strncmp(props.gcnArchName,"gfx1150",7)!=0)return 1;
    CHECK(hipSetDevice(0)); unsigned *device; CHECK(hipMalloc(&device,1024*sizeof(unsigned)));
    compute<<<16,64>>>(device); CHECK(hipGetLastError()); CHECK(hipDeviceSynchronize());
    unsigned values[1024]; CHECK(hipMemcpy(values,device,sizeof(values),hipMemcpyDeviceToHost));
    for(unsigned i=0;i<1024;i++)if(values[i]!=i*3u+7u)return 1;
    CHECK(hipFree(device));std::puts("PASS: 1024 HIP GPU results verified");return 0;
}
