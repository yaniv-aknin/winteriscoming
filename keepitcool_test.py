#!/usr/bin/env python
import os
import logging
import sys
import unittest

import keepitcool

logging.getLogger().setLevel(logging.CRITICAL)

class TestCoolKeeper(unittest.TestCase):
    SAMPLE_READING='|/dev/disk/by-nickname/buscemi|WDC WD30EZRX-00DC0B0|25|C||/dev/disk/by-nickname/bridges|WDC WD30EZRX-00DC0B0|26|C||/dev/disk/by-nickname/goodman|WDC WD30EZRX-00DC0B0|26|C|'
    SAMPLE_UNSUPPORTED='|/dev/disk/by-nickname/buscemi|WDC WD30EZRX-00DC0B0|24|C||/dev/disk/by-nickname/bridges|WDC WD30EZRX-00DC0B0|26|C||/dev/disk/by-nickname/goodman|WDC WD30EZRX-00DC0B0|26|C||/dev/sdf|WD PP III Studio II|NOS|*|'
    SAMPLE_ONE_TEMPLATE='|/dev/disk/by-nickname/buscemi|WDC WD30EZRX-00DC0B0|%s|C||/dev/disk/by-nickname/bridges|WDC WD30EZRX-00DC0B0|26|C||/dev/disk/by-nickname/goodman|WDC WD30EZRX-00DC0B0|26|C|'

    def setUp(self):
        self.keeper = keepitcool.CoolKeeper()

    def testParseReading(self):
        self.keeper.raw = self.SAMPLE_READING
        self.keeper.parse_reading()
        self.assertEqual(self.keeper.disks, {('/dev/disk/by-nickname/bridges', 'WDC WD30EZRX-00DC0B0'): '26',
                                             ('/dev/disk/by-nickname/buscemi', 'WDC WD30EZRX-00DC0B0'): '25',
                                             ('/dev/disk/by-nickname/goodman', 'WDC WD30EZRX-00DC0B0'): '26'})

    def testParseUnsupported(self):
        self.keeper.raw = self.SAMPLE_UNSUPPORTED
        self.keeper.parse_reading()
        self.assertEqual(self.keeper.disks, {('/dev/disk/by-nickname/bridges', 'WDC WD30EZRX-00DC0B0'): '26',
                                             ('/dev/disk/by-nickname/buscemi', 'WDC WD30EZRX-00DC0B0'): '24',
                                             ('/dev/disk/by-nickname/goodman', 'WDC WD30EZRX-00DC0B0'): '26',
                                             ('/dev/sdf', 'WD PP III Studio II'): 'NOS'})

    def testEvaluateStatus(self):
        self.keeper.raw = self.SAMPLE_READING
        self.keeper.parse_reading()
        self.keeper.evaluate_status()
        self.assertFalse(self.keeper.warning)
        self.assertEqual(self.keeper.error, 0)
        self.assertFalse(self.keeper.fatal)
        self.assertFalse(self.keeper.output)

    def testEvaluateStatus_Warning(self):
        self.keeper.raw = self.SAMPLE_ONE_TEMPLATE % (self.keeper.WARNING_THRESHOLD,)
        self.keeper.parse_reading()
        self.keeper.evaluate_status()
        self.assertTrue(self.keeper.warning)
        self.assertEqual(self.keeper.error, 0)
        self.assertFalse(self.keeper.fatal)
        self.assertTrue(self.keeper.output)

    def testEvaluateStatus_Fatal(self):
        self.keeper.raw = self.SAMPLE_ONE_TEMPLATE % (self.keeper.FATAL_THRESHOLD,)
        self.keeper.parse_reading()
        self.keeper.evaluate_status()
        self.assertTrue(self.keeper.warning)
        self.assertEqual(self.keeper.error, 1)
        self.assertTrue(self.keeper.fatal)
        self.assertTrue(self.keeper.output)

    def testShutdownOnFatal(self):
        shutdown_invocations = []
        self.keeper.fatal = True
        self.keeper.shutdown = lambda: shutdown_invocations.append(True)
        self.keeper.perform_required_actions()
        self.assertTrue(shutdown_invocations)


if __name__ == '__main__':
    unittest.main()
