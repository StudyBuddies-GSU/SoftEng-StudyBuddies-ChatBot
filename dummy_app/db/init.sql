CREATE TABLE messages (
    id SERIAL PRIMARY KEY,
    content TEXT
);

INSERT INTO messages (content)
VALUES ('PostGRE works!');