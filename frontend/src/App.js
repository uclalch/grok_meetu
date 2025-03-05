import React, { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [userId, setUserId] = useState("");
  const [recommendations, setRecommendations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [thresholds, setThresholds] = useState({
    motivation: 0.1,
    pressure: 0.5,
    credit_level: "partial",
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      // First try to GET existing recommendations
      try {
        const response = await axios.get(
          `http://localhost:8000/recommendations/${userId}`
        );
        setRecommendations(response.data.recommendations || []);
        return;
      } catch (err) {
        // If 404, recommendations don't exist - continue to create new ones
        if (err.response?.status !== 404) {
          throw err;
        }
      }

      // If we get here, no recommendations exist - create new ones
      const response = await axios.post(
        "http://localhost:8000/recommendations",
        {
          user_id: userId,
          filters: {
            top_k: 5,
          },
          thresholds: thresholds,
        }
      );
      setRecommendations(response.data.recommendations || []);
    } catch (err) {
      const errorMessage = err.response?.data?.detail
        ? `Error: ${err.response.data.detail}`
        : "Failed to get recommendations";
      setError(errorMessage);
      console.error("Request failed:", err.response?.data || err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <h1>Grok MeetU</h1>
      <div className="container">
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Enter User ID"
              required
            />
          </div>

          <div className="thresholds">
            <h3>Thresholds</h3>
            <div className="form-group">
              <label>Motivation:</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={thresholds.motivation}
                onChange={(e) =>
                  setThresholds({
                    ...thresholds,
                    motivation: parseFloat(e.target.value),
                  })
                }
              />
            </div>

            <div className="form-group">
              <label>Pressure:</label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="1"
                value={thresholds.pressure}
                onChange={(e) =>
                  setThresholds({
                    ...thresholds,
                    pressure: parseFloat(e.target.value),
                  })
                }
              />
            </div>

            <div className="form-group">
              <label>Credit Level:</label>
              <select
                value={thresholds.credit_level}
                onChange={(e) =>
                  setThresholds({
                    ...thresholds,
                    credit_level: e.target.value,
                  })
                }
              >
                <option value="none">None</option>
                <option value="partial">Partial</option>
                <option value="full">Full</option>
              </select>
            </div>
          </div>

          <button type="submit" disabled={loading}>
            {loading ? "Loading..." : "Get Recommendations"}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {recommendations.length > 0 && (
          <div className="recommendations">
            <h2>Recommended Chatrooms</h2>
            <div className="cards">
              {recommendations.map((rec) => (
                <div key={rec.chatroom_id} className="card">
                  <h3>Chatroom {rec.chatroom_id}</h3>
                  <div className="score">
                    Score: {rec.predicted_score.toFixed(2)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
