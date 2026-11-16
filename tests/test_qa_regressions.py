"""GitHub DEV01~DEV05 회귀 테스트. 실제 데이터는 변경하지 않는다."""
import csv
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from unittest import TestCase
from unittest.mock import patch

from streamlit.testing.v1 import AppTest
import test_rental
from services import storage
from services.chatbot import ChatError, find_date, get_inventory_facts, get_reply
from services.rental import create_rental
from services.return_service import get_return_history, register_return


class QaRegressionTests(TestCase):
    setUp = test_rental.RentalTests.setUp

    def app(self, path):
        return AppTest.from_file(str(Path(__file__).resolve().parents[1] / path)).run()

    def raw_csv(self, name, fields, rows):
        with (storage.DATA_DIR / name).open('w', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_dev01_explicit_date_wins_over_now_and_relative_words(self):
        day = self.today + timedelta(days=10)
        for phrase in ['지금 예약 가능해?', '내일이라고 하지 말고 알려줘', '현재 예약 가능해?']:
            self.assertEqual(find_date(f'{day.isoformat()} Test {phrase}'), day)
        self.assertEqual(find_date('12월 20일 지금 예약 가능해?').month, 12)

    def test_dev01_invalid_and_multiple_explicit_dates_need_confirmation(self):
        with self.assertRaises(ChatError):
            find_date('2027-02-30 지금 재고')
        with self.assertRaisesRegex(ChatError, '하루'):
            find_date('2027-11-20부터 2027-11-22까지 Test')
        with self.assertRaises(ChatError):
            find_date('11월 20일과 11월 22일 Test')

    @patch('services.chatbot.Client')
    def test_dev02_unknown_item_stops_before_model_call(self, client):
        with self.assertRaisesRegex(ChatError, '물품을 확인하지 못했습니다'):
            get_reply([], '없는물품XYZ 3개 대여 가능해?', self.today)
        client.assert_not_called()
        with self.assertRaises(ChatError):
            get_inventory_facts('A000 3개', self.today)

    def test_dev02_known_item_ids_and_explicit_all_queries(self):
        rows = storage.read_rows('items.csv')
        rows.append(dict(item_id='B', name='빔 프로젝터', category='Test', total=5))
        storage.write_rows('items.csv', storage.ITEM_FIELDS, rows)
        for question in ['전체 재고', '오늘 전체 재고 알려줘', '모든 물품 보여줘', '재고 알려줘']:
            facts = get_inventory_facts(question, self.today)
            self.assertIn('Test (A)', facts)
            self.assertIn('빔 프로젝터 (B)', facts)
        facts = get_inventory_facts('빔프로젝터 2개', self.today)
        self.assertIn('빔 프로젝터 (B)', facts)
        self.assertNotIn('Test (A)', facts)
        self.assertIn('Test (A)', get_inventory_facts('A 1개', self.today))

    def test_dev03_bad_counts_give_filename_row_and_column(self):
        for bad in ['abc', '-1', '1.5', '']:
            self.raw_csv('items.csv', storage.ITEM_FIELDS, [dict(item_id='A', name='Test', category='Test', total=bad)])
            with self.assertRaises(storage.DataError) as error:
                storage.read_rows('items.csv')
            for expected in ['items.csv', '2행', 'total', '정수']:
                self.assertIn(expected, str(error.exception))

    def test_dev03_missing_columns_and_duplicate_item_ids(self):
        self.raw_csv('items.csv', ['item_id', 'name'], [dict(item_id='A', name='Test')])
        with self.assertRaisesRegex(storage.DataError, '필수 컬럼'):
            storage.read_rows('items.csv')
        rows = [dict(item_id='A', name='Test', category='Test', total=10)] * 2
        self.raw_csv('items.csv', storage.ITEM_FIELDS, rows)
        with self.assertRaisesRegex(storage.DataError, '중복'):
            storage.read_rows('items.csv')

    def test_dev03_data_error_is_shown_in_all_related_pages(self):
        self.raw_csv('items.csv', storage.ITEM_FIELDS, [dict(item_id='A', name='Test', category='Test', total='abc')])
        for path in ['pages/1_재고조회.py', 'pages/2_대여신청.py', 'pages/3_반납등록.py', 'pages/4_대여현황.py']:
            app = self.app(path)
            self.assertFalse(app.exception, path)
            self.assertTrue(app.error, path)
            self.assertIn('items.csv', app.error[0].value)

    def test_dev04_each_return_has_quantity_unique_id_and_korean_time(self):
        key = create_rental('A', 'User', 'Team', 4, self.today, self.today)
        register_return(key, 1)
        register_return(key, 2)
        events = get_return_history(key)
        self.assertEqual([e['반납 수량'] for e in events], [1, 2])
        self.assertEqual(len({e['반납번호'] for e in events}), 2)
        for event in events:
            self.assertEqual(datetime.fromisoformat(event['반납 일시']).utcoffset(), timedelta(hours=9))
        row = storage.read_rows('rentals.csv')[0]
        self.assertEqual(int(row['returned']), sum(e['반납 수량'] for e in events))
        with self.assertRaises(ValueError):
            register_return(key, 2)
        self.assertEqual(get_return_history(key), events)

    def test_dev04_failed_atomic_replace_keeps_quantity_and_events(self):
        key = create_rental('A', 'User', 'Team', 4, self.today, self.today)
        before = (storage.DATA_DIR / 'rentals.csv').read_bytes()
        with patch.object(storage.os, 'replace', side_effect=OSError('simulated write failure')):
            with self.assertRaises(OSError):
                register_return(key, 1)
        self.assertEqual((storage.DATA_DIR / 'rentals.csv').read_bytes(), before)
        self.assertEqual(get_return_history(key), [])
        self.assertFalse(list(storage.DATA_DIR.glob('*.tmp')))

    def test_dev04_legacy_csv_is_preserved_without_invented_timestamps(self):
        key = create_rental('A', 'User', 'Team', 4, self.today, self.today)
        rows = storage.read_rows('rentals.csv')
        row = rows[0]
        row['returned'] = '1'
        row.pop('return_events')
        legacy_fields = [f for f in storage.RENTAL_FIELDS if f != 'return_events']
        self.raw_csv('rentals.csv', legacy_fields, rows)
        self.assertEqual(get_return_history(key), [])
        register_return(key, 2)
        self.assertEqual(int(storage.read_rows('rentals.csv')[0]['returned']), 3)
        self.assertEqual([e['반납 수량'] for e in get_return_history(key)], [2])
        app = self.app('pages/4_대여현황.py')
        self.assertFalse(app.exception)
        self.assertTrue(any('도입 전에 반납한 1개' in e.value for e in app.caption))

    def test_dev04_invalid_events_do_not_silently_disappear(self):
        create_rental('A', 'User', 'Team', 4, self.today, self.today)
        row = storage.read_rows('rentals.csv')[0]
        row['return_events'] = json.dumps([{'return_id': 'bad', 'quantity': 2, 'returned_at': 'invalid'}])
        self.raw_csv('rentals.csv', storage.RENTAL_FIELDS, [row])
        with self.assertRaisesRegex(storage.DataError, 'return_events'):
            storage.read_rows('rentals.csv')

    @patch('services.chatbot.get_reply', return_value='모의 답변')
    def test_dev05_date_change_clears_history_and_announces_new_day(self, reply):
        histories = []

        def answer(history, question, day):
            histories.append(list(history))
            return '모의 답변'

        reply.side_effect = answer
        app = self.app('pages/5_AI챗봇.py')
        app.chat_input[0].set_value('Test 1개').run()
        self.assertEqual(len(app.session_state['rental_chat_messages']), 2)
        day = self.today + timedelta(days=1)
        app.date_input(key='chat_date').set_value(day).run()
        self.assertFalse(app.exception)
        self.assertEqual(app.session_state['rental_chat_messages'], [])
        self.assertEqual(len(app.chat_message), 0)
        self.assertTrue(any(day.isoformat() in e.value and '초기화' in e.value for e in app.info))
        app.chat_input[0].set_value('Test 1개').run()
        self.assertEqual(reply.call_args.args[2], day)
        self.assertEqual(histories, [[], []])
        app.button(key='clear_chat').click().run()
        self.assertEqual(app.session_state['rental_chat_messages'], [])
