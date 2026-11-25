"""
Comprehensive Test Suite for Spotify Audio Features & Popularity Explorer
Tests all backend routes, CRUD operations, SQL queries, CSV exports,
Pandas data analytics, and JSON APIs.
"""

import unittest
from app import app, get_pandas_analytics
import db

class TestSpotifyExplorer(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.app.config["TESTING"] = True

    def test_01_dashboard(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Spotify Audio Explorer", response.data)
        self.assertIn(b"Total Tracks", response.data)
        self.assertIn(b"Blinding Lights", response.data)

    def test_02_artists_list(self):
        response = self.client.get("/artists")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Weeknd", response.data)
        self.assertIn(b"Taylor Swift", response.data)

    def test_03_albums_list(self):
        response = self.client.get("/albums")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"After Hours", response.data)
        self.assertIn(b"1989", response.data)

    def test_04_tracks_list(self):
        response = self.client.get("/tracks")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Save Your Tears", response.data)

    def test_05_audio_features_list(self):
        response = self.client.get("/audio-features")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Danceability", response.data)

    def test_06_sql_analysis_queries(self):
        for q_id in range(1, 9):
            response = self.client.get(f"/analysis?q_id={q_id}")
            self.assertEqual(response.status_code, 200, f"Query {q_id} failed!")

    def test_07_reports_and_csv_export(self):
        response = self.client.get("/reports")
        self.assertEqual(response.status_code, 200)

        for entity in ["tracks", "artists", "albums", "audio_features", "statistical_summary", "all"]:
            csv_resp = self.client.get(f"/export/csv/{entity}")
            self.assertEqual(csv_resp.status_code, 200, f"CSV export for {entity} failed!")
            self.assertEqual(csv_resp.mimetype, "text/csv")
            self.assertTrue(len(csv_resp.data) > 0)

    def test_08_crud_artist_lifecycle(self):
        # 1. Add
        add_resp = self.client.post("/artists/add", data={"artist_name": "Post Malone", "country": "USA"}, follow_redirects=True)
        self.assertEqual(add_resp.status_code, 200)
        self.assertIn(b"Post Malone", add_resp.data)

        # 2. Find added artist ID
        artists = db.get_all_artists(search="Post Malone")
        self.assertTrue(len(artists) > 0)
        art_id = artists[0]["artist_id"]

        # 3. Edit
        edit_resp = self.client.post(f"/artists/edit/{art_id}", data={"artist_name": "Post Malone Updated", "country": "United States"}, follow_redirects=True)
        self.assertEqual(edit_resp.status_code, 200)
        self.assertIn(b"Post Malone Updated", edit_resp.data)

        # 4. Delete
        del_resp = self.client.post(f"/artists/delete/{art_id}", follow_redirects=True)
        self.assertEqual(del_resp.status_code, 200)
        self.assertNotIn(b"Post Malone Updated", del_resp.data)

    def test_09_api_endpoints(self):
        resp = self.client.get("/api/charts/dashboard")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("line_labels", data)
        self.assertIn("feature_values", data)
        self.assertIn("filters", data)

        filter_resp = self.client.get("/api/chart/filter/high_pop")
        self.assertEqual(filter_resp.status_code, 200)
        f_data = filter_resp.get_json()
        self.assertIn("values", f_data)

        search_resp = self.client.get("/api/search?q=Lights")
        self.assertEqual(search_resp.status_code, 200)
        search_data = search_resp.get_json()
        self.assertTrue(len(search_data) > 0)
        self.assertEqual(search_data[0]["track_name"], "Blinding Lights")

        notif_resp = self.client.get("/api/notifications")
        self.assertEqual(notif_resp.status_code, 200)
        self.assertTrue(len(notif_resp.get_json()) >= 3)

    def test_10_pandas_analytics(self):
        analytics = get_pandas_analytics()
        self.assertIsNotNone(analytics)
        self.assertIn("stats", analytics)
        self.assertIn("corr_matrix", analytics)
        self.assertIn("popularity", analytics["stats"])

if __name__ == "__main__":
    unittest.main()
