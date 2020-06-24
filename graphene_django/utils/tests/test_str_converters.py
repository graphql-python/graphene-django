# coding: utf-8
from ..str_converters import to_const


def test_to_const():
    assert to_const('snakes $1. on a "#plane') == "SNAKES_1_ON_A_PLANE"


def test_to_const_unicode():
    assert to_const(u"Skoða þetta unicode stöff") == "SKODA_THETTA_UNICODE_STOFF"
