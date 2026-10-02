#!/usr/bin/env python3
import unittest
from apt_change_guard import classify_simulation


class ProtectedStackSimulationTests(unittest.TestCase):
    def test_safe_new_userspace_package(self):
        result = classify_simulation("Inst libfmt-dev (10.1.1-2 Ubuntu:24.04/noble [amd64])")
        self.assertEqual(result["verdict"], "SAFE_SIMULATION")
        self.assertFalse(result["actions"][0]["protected"])

    def test_graphics_and_drm_changes_blocked(self):
        result = classify_simulation(
            "Inst mesa-vulkan-drivers [25.2.8-1] (25.3.0-1 Ubuntu:24.04/noble [amd64])\n"
            "Inst libdrm-amdgpu1:amd64 [2.4.125-1] (2.4.126-1 Ubuntu:24.04/noble [amd64])"
        )
        self.assertEqual(len(result["protected_changes"]), 2)
        self.assertEqual(result["verdict"], "BLOCKED_PROTECTED_STACK")

    def test_kernel_xrt_and_firmware_removals_blocked(self):
        result = classify_simulation(
            "Remv linux-image-6.17.0-14-generic [6.17.0-14.14~24.04.1]\n"
            "Remv xrt-base [2.21.75]\n"
            "Remv linux-firmware [20240318.git3b128b60-0ubuntu2.15]"
        )
        self.assertEqual(len(result["protected_changes"]), 3)

    def test_strict_mode_fails_closed_when_apt_summary_is_missing(self):
        result = classify_simulation("NOTE: simulation", strict=True)
        self.assertEqual(result["verdict"], "UNKNOWN_SIMULATION_OUTPUT")

    def test_rocm_libraries_and_amdgpu_driver_blocked(self):
        result = classify_simulation(
            "Inst librocblas0 (4.3.0 Ubuntu:24.04/noble [amd64])\n"
            "Inst libamdhip64 (7.2.0 Ubuntu:24.04/noble [amd64])\n"
            "Inst amdgpu-dkms (6.14.0 Ubuntu:24.04/noble [amd64])"
        )
        self.assertEqual(len(result["protected_changes"]), 3)

    def test_unrelated_replacement_and_protected_change_blocked(self):
        result = classify_simulation(
            "Inst libncurses6 (6.4-2 Ubuntu:24.04/noble [amd64])\n"
            "Inst hip-runtime-amd (7.2.1 Ubuntu:24.04/noble [amd64])"
        )
        self.assertEqual(len(result["actions"]), 2)
        self.assertEqual(result["protected_changes"][0]["package"], "hip-runtime-amd")


if __name__ == "__main__":
    unittest.main()
