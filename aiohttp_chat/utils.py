import logging

from aiohttp.web_request import Request
from typing import List, Dict, Union, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def change_nick(request: Request, new_nick: str, old_nick: str) -> Dict[str, Union[str, bool]]:
    """
    Takes a user and changes it's nickname.
    :param request: Request object
    :param new_nick: New nick
    :param old_nick: Old nick
    :return: A tuple that contains a JSON to return to the user and one to broadcast, containing two elements:
      * JSON to return to the user (either one of these)
        - {'action': 'set_nick', 'success': False, 'message': 'Nickname is already in use'}
        - {'action': 'set_nick', 'success': True, 'message': ''}
      * JSON to broadcast to the current room
        - {'action': 'nick_changed', 'room': room, 'from_user': user, 'to_user': user}
    """
    pass
    

async def change_room(request: Request, room: str) -> Tuple[Dict[str, Union[str, bool]]]:
    """
    Takes a user and changes it's connected room.
    :param request: Request object
    :param room: Room name
    :return: A tuple that contains three elements:
       * JSON to return to the user
         - {'action': 'join_room', 'success': True, 'message': ''})
       * JSON to broadcast to the current room
         - {'action': 'left', 'room': room, 'user': user}
       * JSON to broadcast to the new room
         - {'action': 'joined', 'room': room, 'user': user}
    """
    pass
    

async def retrieve_users(request: Request, room: str) -> Dict[str, Union[str, bool, List[str]]]:
    """
    Takes a room and returns it's users
    :param request: Request object
    :param room: Room name
    :return: JSON to return to the user
      * {'action': 'user_list', 'success': True, 'room': '<room_name>', 'users': ['<user1>', '<user2>']}
    """
    pass
