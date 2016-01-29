__author__ = 'kako'

import unittest
import xmlrunner

from tests.test_file import *
from tests.test_streams import *


if __name__ == '__main__':
    unittest.main(
        testRunner=xmlrunner.XMLTestRunner(output='test-reports'),
        # these make sure that some options that are not applicable
        # remain hidden from the help menu.
        failfast=False, buffer=False, catchbreak=False
    )
