# Multimodal Live API UI

This project contains the user interface for the Multimodal Live API. It has been converted to a Node.js application that serves the frontend and handles WebSocket connections.

## Prerequisites

- [Node.js](https://nodejs.org/) (which includes npm) must be installed on your system.

## Getting Started

1.  **Install Frontend Dependencies:**
    Open a terminal in the project directory and run the following command to install the required Node.js packages:
    ```bash
    npm install
    ```

2.  **Install Backend Dependencies:**
    Open a new terminal and navigate to the `server` directory. Run the following command to install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Start the Backend Server:**
    In the same terminal (inside the `server` directory), run the following command to start the Python WebSocket server:
    ```bash
    python server.py
    ```

4.  **Start the Frontend Server:**
    In a separate terminal, navigate to the project root directory and run the following command to start the Node.js server:
    ```bash
    npm start
    ```
    This will start an Express server on port 8080, serving the frontend.

5.  **Access the Application:**
    Open your web browser and navigate to [http://localhost:8080](http://localhost:8080) to use the application.

## Project Structure

-   `client/`: Contains the frontend files (`index.html`, `audio-client.js`, etc.).
-   `server.js`: The main Node.js server file that uses Express to serve the frontend.
-   `package.json`: Defines the project's dependencies and scripts.
-   `server/`: Contains the Python WebSocket server files.

## Architecture

```mermaid
sequenceDiagram
    participant Client (Browser)
    participant WebSocket Server (Python)
    participant Gemini API
    participant SessionFile (session_handle.json)

    Client->>+WebSocket Server: 1. Establish WebSocket Connection
    WebSocket Server->>+SessionFile: 2. Load Previous Session Handle
    SessionFile-->>-WebSocket Server: 3. Return Handle (or null)
    WebSocket Server->>+Gemini API: 4. Connect (with session handle)
    Gemini API-->>-WebSocket Server: 5. Connection Established
    WebSocket Server-->>-Client: 6. Connection Ready

    loop Audio Streaming
        Client->>WebSocket Server: 7. Stream Audio Chunks
        WebSocket Server->>Gemini API: 8. Forward Audio Chunks
    end

    Gemini API->>WebSocket Server: 9. Stream Response (Audio/Text)
    
    alt Session Resumption Update
        Gemini API->>WebSocket Server: 10a. Send New Session Handle
        WebSocket Server->>+SessionFile: 10b. Save New Handle
        SessionFile-->>-WebSocket Server: 10c. Confirm Save
    end

    WebSocket Server->>Client: 11. Stream Response to Client
    Client->>Client: 12. Play Audio / Display Text

    Client->>-WebSocket Server: 13. Close Connection
```

## Features

-   **Full-Screen Chat Interface**: The chat application now runs in a full-screen mode for an immersive experience.
-   **Voice-Powered Interaction**: Users can interact with the assistant using their voice.
-   **Session Resumption**: The application remembers your conversation history between connections.

## Contributing

1.  **Commit Changes:**
    After making changes, commit them with a descriptive message:
    ```bash
    git commit -am "Your descriptive commit message"
    ```

2.  **Push to GitHub:**
    Push your changes to the main branch of the repository:
    ```bash
    git push
    ```
