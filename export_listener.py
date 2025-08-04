import zmq
import json
from agenda import Agenda
from contextlib import redirect_stdout #https://stackoverflow.com/questions/71024919/how-to-capture-prints-in-real-time-from-function
import io

PORT = 5050
VERBOSE = False

def main():

    # Create a ZeroMQ context and socket
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{PORT}")
    print(f"Server up: Listening for clients on port {PORT}...")

    # Listen for requests from the client
    while True:
        message = socket.recv_json()
        if VERBOSE:
            print(f"Received request from the client: {json.dumps(message,indent=2)}")
        else:
            print(f"Received request from the client: {message}")

        if len(message) > 0:
            json_data = message
            # In case running headless/remotely
            if json_data.get("quit", False):  # Client asked server to quit
                break

            # Process the request
            success = False
            output_buf = io.StringIO() # For capturing stdout
            try:
                with redirect_stdout(output_buf):
                    # Create an Agenda to handle events
                    e = Agenda(json_data)
                    # Export the events, export type is specified in the request
                    file_path = e.export()
                    # If return, then export was successful
                    if file_path:
                        success = True
                        #output_buf.write(status)

            except Exception as e:
                output_buf.write(str(e))
            finally:
                if success:
                    print("Processed successfully!")
                else:
                    print("Processed unsuccessfully!")
                # Send responses and log back to client
                captured_output = output_buf.getvalue()
                response = {
                    "status" : success,
                    "file_path" : file_path,
                    "response" : captured_output
                }
                socket.send_json(response)
    # Make a clean exit.
    context.destroy()


if __name__ == '__main__':
    main()
