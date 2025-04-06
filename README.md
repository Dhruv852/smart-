# Smart Home Energy Monitor

An AI-powered energy monitoring system that tracks and analyzes home energy consumption, providing insights and suggestions for energy efficiency.

## Features

- Real-time energy consumption tracking
- Device-wise energy consumption analysis
- Daily consumption trends
- AI-powered energy-saving suggestions
- Modern, eco-friendly UI design

## Setup

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the root directory and add your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```
4. Run the application:
   ```bash
   python app.py
   ```
5. Open your browser and navigate to `http://localhost:5000`

## Data Structure

The application expects a CSV file in the `data` directory with the following columns:
- timestamp: Date and time of the reading
- device: Name of the device
- power_consumption: Power consumption in kWh

## Technologies Used

- Python Flask (Backend)
- HTML/CSS/JavaScript (Frontend)
- Google Gemini API (AI Analysis)
- Plotly.js (Data Visualization)
- Bootstrap 5 (UI Framework)

## Contributing

Feel free to submit issues and enhancement requests! 