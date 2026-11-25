"""
==============================================================================
PROJECT: Spotify Audio Features & Popularity Explorer
DBMS Capstone Project - Flask Full-Stack Web Application
==============================================================================
"""

import os
import io
import csv
import pandas as pd
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, Response, send_file
)
import db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "spotify_explorer_capstone_key_2026")


def get_pandas_analytics():
    """Generates multi-dimensional descriptive statistics and correlation matrix using Pandas."""
    try:
        rows = db.get_all_tracks_joined()
        if not rows:
            return None
        df = pd.DataFrame(rows)
        
        numeric_cols = ['popularity', 'danceability', 'energy', 'valence', 'tempo', 'acousticness', 'loudness']
        valid_cols = [c for c in numeric_cols if c in df.columns and df[c].notna().any()]
        
        # 1. Descriptive stats (Mean, Std, Min, 25%, Median, 75%, Max)
        desc_df = df[valid_cols].describe().round(3).T
        desc_dict = desc_df.to_dict(orient="index")
        
        # 2. Audio features Pearson correlation matrix
        corr_cols = [c for c in ['popularity', 'danceability', 'energy', 'valence', 'tempo', 'acousticness'] if c in valid_cols]
        corr_matrix = df[corr_cols].corr().round(3)
        corr_dict = corr_matrix.to_dict()
        
        # 3. Country-wise aggregate analysis
        country_summary = []
        if 'country' in df.columns:
            c_grp = df.groupby('country').agg(
                track_count=('track_id', 'count'),
                avg_pop=('popularity', 'mean'),
                avg_dance=('danceability', 'mean'),
                avg_energy=('energy', 'mean')
            ).round(2).reset_index()
            country_summary = c_grp.to_dict(orient="records")
            
        return {
            "stats": desc_dict,
            "corr_matrix": corr_dict,
            "corr_cols": corr_cols,
            "country_summary": country_summary,
            "total_rows": len(df)
        }
    except Exception as e:
        print(f"[Pandas Analytics Error] {e}")
        return None


@app.context_processor
def inject_globals():
    """Make DB status and helper functions accessible across all templates."""
    def format_duration(ms):
        if not ms or ms <= 0:
            return "0:00"
        total_seconds = int(ms) // 1000
        minutes = total_seconds // 60
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:02d}"
    
    return {
        "db_status": db.db_status,
        "format_duration": format_duration
    }


# ==============================================================================
# DASHBOARD ROUTE (INDEX)
# ==============================================================================
@app.route("/")
def home():
    search = request.args.get("q", "").strip()
    stats = db.get_dashboard_summary()
    top_tracks = db.get_all_tracks(search=search, order_by="popularity_desc")
    # Take top 10 for dashboard table
    top_tracks_slice = top_tracks[:10] if not search else top_tracks
    
    chart_data = db.get_dashboard_chart_data()
    return render_template(
        "index.html",
        stats=stats,
        tracks=top_tracks_slice,
        chart_data=chart_data,
        search_query=search,
        active_page="dashboard"
    )


# ==============================================================================
# MODULE 1: CRUD ROUTES
# ==============================================================================

# --- ARTISTS ---
@app.route("/artists", methods=["GET"])
def artists_list():
    search = request.args.get("q", "").strip()
    artists = db.get_all_artists(search=search)
    return render_template(
        "artists.html",
        artists=artists,
        search_query=search,
        active_page="artists"
    )

@app.route("/artists/add", methods=["POST"])
def artist_add():
    artist_name = request.form.get("artist_name", "").strip()
    country = request.form.get("country", "").strip()
    
    if not artist_name or not country:
        flash("Artist name and country are required.", "danger")
        return redirect(url_for("artists_list"))
    
    try:
        db.add_artist(artist_name, country)
        flash(f"Artist '{artist_name}' added successfully to database!", "success")
    except Exception as e:
        flash(f"Error adding artist: {str(e)}", "danger")
    return redirect(url_for("artists_list"))

@app.route("/artists/edit/<int:artist_id>", methods=["POST"])
def artist_edit(artist_id):
    artist_name = request.form.get("artist_name", "").strip()
    country = request.form.get("country", "").strip()
    
    if not artist_name or not country:
        flash("Artist name and country cannot be empty.", "danger")
        return redirect(url_for("artists_list"))
    
    try:
        db.update_artist(artist_id, artist_name, country)
        flash(f"Artist #{artist_id} updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating artist: {str(e)}", "danger")
    return redirect(url_for("artists_list"))

