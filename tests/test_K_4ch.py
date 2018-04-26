import unittest
import logging

from support.test import auto_test, AutoTestSuite
from support.logs import setup_logging

from MonitorControl.FrontEnds.Kband import K_4ch

auto_tester = AutoTestSuite(K_4ch,args=("K",))
suite, TestK_4ch_factory = auto_tester.create_test_suite(factory=True)

class TestK_4ch(TestK_4ch_factory()):
    pass

class TestK_4ch_with_hardware(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fe = K_4ch("K",hardware=True)

    def test_init(self):
        self.assertTrue(self.fe.channel.keys() == ["F1","F2"])

    def test_read_temp(self):
        temp = self.fe.read_temps()
        print(temp)

    def test_read_pm(self):
        pm = self.fe.read_PMs()
        print(pm)

if __name__ == "__main__":
    setup_logging(logLevel=logging.DEBUG)
    unittest.main()
