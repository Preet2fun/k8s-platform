CREATE TABLE IF NOT EXISTS items (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS football_clubs (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL,
  country TEXT NOT NULL
);

INSERT INTO items (name) VALUES
  ('alpha'), ('beta'), ('gamma');

INSERT INTO football_clubs (name, country) VALUES
  ('Manchester United', 'England'),
  ('Real Madrid', 'Spain'),
  ('Barcelona', 'Spain');
