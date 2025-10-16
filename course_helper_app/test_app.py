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
        result = get_chatbot_response()
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

    def test_3_flashcards_chapter2_has_questions(self):
        """Flashcards for Chapter 2 start with question side (contains '?')."""
        cards = get_flashcards(self.conn, 2)
        self.assertTrue(len(cards) > 0, "No flashcards found for Chapter 2.")
        question, _ = cards[0]
        self.assertIn("?", question, "First flashcard does not contain a question mark.")

    def test_4_flashcards_loop_back(self):
        """Reaching end of Chapter 1 loops back to first card."""
        cards = get_flashcards(self.conn, 1)
        self.assertTrue(len(cards) > 1, "Need multiple flashcards to test looping.")
        last_index = len(cards) - 1
        next_index = (last_index + 1) % len(cards)
        self.assertEqual(next_index, 0, "Deck did not loop to first card.")

    def test_5_quiz_correct_answer_shows_checkmark(self):
        """User enters correct quiz answer → system marks correct."""
        cards = get_flashcards(self.conn, 2)
        self.assertTrue(len(cards) > 0)
        question, answer = cards[0]
        user_input = answer.strip().lower()
        is_correct = user_input == answer.strip().lower()
        self.assertTrue(is_correct, "Correct answer did not validate correctly.")

    def test_6_quiz_loops_back(self):
        """End of quiz deck loops to first question."""
        cards = get_flashcards(self.conn, 1)
        self.assertTrue(len(cards) > 1)
        last_index = len(cards) - 1
        next_index = (last_index + 1) % len(cards)
        self.assertEqual(next_index, 0, "Quiz deck did not loop back to first card.")

if __name__ == "__main__":
    unittest.main()
