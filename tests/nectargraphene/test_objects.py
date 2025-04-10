# This Python file uses the following encoding: utf-8
from __future__ import absolute_import, division, print_function, unicode_literals

import json
import unittest

import pytest

from nectargraphenebase import objects, types


class Testcases(unittest.TestCase):
    @pytest.mark.skipif(
        not hasattr(objects, "Array"),
        reason="AttributeError: module 'nectargraphenebase.objects' has no attribute 'Array'",
    )
    def test_GrapheneObject(self):
        j = {"a": 2, "b": "abcde", "c": ["a", "b"]}
        j2 = objects.GrapheneObject(j)
        self.assertEqual(j, j2.data)
        self.assertEqual(json.loads(j2.__str__()), j2.json())

        a = objects.Array(["1000", 3, "@@000000013"])
        j = {"a": a}
        j2 = objects.GrapheneObject(j)
        self.assertEqual(j, j2.data)
        self.assertEqual(json.loads(j2.__str__()), j2.json())

        a = types.Array(["1000", 3, "@@000000013"])
        j = {"a": a}
        j2 = objects.GrapheneObject(j)
        self.assertEqual(j, j2.data)
        self.assertEqual(json.loads(j2.__str__()), j2.json())
