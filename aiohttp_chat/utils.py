import logging
from typing import Dict, List, Tuple, Union

from aiohttp import web

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def change_nick(
    app: web.Application, room: str, new_nick: str, old_nick: str
) -> Tuple[Dict[str, Union[str, bool]], bool]:
    """
    Takes a user and changes it's nickname.
    :param app: Application
    :param room: Room the user is in
    :param new_nick: New nick
    :param old_nick: Old nick
    :return: A tuple that contains the dict to be returned to the end user and whether it was successful or not.
    """
    if not isinstance(new_nick, str) or not 3 <= len(new_nick) <= 20:
        return (
            {'action': 'set_nick', 'success': False, 'message': 'Name must be a string and between 3-20 chars.'},
            False,
        )
    if new_nick in app['websockets'][room].keys():
        return (
            {'action': 'set_nick', 'success': False, 'message': 'Name already in use.'},
            False,
        )
    else:
        app['websockets'][room][new_nick] = app['websockets'][room].pop(old_nick)
        return {'action': 'set_nick', 'success': True, 'message': ''}, True


async def change_room(
    app: web.Application, new_room: str, old_room: str, nick: str
) -> Tuple[Dict[str, Union[str, bool]], bool]:
    """
    Takes a user and changes it's connected room.
    :param app: Application
    :param new_room: New room name
    :param old_room: Old room name
    :return: A tuple that contains the dict to return to the end user, as well as 
    """
    if not isinstance(new_room, str) or not 3 <= len(new_room) <= 20:
        return (
            {'action': 'join_room', 'success': False, 'message': 'Room name must be a string and between 3-20 chars.'},
            False,
        )
    if nick in app['websockets'][new_room].keys():
        return (
            {'action': 'join_room', 'success': False, 'message': 'Name already in use in this room.'},
            False,
        )
    app['websockets'][new_room][nick] = app['websockets'][old_room].pop(nick)
    return {'action': 'join_room', 'success': True, 'message': ''}, True


async def retrieve_users(app: web.Application, room: str) -> Dict[str, Union[str, bool, List[str]]]:
    """
    Takes a room and returns it's users
    :param app: Application
    :param room: Room name
    :return: JSON to return to the user
    """
    return {'action': 'user_list', 'success': True, 'room': room, 'users': list(app['websockets'][room].keys())}


async def broadcast(app: web.Application, room: str, message: dict, ignore_user: str = None) -> None:
    """
    Broadcasts a message to every user in a room. Can specify a user to ignore. 

    :param app: Application. From a request, pass `request.app`
    :param room: Room name
    :param message: What to broadcast
    :param ignore_user: Skip broadcast to this user (used for e.g. chat messages)
    :return: None
    """
    for user, ws in app['websockets'][room].items():
        if ignore_user and user == ignore_user:
            pass
        else:
            logger.debug('> Sending message %s to %s', message, user)
            await ws.send_json(message)
