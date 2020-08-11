import asyncio
import logging

from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from aioconsole import ainput

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger('client')


async def subscribe_to_messages(websocket: ClientWebSocketResponse) -> None:
    """
    A subscription handler to subscribe to messages. Simply logs them. 
    
    :param websocket: Websocket connection
    :return: None, forever living task
    """
    async for message in websocket:
        if isinstance(message, WSMessage):
            message_json = message.json()
            if chat_message := message_json.get('chat_message'):
                print(f'> {chat_message}')
            logger.info('> Message from server received: %s', message_json)


async def ping(websocket: ClientWebSocketResponse) -> None:
    """
    A function that sends a PING every minute to keep the connection alive.
    
    :param websocket: Websocket connection
    :return: None, forever living task
    """
    while True:
        message = {'jonas': 'is cool'}
        logger.info('< Sending message: %s', message)
        await websocket.send_json(message)
        await asyncio.sleep(60)


async def send_input_message(websocket: ClientWebSocketResponse) -> None:
    """
    A function to send messages over the connection.

    :param websocket: Websocket connection
    :return:
    """
    while True:
        message = await ainput(prompt='Message: ')
        logger.info('< Sending message: %s', message)
        await websocket.send_json({'message': message})


async def handler() -> None:
    async with ClientSession() as session:
        async with session.ws_connect('ws://0.0.0.0:8080/echo', ssl=False) as ws:
            read_message_task = asyncio.create_task(subscribe_to_messages(websocket=ws))
            ping_task = asyncio.create_task(ping(websocket=ws))
            send_input_message_task = asyncio.create_task(send_input_message(websocket=ws))

            # This function returns two variables, a list of `done` and a list of `pending` tasks.
            # We can ask it to return when all tasks are completed, first task is completed or on first exception
            done, pending = await asyncio.wait(
                [read_message_task, ping_task, send_input_message_task], return_when=asyncio.FIRST_COMPLETED,
            )
            # When this line of line is hit, we know that one of the tasks has been completed.
            # In this program, this can happen when:
            #   * we (the client) or the server is closing the connection. (websocket.close() in aiohttp)
            #   * an exception is raised

            # First, we want to close the websocket connection
            await ws.close()
            # Then, we cancel each task which is pending:
            for task in pending:
                task.cancel()
            # At this point, everything is shut down. The program will exit.


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(handler())

    # The code below can be ignored, but I put it in as a reference for those who would like to implement this in a
    # production system.
    # Zero-sleep to allow underlying connections to close
    # Change sleep to 0.250 if using SSL! https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
    loop.run_until_complete(asyncio.sleep(0))
    loop.close()
