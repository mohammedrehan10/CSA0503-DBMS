-- ==============================================================================
-- PROJECT: Spotify Audio Features & Popularity Explorer
-- DBMS CAPSTONE PROJECT - RELATIONAL DATABASE SCHEMA & DATA
-- Database System: MySQL 8.0+
-- ==============================================================================
-- DISCLAIMER: All data contained herein is synthetic / compiled for academic
-- demonstration, testing, and educational purposes. Not an official Spotify API dump.
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS spotify_explorer;
USE spotify_explorer;

-- ------------------------------------------------------------------------------
-- 1. DROP EXISTING TABLES (Reverse Dependency Order for clean reset)
-- ------------------------------------------------------------------------------
DROP TABLE IF EXISTS audio_features;
DROP TABLE IF EXISTS tracks;
DROP TABLE IF EXISTS albums;
DROP TABLE IF EXISTS artists;

-- ------------------------------------------------------------------------------
-- 2. CREATE TABLE: ARTISTS
-- Primary Entity storing musical artists and their origin country
-- ------------------------------------------------------------------------------
CREATE TABLE artists (
    artist_id INT AUTO_INCREMENT PRIMARY KEY,
    artist_name VARCHAR(100) NOT NULL UNIQUE,
    country VARCHAR(60) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 3. CREATE TABLE: ALBUMS
-- Weak/Dependent Entity referencing Artists via 1-to-Many relationship
-- ------------------------------------------------------------------------------
CREATE TABLE albums (
    album_id INT AUTO_INCREMENT PRIMARY KEY,
    album_name VARCHAR(150) NOT NULL,
    release_date DATE NOT NULL,
    artist_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_albums_artist
        FOREIGN KEY (artist_id) REFERENCES artists(artist_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 4. CREATE TABLE: TRACKS
-- Central Entity storing individual songs, popularity score (0-100), and duration
-- ------------------------------------------------------------------------------
CREATE TABLE tracks (
    track_id INT AUTO_INCREMENT PRIMARY KEY,
    track_name VARCHAR(150) NOT NULL,
    album_id INT NOT NULL,
    popularity INT NOT NULL CHECK (popularity >= 0 AND popularity <= 100),
    duration_ms INT NOT NULL CHECK (duration_ms > 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_tracks_album
        FOREIGN KEY (album_id) REFERENCES albums(album_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 5. CREATE TABLE: AUDIO_FEATURES
-- 1-to-1 Specialized Entity capturing audio DSP metrics per track
-- ------------------------------------------------------------------------------
CREATE TABLE audio_features (
    track_id INT PRIMARY KEY,
    danceability DECIMAL(4,3) NOT NULL CHECK (danceability >= 0.000 AND danceability <= 1.000),
    energy DECIMAL(4,3) NOT NULL CHECK (energy >= 0.000 AND energy <= 1.000),
    valence DECIMAL(4,3) NOT NULL CHECK (valence >= 0.000 AND valence <= 1.000),
    tempo DECIMAL(6,2) NOT NULL CHECK (tempo > 0.00),
    acousticness DECIMAL(4,3) NOT NULL CHECK (acousticness >= 0.000 AND acousticness <= 1.000),
    loudness DECIMAL(5,2) NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_features_track
        FOREIGN KEY (track_id) REFERENCES tracks(track_id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 6. POPULATE SAMPLE DATA
-- ------------------------------------------------------------------------------

-- ARTISTS (8 Distinct Artists across countries)
INSERT INTO artists (artist_id, artist_name, country) VALUES
(1, 'The Weeknd', 'Canada'),
(2, 'Taylor Swift', 'USA'),
(3, 'Drake', 'Canada'),
(4, 'Ed Sheeran', 'UK'),
(5, 'Ariana Grande', 'USA'),
(6, 'Coldplay', 'UK'),
(7, 'Dua Lipa', 'UK'),
(8, 'Billie Eilish', 'USA');

-- ALBUMS (12 Distinct Albums)
INSERT INTO albums (album_id, album_name, release_date, artist_id) VALUES
(1, 'After Hours', '2020-03-20', 1),
(2, 'Starboy', '2016-11-25', 1),
(3, '1989', '2014-10-27', 2),
(4, 'Midnights', '2022-10-21', 2),
(5, 'Lover', '2019-08-23', 2),
(6, 'Scorpion', '2018-06-29', 3),
(7, 'Views', '2016-04-29', 3),
(8, '÷ (Divide)', '2017-03-03', 4),
(9, 'Positions', '2020-10-30', 5),
(10, 'Music of the Spheres', '2021-10-15', 6),
(11, 'Future Nostalgia', '2020-03-27', 7),
(12, 'When We All Fall Asleep, Where Do We Go?', '2019-03-29', 8);

-- TRACKS (26 Sample Tracks with varying popularity & durations)
INSERT INTO tracks (track_id, track_name, album_id, popularity, duration_ms) VALUES
(1, 'Blinding Lights', 1, 100, 200040),
(2, 'Save Your Tears', 1, 92, 215626),
(3, 'Starboy', 2, 94, 230453),
(4, 'Die For You', 2, 88, 260253),
(5, 'Blank Space', 3, 95, 231826),
(6, 'Shake It Off', 3, 90, 219200),
(7, 'Anti-Hero', 4, 94, 200690),
(8, 'Lavender Haze', 4, 86, 202395),
(9, 'Cruel Summer', 5, 96, 178426),
(10, 'Lover', 5, 87, 221306),
(11, 'God''s Plan', 6, 95, 198973),
(12, 'In My Feelings', 6, 89, 217925),
(13, 'One Dance', 7, 91, 173986),
(14, 'Hotline Bling', 7, 84, 267066),
(15, 'Shape of You', 8, 98, 233712),
(16, 'Perfect', 8, 92, 263400),
(17, 'Castle on the Hill', 8, 85, 261153),
(18, 'Positions', 9, 93, 172324),
(19, '34+35', 9, 87, 173710),
(20, 'My Universe', 10, 89, 226342),
(21, 'feelslikeimfalling', 10, 88, 220000),
(22, 'Levitating', 11, 93, 203807),
(23, 'Don''t Start Now', 11, 91, 183290),
(24, 'bad guy', 12, 92, 194087),
(25, 'bury a friend', 12, 84, 193246),
(26, 'Someone Like You', 8, 89, 285000);

-- AUDIO_FEATURES (26 corresponding DSP records)
INSERT INTO audio_features (track_id, danceability, energy, valence, tempo, acousticness, loudness) VALUES
(1, 0.514, 0.730, 0.334, 171.00, 0.001, -5.93),
(2, 0.680, 0.826, 0.644, 118.05, 0.021, -5.48),
(3, 0.679, 0.587, 0.486, 186.00, 0.141, -7.01),
(4, 0.586, 0.525, 0.508, 133.62, 0.111, -7.16),
(5, 0.760, 0.703, 0.570, 95.99, 0.103, -5.41),
(6, 0.647, 0.785, 0.942, 160.01, 0.064, -5.41),
(7, 0.637, 0.643, 0.533, 97.00, 0.204, -6.57),
(8, 0.733, 0.436, 0.097, 96.98, 0.258, -10.48),
(9, 0.552, 0.702, 0.564, 169.99, 0.117, -5.70),
(10, 0.359, 0.543, 0.453, 68.53, 0.492, -7.58),
(11, 0.754, 0.449, 0.357, 77.17, 0.033, -9.21),
(21, 0.620, 0.710, 0.590, 122.00, 0.080, -6.20),
(12, 0.835, 0.626, 0.350, 91.03, 0.059, -5.83),
(13, 0.792, 0.625, 0.551, 103.96, 0.007, -5.60),
(14, 0.900, 0.623, 0.558, 134.98, 0.002, -8.19),
(15, 0.825, 0.652, 0.931, 95.97, 0.581, -3.18),
(16, 0.599, 0.448, 0.168, 95.05, 0.163, -6.31),
(17, 0.461, 0.834, 0.471, 135.00, 0.023, -4.86),
(18, 0.737, 0.802, 0.682, 144.01, 0.468, -4.77),
(19, 0.798, 0.678, 0.737, 110.02, 0.237, -4.97),
(20, 0.588, 0.701, 0.470, 105.01, 0.008, -6.39),
(22, 0.702, 0.825, 0.915, 103.01, 0.008, -3.78),
(23, 0.794, 0.793, 0.679, 123.94, 0.012, -4.52),
(24, 0.701, 0.425, 0.562, 135.12, 0.328, -10.96),
(25, 0.905, 0.389, 0.196, 120.04, 0.040, -14.50),
(26, 0.559, 0.430, 0.285, 135.10, 0.692, -7.05);

-- ------------------------------------------------------------------------------
-- 7. ESSENTIAL CAPSTONE SQL QUERIES (MODULE 2 REFERENCE IMPLEMENTATION)
-- ------------------------------------------------------------------------------

-- Query 1: Top 10 popular tracks with artist and album
-- SELECT t.track_id, t.track_name, ar.artist_name, al.album_name, t.popularity, t.duration_ms
-- FROM tracks t
-- JOIN albums al ON t.album_id = al.album_id
-- JOIN artists ar ON al.artist_id = ar.artist_id
-- ORDER BY t.popularity DESC
-- LIMIT 10;

-- Query 2: Aggregate track popularity statistics (Average, Min, Max, Count)
-- SELECT COUNT(track_id) AS total_tracks, AVG(popularity) AS avg_popularity,
--        MIN(popularity) AS min_popularity, MAX(popularity) AS max_popularity
-- FROM tracks;

-- Query 3: Artist-wise average popularity with track count
-- SELECT ar.artist_id, ar.artist_name, ar.country,
--        COUNT(t.track_id) AS total_tracks,
--        ROUND(AVG(t.popularity), 2) AS avg_popularity
-- FROM artists ar
-- JOIN albums al ON ar.artist_id = al.artist_id
-- JOIN tracks t ON al.album_id = t.album_id
-- GROUP BY ar.artist_id, ar.artist_name, ar.country
-- ORDER BY avg_popularity DESC;

-- Query 4: Album-wise track analysis (track count, avg popularity, total duration)
-- SELECT al.album_id, al.album_name, ar.artist_name, al.release_date,
--        COUNT(t.track_id) AS track_count,
--        ROUND(AVG(t.popularity), 2) AS avg_popularity,
--        ROUND(AVG(t.duration_ms)/1000, 1) AS avg_duration_sec
-- FROM albums al
-- JOIN artists ar ON al.artist_id = ar.artist_id
-- LEFT JOIN tracks t ON al.album_id = t.album_id
-- GROUP BY al.album_id, al.album_name, ar.artist_name, al.release_date
-- ORDER BY track_count DESC, avg_popularity DESC;

-- Query 5: High popularity tracks (Popularity >= 70)
-- SELECT t.track_name, ar.artist_name, al.album_name, t.popularity
-- FROM tracks t
-- JOIN albums al ON t.album_id = al.album_id
-- JOIN artists ar ON al.artist_id = ar.artist_id
-- WHERE t.popularity >= 70
-- ORDER BY t.popularity DESC;

-- Query 6: Most popular artist overall
-- SELECT ar.artist_name, ar.country,
--        COUNT(t.track_id) AS track_count,
--        ROUND(AVG(t.popularity), 2) AS avg_popularity
-- FROM artists ar
-- JOIN albums al ON ar.artist_id = al.artist_id
-- JOIN tracks t ON al.album_id = t.album_id
-- GROUP BY ar.artist_id, ar.artist_name, ar.country
-- ORDER BY avg_popularity DESC
-- LIMIT 1;

-- Query 7: Audio features comparison across top artists
-- SELECT ar.artist_name,
--        ROUND(AVG(af.danceability), 3) AS avg_danceability,
--        ROUND(AVG(af.energy), 3) AS avg_energy,
--        ROUND(AVG(af.valence), 3) AS avg_valence,
--        ROUND(AVG(af.acousticness), 3) AS avg_acousticness,
--        ROUND(AVG(af.tempo), 1) AS avg_tempo
-- FROM artists ar
-- JOIN albums al ON ar.artist_id = al.artist_id
-- JOIN tracks t ON al.album_id = t.album_id
-- JOIN audio_features af ON t.track_id = af.track_id
-- GROUP BY ar.artist_id, ar.artist_name
-- ORDER BY avg_energy DESC;

-- Query 8: Danceability vs Energy Party Index
-- SELECT t.track_name, ar.artist_name,
--        af.danceability, af.energy,
--        ROUND((af.danceability + af.energy) / 2, 3) AS party_index,
--        af.tempo
-- FROM tracks t
-- JOIN albums al ON t.album_id = al.album_id
-- JOIN artists ar ON al.artist_id = ar.artist_id
-- JOIN audio_features af ON t.track_id = af.track_id
-- ORDER BY party_index DESC;
