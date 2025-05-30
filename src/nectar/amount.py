# -*- coding: utf-8 -*-
from decimal import ROUND_DOWN, Decimal

from nectar.asset import Asset
from nectar.instance import shared_blockchain_instance
from nectargraphenebase.py23 import integer_types, string_types


def check_asset(other, self, stm):
    if isinstance(other, dict) and "asset" in other and isinstance(self, dict) and "asset" in self:
        if not Asset(other["asset"], blockchain_instance=stm) == Asset(
            self["asset"], blockchain_instance=stm
        ):
            raise AssertionError()
    else:
        if not other == self:
            raise AssertionError()


def quantize(amount, precision):
    # make sure amount is decimal and has the asset precision
    amount = Decimal(amount)
    places = Decimal(10) ** (-precision)
    return amount.quantize(places, rounding=ROUND_DOWN)


class Amount(dict):
    """This class deals with Amounts of any asset to simplify dealing with the tuple::

        (amount, asset)

    :param list args: Allows to deal with different representations of an amount
    :param float amount: Let's create an instance with a specific amount
    :param str asset: Let's you create an instance with a specific asset (symbol)
    :param boolean fixed_point_arithmetic: when set to True, all operation are fixed
        point operations and the amount is always be rounded down to the precision
    :param Steem steem_instance: Steem instance
    :returns: All data required to represent an Amount/Asset
    :rtype: dict
    :raises ValueError: if the data provided is not recognized

    Way to obtain a proper instance:

        * ``args`` can be a string, e.g.:  "1 SBD"
        * ``args`` can be a dictionary containing ``amount`` and ``asset_id``
        * ``args`` can be a dictionary containing ``amount`` and ``asset``
        * ``args`` can be a list of a ``float`` and ``str`` (symbol)
        * ``args`` can be a list of a ``float`` and a :class:`nectar.asset.Asset`
        * ``amount`` and ``asset`` are defined manually

    An instance is a dictionary and comes with the following keys:

        * ``amount`` (float)
        * ``symbol`` (str)
        * ``asset`` (instance of :class:`nectar.asset.Asset`)

    Instances of this class can be used in regular mathematical expressions
    (``+-*/%``) such as:

    .. testcode::

        from nectar.amount import Amount
        from nectar.asset import Asset
        a = Amount("1 STEEM")
        b = Amount(1, "STEEM")
        c = Amount("20", Asset("STEEM"))
        a + b
        a * 2
        a += b
        a /= 2.0

    .. testoutput::

        2.000 STEEM
        2.000 STEEM

    """

    def __init__(
        self,
        amount,
        asset=None,
        fixed_point_arithmetic=False,
        new_appbase_format=True,
        blockchain_instance=None,
        **kwargs,
    ):
        self["asset"] = {}
        self.new_appbase_format = new_appbase_format
        self.fixed_point_arithmetic = fixed_point_arithmetic

        if blockchain_instance is None:
            if kwargs.get("steem_instance"):
                blockchain_instance = kwargs["steem_instance"]
            elif kwargs.get("hive_instance"):
                blockchain_instance = kwargs["hive_instance"]
        self.blockchain = blockchain_instance or shared_blockchain_instance()

        if amount and asset is None and isinstance(amount, Amount):
            # Copy Asset object
            self["amount"] = amount["amount"]
            self["symbol"] = amount["symbol"]
            self["asset"] = amount["asset"]

        elif amount and asset is None and isinstance(amount, list) and len(amount) == 3:
            # Copy Asset object
            self["amount"] = Decimal(amount[0]) / Decimal(10 ** amount[1])
            self["asset"] = Asset(amount[2], blockchain_instance=self.blockchain)
            self["symbol"] = self["asset"]["symbol"]

        elif (
            amount
            and asset is None
            and isinstance(amount, dict)
            and "amount" in amount
            and "nai" in amount
            and "precision" in amount
        ):
            # Copy Asset object
            self.new_appbase_format = True
            self["amount"] = Decimal(amount["amount"]) / Decimal(10 ** amount["precision"])
            self["asset"] = Asset(amount["nai"], blockchain_instance=self.blockchain)
            self["symbol"] = self["asset"]["symbol"]

        elif amount is not None and asset is None and isinstance(amount, string_types):
            self["amount"], self["symbol"] = amount.split(" ")
            self["asset"] = Asset(self["symbol"], blockchain_instance=self.blockchain)

        elif (
            amount
            and asset is None
            and isinstance(amount, dict)
            and "amount" in amount
            and "asset_id" in amount
        ):
            self["asset"] = Asset(amount["asset_id"], blockchain_instance=self.blockchain)
            self["symbol"] = self["asset"]["symbol"]
            self["amount"] = Decimal(amount["amount"]) / Decimal(10 ** self["asset"]["precision"])

        elif (
            amount
            and asset is None
            and isinstance(amount, dict)
            and "amount" in amount
            and "asset" in amount
        ):
            self["asset"] = Asset(amount["asset"], blockchain_instance=self.blockchain)
            self["symbol"] = self["asset"]["symbol"]
            self["amount"] = Decimal(amount["amount"]) / Decimal(10 ** self["asset"]["precision"])

        elif isinstance(amount, (float)) and asset and isinstance(asset, Asset):
            self["amount"] = str(amount)
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]

        elif isinstance(amount, (integer_types, Decimal)) and asset and isinstance(asset, Asset):
            self["amount"] = amount
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]

        elif isinstance(amount, (float)) and asset and isinstance(asset, dict):
            self["amount"] = str(amount)
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]

        elif isinstance(amount, (integer_types, Decimal)) and asset and isinstance(asset, dict):
            self["amount"] = amount
            self["asset"] = asset
            self["symbol"] = self["asset"]["symbol"]

        elif isinstance(amount, (float)) and asset and isinstance(asset, string_types):
            self["amount"] = str(amount)
            self["asset"] = Asset(asset, blockchain_instance=self.blockchain)
            self["symbol"] = asset

        elif (
            isinstance(amount, (integer_types, Decimal))
            and asset
            and isinstance(asset, string_types)
        ):
            self["amount"] = amount
            self["asset"] = Asset(asset, blockchain_instance=self.blockchain)
            self["symbol"] = asset
        elif amount and asset and isinstance(asset, Asset):
            self["amount"] = amount
            self["symbol"] = asset["symbol"]
            self["asset"] = asset
        elif amount and asset and isinstance(asset, string_types):
            self["amount"] = amount
            self["asset"] = Asset(asset, blockchain_instance=self.blockchain)
            self["symbol"] = self["asset"]["symbol"]
        else:
            raise ValueError
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        else:
            self["amount"] = Decimal(self["amount"])

    def copy(self):
        """Copy the instance and make sure not to use a reference"""
        return Amount(
            amount=self["amount"],
            asset=self["asset"].copy(),
            new_appbase_format=self.new_appbase_format,
            fixed_point_arithmetic=self.fixed_point_arithmetic,
            blockchain_instance=self.blockchain,
        )

    @property
    def amount(self):
        """Returns the amount as float"""
        return float(self["amount"])

    @property
    def amount_decimal(self):
        """Returns the amount as decimal"""
        return self["amount"]

    @property
    def symbol(self):
        """Returns the symbol of the asset"""
        return self["symbol"]

    def tuple(self):
        return float(self), self.symbol

    @property
    def asset(self):
        """Returns the asset as instance of :class:`steem.asset.Asset`"""
        if not self["asset"]:
            self["asset"] = Asset(self["symbol"], blockchain_instance=self.blockchain)
        return self["asset"]

    def json(self):
        if self.blockchain.is_connected() and self.blockchain.rpc.get_use_appbase():
            if self.new_appbase_format:
                return {
                    "amount": str(int(self)),
                    "nai": self["asset"]["asset"],
                    "precision": self["asset"]["precision"],
                }
            else:
                return [str(int(self)), self["asset"]["precision"], self["asset"]["asset"]]
        else:
            return str(self)

    def __str__(self):
        amount = quantize(self["amount"], self["asset"]["precision"])
        symbol = self["symbol"]
        return "{:.{prec}f} {}".format(amount, symbol, prec=self["asset"]["precision"])

    def __float__(self):
        if self.fixed_point_arithmetic:
            return float(quantize(self["amount"], self["asset"]["precision"]))
        else:
            return float(self["amount"])

    def __int__(self):
        amount = quantize(self["amount"], self["asset"]["precision"])
        return int(amount * 10 ** self["asset"]["precision"])

    def __add__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            a["amount"] += other["amount"]
        else:
            a["amount"] += Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __sub__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            a["amount"] -= other["amount"]
        else:
            a["amount"] -= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __mul__(self, other):
        from .price import Price

        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            a["amount"] *= other["amount"]
        elif isinstance(other, Price):
            if not self["asset"] == other["quote"]["asset"]:
                raise AssertionError()
            a = self.copy() * other["price"]
            a["asset"] = other["base"]["asset"].copy()
            a["symbol"] = other["base"]["asset"]["symbol"]
        else:
            a["amount"] *= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __floordiv__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            from .price import Price

            check_asset(other["asset"], self["asset"], self.blockchain)
            return Price(self, other, blockchain_instance=self.blockchain)
        else:
            a["amount"] //= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __div__(self, other):
        from .price import Price

        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return Price(self, other, blockchain_instance=self.blockchain)
        elif isinstance(other, Price):
            if not self["asset"] == other["base"]["asset"]:
                raise AssertionError()
            a = self.copy()
            a["amount"] = a["amount"] / other["price"]
            a["asset"] = other["quote"]["asset"].copy()
            a["symbol"] = other["quote"]["asset"]["symbol"]
        else:
            a["amount"] /= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __mod__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            a["amount"] %= other["amount"]
        else:
            a["amount"] %= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __pow__(self, other):
        a = self.copy()
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            a["amount"] **= other["amount"]
        else:
            a["amount"] **= Decimal(other)
        if self.fixed_point_arithmetic:
            a["amount"] = quantize(a["amount"], self["asset"]["precision"])
        return a

    def __iadd__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            self["amount"] += other["amount"]
        else:
            self["amount"] += Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __isub__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            self["amount"] -= other["amount"]
        else:
            self["amount"] -= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __imul__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            self["amount"] *= other["amount"]
        else:
            self["amount"] *= Decimal(other)

        self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __idiv__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return self["amount"] / other["amount"]
        else:
            self["amount"] /= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __ifloordiv__(self, other):
        if isinstance(other, Amount):
            self["amount"] //= other["amount"]
        else:
            self["amount"] //= Decimal(other)
        self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __imod__(self, other):
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            self["amount"] %= other["amount"]
        else:
            self["amount"] %= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __ipow__(self, other):
        if isinstance(other, Amount):
            self["amount"] **= other
        else:
            self["amount"] **= Decimal(other)
        if self.fixed_point_arithmetic:
            self["amount"] = quantize(self["amount"], self["asset"]["precision"])
        return self

    def __lt__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return quant_amount < quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount < quantize((other or 0), self["asset"]["precision"])

    def __le__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return quant_amount <= quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount <= quantize((other or 0), self["asset"]["precision"])

    def __eq__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return quant_amount == quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount == quantize((other or 0), self["asset"]["precision"])

    def __ne__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return self["amount"] != quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount != quantize((other or 0), self["asset"]["precision"])

    def __ge__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return self["amount"] >= quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount >= quantize((other or 0), self["asset"]["precision"])

    def __gt__(self, other):
        quant_amount = quantize(self["amount"], self["asset"]["precision"])
        if isinstance(other, Amount):
            check_asset(other["asset"], self["asset"], self.blockchain)
            return quant_amount > quantize(other["amount"], self["asset"]["precision"])
        else:
            return quant_amount > quantize((other or 0), self["asset"]["precision"])

    __repr__ = __str__
    __truediv__ = __div__
    __truemul__ = __mul__
