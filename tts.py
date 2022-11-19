from asyncio import ensure_future, new_event_loop, set_event_loop, sleep, wait
from json import loads
from os import system
from subprocess import PIPE, STDOUT, Popen

from aiohttp import ClientSession, ClientTimeout, TCPConnector
from khl import Bot, Message
from khl._types import MessageTypes

from voiceAPI import Voice

with open("tts_config.json", 'r') as f:
    _ = loads(f.read())
    voiceid = _['voiceid']
    token = _['token']
    lang = _['lang']

eventloop = new_event_loop()
set_event_loop(eventloop)

tts_bot = Bot(token=token)
voice = Voice(token=token)
middle_layer_process = None


def play():
    return Popen(
        'ffmpeg -re -nostats -i "ttss.mp3" -acodec libopus -ab 128k -f mpegts zmq:tcp://127.0.0.1:1234',
        shell=True,
        encoding='utf-8')


async def text_to_sound(t: str):
    url = f"https://tts.youdao.com/fanyivoice?word={t}&le={lang}&keyfrom=speaker-target"
    async with ClientSession(connector=TCPConnector(ssl=False)) as s:
        async with s.get(url, timeout=ClientTimeout(total=10)) as r:
            with open("tts.mp3", 'wb') as f:
                while True:
                    chunk = await r.content.read()
                    if not chunk:
                        break
                    f.write(chunk)
    system('ffmpeg -f concat -i "met.txt" -y ttss.mp3')


async def start(voice: Voice, voiceid: str):
    await wait([voice_Engine(voice, voiceid), voice.handler()])


async def voice_Engine(voice: Voice, voiceid: str):
    global middle_layer_process
    voice.channel_id = voiceid
    while True:
        if len(voice.rtp_url) != 0:
            comm = f"ffmpeg -re -loglevel debug -nostats -stream_loop -1 -i zmq:tcp://127.0.0.1:1234 -map 0:a:0 -acodec libopus -ab 128k -filter:a volume=0.15 -ac 2 -ar 48000 -f tee [select=a:f=rtp:ssrc={voice.ssrc}:payload_type=100]{voice.rtp_url}"
            middle_layer_process = Popen(comm, shell=True, encoding='utf-8')
            break
        await sleep(0.1)


@tts_bot.on_message(MessageTypes.AUDIO, MessageTypes.CARD, MessageTypes.FILE,
                    MessageTypes.IMG, MessageTypes.SYS, MessageTypes.VIDEO)
async def listener(msg: Message):
    print(msg.content)
    await text_to_sound(msg.content)
    play()


ensure_future(tts_bot.start(), loop=eventloop)
ensure_future(start(voice, voiceid), loop=eventloop)
eventloop.run_forever()
