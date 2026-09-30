import unittest
from m5_kernel_policy import classify

class PolicyTest(unittest.TestCase):
    warning = "amdxdna: module verification failed: signature and/or required key missing - tainting kernel"
    def test_expected_signature_warning(self):
        w, f = classify(self.warning, "SecureBoot disabled", "2.21.260102.53.release_20260309")
        self.assertEqual((len(w), len(f)), (1, 0))
    def test_wrong_module_or_enabled_secure_boot(self):
        for sb, version in [("SecureBoot enabled", "2.21.260102.53.release"), ("SecureBoot disabled", "inbox")]:
            self.assertTrue(classify(self.warning, sb, version)[1])
    def test_functional_failure_survives_warning(self):
        for error in ["amdxdna: command timeout", "amdxdna: execution failed", "amdgpu: GPU reset", "amdgpu: VM fault"]:
            self.assertTrue(classify(self.warning + "\n" + error, "SecureBoot disabled", "2.21.260102.53.release")[1])

if __name__ == "__main__":
    unittest.main()
