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
('I’m sorry, I cannot help you with that. That question falls out of scope with the course material and syllabus. I’m here to help with questions more relevant to your Software Engineering course.')
ON CONFLICT DO NOTHING;

INSERT INTO flashcards (chapter, question, answer)
VALUES
(1, 'What is software engineering?', 'The application of engineering principles to software development.'),
(1, 'What is version control?', 'A system for tracking changes in code over time.'),
(2, 'What is a use case diagram?', 'A diagram showing interactions between users and a system.');
