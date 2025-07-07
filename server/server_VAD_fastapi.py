import asyncio
import json
import base64
import os
import time

# Record program start time
PROGRAM_START_TIME = time.time()
print(f"🚀 PROGRAM STARTED at {PROGRAM_START_TIME:.3f}")

# Import Google Generative AI components
print("🔧 Initializing Google Generative AI client...")
client_init_start = time.time()
from google import genai
from google.genai import types
from google.genai.types import (
    LiveConnectConfig,
    SpeechConfig,
    VoiceConfig,
    PrebuiltVoiceConfig,
)

# Import common components
from common import (
    BaseWebSocketServer,
    logger,
    PROJECT_ID,
    LOCATION,
    MODEL,
    VOICE_NAME,
    SEND_SAMPLE_RATE,
    SYSTEM_INSTRUCTION,
)

# Initialize Google client
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
client_init_time = (time.time() - client_init_start) * 1000
print(f"✅ Google client initialized in {client_init_time:.2f}ms")

tools = [{'google_search': {}}]


# Load previous session handle from a file
# You must delete the session_handle.json file to start a new session when last session was
# finished for a while.
def load_previous_session_handle():
    try:
        with open('session_handle.json', 'r') as f:
            data = json.load(f)
            print(f"Loaded previous session handle: {data.get('previous_session_handle', None)}")
            return data.get('previous_session_handle', None)
    except FileNotFoundError:
        return None

# Save previous session handle to a file
def save_previous_session_handle(handle):
    with open('session_handle.json', 'w') as f:
        json.dump({'previous_session_handle': handle}, f)

previous_session_handle = load_previous_session_handle()


CONFIG = {
    "response_modalities": ["AUDIO"], 
    "tools": tools,
    # Audio transcription settings
    "output_audio_transcription": {},  # Enable transcription of model's audio output
    "input_audio_transcription": {},   # Enable transcription of user's audio input
    # Voice Activity Detection (VAD) configuration
    "realtime_input_config": {
        "automatic_activity_detection": {
            "disabled": False,  # Enable automatic VAD
            "start_of_speech_sensitivity": types.StartSensitivity.START_SENSITIVITY_LOW,  # Less sensitive
            "end_of_speech_sensitivity": types.EndSensitivity.END_SENSITIVITY_LOW,        # Less sensitive
            "prefix_padding_ms": 400,      # More audio padding before speech starts
            "silence_duration_ms": 800,  # Longer silence before considering speech ended
        },
        #"denoiser_config": {
        #    "denoise_audio": True  # Enable audio denoising
        # },
    },

    "session_resumption": types.SessionResumptionConfig(
        handle=previous_session_handle
    ),
}