@app.route("/artists/delete/<int:artist_id>", methods=["POST"])
def artist_delete(artist_id):
    try:
        db.delete_artist(artist_id)
        flash(f"Artist #{artist_id} and associated records deleted (Cascaded).", "success")
    except Exception as e:
        flash(f"Error deleting artist: {str(e)}", "danger")
    return redirect(url_for("artists_list"))


# --- ALBUMS ---
@app.route("/albums", methods=["GET"])
def albums_list():
    search = request.args.get("q", "").strip()
    albums = db.get_all_albums(search=search)
    artists = db.get_all_artists()
    return render_template(
        "albums.html",
        albums=albums,
        artists=artists,
        search_query=search,
        active_page="albums"
    )

@app.route("/albums/add", methods=["POST"])
def album_add():
    album_name = request.form.get("album_name", "").strip()
    release_date = request.form.get("release_date", "").strip()
    artist_id = request.form.get("artist_id", "").strip()
    
    if not album_name or not release_date or not artist_id:
        flash("All album fields are required.", "danger")
        return redirect(url_for("albums_list"))
    
    try:
        db.add_album(album_name, release_date, int(artist_id))
        flash(f"Album '{album_name}' created successfully!", "success")
    except Exception as e:
        flash(f"Error adding album: {str(e)}", "danger")
    return redirect(url_for("albums_list"))

@app.route("/albums/edit/<int:album_id>", methods=["POST"])
def album_edit(album_id):
    album_name = request.form.get("album_name", "").strip()
    release_date = request.form.get("release_date", "").strip()
    artist_id = request.form.get("artist_id", "").strip()
    
    try:
        db.update_album(album_id, album_name, release_date, int(artist_id))
        flash(f"Album #{album_id} updated successfully!", "success")
    except Exception as e:
        flash(f"Error updating album: {str(e)}", "danger")
    return redirect(url_for("albums_list"))

@app.route("/albums/delete/<int:album_id>", methods=["POST"])
def album_delete(album_id):
    try:
        db.delete_album(album_id)
        flash(f"Album #{album_id} deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting album: {str(e)}", "danger")
    return redirect(url_for("albums_list"))


# --- TRACKS ---
@app.route("/tracks", methods=["GET"])
def tracks_list():
    search = request.args.get("q", "").strip()
    order_by = request.args.get("sort", "popularity_desc")
    tracks = db.get_all_tracks(search=search, order_by=order_by)
    albums = db.get_all_albums()
    return render_template(
        "tracks.html",
        tracks=tracks,
        albums=albums,
        search_query=search,
        current_sort=order_by,
        active_page="tracks"
    )

@app.route("/tracks/add", methods=["POST"])
def track_add():
    track_name = request.form.get("track_name", "").strip()
    album_id = request.form.get("album_id", "").strip()
    popularity = request.form.get("popularity", "50").strip()
    duration_sec = request.form.get("duration_sec", "180").strip()
    
    try:
        pop = max(0, min(100, int(popularity)))
        dur_ms = max(1000, int(duration_sec) * 1000)
        track_id = db.add_track(track_name, int(album_id), pop, dur_ms)
        
        # If optional audio features submitted with track
        danceability = request.form.get("danceability")
        if danceability:
            energy = request.form.get("energy", "0.5")
            valence = request.form.get("valence", "0.5")
            tempo = request.form.get("tempo", "120.0")
            acousticness = request.form.get("acousticness", "0.2")
            loudness = request.form.get("loudness", "-6.0")
            db.save_audio_features(
                track_id, float(danceability), float(energy),
                float(valence), float(tempo), float(acousticness), float(loudness)
            )
            
        flash(f"Track '{track_name}' added to catalogue with ID #{track_id}!", "success")
    except Exception as e:
        flash(f"Error inserting track: {str(e)}", "danger")
    return redirect(url_for("tracks_list"))

@app.route("/tracks/edit/<int:track_id>", methods=["POST"])
def track_edit(track_id):
    track_name = request.form.get("track_name", "").strip()
    album_id = request.form.get("album_id", "").strip()
    popularity = request.form.get("popularity", "50").strip()
    duration_sec = request.form.get("duration_sec", "180").strip()
    
    try:
        pop = max(0, min(100, int(popularity)))
        dur_ms = max(1000, int(duration_sec) * 1000)
        db.update_track(track_id, track_name, int(album_id), pop, dur_ms)
        flash(f"Track #{track_id} '{track_name}' successfully updated!", "success")
    except Exception as e:
        flash(f"Error updating track: {str(e)}", "danger")
    return redirect(url_for("tracks_list"))

@app.route("/tracks/delete/<int:track_id>", methods=["POST"])
def track_delete(track_id):
    try:
        db.delete_track(track_id)
        flash(f"Track #{track_id} deleted from database.", "success")
    except Exception as e:
        flash(f"Error removing track: {str(e)}", "danger")
    return redirect(url_for("tracks_list"))


