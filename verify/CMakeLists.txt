cmake_minimum_required(VERSION 3.22)
project(ai370_verification LANGUAGES C CXX)
find_package(Vulkan REQUIRED)
add_executable(vulkan-compute vulkan_compute.c)
target_link_libraries(vulkan-compute PRIVATE Vulkan::Vulkan)
target_compile_options(vulkan-compute PRIVATE -Wall -Wextra)
add_custom_command(OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/verify.spv
  COMMAND glslc ${CMAKE_CURRENT_SOURCE_DIR}/vulkan_compute.comp -o ${CMAKE_CURRENT_BINARY_DIR}/verify.spv
  DEPENDS vulkan_compute.comp)
add_custom_target(shader ALL DEPENDS ${CMAKE_CURRENT_BINARY_DIR}/verify.spv)
