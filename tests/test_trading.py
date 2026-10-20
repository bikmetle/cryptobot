import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import trading
from bitget import _check_response
from exchange_types import BtcOrderResult
from database import Base, BitcoinTrade, Company
from trading_exceptions import LessThanMinimumAmountException
import utils


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

    def test_fresh_company_and_entry_committed(self):
        with Session(self.engine) as session, patch.object(trading, 'buy_btc', return_value=self.order) as buy:
            self.assertIn('bought', trading.trade(session, self.now))
            buy.assert_called_once_with(D('10'))
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Company)).balance, D('-10'))
            self.assertEqual(len(list(session.scalars(select(BitcoinTrade)))), 1)

    def test_exit_and_replacement_committed_together(self):
        self.seed()
        with Session(self.engine) as session, patch.object(trading, 'get_trades_to_exit', side_effect=self.candidates), patch.object(trading, 'sell_btc', return_value=BtcOrderResult(usd=D('20'), btc=D('2'), price=D('10'))) as sell, patch.object(trading, 'buy_btc', return_value=self.order) as buy:
            self.assertIn('sold', trading.trade(session, self.now))
            sell.assert_called_once_with(D('2'))
            buy.assert_called_once_with(D('10'))
        with Session(self.engine) as session:
            trades = list(session.scalars(select(BitcoinTrade).order_by(BitcoinTrade.id)))
            self.assertEqual(len(trades), 2)
            self.assertEqual(trades[0].exit_price, D('10'))
            company = session.scalar(select(Company))
            self.assertEqual((company.balance, company.btc), (D('110'), D('1')))

    def test_failure_after_exit_rolls_back_without_retry(self):
        self.seed()
        with Session(self.engine) as session, patch.object(trading, 'get_trades_to_exit', side_effect=self.candidates), patch.object(trading, 'sell_btc', return_value=self.order) as sell, patch.object(trading, 'buy_btc', return_value=self.order) as buy, patch.object(trading, 'record_trade_entry', side_effect=LessThanMinimumAmountException('persistence failure')):
            with self.assertRaises(LessThanMinimumAmountException):
                trading.trade(session, self.now)
            sell.assert_called_once()
            buy.assert_called_once_with(D('10'))
            self.assertFalse(session.in_transaction())
        with Session(self.engine) as session:
            trades = list(session.scalars(select(BitcoinTrade)))
            self.assertEqual(len(trades), 1)
            self.assertIsNone(trades[0].exit_price)
            company = session.scalar(select(Company))
            self.assertEqual((company.balance, company.btc), (D('100'), D('2')))

    def test_exit_rejection_propagates_without_buying_or_changing_rows(self):
        self.seed()
        with Session(self.engine) as session, patch.object(trading, 'get_trades_to_exit', side_effect=self.candidates), patch.object(trading, 'sell_btc', side_effect=LessThanMinimumAmountException('exchange detail')) as sell, patch.object(trading, 'buy_btc') as buy:
            with self.assertRaisesRegex(LessThanMinimumAmountException, 'exchange detail'):
                trading.trade(session, self.now)
            sell.assert_called_once_with(D('2'))
            buy.assert_not_called()
            self.assertFalse(session.in_transaction())
        with Session(self.engine) as session:
            trades = list(session.scalars(select(BitcoinTrade)))
            self.assertEqual(len(trades), 1)
            self.assertIsNone(trades[0].exit_price)
            company = session.scalar(select(Company))
            self.assertEqual((company.balance, company.btc), (D('100'), D('2')))

    def test_api_error_preserves_message(self):
        with self.assertRaisesRegex(LessThanMinimumAmountException, '45110: exchange detail'):
            _check_response({'code': '45110', 'msg': 'exchange detail'})


class ExitOrderTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.session = object()
        self.planned_entry_usd = D('5')

    def candidate(self, trade_id):
        return BitcoinTrade(
            id=trade_id,
            btc_amount=D('0.0001'),
            entry_price=D('50000'),
            entry_usd_amount=D('5'),
            entered_at=self.now,
        )

    def test_no_exit_trades_returns_zero_without_order(self):
        with patch.object(trading, 'get_trades_to_exit', return_value=[]), \
                patch.object(trading, 'buy_btc') as buy, \
                patch.object(trading, 'sell_btc') as sell, \
                patch.object(trading, 'record_trade_exit') as record_exit, \
                patch.object(trading, 'update_company') as update_company:
            self.assertEqual(
                trading.exit_order(D('85000'), self.planned_entry_usd, self.session, self.now),
                (0, 0),
            )
        buy.assert_not_called()
        sell.assert_not_called()
        record_exit.assert_not_called()
        update_company.assert_not_called()

    def test_only_first_candidate_is_sold_in_full_and_actual_fill_is_recorded(self):
        first, second = self.candidate(1), self.candidate(2)
        order = BtcOrderResult(usd=D('8.49'), btc=D('0.0001'), price=D('84900'))
        with patch.object(trading, 'get_trades_to_exit', return_value=[first, second]) as candidates, \
                patch.object(trading, 'sell_btc', return_value=order) as sell, \
                patch.object(trading, 'buy_btc') as buy, \
                patch.object(trading, 'record_trade_exit') as record_exit, \
                patch.object(trading, 'update_company') as update_company:
            result = trading.exit_order(D('85000'), self.planned_entry_usd, self.session, self.now)

        self.assertEqual(result, (order.btc, order.usd))
        candidates.assert_called_once_with(self.session, D('85000'), self.planned_entry_usd, self.now)
        sell.assert_called_once_with(first.btc_amount)
        buy.assert_not_called()
        record_exit.assert_called_once_with(first, order.usd, order.price, self.now)
        update_company.assert_called_once_with(self.session, order.usd, -order.btc)

    def test_rejected_exit_propagates_without_trying_next_candidate(self):
        first, second = self.candidate(1), self.candidate(2)
        rejection = LessThanMinimumAmountException('below minimum at execution')
        with patch.object(trading, 'get_trades_to_exit', return_value=[first, second]), \
                patch.object(trading, 'sell_btc', side_effect=rejection) as sell, \
                patch.object(trading, 'record_trade_exit') as record_exit, \
                patch.object(trading, 'update_company') as update_company:
            with self.assertRaises(LessThanMinimumAmountException) as error:
                trading.exit_order(D('85000'), self.planned_entry_usd, self.session, self.now)

        self.assertIs(error.exception, rejection)
        sell.assert_called_once_with(first.btc_amount)
        record_exit.assert_not_called()
        update_company.assert_not_called()

    def test_exit_below_minimum_dollar_difference_is_not_attempted(self):
        engine = create_engine('sqlite:///:memory:')
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            session.add(self.candidate(1))

        with Session(engine) as session, \
                patch.object(utils, 'INTEREST', '0'), \
                patch.object(utils, 'MIN_PLATFORM_USD', '1'), \
                patch.object(trading, 'buy_btc') as buy, \
                patch.object(trading, 'sell_btc') as sell:
            self.assertEqual(
                trading.exit_order(D('55000'), self.planned_entry_usd, session, self.now),
                (0, 0),
            )

        buy.assert_not_called()
        sell.assert_not_called()


if __name__ == '__main__':
    unittest.main()