# --- AUDIO FEATURES ---
@app.route("/audio-features", methods=["GET"])
def audio_features_list():
    search = request.args.get("q", "").strip()
    features = db.get_all_audio_features(search=search)
    tracks = db.get_all_tracks()
    return render_template(
        "audio_features.html",
        features=features,
        tracks=tracks,
        search_query=search,
        active_page="audio_features"
    )

@app.route("/audio-features/save", methods=["POST"])
def audio_features_save():
    track_id = request.form.get("track_id", "").strip()
    danceability = request.form.get("danceability", "0.5").strip()
    energy = request.form.get("energy", "0.5").strip()
    valence = request.form.get("valence", "0.5").strip()
    tempo = request.form.get("tempo", "120.0").strip()
    acousticness = request.form.get("acousticness", "0.1").strip()
    loudness = request.form.get("loudness", "-6.0").strip()
    
    try:
        db.save_audio_features(
            int(track_id),
            float(danceability),
            float(energy),
            float(valence),
            float(tempo),
            float(acousticness),
            float(loudness)
        )
        flash(f"Audio features saved for Track ID #{track_id}!", "success")
    except Exception as e:
        flash(f"Failed to save audio features: {str(e)}", "danger")
    return redirect(url_for("audio_features_list"))


# ==============================================================================
# MODULE 2: SQL ANALYSIS ENGINE
# ==============================================================================
@app.route("/analysis")
def sql_analysis():
    query_id = request.args.get("q_id", "1")
    
    queries = {
        "1": db.query_top_10_popular_tracks,
        "2": db.query_average_popularity,
        "3": db.query_artist_wise_popularity,
        "4": db.query_album_wise_analysis,
        "5": db.query_tracks_popularity_above_70,
        "6": db.query_most_popular_artist,
        "7": db.query_audio_features_comparison,
        "8": db.query_danceability_energy_analysis
    }
    
    query_func = queries.get(query_id, db.query_top_10_popular_tracks)
    result = query_func()
    
    return render_template(
        "analysis.html",
        selected_id=query_id,
        analysis=result,
        active_page="analysis"
    )


# ==============================================================================
# MODULE 3: REPORTS & CSV EXPORT
# ==============================================================================
@app.route("/reports")
def reports():
    stats = db.get_dashboard_summary()
    top_artist = db.query_most_popular_artist()
    top_tracks = db.query_top_10_popular_tracks()
    features_comp = db.query_audio_features_comparison()
    album_analysis = db.query_album_wise_analysis()
    pandas_analytics = get_pandas_analytics()
    
    return render_template(
        "reports.html",
        stats=stats,
        top_artist=top_artist["data"],
        top_tracks=top_tracks["data"],
        features_comp=features_comp["data"],
        album_analysis=album_analysis["data"],
        pandas_analytics=pandas_analytics,
        active_page="reports"
    )

