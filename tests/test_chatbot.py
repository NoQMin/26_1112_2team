import unittest
from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch
import test_rental
from services.chatbot import ChatError, find_date, get_inventory_facts, get_reply
from services.rental import create_rental
from services.return_service import register_return

class ChatbotTests(unittest.TestCase):
    setUp = test_rental.RentalTests.setUp
    def test_inventory_tracks_rental_and_return(self):
        key = create_rental("A", "PrivateName", "PrivateTeam", 4, self.today, self.today)
        facts = get_inventory_facts("Test 7개", self.today)
        self.assertIn("대여 가능 6개", facts)
        self.assertIn("불가능", facts)
        self.assertNotIn("PrivateName", facts)
        self.assertNotIn("PrivateTeam", facts)
        register_return(key, 2)
        self.assertIn("대여 가능 8개", get_inventory_facts("Test", self.today))

    def test_dates_and_validation(self):
        self.assertEqual(find_date("내일"), date.today()+timedelta(days=1))
        self.assertEqual(find_date("2027년 11월 20일"), date(2027,11,20))
        with self.assertRaises(ChatError): find_date("2027-02-30")
        with self.assertRaises(ChatError): get_inventory_facts("Test", self.today-timedelta(days=1))
        with self.assertRaises(ChatError): get_reply([], " ")

    @patch("services.chatbot.Client")
    def test_reply_and_connection_failure(self, client):
        client.return_value.chat.return_value = SimpleNamespace(done_reason="stop", message=SimpleNamespace(content="안내 답변"))
        answer = get_reply([], "Test 2개", self.today)
        self.assertIn("시스템 재고 확인 결과", answer)
        self.assertIn("대여 가능 10개", answer)
        client.return_value.chat.side_effect = ConnectionError("offline")
        with self.assertRaises(ChatError): get_reply([], "Test", self.today)
