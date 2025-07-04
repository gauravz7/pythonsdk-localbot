import asyncio
import json
import base64
import os

# Import Google Generative AI components
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
    get_order_status,
)

# Initialize Google client
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)


#model = "gemini-2.5-flash-preview-native-audio-dialog"

# Define function declarations for custom tools
turn_on_the_lights = {
    "name": "turn_on_the_lights",
    "description": "Turn on the smart lights in the room"
    }

turn_off_the_lights = {
    "name": "turn_off_the_lights", 
    "description": "Turn off the smart lights in the room"
}

get_weather = {
    "name": "get_weather",
    "description": "Get current weather information for a location",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA"
            }
        },
        "required": ["location"]
    }
}

pause_for_10_seconds = {
    "name": "pause_for_10_seconds",
    "description": "Make a slow API call to external service that takes 10 seconds to complete",
    #"behavior": "NON_BLOCKING"  # Enable asynchronous execution
}


# Backend dummy functions that actually execute
async def execute_turn_on_lights():
    """Backend function to turn on lights"""
    print("----- Turned on Successfull")
    return {"result": "Lights turned on successfully", "status": "on"}

async def execute_turn_off_lights():
    """Backend function to turn off lights"""
    print("Turned off Successfull -----")
    return {"result": "Lights turned off successfully", "status": "off"}

async def execute_get_weather(location="Unknown"):
    """Backend function to get weather"""
    print(f"Fetching weather for: {location}")
    import random
    temperature = random.randint(60, 85)
    conditions = random.choice(["sunny", "cloudy", "partly cloudy", "rainy"])
    result = f"Current weather in {location}: {temperature}°F, {conditions}"
    print(f"Weather result: {result}")
    return {"result": result, "temperature": temperature, "conditions": conditions}

async def execute_pause():
    """Backend function to simulate a slow API call that takes 10 seconds"""
    print("🌐 Making API call to external service...")
    print("📡 Connecting to slow-response-api.example.com...")
    
    # Simulate network delay and processing time
    await asyncio.sleep(2)
    print("🔄 Processing request on remote server...")
    
    await asyncio.sleep(3)
    print("⏳ Waiting for database query to complete...")
    
    await asyncio.sleep(3)
    print("📊 Analyzing response data...")
    
    await asyncio.sleep(2)
    print("✅ API call completed successfully!")
    
    return {
        "result": "External API call completed", 
        "duration": 10,
        "api_endpoint": "slow-response-api.example.com",
        "status": "success",
        "data": {
            "processing_time": "10.2 seconds",
            "records_processed": 15420,
            "cache_status": "miss"
        }
    }

# Combined tools configuration
tools = [
    {"google_search": {}},  # Google Search tool
    {"function_declarations": [
        turn_on_the_lights,
        turn_off_the_lights,
        get_weather,
        pause_for_10_seconds
    ]}
]

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
            "silence_duration_ms": 400,  # Longer silence before considering speech ended
        }
    },

    "session_resumption": types.SessionResumptionConfig(
        handle=previous_session_handle
    ),
}


