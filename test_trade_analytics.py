import unittest
from types import SimpleNamespace

import x4_supreme_auditor as auditor


class TradeLogParsingTests(unittest.TestCase):
    def setUp(self):
        self.parser = auditor.SaveParser()
        self.parser.tags = ["save", "log", "entry"]
        self.ship = SimpleNamespace(id="ship-1", transactions=[])
        self.parser.ships["ship-1"] = self.ship
        self.parser.ship_by_code["ABC-123"] = self.ship

    def test_reputation_trade_completed_is_not_a_trade(self):
        self.parser._t_entry({
            "time": "233.172",
            "title": "Reputation gained",
            "text": "Reason: Trade Completed[\\012]Current reputation: 20"
        })

        self.assertEqual(self.parser.all_transactions, [])

    def test_trade_requires_amount_and_price(self):
        self.parser._t_entry({
            "time": "60",
            "title": "Trade completed",
            "text": "ABC-123 sold Energy Cells"
        })

        self.assertEqual(self.parser.all_transactions, [])

    def test_player_trade_state_log_is_counted_separately(self):
        self.parser._t_log({
            "type": "trade",
            "owner": "ship-1",
            "ware": "energycells",
            "v": "920"
        })
        self.parser._t_log({
            "type": "trade",
            "owner": "unknown-ship",
            "ware": "energycells",
            "v": "460"
        })

        self.assertEqual(self.parser.trade_state_log_count, 1)
        self.assertEqual(self.parser.all_transactions, [])

    def test_complete_trade_log_resolves_ship_and_values(self):
        self.parser._t_entry({
            "time": "60",
            "title": "Trade completed",
            "text": "ABC-123 sold 500 Energy Cells for 8,000 Cr"
        })

        self.assertEqual(len(self.parser.all_transactions), 1)
        transaction = self.parser.all_transactions[0]
        self.assertEqual(transaction.ship_id, "ship-1")
        self.assertEqual(transaction.ware, "energycells")
        self.assertEqual(transaction.amount, 500)
        self.assertEqual(transaction.price, 16.0)
        self.assertEqual(transaction.op, "SELL")
        self.assertIs(self.ship.transactions[0], transaction)


class TradeCycleMatchingTests(unittest.TestCase):
    def setUp(self):
        self.ship = SimpleNamespace(
            id="ship-1",
            cargo_capacity_m3=100.0,
            category="Trader",
            commander=None,
            assignment=""
        )
        self.parser = SimpleNamespace(
            info={"time": 1000},
            all_transactions=[],
            ships={"ship-1": self.ship}
        )
        self.namer = SimpleNamespace(volume=lambda ware: 1.0, price=lambda ware: 10.0)

    def add_transaction(self, time, amount, price, operation):
        self.parser.all_transactions.append(auditor.TradeTransaction(
            t=time,
            ship_id="ship-1",
            partner_id="npc",
            ware="energycells",
            amount=amount,
            price=price,
            op=operation,
            sector=None
        ))

    def test_partial_sells_consume_fifo_buy_lots_once(self):
        self.add_transaction(1, 10, 2.0, "BUY")
        self.add_transaction(2, 4, 3.0, "SELL")
        self.add_transaction(3, 8, 4.0, "SELL")

        completed, _, _, _ = auditor.process_trade_analytics(self.parser, self.namer)

        self.assertEqual([trade.amount for trade in completed], [4, 6])
        self.assertEqual(sum(trade.net_profit for trade in completed), 16.0)

    def test_unmatched_sell_does_not_invent_cost_or_profit(self):
        self.add_transaction(1, 10, 4.0, "SELL")

        completed, _, _, _ = auditor.process_trade_analytics(self.parser, self.namer)

        self.assertEqual(completed, [])


if __name__ == "__main__":
    unittest.main()