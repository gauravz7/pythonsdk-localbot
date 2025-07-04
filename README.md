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

2.  **Start the Server:**
    After the installation is complete, you can start the server with this command:
    ```bash
    npm start
    ```
    This will start an Express server on port 8080, serving the frontend and handling WebSocket connections.

3.  **Access the Application:**
    Open your web browser and navigate to [http://localhost:8080](http://localhost:8080) to use the application.

## Project Structure

-   `client/`: Contains the frontend files (`index.html`, `audio-client.js`, etc.).
-   `server.js`: The main Node.js server file that uses Express and ws.
-   `package.json`: Defines the project's dependencies and scripts.
-   `server/`: Contains the original Python server files (no longer in use).