class LiveAPIWebSocketServer(BaseWebSocketServer):
    """WebSocket server implementation using Gemini LiveAPI directly."""

    async def handle_tool_calls(self, response):
        """Handle tool calls from the Gemini model - based on reference implementation"""
        if response.tool_call:
            function_responses = []
            for fc in response.tool_call.function_calls:
                print(f"\n🔧 Executing tool: {fc.name}")
                
                # Execute actual backend functions for each tool call
                if fc.name == "turn_on_the_lights":
                    response_data = await execute_turn_on_lights()
                elif fc.name == "turn_off_the_lights":
                    response_data = await execute_turn_off_lights()
                elif fc.name == "get_weather":
                    # Extract location parameter if provided
                    location = "Unknown Location"  # Default
                    if hasattr(fc, 'args') and fc.args and 'location' in fc.args:
                        location = fc.args['location']
                    response_data = await execute_get_weather(location)
                elif fc.name == "pause_for_10_seconds":
                    response_data = await execute_pause()
                    # Add scheduling parameter for NON_BLOCKING function
                    #response_data["scheduling"] = "INTERRUPT"  # Can also be "WHEN_IDLE" or "SILENT"
                else:
                    print(f"Unknown function: {fc.name}")
                    response_data = {"result": "Function executed successfully"}
                
                function_response = types.FunctionResponse(
                    id=fc.id,
                    name=fc.name,
                    response=response_data
                )
                function_responses.append(function_response)
                print(f"✅ Tool {fc.name} completed")

            # Send tool responses back to the session
            await self.session.send_tool_response(function_responses=function_responses)

    async def process_audio(self, websocket, client_id):
        # Store reference to client
        self.active_clients[client_id] = websocket

        # Connect to Gemini using LiveAPI
        async with client.aio.live.connect(model=MODEL, config=CONFIG) as session:
            # Store session reference for tool calls
            self.session = session
            
            # Track if we've already handled the initial session setup
            session_initialized = False
            
            async with asyncio.TaskGroup() as tg:
                # Create a queue for audio data from the client
                audio_queue = asyncio.Queue()

                # Task to process incoming WebSocket messages
                async def handle_websocket_messages():
                    async for message in websocket:
                        try:
                            data = json.loads(message)
                            if data.get("type") == "audio":
                                # Decode base64 audio data
                                audio_bytes = base64.b64decode(data.get("data", ""))
                                # Put audio in queue for processing
                                await audio_queue.put(audio_bytes)
                            elif data.get("type") == "end":
                                # Client is done sending audio for this turn
                                logger.info("Received end signal from client")
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
                    nonlocal session_initialized
                    
                    while True:
                        input_transcriptions = []
                        output_transcriptions = []

                        # Use the same pattern as reference code
                        turn = session.receive()
                        async for response in turn:
                            # Handle tool calls using reference implementation
                            await self.handle_tool_calls(response)

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

                            # Handle audio transcriptions (like reference code)
                            if response.server_content:
                                # Output transcription (model's speech to text)
                                if response.server_content.output_transcription:
                                    transcript = response.server_content.output_transcription.text
                                    if transcript and transcript.strip():  # Only print non-empty transcripts
                                        logger.info(f"🎤 Model said: {transcript}")
                                        output_transcriptions.append(transcript)
                                        # Send text to client
                                        await websocket.send(json.dumps({
                                            "type": "text",
                                            "data": transcript
                                        }))
                                
                                # Input transcription (user's speech to text)
                                if response.server_content.input_transcription:
                                    transcript = response.server_content.input_transcription.text
                                    if transcript and transcript.strip():  # Only print non-empty transcripts
                                        logger.info(f"🗣️  You said: {transcript}")
                                        input_transcriptions.append(transcript)
                                        await websocket.send(json.dumps({
                                            "type": "text",
                                            "data": transcript
                                        }))

                            # Handle audio data (like reference code)
                            if data := response.data:
                                # Send audio to client only (don't play locally)
                                b64_audio = base64.b64encode(data).decode('utf-8')
                                await websocket.send(json.dumps({
                                    "type": "audio",
                                    "data": b64_audio
                                }))
                            elif text := response.text:
                                # Handle any text responses
                                logger.info(f"Text response: {text}")

                            # Handle turn completion
                            if server_content and server_content.turn_complete:
                                logger.info("✅ Gemini done talking")
                                await websocket.send(json.dumps({
                                    "type": "turn_complete"
                                }))

                        logger.info(f"Input transcription: {''.join(input_transcriptions)}")
                        logger.info(f"Output transcription: {''.join(output_transcriptions)}")
                        

                # Start all tasks
                tg.create_task(handle_websocket_messages())
                tg.create_task(process_and_send_audio())
                tg.create_task(receive_and_play())

async def main():
    """Main function to start the server"""
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