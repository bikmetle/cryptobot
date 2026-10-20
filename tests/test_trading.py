import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import trading
from bitget import BtcOrderResult, _check_response
from database import Base, BitcoinTrade, Company
from trading_exceptions import ExitFailedException, LessThanMinimumAmountException
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


class RetryTest(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.planned_entry_usd = 5
    
    def get_args(self, price):
        btc_amount=D(self.planned_entry_usd)/D(price)
        return (D(price), D(self.planned_entry_usd), btc_amount, object(), self.now)

    def sell_order(self, old_price, new_price):
        exiting_trade_btc = D(self.planned_entry_usd)/D(old_price)
        planned_entry_btc = D(self.planned_entry_usd)/D(new_price)
        btc = exiting_trade_btc - planned_entry_btc        
        usd = btc*new_price
        return BtcOrderResult(
            usd=D(usd),
            btc=D(btc),
            price=D(new_price),
        )

    def trade(self, trade_id, entry_price):
        return BitcoinTrade(
            id=trade_id,
            btc_amount=D(self.planned_entry_usd)/D(entry_price),
            entry_price=D(entry_price),
            entry_usd_amount=D(self.planned_entry_usd),
            entered_at=self.now,
        )

    def test_no_exit_trades(self):
        with patch.object(trading, 'get_trades_to_exit', return_value=[]), \
                patch.object(trading, 'buy_btc') as buy, \
                patch.object(trading, 'sell_btc') as sell:
            with self.assertRaises(ExitFailedException):
                trading.exit_order(*self.args)
            buy.assert_not_called()
            sell.assert_not_called()

    def test_exit_above_one_dollar_succeeds_at_trade_time(self):
        old_price = 60000
        new_price = 85000
        candidate = self.trade(1, old_price)
        buy_order = self.sell_order(old_price, new_price)
        with patch.object(trading, 'get_trades_to_exit', return_value=[candidate]), \
                patch.object(trading, 'sell_btc', return_value=buy_order) as buy, \
                patch.object(trading, 'record_trade_exit') as record_exit, \
                patch.object(trading, 'update_company') as update_company:
            result = trading.exit_order(self.get_args(new_price))

        self.assertEqual(result[:3], (D('80000'), D('0.000030'), D('2.40')))
        buy.assert_called_once_with(D('1.200000'))
        record_exit.assert_called_once_with(
            self.args[3], candidate, D('1.200000'), D('80000'), self.now
        )
        update_company.assert_called_once_with(
            self.args[3], D('1.200000'), D('-0.000015')
        )

    def test_exit_above_one_dollar_rejected_below_minimum_at_trade_time(self):
        candidate = self.trade(1, '0.000015')
        rejection = LessThanMinimumAmountException('below minimum at execution')
        with patch.object(trading, 'get_trades_to_exit', return_value=[candidate]), \
                patch.object(trading, 'buy_btc', side_effect=rejection) as buy, \
                patch.object(trading, 'record_trade_exit') as record_exit:
            with self.assertRaises(ExitFailedException):
                trading.exit_order(*self.args)

        buy.assert_called_once_with(D('1.200000'))
        record_exit.assert_not_called()

    def test_rejected_exit_retries_another_exit_above_one_dollar(self):
        rejected = self.trade(1, '0.000014')
        successful = self.trade(2, '0.000015')
        rejection = LessThanMinimumAmountException('below minimum at execution')
        with patch.object(trading, 'get_trades_to_exit', return_value=[rejected, successful]), \
                patch.object(trading, 'buy_btc', side_effect=[rejection, self.sell_order]) as buy, \
                patch.object(trading, 'sell_btc') as sell, \
                patch.object(trading, 'record_trade_exit') as record_exit, \
                patch.object(trading, 'update_company'):
            result = trading.exit_order(*self.args)

        self.assertEqual(result[:3], (D('80000'), D('0.000030'), D('2.40')))
        self.assertEqual(
            [call.args[0] for call in buy.call_args_list],
            [D('1.280000'), D('1.200000')],
        )
        sell.assert_not_called()
        self.assertIs(record_exit.call_args.args[1], successful)

    def test_rejected_exits_retry_until_no_exit_trades_remain(self):
        candidates = [self.trade(1, '0.000014'), self.trade(2, '0.000015')]
        rejection = LessThanMinimumAmountException('below minimum at execution')
        with patch.object(trading, 'get_trades_to_exit', return_value=candidates), \
                patch.object(trading, 'buy_btc', side_effect=rejection) as buy, \
                patch.object(trading, 'sell_btc') as sell, \
                patch.object(trading, 'record_trade_exit') as record_exit:
            with self.assertRaises(ExitFailedException):
                trading.exit_order(*self.args)

        self.assertEqual(
            [call.args[0] for call in buy.call_args_list],
            [D('1.280000'), D('1.200000')],
        )
        sell.assert_not_called()
        record_exit.assert_not_called()

    def test_exit_below_one_dollar_difference_is_not_attempted(self):
        engine = create_engine('sqlite:///:memory:')
        self.addCleanup(engine.dispose)
        Base.metadata.create_all(engine)
        with Session(engine) as session, session.begin():
            session.add(self.trade(1, '0.000020'))

        with Session(engine) as session, \
                patch.object(utils, 'INTEREST', '0'), \
                patch.object(utils, 'MIN_PLATFORM_USD', '1'), \
                patch.object(trading, 'buy_btc') as buy, \
                patch.object(trading, 'sell_btc') as sell:
            with self.assertRaises(ExitFailedException):
                trading.exit_order(
                    D('80000'), D('2.40'), D('0.000030'), session, self.now
                )

        buy.assert_not_called()
        sell.assert_not_called()


if __name__ == '__main__':
    unittest.main()
