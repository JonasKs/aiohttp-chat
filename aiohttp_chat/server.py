import logging
import random
from collections import defaultdict

from aiohttp import web
from aiohttp.http_websocket import WSCloseCode, WSMessage
from aiohttp.web_request import Request

from aiohttp_chat.utils import broadcast, change_nick, change_room, retrieve_users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_USER_ACTIONS = ['set_nick', 'join_room', 'chat_message', 'user_list']


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
            if message.type == web.WSMsgType.text:  # If it's a text, process it as a message
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

    #Input/Response API
    Note that you will *not* receive the broadcast message about your changes, only your confirmation or error.

    **Change Nick**:
    * Input: `{'action': 'set_nick', 'nick': '<my nickname>'}`
    * Fail: `{'action': 'set_nick', 'success': False, 'message': 'Nickname is already in use'}`
    * OK: `{'action': 'set_nick', 'success': True, 'message': ''}`


    **Join a room**:
    * Input: `{'action': 'join_room', 'room': '<room name>'}`
    * OK: `{'action': 'join_room', 'success': True, 'message': ''}`

    **Send a message**:
    * Input: `{'action': 'chat_message', 'message': '<my message>'}`
    * OK: `{'action': 'chat_message', 'success': True, 'message': '<chat_message>'}`

    **Room user list**:
    * Input: `{'action': 'user_list', 'room': '<room_name>'}`
    * OK:`{'action': 'user_list', 'success': True, 'room': '<room_name>', 'users': ['<user1>', '<user2>']}`


    # Broadcast messages
    Bodies this server may broadcast to your client at any time:
    - When your client is connecting:
        - `{'action': 'connecting', 'room': room, 'user': user}`
    - When someone joins the room:
        - `{'action': 'joined', 'room': room, 'user': user}`
    - When someone leaves the room:
        - `{'action': 'left', 'room': room, 'user': user}`
    - When someone changes their nick name:
        - `{'action': 'nick_changed', 'room': room, 'from_user': user, 'to_user': user}`
    - When someone sends a message:
        - `{'action': 'chat_message', 'message': message, 'user': user}`

    :param request: Request object
    :return: Websocket response
    """
    current_websocket = web.WebSocketResponse(autoping=True, heartbeat=60)  # Create a websocket response object
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
            if message.type == web.WSMsgType.text:  # If it's a text, process it as a message
                # Parse incoming data
                message_json = message.json()
                action = message_json.get('action')
                if action not in ALLOWED_USER_ACTIONS:
                    await current_websocket.send_json({'action': action, 'success': False, 'message': 'Not allowed.'})

                if action == 'set_nick':
                    return_body, success = await change_nick(
                        app=request.app, room=room, new_nick=message_json.get('nick'), old_nick=user
                    )
                    if not success:
                        logger.warning(
                            'Failed to set nick %s for %s. Reason %s',
                            message_json.get('nick'),
                            user,
                            return_body['message'],
                        )
                        await current_websocket.send_json(return_body)
                    else:
                        logger.info('%s: %s is now known as %s', room, user, message_json.get('nick'))
                        await current_websocket.send_json(return_body)
                        await broadcast(
                            app=request.app,
                            room=room,
                            message={
                                'action': 'nick_changed',
                                'room': room,
                                'from_user': user,
                                'to_user': message_json.get('nick'),
                            },
                            ignore_user=message_json.get('nick'),
                        )  # Customized return body to the user is sent, so we ignore it.
                        user = message_json.get('nick')

                elif action == 'join_room':
                    return_body, success = await change_room(
                        app=request.app, new_room=message_json.get('room'), old_room=room, nick=user
                    )
                    if not success:
                        logger.info(
                            '%s: Unable to change room for %s to %s, reason: %s',
                            room,
                            user,
                            message_json.get('room'),
                            return_body['message'],
                        )
                        await current_websocket.send_json(return_body)
                    else:
                        logger.info('%s: User %s joined the room', user, message_json.get('room'))
                        await broadcast(
                            app=request.app, room=room, message={'action': 'left', 'room': room, 'user': user}
                        )
                        await broadcast(
                            app=request.app,
                            room=message_json.get('room'),
                            message={'action': 'joined', 'room': room, 'user': user},
                            ignore_user=user,
                        )
                        room = message_json.get('room')

                elif action == 'user_list':
                    logger.info('%s: %s requested user list', room, user)
                    user_list = await retrieve_users(app=request.app, room=message_json['room'])
                    await current_websocket.send_json(user_list)

                elif action == 'chat_message':
                    logger.info('%s: Message: %s', room, message_json.get('message'))
                    await current_websocket.send_json(
                        {'action': 'chat_message', 'success': True, 'message': message_json.get('message')}
                    )
                    await broadcast(
                        app=request.app,
                        room=room,
                        message={'action': 'chat_message', 'message': message_json.get('message'), 'user': user},
                        ignore_user=user,
                    )
    if current_websocket.closed:
        await broadcast(app=request.app, room=room, message={'action': 'left', 'room': room, 'user': user})
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
