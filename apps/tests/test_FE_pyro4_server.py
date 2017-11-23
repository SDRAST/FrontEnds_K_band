import logging
import unittest
import threading

import Pyro4
import Pyro4.socketutil
import Pyro4.naming

import pyro4tunneling

from FE_pyro4_server import FEServer

class TestFEServer(unittest.TestCase):

    isSetup = False
    server = None
    client = None

    def setUp(self):
        if not self.__class__.isSetup:

            port = Pyro4.socketutil.findProbablyUnusedPort()
            ns_details = Pyro4.naming.startNS(port=port)
            ns_thread = threading.Thread(target=ns_details[1].requestLoop)
            ns_thread.daemon = True
            ns_thread.start()

            res = pyro4tunneling.util.check_connection(Pyro4.locateNS, kwargs={"port":port})
            ns = Pyro4.locateNS(port=port)

            name = "FE_pyro4_server"
            logger = logging.getLogger(name)
            logger.setLevel(logging.DEBUG)
            server = FEServer(name, logger=logger)
            server_thread = server.launch_server(ns_port=port, local=True, threaded=True)

            self.__class__.client = Pyro4.Proxy(ns.lookup(server.name))
            self.__class__.server = server
            self.__class__.isSetup = True

        else:
            pass

    def test_read_temp(self):
        client = self.__class__.client
        result = client.read_temp()
        self.assertTrue(isinstance(result, dict))

    def test_set_feed(self):
        client = self.__class__.client

    def test_get_ND_state(self):
        client = self.__class__.client
        result = client.get_ND_state()
        self.assertIsNotNone(result)

    def test_set_ND_state(self):
        client = self.__class__.client

    def test_set_preamp_bias(self):
        client = self.__class__.client

if __name__ == "__main__":
    logging.basicConfig(loglevel=logging.DEBUG)
    suite_get = unittest.TestSuite()
    suite_set = unittest.TestSuite()

    suite_get.addTest(TestFEServer("test_read_temp"))
    suite_get.addTest(TestFEServer("test_get_ND_state"))

    suite_set.addTest(TestFEServer("test_set_feed"))
    suite_set.addTest(TestFEServer("test_set_ND_state"))
    suite_set.addTest(TestFEServer("test_set_preamp_bias"))

    result_get = unittest.TextTestRunner().run(suite_get)
    if result_get.wasSuccessful():
        unittest.TextTestRunner().run(suite_set)
