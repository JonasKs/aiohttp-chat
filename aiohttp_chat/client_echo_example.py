# This file is aimed to be a very simple example on how to:
#  * Establish a websocket connection
#  * Create async tasks and control them properly. In this example we have two tasks:
#    - Task that prints every incoming message (Messages returned from the echo server)
#    - Task that sends a message to the echo server every 15 seconds
import asyncio
import logging

from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('client')


async def subscribe_to_messages(websocket: ClientWebSocketResponse) -> None:
    """
    A subscription handler to subscribe to messages. Simply logs them. 

    :param websocket: Websocket connection
    :return: None, forever living task
    """
    async for message in websocket:
        if isinstance(message, WSMessage):
            logger.info('> Message from server received: %s', message.json())


async def send_hello_world_message(websocket: ClientWebSocketResponse) -> None:
    """
    A function that sends a Hello World message every 15 seconds.

    :param websocket: Websocket connection
    :return: None, forever living task
    """
    while True:
        message = {'message': 'Hello world!'}
        logger.info('< Sending message: %s', message)
        await websocket.send_json(message)
        await asyncio.sleep(15)


async def echo_handler() -> None:
    """
    Does the following:
    
     * Open a websocket connection
     * Creates two tasks, one that sends a message, one that prints the messages that gets back
     * Every 60 seconds it sends a "Hello world!" message to the echo endpoint (`/`)
    :return: None
    """
    # Create a session
    async with ClientSession() as session:
        # Connect with websocket to the echo endpoint
        async with session.ws_connect('ws://0.0.0.0:8080/echo', ssl=False) as ws:
            send_message_task = asyncio.create_task(send_hello_world_message(websocket=ws))
            subscribe_to_messages_task = asyncio.create_task(subscribe_to_messages(websocket=ws))

            # This function returns two variables, a list of `done` and a list of `pending` tasks.
            # We can ask it to return when all tasks are completed, first task is completed or on first exception
            done, pending = await asyncio.wait(
                [send_message_task, subscribe_to_messages_task], return_when=asyncio.FIRST_COMPLETED,
            )
            # When this line of line is hit, we know that one of the tasks has been completed.
            # In this program, this can happen when:
            #   * we (the client) or the server is closing the connection. (websocket.close() in aiohttp)
            #   * an exception is raised

            # First, we want to close the websocket connection
            if not ws.closed:
                await ws.close()
            # Then, we cancel each task which is pending:
            for task in pending:
                task.cancel()
            # At this point, everything is shut down. The program will exit.


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(echo_handler())
