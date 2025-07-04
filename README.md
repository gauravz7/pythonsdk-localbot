# Multimodal Live API UI

This project contains the user interface for the Multimodal Live API. It has been converted to a Node.js application that serves the frontend and handles WebSocket connections.

## Prerequisites

- [Node.js](https://nodejs.org/) (which includes npm) must be installed on your system.

## Getting Started

1.  **Install Dependencies:**
    Open a terminal in the `ui-cloned/multimodal-live-api/ui` directory and run the following command to install the required Node.js packages:
    ```bash
    npm install
    ```

2.  **Start the Backend Server:**
    Open a new terminal and navigate to the `ui-cloned/multimodal-live-api/ui/server` directory. Run the following command to start the Python WebSocket server:
    ```bash
    python server.py
    ```

3.  **Start the Frontend Server:**
    In a separate terminal, navigate to the `ui-cloned/multimodal-live-api/ui` directory and run the following command to start the Node.js server:
    ```bash
    npm start
    ```
    This will start an Express server on port 8080, serving the frontend.

4.  **Access the Application:**
    Open your web browser and navigate to [http://localhost:8080](http://localhost:8080) to use the application.

## Project Structure

-   `client/`: Contains the frontend files (`index.html`, `audio-client.js`, etc.).
-   `server.js`: The main Node.js server file that uses Express to serve the frontend.
-   `package.json`: Defines the project's dependencies and scripts.
-   `server/`: Contains the Python WebSocket server files.
