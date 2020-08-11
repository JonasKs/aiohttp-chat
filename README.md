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

## Usage
### Server
