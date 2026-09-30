#include <vulkan/vulkan.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(call) do { VkResult r = (call); if (r != VK_SUCCESS) { fprintf(stderr, "%s: %d\n", #call, r); exit(1); } } while (0)
int main(int argc, char **argv) {
    if (argc != 2) return 2;
    VkApplicationInfo app = {.sType=VK_STRUCTURE_TYPE_APPLICATION_INFO, .pApplicationName="AI370 Vulkan verification", .apiVersion=VK_API_VERSION_1_1};
    VkInstanceCreateInfo ici = {.sType=VK_STRUCTURE_TYPE_INSTANCE_CREATE_INFO, .pApplicationInfo=&app};
    VkInstance instance; CHECK(vkCreateInstance(&ici, NULL, &instance));
    uint32_t count=0; CHECK(vkEnumeratePhysicalDevices(instance, &count, NULL));
    VkPhysicalDevice *devices=calloc(count, sizeof(*devices));
    CHECK(vkEnumeratePhysicalDevices(instance, &count, devices));
    VkPhysicalDevice physical=VK_NULL_HANDLE; VkPhysicalDeviceProperties props;
    for (uint32_t i=0;i<count;i++) {
        vkGetPhysicalDeviceProperties(devices[i], &props);
        if (props.vendorID==0x1002 && props.deviceID==0x150e && props.deviceType==VK_PHYSICAL_DEVICE_TYPE_INTEGRATED_GPU) {physical=devices[i]; break;}
    }
    free(devices);
    if (!physical) {fprintf(stderr,"Expected Radeon 890M missing; CPU fallback forbidden\n"); return 1;}
    printf("Device: %s (vendor %04x device %04x)\n",props.deviceName,props.vendorID,props.deviceID);
    uint32_t nq=0; vkGetPhysicalDeviceQueueFamilyProperties(physical,&nq,NULL);
    VkQueueFamilyProperties *qp=calloc(nq,sizeof(*qp)); vkGetPhysicalDeviceQueueFamilyProperties(physical,&nq,qp);
    uint32_t family=UINT32_MAX;
    for(uint32_t i=0;i<nq;i++) if(qp[i].queueFlags & VK_QUEUE_COMPUTE_BIT){family=i;break;}
    free(qp); if(family==UINT32_MAX)return 1;
    float priority=1.f;
    VkDeviceQueueCreateInfo qci={.sType=VK_STRUCTURE_TYPE_DEVICE_QUEUE_CREATE_INFO,.queueFamilyIndex=family,.queueCount=1,.pQueuePriorities=&priority};
    VkDeviceCreateInfo dci={.sType=VK_STRUCTURE_TYPE_DEVICE_CREATE_INFO,.queueCreateInfoCount=1,.pQueueCreateInfos=&qci};
    VkDevice device; CHECK(vkCreateDevice(physical,&dci,NULL,&device));
    VkQueue queue; vkGetDeviceQueue(device,family,0,&queue);
    const uint32_t n=1024; const VkDeviceSize bytes=n*sizeof(uint32_t);
    VkBufferCreateInfo bci={.sType=VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO,.size=bytes,.usage=VK_BUFFER_USAGE_STORAGE_BUFFER_BIT,.sharingMode=VK_SHARING_MODE_EXCLUSIVE};
    VkBuffer buffer; CHECK(vkCreateBuffer(device,&bci,NULL,&buffer));
    VkMemoryRequirements req; vkGetBufferMemoryRequirements(device,buffer,&req);
    VkPhysicalDeviceMemoryProperties mp; vkGetPhysicalDeviceMemoryProperties(physical,&mp);
    uint32_t mt=UINT32_MAX;
    for(uint32_t i=0;i<mp.memoryTypeCount;i++) if((req.memoryTypeBits&(1u<<i)) && ((mp.memoryTypes[i].propertyFlags&(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))==(VK_MEMORY_PROPERTY_HOST_VISIBLE_BIT|VK_MEMORY_PROPERTY_HOST_COHERENT_BIT))){mt=i;break;}
    if(mt==UINT32_MAX)return 1;
    VkMemoryAllocateInfo mai={.sType=VK_STRUCTURE_TYPE_MEMORY_ALLOCATE_INFO,.allocationSize=req.size,.memoryTypeIndex=mt};
    VkDeviceMemory memory; CHECK(vkAllocateMemory(device,&mai,NULL,&memory)); CHECK(vkBindBufferMemory(device,buffer,memory,0));
    void *mapped; CHECK(vkMapMemory(device,memory,0,bytes,0,&mapped)); memset(mapped,0,bytes);
    FILE *f=fopen(argv[1],"rb"); if(!f)return 1; fseek(f,0,SEEK_END); long len=ftell(f); rewind(f);
    if(len<=0 || len%4)return 1;
    uint32_t *code=malloc((size_t)len); if(fread(code,1,(size_t)len,f)!=(size_t)len)return 1; fclose(f);
    VkShaderModuleCreateInfo sci={.sType=VK_STRUCTURE_TYPE_SHADER_MODULE_CREATE_INFO,.codeSize=(size_t)len,.pCode=code};
    VkShaderModule shader; CHECK(vkCreateShaderModule(device,&sci,NULL,&shader)); free(code);
    VkDescriptorSetLayoutBinding binding={.binding=0,.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,.descriptorCount=1,.stageFlags=VK_SHADER_STAGE_COMPUTE_BIT};
    VkDescriptorSetLayoutCreateInfo dlci={.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_LAYOUT_CREATE_INFO,.bindingCount=1,.pBindings=&binding};
    VkDescriptorSetLayout layout; CHECK(vkCreateDescriptorSetLayout(device,&dlci,NULL,&layout));
    VkPipelineLayoutCreateInfo plci={.sType=VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,.setLayoutCount=1,.pSetLayouts=&layout};
    VkPipelineLayout pipelineLayout; CHECK(vkCreatePipelineLayout(device,&plci,NULL,&pipelineLayout));
    VkComputePipelineCreateInfo pci={.sType=VK_STRUCTURE_TYPE_COMPUTE_PIPELINE_CREATE_INFO,.stage={.sType=VK_STRUCTURE_TYPE_PIPELINE_SHADER_STAGE_CREATE_INFO,.stage=VK_SHADER_STAGE_COMPUTE_BIT,.module=shader,.pName="main"},.layout=pipelineLayout};
    VkPipeline pipeline; CHECK(vkCreateComputePipelines(device,VK_NULL_HANDLE,1,&pci,NULL,&pipeline));
    VkDescriptorPoolSize size={.type=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,.descriptorCount=1};
    VkDescriptorPoolCreateInfo dpci={.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_POOL_CREATE_INFO,.maxSets=1,.poolSizeCount=1,.pPoolSizes=&size};
    VkDescriptorPool pool; CHECK(vkCreateDescriptorPool(device,&dpci,NULL,&pool));
    VkDescriptorSetAllocateInfo dsai={.sType=VK_STRUCTURE_TYPE_DESCRIPTOR_SET_ALLOCATE_INFO,.descriptorPool=pool,.descriptorSetCount=1,.pSetLayouts=&layout};
    VkDescriptorSet set; CHECK(vkAllocateDescriptorSets(device,&dsai,&set));
    VkDescriptorBufferInfo dbi={.buffer=buffer,.offset=0,.range=bytes};
    VkWriteDescriptorSet write={.sType=VK_STRUCTURE_TYPE_WRITE_DESCRIPTOR_SET,.dstSet=set,.dstBinding=0,.descriptorCount=1,.descriptorType=VK_DESCRIPTOR_TYPE_STORAGE_BUFFER,.pBufferInfo=&dbi};
    vkUpdateDescriptorSets(device,1,&write,0,NULL);
    VkCommandPoolCreateInfo cpci={.sType=VK_STRUCTURE_TYPE_COMMAND_POOL_CREATE_INFO,.queueFamilyIndex=family};
    VkCommandPool commandPool; CHECK(vkCreateCommandPool(device,&cpci,NULL,&commandPool));
    VkCommandBufferAllocateInfo cbai={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_ALLOCATE_INFO,.commandPool=commandPool,.level=VK_COMMAND_BUFFER_LEVEL_PRIMARY,.commandBufferCount=1};
    VkCommandBuffer command; CHECK(vkAllocateCommandBuffers(device,&cbai,&command));
    VkCommandBufferBeginInfo begin={.sType=VK_STRUCTURE_TYPE_COMMAND_BUFFER_BEGIN_INFO}; CHECK(vkBeginCommandBuffer(command,&begin));
    vkCmdBindPipeline(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipeline);
    vkCmdBindDescriptorSets(command,VK_PIPELINE_BIND_POINT_COMPUTE,pipelineLayout,0,1,&set,0,NULL);
    vkCmdDispatch(command,n/64,1,1);
    VkMemoryBarrier barrier={.sType=VK_STRUCTURE_TYPE_MEMORY_BARRIER,.srcAccessMask=VK_ACCESS_SHADER_WRITE_BIT,.dstAccessMask=VK_ACCESS_HOST_READ_BIT};
    vkCmdPipelineBarrier(command,VK_PIPELINE_STAGE_COMPUTE_SHADER_BIT,VK_PIPELINE_STAGE_HOST_BIT,0,1,&barrier,0,NULL,0,NULL);
    CHECK(vkEndCommandBuffer(command));
    VkFenceCreateInfo fci={.sType=VK_STRUCTURE_TYPE_FENCE_CREATE_INFO}; VkFence fence; CHECK(vkCreateFence(device,&fci,NULL,&fence));
    VkSubmitInfo submit={.sType=VK_STRUCTURE_TYPE_SUBMIT_INFO,.commandBufferCount=1,.pCommandBuffers=&command};
    CHECK(vkQueueSubmit(queue,1,&submit,fence)); CHECK(vkWaitForFences(device,1,&fence,VK_TRUE,10000000000ull));
    uint32_t *values=mapped;
    for(uint32_t i=0;i<n;i++) if(values[i]!=i*3u+7u){fprintf(stderr,"Mismatch at %u: %u\n",i,values[i]);return 1;}
    printf("PASS: %u GPU shader results verified; CPU fallback forbidden\n",n);
    vkUnmapMemory(device,memory); vkDestroyFence(device,fence,NULL); vkDestroyCommandPool(device,commandPool,NULL);
    vkDestroyDescriptorPool(device,pool,NULL); vkDestroyPipeline(device,pipeline,NULL); vkDestroyPipelineLayout(device,pipelineLayout,NULL);
    vkDestroyDescriptorSetLayout(device,layout,NULL); vkDestroyShaderModule(device,shader,NULL); vkDestroyBuffer(device,buffer,NULL); vkFreeMemory(device,memory,NULL);
    vkDestroyDevice(device,NULL); vkDestroyInstance(instance,NULL); return 0;
}
