-- CPL Analytics Database Schema
-- Canadian Premier League Open Dataset

-- Teams table
CREATE TABLE teams (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    city VARCHAR(100),
    stadium VARCHAR(100),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    founded_year INTEGER
);

-- Insert CPL teams with coordinates
INSERT INTO teams (name, city, stadium, latitude, longitude, founded_year) VALUES
('Forge FC', 'Hamilton', 'Tim Hortons Field', 43.2557, -79.8711, 2018),
('Cavalry FC', 'Calgary', 'ATCO Field', 50.9977, -114.0672, 2018),
('Pacific FC', 'Langford', 'Starlight Stadium', 48.4494, -123.4879, 2018),
('York United FC', 'Toronto', 'York Lions Stadium', 43.7735, -79.4980, 2018),
('Valour FC', 'Winnipeg', 'IG Field', 49.8076, -97.1443, 2018),
('HFX Wanderers FC', 'Halifax', 'Wanderers Grounds', 44.6488, -63.5752, 2018),
('FC Edmonton', 'Edmonton', 'Clarke Stadium', 53.5720, -113.4564, 2018),
('Vancouver FC', 'Langley', 'Willoughby Community Park', 49.0171, -122.6593, 2022),
('Atletico Ottawa', 'Ottawa', 'TD Place Stadium', 45.3989, -75.6831, 2020);

-- Matches table
CREATE TABLE matches (
    id SERIAL PRIMARY KEY,
    season INTEGER NOT NULL,
    match_week INTEGER,
    date DATE NOT NULL,
    kickoff_time TIME,
    home_team_id INTEGER REFERENCES teams(id),
    away_team_id INTEGER REFERENCES teams(id),
    home_goals INTEGER,
    away_goals INTEGER,
    ht_home_goals INTEGER,
    ht_away_goals INTEGER,
    venue VARCHAR(100),
    attendance INTEGER,
    referee VARCHAR(100),
    is_playoff BOOLEAN DEFAULT FALSE,
    weather_temp_c DECIMAL(4,1),
    weather_conditions VARCHAR(50),
    wind_speed_kmh DECIMAL(4,1)
);

-- Match statistics table
CREATE TABLE match_stats (
    match_id INTEGER REFERENCES matches(id),
    team_id INTEGER REFERENCES teams(id),
    shots INTEGER,
    shots_on_target INTEGER,
    possession_pct DECIMAL(4,1),
    corners INTEGER,
    fouls INTEGER,
    yellow_cards INTEGER,
    red_cards INTEGER,
    xg DECIMAL(4,2),
    PRIMARY KEY (match_id, team_id)
);

-- Players table
CREATE TABLE players (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    position VARCHAR(20),
    nationality VARCHAR(50),
    date_of_birth DATE
);

-- Lineups table
CREATE TABLE lineups (
    match_id INTEGER REFERENCES matches(id),
    team_id INTEGER REFERENCES teams(id),
    player_id INTEGER REFERENCES players(id),
    is_starter BOOLEAN DEFAULT TRUE,
    minutes_played INTEGER,
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    yellow_card BOOLEAN DEFAULT FALSE,
    red_card BOOLEAN DEFAULT FALSE,
    PRIMARY KEY (match_id, player_id)
);

-- Historical odds table
CREATE TABLE historical_odds (
    id SERIAL PRIMARY KEY,
    match_id INTEGER REFERENCES matches(id),
    bookmaker VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    home_odds DECIMAL(5,2),
    draw_odds DECIMAL(5,2),
    away_odds DECIMAL(5,2),
    over_25_odds DECIMAL(5,2),
    under_25_odds DECIMAL(5,2)
);

-- Contextual data table
CREATE TABLE contextual_data (
    match_id INTEGER PRIMARY KEY REFERENCES matches(id),
    away_team_travel_km INTEGER,
    home_team_days_rest INTEGER,
    away_team_days_rest INTEGER,
    home_team_form_last5 VARCHAR(5),
    away_team_form_last5 VARCHAR(5),
    playoff_implications TEXT
);

-- Indexes for performance
CREATE INDEX idx_matches_date ON matches(date);
CREATE INDEX idx_matches_season ON matches(season);
CREATE INDEX idx_matches_home_team ON matches(home_team_id);
CREATE INDEX idx_matches_away_team ON matches(away_team_id);
CREATE INDEX idx_historical_odds_match ON historical_odds(match_id);
CREATE INDEX idx_historical_odds_timestamp ON historical_odds(timestamp);
CREATE INDEX idx_lineups_player ON lineups(player_id);

-- View for match results with team names
CREATE VIEW match_results AS
SELECT
    m.id,
    m.season,
    m.match_week,
    m.date,
    m.kickoff_time,
    ht.name AS home_team,
    at.name AS away_team,
    m.home_goals,
    m.away_goals,
    m.ht_home_goals,
    m.ht_away_goals,
    m.venue,
    m.attendance,
    m.referee,
    m.is_playoff,
    m.weather_temp_c,
    m.weather_conditions,
    m.wind_speed_kmh
FROM matches m
JOIN teams ht ON m.home_team_id = ht.id
JOIN teams at ON m.away_team_id = at.id;
