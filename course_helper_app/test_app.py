import unittest
import psycopg2
from app import get_flashcards, get_fallback_message, get_chatbot_response, init_connection


class TestCourseHelperApp(unittest.TestCase):


    @classmethod
    def setUpClass(cls):
        """Connect to database once before all tests."""
        cls.conn = init_connection()


    @classmethod
    def tearDownClass(cls):
        cls.conn.close()


    def test_1_chatbot_prerequisites(self):
        result = get_chatbot_response("What are the prerequisites for CSC 4350?")
        self.assertIsNotNone(result, "No response found for CSC 4350.")
        text = result[0].lower()
        self.assertIn("csc 2720", text)
        self.assertIn("csc 3210", text)
        self.assertIn("csc 3320", text)


    def test_2_fallback_message_irrelevant_question(self):
        """Fallback message is returned for irrelevant questions."""
        fallback = get_fallback_message(self.conn)
        self.assertIn(
            "i’m sorry, i cannot help you with that",
            fallback.lower()
        )


if __name__ == "__main__":
    unittest.main()
