import React, { useState } from "react";
import axios from "axios";
import "./styles.css";

function HW() {
  const xx = "";
  const handleSubmit = async (e) => {
    e.preventDefault();

    try {
      // First try to GET existing recommendations
        const response = await axios.get(
          `http://localhost:8000/helloworld`
        );
        xx = response.data
    } catch (err) {
      const errorMessage = err.response?.data?.detail
        ? `Error: ${err.response.data.detail}`
        : "Failed to get recommendations";
      console.error("Request failed:", err.response?.data || err.message);
    }
  };

  return (
    <div className="HW">
      <h1>Hello World!!!</h1>
    </div>
  );
}

export default HW;
