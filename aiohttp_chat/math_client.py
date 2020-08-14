import asyncio
import logging

from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage
from aiohttp.web import WSMsgType

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
            if message.type == WSMsgType.text:
                message_json = message.json()
                if message_json.get('action') == 'chat_message' and not message_json.get('success'):
                    print(f'>>>{message_json.get("user")}: {message_json.get("message")}')
                elif message_json.get('action') == 'joined':
                    print(f'>>>SYSTEM: {message_json.get("user")} join the room')
                elif message_json.get('action') == 'left':
                    if message_json.get('shame'):
                        print(f'>>>SYSTEM: {message_json.get("user")} left the room in SHAME!')
                    else:
                        print(f'>>>SYSTEM: {message_json.get("user")} left the room politely!')
                elif message_json.get('action') == 'nick_changed':
                    print(f'>>>SYSTEM: {message_json.get("from_user")} is now known as {message_json.get("to_user")}')
                logger.info('> Message from server received: %s', message_json)


async def send_input_message(websocket: ClientWebSocketResponse) -> None:
    """
    A function to send messages over the connection.

    :param websocket: Websocket connection
    :return:
    """

    while True:
        questions = ['2 + 2', '10 * 1', '40 * 40', '10 - 5', '12 + 4', '55 + 45', '99 + 1', '0 * 999', '44 -14']
        for question in questions:
            print(f'< What is {question}')
            await websocket.send_json({'action': 'chat_message', 'message': question})
            await asyncio.sleep(15)


async def handler() -> None:
    """
    Does the following things well:
        * Subscribes to messages and prints them
        * Asks questions
    :return: None
    """
    async with ClientSession() as session:
        async with session.ws_connect('ws://0.0.0.0:8080/chat', ssl=False) as ws:
            read_message_task = asyncio.create_task(subscribe_to_messages(websocket=ws))
            # Change nick to `Jonas` and change room to `test`
            await ws.send_json({'action': 'join_room', 'room': 'math'})
            await ws.send_json({'action': 'set_nick', 'nick': 'MathStudent'})
            send_input_message_task = asyncio.create_task(send_input_message(websocket=ws))

            # This function returns two variables, a list of `done` and a list of `pending` tasks.
            # We can ask it to return when all tasks are completed, first task is completed or on first exception
            done, pending = await asyncio.wait(
                [read_message_task, send_input_message_task], return_when=asyncio.FIRST_COMPLETED,
            )
            # When this line of line is hit, we know that one of the tasks has been completed.
            # In this program, this can happen when:
            #   * we (the client) or the server is closing the connection. (websocket.close() in aiohttp)
            #   * an exception is raised

            # First, we want to close the websocket connection if it's not closed by some other function above
            if not ws.closed:
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
