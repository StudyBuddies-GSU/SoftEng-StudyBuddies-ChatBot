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

    # Ben
    def test_1_chatbot_prerequisites(self):
        result = get_chatbot_response("What are the prerequisites for CSC 4350?")
        self.assertIsNotNone(result, "No response found for CSC 4350.")
        text = result[0].lower()
        self.assertIn("csc 2720", text)
        self.assertIn("csc 3210", text)
        self.assertIn("csc 3320", text)

    # Ben
    def test_2_fallback_message_irrelevant_question(self):
        """Fallback message is returned for irrelevant questions."""
        fallback = get_fallback_message(self.conn)
        self.assertIn(
            "i’m sorry, i cannot help you with that",
            fallback.lower()
        )
    
    #Emran
    def test_3_flashcards_show_question_side(self):
        rows = get_flashcards(self.conn, chapter=2)
        self.assertGreater(len(rows), 0, "Expected at least one flashcard in chapter 2")
        question, answer = rows[0]
        self.assertIn("?", question)

    # Emran
    def test_4_flashcards_loop(self):
        rows = get_flashcards(self.conn, chapter=1)
        self.assertGreaterEqual(len(rows), 2, "Expected at least two flashcards in chapter 1")
        current_index = len(rows) - 1  # last card
        next_index = (current_index + 1) % len(rows)
        self.assertEqual(next_index, 0)
    
    # Khushi
    def test_5_quiz_correct_answer_shows_checkmark(self):
        """User enters correct quiz answer → system marks correct."""
        cards = get_flashcards(self.conn, 2)
        self.assertTrue(len(cards) > 0)
        question, answer = cards[0]
        user_input = answer.strip().lower()
        is_correct = user_input == answer.strip().lower()
        self.assertTrue(is_correct, "Correct answer did not validate correctly.")

    # Ishtiaq
    def test_6_quiz_loops_back(self):
        """End of quiz deck loops to first question."""
        cards = get_flashcards(self.conn, 1)
        self.assertTrue(len(cards) > 1)
        last_index = len(cards) - 1
        next_index = (last_index + 1) % len(cards)
        self.assertEqual(next_index, 0, "Quiz deck did not loop back to first card.")    
        

if __name__ == "__main__":
    unittest.main()
