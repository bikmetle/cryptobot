import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import trading
from bitget import BtcOrderResult, _check_response
from database import Base, BitcoinTrade, Company
from trading_exceptions import LessThanMinimumAmountException


class TradingTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.addCleanup(self.engine.dispose)
        self.now = datetime.now(timezone.utc)
        self.order = BtcOrderResult(usd=D('10'), btc=D('1'), price=D('10'))
        for name, value in [('calculate_usd_amount', D('10')), ('get_btc_prices', (D('10'), D('10')))]:
            mock = patch.object(trading, name, return_value=value)
            mock.start()
            self.addCleanup(mock.stop)

    def seed(self):
        with Session(self.engine) as session, session.begin():
            session.add(Company(balance=D('100'), btc=D('2'), created_at=self.now))
            session.add(BitcoinTrade(btc_amount=D('2'), entry_price=D('1'), entry_usd_amount=D('2'), entered_at=self.now))

    def candidates(self, session, *args):
        return list(session.scalars(select(BitcoinTrade)))

    def test_fresh_company_and_fallback_committed(self):
        with Session(self.engine) as session, patch.object(trading, 'buy_btc', return_value=self.order) as buy:
            self.assertIn('bought', trading.trade(session, self.now))
            buy.assert_called_once_with(D('10'))
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Company)).balance, D('-10'))
            self.assertEqual(len(list(session.scalars(select(BitcoinTrade)))), 1)

    def test_exit_and_replacement_committed_together(self):
        self.seed()
        with Session(self.engine) as session, patch.object(trading, 'get_trades_to_exit', side_effect=self.candidates), patch.object(trading, 'sell_btc', return_value=self.order):
            self.assertIn('sold', trading.trade(session, self.now))
        with Session(self.engine) as session:
            trades = list(session.scalars(select(BitcoinTrade).order_by(BitcoinTrade.id)))
            self.assertEqual(len(trades), 2)
            self.assertEqual(trades[0].exit_price, D('10'))
            company = session.scalar(select(Company))
            self.assertEqual((company.balance, company.btc), (D('110'), D('1')))

    def test_failure_after_exit_rolls_back_without_retry(self):
        self.seed()
        with Session(self.engine) as session, patch.object(trading, 'get_trades_to_exit', side_effect=self.candidates), patch.object(trading, 'sell_btc', return_value=self.order) as sell, patch.object(trading, 'buy_btc') as buy, patch.object(trading, 'record_trade_entry', side_effect=LessThanMinimumAmountException('persistence failure')):
            with self.assertRaises(LessThanMinimumAmountException):
                trading.trade(session, self.now)
            sell.assert_called_once()
            buy.assert_not_called()
            self.assertFalse(session.in_transaction())
        with Session(self.engine) as session:
            trades = list(session.scalars(select(BitcoinTrade)))
            self.assertEqual(len(trades), 1)
            self.assertIsNone(trades[0].exit_price)
            company = session.scalar(select(Company))
            self.assertEqual((company.balance, company.btc), (D('100'), D('2')))

    def test_minimum_rejection_logs_details_and_falls_back(self):
        self.seed()
        with Session(self.engine) as session, patch.object(trading, 'get_trades_to_exit', side_effect=self.candidates), patch.object(trading, 'sell_btc', side_effect=LessThanMinimumAmountException('exchange detail')), patch.object(trading, 'buy_btc', return_value=self.order) as buy, self.assertLogs('trading') as logs:
            trading.trade(session, self.now)
            buy.assert_called_once()
            self.assertIn('exchange detail', logs.output[0])

    def test_api_error_preserves_message(self):
        with self.assertRaisesRegex(LessThanMinimumAmountException, '45110: exchange detail'):
            _check_response({'code': '45110', 'msg': 'exchange detail'})


if __name__ == '__main__':
    unittest.main()
