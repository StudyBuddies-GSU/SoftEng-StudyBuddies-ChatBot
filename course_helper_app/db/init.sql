CREATE TABLE IF NOT EXISTS flashcards (
    id SERIAL PRIMARY KEY,
    chapter INTEGER,
    question TEXT,
    answer TEXT
);

CREATE TABLE IF NOT EXISTS fallbacks (
    id SERIAL PRIMARY KEY,
    fallback_message TEXT
);

-- Optional: insert one fallback message
INSERT INTO fallbacks (fallback_message) VALUES
('Sorry, I don’t know that yet. Try asking about deadlines or syllabus topics.')
ON CONFLICT DO NOTHING;

INSERT INTO flashcards (chapter, question, answer)
VALUES
(1, 'What is software engineering?', 'The application of engineering principles to software development.'),
(1, 'What is version control?', 'A system for tracking changes in code over time.'),
(2, 'What is a use case diagram?', 'A diagram showing interactions between users and a system.');