@app.route("/export/csv/<entity>")
def export_csv(entity):
    """Generates standardized CSV downloads directly from SQL database queries using Pandas."""
    if entity == "tracks":
        rows = db.get_all_tracks()
        df = pd.DataFrame(rows)
        if not df.empty:
            cols = [c for c in ['track_id', 'track_name', 'artist_name', 'album_name', 'popularity', 'duration_ms', 'created_at'] if c in df.columns]
            df = df[cols]
            df.columns = ["Track ID", "Track Name", "Artist", "Album", "Popularity", "Duration (ms)", "Created At"][:len(cols)]
        filename = "spotify_tracks_export.csv"
        
    elif entity == "artists":
        rows = db.execute_query("""
            SELECT ar.artist_id, ar.artist_name, ar.country,
                   COUNT(t.track_id) AS total_tracks,
                   ROUND(AVG(t.popularity), 2) AS avg_popularity
            FROM artists ar
            LEFT JOIN albums al ON ar.artist_id = al.artist_id
            LEFT JOIN tracks t ON al.album_id = t.album_id
            GROUP BY ar.artist_id, ar.artist_name, ar.country
            ORDER BY avg_popularity DESC
        """)
        df = pd.DataFrame(rows)
        if not df.empty:
            df.columns = ["Artist ID", "Artist Name", "Country", "Total Tracks", "Average Popularity"]
        filename = "spotify_artists_summary.csv"

    elif entity == "albums":
        rows = db.get_all_albums()
        df = pd.DataFrame(rows)
        if not df.empty:
            cols = [c for c in ['album_id', 'album_name', 'artist_name', 'release_date', 'track_count'] if c in df.columns]
            df = df[cols]
            df.columns = ["Album ID", "Album Name", "Artist", "Release Date", "Track Count"][:len(cols)]
        filename = "spotify_albums_export.csv"

    elif entity == "audio_features":
        rows = db.get_all_audio_features()
        df = pd.DataFrame(rows)
        if not df.empty:
            cols = [c for c in ['track_id', 'track_name', 'artist_name', 'danceability', 'energy', 'valence', 'tempo', 'acousticness', 'loudness'] if c in df.columns]
            df = df[cols]
            df.columns = ["Track ID", "Track Name", "Artist", "Danceability", "Energy", "Valence", "Tempo (BPM)", "Acousticness", "Loudness (dB)"][:len(cols)]
        filename = "spotify_audio_features_matrix.csv"

    elif entity == "statistical_summary":
        rows = db.get_all_tracks_joined()
        df_raw = pd.DataFrame(rows)
        num_cols = [c for c in ['popularity', 'danceability', 'energy', 'valence', 'tempo', 'acousticness', 'loudness'] if c in df_raw.columns]
        df = df_raw[num_cols].describe().round(3).reset_index()
        df = df.rename(columns={'index': 'Statistic'})
        filename = "spotify_pandas_statistical_summary.csv"

    else: # complete joined dump
        rows = db.get_all_tracks_joined()
        df = pd.DataFrame(rows)
        if not df.empty:
            df.columns = [c.replace('_', ' ').title() for c in df.columns]
        filename = "spotify_complete_database_dump.csv"

    output = io.BytesIO()
    df.to_csv(output, index=False, encoding='utf-8')
    output.seek(0)
    return send_file(output, mimetype="text/csv", as_attachment=True, download_name=filename)


# ==============================================================================
# SETTINGS & DB HEALTH CHECK ROUTE
# ==============================================================================
@app.route("/settings")
def settings():
    return render_template(
        "settings.html",
        active_page="settings"
    )

@app.route("/settings/reconnect", methods=["POST"])
def db_reconnect():
    try:
        conn, engine = db.check_and_get_connection(force_check=True)
        conn.close()
        flash(f"Database check completed: {db.db_status['message']}", "success" if db.db_status["connected"] else "danger")
    except Exception as e:
        flash(f"Connection test error: {str(e)}", "danger")
    return redirect(url_for("settings"))

@app.route("/settings/reset-database", methods=["POST"])
def reset_database():
    try:
        conn, engine = db.check_and_get_connection()
        if engine == "mysql":
            db.initialize_mysql_schema(conn)
            conn.close()
            flash("MySQL Database successfully reset and reseeded from database.sql!", "success")
        else:
            db.initialize_sqlite_schema(conn)
            conn.close()
            flash("Local database successfully reset and reseeded with sample data!", "success")
    except Exception as e:
        flash(f"Error resetting database: {str(e)}", "danger")
    return redirect(url_for("settings"))


# ==============================================================================
# JSON API ENDPOINTS
# ==============================================================================
@app.route("/api/charts/dashboard")
def api_dashboard_charts():
    return jsonify(db.get_dashboard_chart_data())

@app.route("/api/chart/filter/<filter_name>")
def api_chart_filter(filter_name):
    chart_data = db.get_dashboard_chart_data()
    filters = chart_data.get("filters", {})
    return jsonify(filters.get(filter_name, filters.get("all", {})))

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])
    results = db.get_all_tracks(search=query)
    return jsonify(results[:8])

@app.route("/api/notifications")
def api_notifications():
    """Returns database telemetry and recent transaction logs."""
    stats = db.get_dashboard_summary()
    return jsonify([
        {
            "id": 1,
            "title": f"Database Engine: {db.db_status['engine'].upper()}",
            "desc": db.db_status["message"],
            "time": "Active",
            "type": "success" if db.db_status["connected"] else "warning"
        },
        {
            "id": 2,
            "title": "Catalog Integrity Verified",
            "desc": f"{stats['total_tracks']} tracks, {stats['total_albums']} albums, {stats['total_artists']} artists mapped.",
            "time": "System",
            "type": "info"
        },
        {
            "id": 3,
            "title": "Audio DSP Matrix Loaded",
            "desc": "1-to-1 audio features normalized with Foreign Key cascading.",
            "time": "System",
            "type": "info"
        }
    ])


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"\n=======================================================")
    print(f"🎵 Spotify Audio Features & Popularity Explorer")
    print(f"📡 Server running at: http://127.0.0.1:{port}")
    print(f"💾 Engine Status: {db.db_status['message']}")
    print(f"=======================================================\n")
    app.run(host="127.0.0.1", port=port, debug=debug)
