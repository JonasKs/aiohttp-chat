[![Example Project](https://img.shields.io/badge/project%20type-example%20code-009900.svg)](https://github.com/JonasKs/aiohttp-chat/)
[![Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

# aiohttp-chat
This project was created in order to learn more about aiohttp and asyncio, aimed to tackle the following tasks:
- Use WebSockets to subscribe to data with `aiohttp`
- Create a client that has multiple functions running async to achieve the following tasks:
  - Constantly read messages from the WebSocket
  - Send messages or have a scheduled refresh task
  - Gracefully shut down all tasks when one task fails or a websocket connection is closed
- Create a server that is very simplified and minimalistic, but supports chat rooms with `aiohttp`. 


## Installation
Install the environment and requirements:
```bash
poetry install
```
(Alternatively use `pip install aiohttp[speedups]` and `pip install aioconsole` in your own environment)

## Simple echo-example
[`client_echo_example.py`](aiohttp_chat/client_echo_example.py) is an example of a clean, simple client that:
* Establishes a connection to the websocket server
* Create two tasks:
    * Infinite loop that sends messages to the server every 15 second
    * Print every incoming message (Messages returned from the echo server)
* Properly shut down if one task raises an exception or is completed

The server is mixed together in `server.py`, but the `ws_echo`-function is the view that is used.  
For more information about the server and how it works, please look at the documentation for [#server](#Server)

## Chat
The chat is a bit more complicated than the echo example, and requires one to know the server API in order to 
completely understand it. For an example on how to write your own client, see [#Usage](#Usage)

#### Input/Response API
Note that you will *not* receive the broadcast message about your changes, only your confirmation or error.

**Change Nick**:
* Input: `{'action': 'set_nick', 'nick': '<my nickname>'}`
* Fail: `{'action': 'set_nick', 'success': False, 'message': 'Nickname is already in use'}`
* OK: `{'action': 'set_nick', 'success': True, 'message': ''}`


**Join a room**:
* Input: `{'action': 'join_room', 'room': '<room name>'}`
* Fail: `{'action': 'join_room', 'success': False, 'message': 'Name already in use in this room.'}`
* OK: `{'action': 'join_room', 'success': True, 'message': ''}`

**Send a message**:
* Input: `{'action': 'chat_message', 'message': '<my message>'}`
* OK: `{'action': 'chat_message', 'success': True, 'message': '<chat_message>'}`

**Room user list**:
* Input: `{'action': 'user_list', 'room': '<room_name>'}`
* OK:`{'action': 'user_list', 'success': True, 'room': '<room_name>', 'users': ['<user1>', '<user2>']}`


#### Broadcast messages
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


#### Usage
This is intended to get you started writing your own client.  
For a short list of the API see [`API Simplified`](#Input/Response-API)


1) Connect via `ws://0.0.0.0:8080/chat`. In `aiohttp` this can be done like this:  
```python
from aiohttp import ClientSession

async with ClientSession() as session:
    async with session.ws_connect('ws://0.0.0.0:8080/chat', ssl=False) as ws:
        # ...
```
See [`client_echo_example.py`](aiohttp_chat/client.py) for an example.

2) Set a nick name. Your nick will be a random nickname by default. (E.g. `User1234`).  
   This can be called multiple times to change your nick name.
   **Usage**:
    - Change nick json body:
        - `{'action': 'set_nick', 'nick': '<my nickname>'}`
    - If nickname is rejected, you will get an error message:
        - `{'action': 'set_nick', 'success': False, 'message': 'Nickname is already in use'}`
    - If nickname is approved, no error will be present:
        - `{'action': 'set_nick', 'success': True, 'message': ''}`  
  
    **Example code**:
    ```python
    from aiohttp import ClientSession
    
    async with ClientSession() as session:
        async with session.ws_connect('ws://0.0.0.0:8080/chat', ssl=False) as ws:
            await ws.send_json({'action': 'set_nick', 'nick': 'Jonas'})
    ```

3) Join a chat room. By default you join the `default` chat room.  
   This can be called multiple times to change room.
   **Usage**:  
    - Change room json body:
        - `{'action': 'join_room', 'room': '<room name>'}`
    - If everything is OK, no error will be present:
        - `{'action': 'join_room', 'success': True, 'message': ''}`
        
    **Example code**:
    ```python
    await ws.send_json({'action': 'join_room', 'room': 'test'})
    ```

4) Chat!  
   NB: The body returned on a sent message is not the same as a message received from another person.  
   **Usage**:
    - Done by sending a body like this:
         - `{'action': 'chat_message', 'message': '<my message>'}`
    - If everything is OK, this message will be returned:
         - `{'action': 'chat_message', 'success': True, 'message': '<chat_message>'}`  
         
    **Example code**:
    ```python
    await websocket.send_json({'action': 'chat_message', 'message': 'Hello world!'})
    ```

5) Ask for user list of a room  
   **Usage**:
    - Ask for user list body:
        - `{'action': 'user_list', 'room': '<room_name>'}`
    - Body retrieved:
        - `{'action': 'user_list', 'success': True, 'room': '<room_name>', 'users': ['<user1>', '<user2>']}`
        
    **Example code**:
    ```python
    await ws.send_json({'action': 'user_list', 'room': 'test'})
    ```
    
6) Disconnect
    - With aiohttp close the connection normally:
         websocket.close()
    - OR Send a [close code](https://developer.mozilla.org/en-US/docs/Web/API/CloseEvent)

All messages on your actions will return with a `'success': True/False`. 

### Full feature client
The [`client.py`](aiohttp_chat/client.py) utilizes all these APIs. It has also included a way to interactively chat with other clients
through the terminal using `aioconsole`. How ever, it's not very clean to use, as it's cluttered with log messages. 
To get rid of the clutter, simply edit the logger to be `WARNING` instead. 


### Server explanation
To spawn a server in `aiohttp` one simply defines an application, what should happen on shut down and add routes to it.
In [`server.py`](aiohttp_chat/server.py) we have added two routes:
```python
app = web.Application()
# ...
app.add_routes([web.get('/echo', handler=ws_echo)])  # `ws_echo` handles this request.
app.add_routes([web.get('/chat', handler=ws_chat)])  # `ws_chat` handles this request
# ...
```
This exposes two endpoints:
```bash
ws://0.0.0.0:8080/echo
ws://0.0.0.0:8080/chat
```

We'll focus on the `echo` endpoint in this section for simplicity, and then later add some of the concepts
needed in order to add broadcasting to all clients later. 

I will refer to the `ws_echo(request: Request)` function as the `view`. The view should always take one input parameter,
which is the `request`. The `request` will contain information about the request, as well as the `app` that we created
before.  
First, we create an empty `WebSocketResponse()`, and check that the request that hit the view is an actual websocket 
request (Remember, full code with doc strings can be found in [`server.py`](aiohttp_chat/server.py)):
```python
async def ws_echo(request: Request) -> web.WebSocketResponse:
    websocket = web.WebSocketResponse()  # Create a websocket response object
    # Check that everything is OK, if it's not, close the connection.
    ready = websocket.can_prepare(request=request)
    if not ready:
        await websocket.close(code=WSCloseCode.PROTOCOL_ERROR)

    await websocket.prepare(request)  # Load it with the request object
    # ...
```
If `can_prepare` returns True, we know that `prepare` will not fail. If `prepare` returns `False`, 
we simply close the connection.

In order to echo the message, we write a simple `async for`-loop, where we check that the incoming message is a 
websocket message (this step can be skipped, but helps PyCharm understand the object type we're dealing with), 
and then that the type is of `WSMsgType.text`. We can then load it with `.json()` and read data as normal.  
In order to send a message to the client, we use `send_json()`. This must be awaited, as `send_json()` is a coroutine.

```python
    # ...
    await websocket.prepare(request)  # Load it with the request object

    async for message in websocket:  # For each message in the websocket connection
        if isinstance(message, WSMessage):
            if message.type == web.WSMsgType.text:  # If it's a text, process it as a message
                message_json = message.json()
                logger.info('> Received: %s', message_json)
                echo = {'echo': message_json}
                await websocket.send_json(echo)  # Send back the message
                logger.info('< Sent: %s', echo)
            # WebSocketResponse handles close, ping, pong etc. by default
    return websocket
```

Please note that `async for` is forever living and could also be written like this:
```python
    message = websocket.receive()
    for msg in message:
        # ...
```

So the server is actually quite simple. The only thing needed in addition to broadcast to other WebSockets is to
add a `websocket` dictionary to the `app`. I did this like this:
```python
app = web.Application()
app['websockets'] = defaultdict(dict)
```

I use a `defaultdict` to not get a `KeyError` when attempting to access an item that does not exist. It will instead 
create it. This is handy since I opted for this structure, where the room name is `testroom` and the username is `Jonas` 
and `Hotfix`:
```python
{ 
  'websockets': {
    'testroom': {
      'Jonas': '<Websocket connection object>',
      'Hotfix': '<Websocket connection object>'
    }
  }
}
```
To store a connection to this object, I simply add it like this:
```python
request.app['websockets'][room][user] = websocket
```
As we can see, I use the `.app['websockets']` on the `request` object. This means my views are able to see all other
connections that is currently active in the `testroom`. In other words, we can do this:
```python
for ws in request.app['websockets']['testroom'].values():
    await ws.send_json({'hello': 'world'})
```

To get less clutter I've created a few helper functions in [`utils.py`](aiohttp_chat/utils.py)
