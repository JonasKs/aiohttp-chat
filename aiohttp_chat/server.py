import logging
from collections import defaultdict

from aiohttp import web
from aiohttp.http_websocket import WSCloseCode, WSMessage
from aiohttp.web_request import Request
import random
from aiohttp_chat.utils import change_nick, change_room, retrieve_users


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_USER_ACTIONS = [
    'set_nick',
    'join_room',
    'chat_message',
    'user_list'
]


async def _broadcast_room(app, room, message):
    # TODO
    pass


async def ws_echo(request: Request) -> web.WebSocketResponse:
    """
    Echo service to send back the JSON sent to this endpoint, but wrapped in {'echo': <input>}

    :param request: Request object
    :return: The websocket response
    """
    websocket = web.WebSocketResponse()  # Create a websocket response object
    # Check that everything is OK, if it's not, close the connection.
    ready = websocket.can_prepare(request=request)
    if not ready:
        await websocket.close(code=WSCloseCode.PROTOCOL_ERROR)

    await websocket.prepare(request)  # Load it with the request object

    async for message in websocket:  # For each message in the websocket connection
        if isinstance(message, WSMessage):
            if message.type == web.WSMsgType.TEXT:  # If it's a text, process it as a message
                message_json = message.json()
                logger.info('> Received: %s', message_json)
                echo = {'echo': message_json}
                await websocket.send_json(echo)  # Send back the message
                logger.info('< Sent: %s', echo)
            # WebSocketResponse handles close, ping, pong etc. by default.
    return websocket


async def ws_chat(request: Request) -> web.WebSocketResponse:
    """
    Chat backend. Add it to the route like this:
        - app.add_routes([web.get('/chat', handler=ws_chat)])

    Things your client can do with this server:
    1) Connect

    2) Set a nick name. Your nick will be a random nickname by default. (E.g. `User1234`)
       This can be called multiple times to change nick name
       Usage:
        - Change nick json body:
            - {'action': 'set_nick', 'nick': '<my nickname>'}
        - If nickname is rejected, you will get an error message:
            - {'action': 'set_nick', 'success': False, 'message': 'Nickname is already in use'}
        - If nickname is approved, no error will be present:
            - {'action': 'set_nick', 'success': True, 'message': ''}

    3) Join a chat room. By default you join the `default` chat room.
       This can be called multiple times to change room
       Usage:
        - Change room json body:
            - {'action': 'join_room', 'room': '<room name>'}
        - If everything is OK, no error will be present:
            - {'action': 'join_room', 'success': True, 'message': ''}

    4) Chat!
       Usage:
        - Done by sending a body like this:
             - {'action': 'chat_message', 'message': '<my message>'}
        - If everything is OK, this message will be returned:
             - {'action': 'chat_message', 'success': True, 'message': '<chat_message>'}
    
    5) Ask for user list of a room
       Usage:
        - Ask for user list body:
            - {'action': 'user_list', 'room': '<room_name>'}
        - Body retrieved:
            - {'action': 'user_list', 'success': True, 'room': '<room_name>', 'users': ['<user1>', '<user2>']}
    6) Disconnect
        - With aiohttp close the connection normally:
             websocket.close()
        (- OR Send a close code: https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent)
    
    All messages on your actions will return with a `'success': True/False`.

    Bodies this server may broadcast to your client at any time:
    - When your client is connecting:
        - {'action': 'connecting', 'room': room, 'user': user}
    - When someone joins the room:
        - {'action': 'joined', 'room': room, 'user': user}
    - When someone leaves the room:
        - {'action': 'left', 'room': room, 'user': user}
    - When someone changes their nick name:
        - {'action': 'nick_changed', 'room': room, 'from_user': user, 'to_user': user}
    - When someone sends a message:
        - {'action': 'chat_message', 'message': message}
    
    :param request: Request object
    :return: Websocket response
    """
    current_websocket = web.WebSocketResponse()  # Create a websocket response object
    # Check that everything is OK, if it's not, close the connection.
    ready = current_websocket.can_prepare(request=request)
    if not ready:
        await current_websocket.close(code=WSCloseCode.PROTOCOL_ERROR)
    await current_websocket.prepare(request)  # Load it with the request object

    # Set default room name
    room = 'Default'
    # Set default user name.
    # Note: Can technically fail, and if it does we'll just close the connection and make them retry later.
    user = f'User{random.randint(0, 999999)}'
    logger.info('%s connected to room %s', user, room)

    # Inform current WS subscription that he's connecting:
    await current_websocket.send_json({'action': 'connecting', 'room': room, 'user': user})

    # Check that the user does not exist in the room already
    if request.app['websockets'][room].get(user):
        logger.warning('User already connected. Disconnecting.')
        await current_websocket.close(code=WSCloseCode.TRY_AGAIN_LATER, message=b'Username already in use')
        return current_websocket
    else:
        # {'websockets': {'<room>': {'<user>': 'obj', '<user2>': 'obj'}}}
        request.app['websockets'][room][user] = current_websocket
        # Inform everyone that user has joined
        for ws in request.app['websockets'][room].values():
            await ws.send_json({'action': 'join', 'user': user, 'room': room})

    # Send out messages whenever they are received
    async for message in current_websocket:  # for each message in the websocket connection
        if isinstance(message, WSMessage):
            if message.type == web.WSMsgType.TEXT:  # If it's a text, process it as a message
                # Parse incoming data
                json_message = message.json()
                action = json_message.get('action')
                if action not in ALLOWED_USER_ACTIONS:
                    await current_websocket.send_json({'action': action, 'success': False, 'message': 'Not allowed.'})
                
                if action == 'set_nick':
                    pass
                
                if action == 'change_room':
                    pass
                    
                if action == 'user_list':
                    pass
                
                if action == 'chat_message':
                    pass
                
                for ws in request.app['websockets'][room].values():  # For each connection in that room
                    logger.warning('ws: %s', ws)
                    if ws != current_websocket:  # Don't send back to current current connection
                        await ws.send_json({'action': 'sent', 'message': message.data})
                    else:
                        logger.warning('< Got message: %s', message.data)
                        # Confirm message was OK (change this? Protocol already implemented?)
                        await ws.send_json({'action': 'confirm', 'message': message.data})
    # If we get here, then connection has been closed (might not be done properly, hence not checking WSMsgType
    # Send leave message, remove from group:
    # TODO

    return current_websocket


async def init_app() -> web.Application:
    """
    Creates an backend app object with a 'websockets' dict on it, where we can store open websocket connections.
    :return: The app
    """
    app = web.Application()
    app['websockets'] = defaultdict(dict)

    app.on_shutdown.append(shutdown)  # Shut down connections before shutting down the app entirely
    app.add_routes([web.get('/echo', handler=ws_echo)])  # `ws_echo` handles this request.
    app.add_routes([web.get('/chat', handler=ws_chat)])  # `ws_chat` handles this request

    return app


async def shutdown(app):
    for room in app['websockets']:
        for ws in app['websockets'][room].values():
            ws.close()
    app['websockets'].clear()


def main():
    app = init_app()
    web.run_app(app)


if __name__ == '__main__':
    main()
