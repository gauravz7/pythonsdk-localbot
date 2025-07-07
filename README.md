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

## System Architecture

![Architecture Diagram](Arch.png)

### Frontend Javascript + NodeJS
- **Initialization**: The main application script instantiates audio-client.js.
- **Connection**: The AudioClient establishes a persistent, two-way connection to the backend using the WebSocket API.
- **Recording (Capture on the Audio Thread)**:
  - When the user starts recording, the AudioClient uses the AudioContext to access the microphone stream.
  - An ScriptProcessorNode (or AudioWorklet) listens for audio data. Crucially, this event handler runs on the dedicated audio thread.
  - As audio chunks arrive, they are encoded and sent over the WebSocket to the server.
- **Playback (Playback on the Audio Thread)**:
  - The AudioClient receives audio response chunks from the server.
  - These chunks are pushed into a queue.
  - The AudioContext is used to decode the audio data into playable buffers.
  - It then schedules these buffers for seamless, back-to-back playback, again ensuring this entire process happens on the audio thread for perfect timing.

### Backend - Python

The stack consists of Python leveraging asyncio for non-blocking I/O, the websockets library for the transport layer, The system's design is based on several decoupled components, each with a distinct responsibility. This architecture ensures scalability, maintainability, and efficient handling of concurrent operations

| Feature | Description |
|---|---|
| **Real-Time Audio Streaming** | Manages continuous, low-latency, bidirectional streaming of audio data between the client and the Gemini API. |
| **WebSocket Communication** | Utilizes the websockets library to establish a persistent, full-duplex communication channel with clients. |
| **Asynchronous Architecture** | Built entirely on Python's asyncio framework to handle multiple clients and I/O operations concurrently without blocking. |
| **Gemini Live API Integration** | Directly integrates with the google-generativeai library's live.connect feature for stateful, real-time interaction. |
| **Session Resumption** | Implements a mechanism to save and load session handles, allowing clients to resume previous conversations. |
| **Dynamic Voice Activity Detection (VAD)** | Configures and utilizes the Gemini API's server-side VAD to intelligently detect the start and end of user speech. |
| **Bidirectional Transcription** | Provides real-time transcription of both the user's input audio and the model's generated audio response. |
| **Interruption Handling** | Supports the ability for the user to interrupt the model's speech, providing a more natural conversational flow. |
| **Modular Design** | Employs a base server class (BaseWebSocketServer) for core connection logic, promoting extensibility and separation of concerns. |

### Core Components

- **System Flow**: Clients send Base64 PCM audio via WebSocket, which gets decoded and queued by the ingress handler. The egress handler streams queued audio to Gemini's API while the response handler processes concurrent API responses. Response demultiplexing handles different message types: model_turn (audio), transcription data, and session metadata.
- **WebSocket Server**: The server handles client connections where BaseWebSocketServer provides generic connection management while subclasses implement protocol specifics. Built on websockets.serve(), it manages HTTP/WebSocket upgrades and spawns isolated session handlers per connection.
- **Gemini API Handler**: This component manages individual Gemini Live API sessions via client.aio.live.connect() with configuration for response modalities, audio transcription, and server-side VAD. It maintains session state and handles resumption using persistent API handles through async context managers.
- **Concurrent Task Orchestrator**: Full-duplex communication is achieved through asyncio.TaskGroup coordinating three coroutines per client: ingress handling (WebSocket messages), egress handling (API streaming), and response processing. This prevents I/O blocking and maintains low-latency voice interactions.
- **Asynchronous Audio Buffer**: A producer-consumer pattern using asyncio.Queue decouples client data from API streaming. The WebSocket handler encodes audio and enqueues bytes while the processor dequeues for API transmission
- **Session Persistence**: Simple file-based persistence saves session handles from session_resumption_update responses to JSON files. This enables conversation continuity after disconnections but requires distributed storage (Redis) for production scaling. Right now the basic implementation takes only the saved session.

### Setup and Deployment
**Prerequisites**
- Authenticated Google Cloud SDK (gcloud auth application-default login).
- Python 3.9+. Create and activate a Python virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate
  # On Windows: venv\Scripts\activate
  ```
- Clone the repository and cd into the project directory.

**Install dependencies from requirements.txt:**
```
google-generativeai
google-cloud-aiplatform
websockets
```
```bash
pip install -r requirements.txt
```
**Configuration**
- **common.py**: Set `PROJECT_ID` and `LOCATION` to match your Google Cloud configuration.
- **live_api_server.py**: The `CONFIG` dictionary contains tunable parameters for the Gemini API session, including VAD sensitivity, which can be adjusted to optimize for different acoustic environments or use cases.

**Execution**
Launch the server using the Python interpreter:
```bash
python server.py
```
The server will bind to 0.0.0.0:8765 and begin listening for connections.

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
