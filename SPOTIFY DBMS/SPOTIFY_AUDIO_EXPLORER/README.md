# Spotify Audio Features & Popularity Explorer

A complete Flask and MySQL DBMS capstone application for managing synthetic music data and analyzing popularity and audio features.

> **Data notice:** every record is synthetic sample data created for this project. It is not real Spotify data.

## Features

- Dashboard with database-derived statistics and Chart.js visualizations
- CRUD screens for artists, albums, tracks and audio features
- Safe deletes using MySQL foreign keys
- SQL JOIN, WHERE, GROUP BY, ORDER BY, AVG, COUNT, MAX and MIN analysis
- Search, sorting, filtering, deletion confirmation and CSV exports
- Environment-based database credentials and parameterized SQL

## Project structure

```text
SPOTIFY_AUDIO_EXPLORER/
├── app.py
├── database.sql
├── requirements.txt
├── README.md
├── .env.example
├── templates/
└── static/
```

## 1. Install prerequisites on Windows

1. Install Python 3.10 or newer.
2. Install MySQL Server and MySQL Workbench.
3. Open MySQL Workbench and start the MySQL server.

## 2. Create the database

Open MySQL Workbench and run the complete contents of `database.sql`, or open a terminal in the project folder and run:

```powershell
mysql -u root -p < database.sql
```

Enter the MySQL root password when prompted.

The script creates `spotify_explorer`, four normalized relational tables, constraints and 22 synthetic tracks with matching audio features.

## 3. Configure VS Code

Open the project folder:

```powershell
code "C:\Users\mrkha\Downloads\SPOTIFY DBMS\SPOTIFY_AUDIO_EXPLORER"
```

Create a virtual environment and install dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Create `.env` by copying `.env.example`:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and set the correct MySQL password:

```text
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=spotify_explorer
SECRET_KEY=choose-a-random-secret
```

## 4. Run the application

```powershell
python app.py
```

Open `http://127.0.0.1:5000` in a browser.

## 5. Database validation

In MySQL Workbench, test the connection and schema:

```sql
USE spotify_explorer;
SHOW TABLES;
SELECT COUNT(*) AS track_count FROM TRACKS;

SELECT ar.artist_name, ROUND(AVG(t.popularity),1) AS average_popularity
FROM ARTISTS ar
JOIN ALBUMS al ON al.artist_id = ar.artist_id
JOIN TRACKS t ON t.album_id = al.album_id
GROUP BY ar.artist_id, ar.artist_name
ORDER BY average_popularity DESC;
```

## Database design

- `ARTISTS.artist_id` is a primary key.
- `ALBUMS.artist_id` references `ARTISTS` with `ON DELETE RESTRICT`.
- `TRACKS.album_id` references `ALBUMS` with `ON DELETE RESTRICT`.
- `AUDIO_FEATURES.track_id` is both the primary key and a foreign key referencing `TRACKS`; deleting a track removes its feature row with `ON DELETE CASCADE`.
- Popularity and feature values have database constraints.

## Troubleshooting

- **Access denied:** verify `MYSQL_USER` and `MYSQL_PASSWORD` in `.env`.
- **Unknown database:** run `database.sql`.
- **Module not found:** activate `.venv` and run `pip install -r requirements.txt`.
- **Port in use:** set `PORT=5001` in `.env` and run again.
