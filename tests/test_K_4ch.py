import unittest

from support.test import auto_test, AutoTestSuite

from MonitorControl.FrontEnds.Kband import K_4ch

auto_tester = AutoTestSuite(K_4ch)
suite, unittest_cls = auto_tester.create_test_suite()

class TestK_4ch(unittest_cls):
    pass

if __name__ == "__main__":
    unittest.main()
