import unittest
import run_workstation_model_performance as p


class HardwareAwareTests(unittest.TestCase):
    def test_background_swap_changes_are_not_an_arbitrary_growth_stop(self):
        total=48*1024**2
        self.assertIsNone(p.risk(20*1024**2,total,0,4,30,0))
        self.assertIsNone(p.risk(3*1024**2,total,0,0,0,0))

    def test_real_pressure_and_emergency_remain_guarded(self):
        total=48*1024**2
        self.assertEqual(p.risk(512*1024,total,0,0,0,0),'EMERGENCY_LOW_MEMORY')
        self.assertEqual(p.risk(2*1024**2,total,5,0,0,0),'SUSTAINED_LOW_MEMORY')
        self.assertEqual(p.risk(20*1024**2,total,0,40,10,0),'SUSTAINED_SWAPOUT')

    def test_configs_use_all_available_threads_and_explicit_devices(self):
        import os
        for backend in ['cpu','vulkan','hip']:
            c=p.base_config(backend)
            self.assertEqual(c['threads'],len(os.sched_getaffinity(0)))
            self.assertEqual(c['layers'],0 if backend=='cpu' else 99)
            self.assertEqual(c['prompt_tokens'],512)
            self.assertEqual(c['output_tokens'],128)

    def test_kernel_gate_not_confused_with_successful_generation(self):
        self.assertFalse(p.safe({'status':'PASS','resources':{},'kernel_audit':{'read_exit':0,'faults':['fault']}}))
        self.assertTrue(p.safe({'status':'PASS','resources':{'guard':None},'kernel_audit':{'read_exit':0,'faults':[]}}))


if __name__=='__main__':unittest.main()