class LiveAPIWebSocketServer(BaseWebSocketServer):
    """WebSocket server implementation using Gemini LiveAPI directly."""

    async def process_audio(self, websocket, client_id):
        # Calculate and display startup metrics on first connection
        connection_time = time.time()
        startup_time = (connection_time - PROGRAM_START_TIME) * 1000
        print(f"🔌 WEBSOCKET READY! Total startup time: {startup_time:.2f}ms")
        
        # TTFT tracking variables
        last_audio_time = None
        turn_start_time = None
        first_token_received = False
        turn_count = 0
        
        # Store reference to client
        self.active_clients[client_id] = websocket

        # Connect to Gemini using LiveAPI
        async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
            # Track if we've already handled the initial session setup
            session_initialized = False
            
            async with asyncio.TaskGroup() as tg:
                # Create a queue for audio data from the client
                audio_queue = asyncio.Queue()

                # Task to process incoming WebSocket messages
                async def handle_websocket_messages():
                    nonlocal last_audio_time, turn_start_time, first_token_received, turn_count
                    
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            if data.get("type") == "audio":
                                # Update last audio time when we receive audio from user
                                last_audio_time = time.time()
                                
                                # Decode base64 audio data
                                audio_bytes = base64.b64decode(data.get("data", ""))
                                # Put audio in queue for processing
                                await audio_queue.put(audio_bytes)
                            elif data.get("type") == "end":
                                # Client is done sending audio for this turn
                                print(f"📨 RECEIVED END SIGNAL FROM CLIENT")
                                logger.info("Received end signal from client")
                                # Mark the start time for TTFT measurement
                                if not turn_start_time:  # Only set if not already set
                                    turn_start_time = time.time()
                                    first_token_received = False
                                    print(f"🎤 USER FINISHED SPEAKING (END SIGNAL) - TTFT timer started at {turn_start_time:.3f}")
                            elif data.get("type") == "text":
                                # Handle text messages (not implemented in this simple version)
                                logger.info(f"Received text: {data.get('data')}")
                        except json.JSONDecodeError:
                            logger.error("Invalid JSON message received")
                        except Exception as e:
                            logger.error(f"Error processing message: {e}")

                # Task to process and send audio to Gemini
                async def process_and_send_audio():
                    while True:
                        data = await audio_queue.get()

                        # Send the audio data to Gemini
                        await session.send(input={
                            "mime_type": f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                            "data": data
                        })

                        audio_queue.task_done()

                # Task to receive and play responses
                async def receive_and_play():
                    nonlocal session_initialized, turn_start_time, first_token_received, last_audio_time, turn_count
                    
                    while True:
                        input_transcriptions = []
                        output_transcriptions = []

                        async for response in session.receive():
                            # Handle session resumption update - log only on initial connection, but save every time
                            if response.session_resumption_update:
                                update = response.session_resumption_update
                                if update.resumable and update.new_handle:
                                    # Always save the updated handle
                                    save_previous_session_handle(update.new_handle)
                                    
                                    if not session_initialized:
                                        logger.info(f"Session established with handle: {update.new_handle}")
                                        # Send session ID to client
                                        session_id_msg = json.dumps({
                                            "type": "session_id",
                                            "data": update.new_handle
                                        })
                                        await websocket.send(session_id_msg)
                                        session_initialized = True
                                    else:
                                        # Print session handle updates after initial connection
                                        logger.info(f"Session handle updated: {update.new_handle}")

                            # Check if connection will be terminated soon
                            if response.go_away is not None:
                                logger.info(f"Session will terminate in: {response.go_away.time_left}")

                            server_content = response.server_content

                            # Handle interruption
                            if (hasattr(server_content, "interrupted") and server_content.interrupted):
                                logger.info("🤐 INTERRUPTION DETECTED")
                                # Just notify the client - no need to handle audio on server side
                                await websocket.send(json.dumps({
                                    "type": "interrupted",
                                    "data": "Response interrupted by user input"
                                }))

                            # Process model response
                            if server_content and server_content.model_turn:
                                for part in server_content.model_turn.parts:
                                    if part.inline_data:
                                        # Calculate TTFT if this is the first token
                                        if turn_start_time and not first_token_received:
                                            ttft = (time.time() - turn_start_time) * 1000  # Convert to milliseconds
                                            print(f"⚡ TURN {turn_count} - TIME TO FIRST AUDIO TOKEN: {ttft:.2f}ms")
                                            logger.info(f"⚡ Time to First Token: {ttft:.2f}ms")
                                            first_token_received = True
                                        
                                        # Send audio to client only (don't play locally)
                                        b64_audio = base64.b64encode(part.inline_data.data).decode('utf-8')
                                        await websocket.send(json.dumps({
                                            "type": "audio",
                                            "data": b64_audio
                                        }))

                            # Handle turn completion
                            if server_content and server_content.turn_complete:
                                if turn_start_time and first_token_received:
                                    total_turn_time = (time.time() - turn_start_time) * 1000
                                    print(f"✅ TURN {turn_count} COMPLETE - Total response time: {total_turn_time:.2f}ms")
                                else:
                                    print(f"✅ TURN {turn_count} COMPLETE - No timing data")
                                
                                logger.info("✅ Gemini done talking")
                                # Reset TTFT tracking for next turn
                                turn_start_time = None
                                first_token_received = False
                                await websocket.send(json.dumps({
                                    "type": "turn_complete"
                                }))

                            # Handle transcriptions
                            input_transcription = getattr(response.server_content, "input_transcription", None)
                            if input_transcription and input_transcription.text:
                                input_transcriptions.append(input_transcription.text)
                                print(f"👤 User said: {input_transcription.text}")
                                
                                # When we get input transcription, this means user just finished speaking
                                # Start TTFT timer if not already started
                                if not turn_start_time and not first_token_received:
                                    turn_start_time = time.time()
                                    turn_count += 1
                                    print(f"🎤 TURN {turn_count}: User finished speaking (VAD detected) - TTFT timer started at {turn_start_time:.3f}")
                                
                                await websocket.send(json.dumps({
                                    "type": "itext",
                                    "data": input_transcription.text
                                }))
                                
                            output_transcription = getattr(response.server_content, "output_transcription", None)
                            if output_transcription and output_transcription.text:
                                print(f"📝 Received text transcription: '{output_transcription.text[:50]}...'")
                                output_transcriptions.append(output_transcription.text)
                                
                                # Calculate TTFT for text if this is the first response and we haven't received audio yet
                                if turn_start_time and not first_token_received:
                                    ttft = (time.time() - turn_start_time) * 1000  # Convert to milliseconds
                                    print(f"📝 TURN {turn_count} - TIME TO FIRST TEXT TOKEN: {ttft:.2f}ms")
                                    logger.info(f"📝 Time to First Text Token: {ttft:.2f}ms")
                                    first_token_received = True
                                
                                # Send text to client
                                await websocket.send(json.dumps({
                                    "type": "otext",
                                    "data": output_transcription.text
                                }))

                        logger.info(f"Input transcription: {''.join(input_transcriptions)}")
                        logger.info(f"Output transcription: {''.join(output_transcriptions)}")
                        

                # Start all tasks
                tg.create_task(handle_websocket_messages())
                tg.create_task(process_and_send_audio())
                tg.create_task(receive_and_play())

async def main():
    """Main function to start the server"""
    # Calculate time to reach main execution
    main_start_time = (time.time() - PROGRAM_START_TIME) * 1000
    print(f"⏰ Reached main() in {main_start_time:.2f}ms")
    
    print("🚀 Starting WebSocket server...")
    server_start_time = time.time()
    
    server = LiveAPIWebSocketServer()
    await server.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting application via KeyboardInterrupt...")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}")
        import traceback
        traceback.print_exc()