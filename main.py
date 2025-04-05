import discord
from discord.ext import commands
import asyncio
import yt_dlp
from collections import deque

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix=lambda bot, msg: '&' if msg is None else msg.content.lower()[0], intents=intents)

music_queues = {}
voice_clients = {}

# yt-dlp 
ydl_opts = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'auto',
    'outtmpl': 'song.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

async def play_next(ctx, guild_id):
    """播放下一首"""
    if music_queues.get(guild_id):
        next_url, title = music_queues[guild_id].popleft()
        await ctx.send(f"🎵 現在播放：{title}")

        # 提前抓取URL
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(next_url, download=False)
            audio_url = info['url']

        vc = voice_clients[guild_id]

        # 非阻塞
        await asyncio.create_task(play_music(vc, audio_url, guild_id, ctx))

async def play_music(vc, audio_url, guild_id, ctx):
    """異步函數"""
    vc.play(
        discord.FFmpegPCMAudio(audio_url, executable="ffmpeg"),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), bot.loop)
    )

@bot.command()
async def p(ctx, *, url: str = None):
    """播放音樂"""
    if not url:
        await ctx.send("❗請輸入 YouTube 連結或搜尋關鍵字！")
        return

    if not ctx.author.voice:
        await ctx.send("❗你需要先加入語音頻道！")
        return

    voice_channel = ctx.author.voice.channel
    guild_id = ctx.guild.id

    vc = ctx.voice_client
    if not vc:
        vc = await voice_channel.connect()
        voice_clients[guild_id] = vc

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            
            info = ydl.extract_info(url, download=False)
            if 'entries' in info:
                info = info['entries'][0]  # 搜尋結果
            audio_url = info['url']
            title = info.get('title', '未知標題')
        except Exception as e:
            await ctx.send(f"❌ 抓取影片失敗：{str(e)}")
            return

    if guild_id not in music_queues:
        music_queues[guild_id] = deque()

    # 開始播放音樂
    if not vc.is_playing():
        await ctx.send(f"🎶 現在播放：{title}")
        await play_music(vc, audio_url, guild_id, ctx)
    else:
        music_queues[guild_id].append((url, title))
        await ctx.send(f"➕ 已加入隊列：{title}")

@bot.command()
async def skip(ctx):
    """跳過"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await ctx.send("⏭️ 已跳過歌曲。")
    else:
        await ctx.send("❌ 沒有播放中的音樂。")

@bot.command()
async def pause(ctx):
    """暫停播放"""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        vc.pause()
        await ctx.send("⏸️ 已暫停播放。")
    else:
        await ctx.send("❌ 沒有播放中的音樂。")

@bot.command()
async def resume(ctx):
    """繼續播放"""
    vc = ctx.voice_client
    if vc and vc.is_paused():
        vc.resume()
        await ctx.send("▶️ 已繼續播放。")
    else:
        await ctx.send("❌ 沒有暫停的音樂。")

@bot.command()
async def queue(ctx):
    """顯示隊列"""
    q = music_queues.get(ctx.guild.id)
    if q and len(q) > 0:
        message = "\n".join([f"{i+1}. {title}" for i, (_, title) in enumerate(q)])
        await ctx.send(f"📜 目前隊列：\n{message}")
    else:
        await ctx.send("🎶 播放隊列是空的")
        
@bot.command()
async def leave(ctx):
    """離開"""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        music_queues.pop(ctx.guild.id, None)
        voice_clients.pop(ctx.guild.id, None)
        await ctx.send("👋 已離開語音頻道並清除播放隊列。")
    else:
        await ctx.send("❌ 我不在語音頻道中。")

@bot.event
async def on_ready():
    """啟動"""
    print(f"✅ 機器人已上線：{bot.user}")

bot.run("YOUR_TOKEN")
