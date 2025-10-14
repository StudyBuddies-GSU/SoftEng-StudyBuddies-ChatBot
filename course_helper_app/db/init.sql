CREATE TABLE flashcards (
    flashcard_id SERIAL PRIMARY KEY,
    question TEXT,
    answer TEXT
);

CREATE TABLE fallbacks (
    fallback_id SERIAL PRIMARY KEY,
    query_text TEXT,
    fallback_message TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    reason TEXT
);

INSERT INTO flashcards (question, answer)
VALUES ('', '');

INSERT INTO fallbacks (query_text, fallback_message, reason)
VALUES (
    '',
    'I’m sorry, I cannot help you with that. That question falls out of scope with the course material and syllabus. I’m here to help with questions more relevant to your Software Engineering course.',
    'Out of scope'
);