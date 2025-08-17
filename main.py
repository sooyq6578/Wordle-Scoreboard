import discord
import re
from discord.ext import commands
import os
import json
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv, set_key
# from keep_alive import keep_alive

intent = discord.Intents.all()
bot = commands.Bot(command_prefix='&', help_command=None, intents=intent)
client = discord.Client()
guild = None
chan = None
chat_lounge = None
with open('scores.json', 'r') as file:
    data = json.load(file)

load_dotenv()
# print(os.environ)
            
channel_id = os.environ["CHANNEL_ID"]

@bot.event
async def on_ready():
    global guild, chan, chat_lounge
    print('We have logged in as {0.user}'.format(bot))
    guild = bot.guilds[0]
    chan = guild.get_channel(int(channel_id))
    chat_lounge = guild.get_channel(914110047859118080)

    if not data:
        data['date'] = ""
        data['scoreboard'] = {}
        data["scores"] = {}
        data["updated"] = {}

async def parse_message(msg):
    user_scores = {}

    # Loop through each line to extract score and users
    for line in msg.splitlines():
        # Match score and everything after (even with emoji or prefix)
        match = re.search(r'(\d+)/6:\s+(.*)', line)
        if match:
            score = match.group(1)
            users = re.findall(r'\w+', match.group(2))
            for user in users:
                user_scores[user] = 7 if score == "X" else int(score)

    return user_scores

async def update_scoreboard(data, scores):
    for k in scores.keys():
        try:
            # pass all manually updated
            if data["updated"][k] != data["date"]:
                data['scoreboard'][k] = data['scoreboard'][k] + scores[k]
            else:
                data['scoreboard'][k] = data['scoreboard'][k]
        except KeyError:
            data['scoreboard'][k] = scores[k]

async def print_scoreboard(data):
    score_string = ""
    r_data = dict(sorted(data["scoreboard"].items(), key=lambda item: item[1], reverse=True))
    count = 1

    for k in r_data.keys():
        score_string += "{}. {} - {}\n".format(count, guild.get_member(int(k)).mention, r_data[k])
        count += 1

    return """
    {} {} is:
    {}
    """.format("Scoreboard as of", data["date"], score_string)

async def print_scores(data, type, today_date):
    y_score_string = ""
    t_score_string = ""
    r_data = {
        k: (7 - v) if type == "tries" else v
        for k, v in sorted(data["scores"].items(), key=lambda item: item[1], reverse=True)
    }
    y_count = 1
    t_count = 1

    for k in r_data.keys():
        if data["updated"][k] != today_date:
            y_score_string += "{}. {} - {}\n".format(y_count, guild.get_member(int(k)).mention, r_data[k])
            y_count += 1
        else:
            t_score_string += "{}. {} - {}\n".format(t_count, guild.get_member(int(k)).mention, r_data[k])
            t_count += 1

    y_string = "{} {} is:\n{}".format(
    "Scores for" if type == "scores" else "Tries for",
    data["date"],
    y_score_string
    )

    t_string = "{} {} is:\n{}".format(
        "Scores for" if type == "scores" else "Tries for",
        today_date,
        t_score_string
    )

    return f"{y_string}\n\n{t_string}"


async def update_scores(data, scores):
    # skip those already manually updated for today
    d = {}
    for k, v in scores.items():
        try:
            if data["scores"][k] and data["updated"][k] != data["date"]:
                d[k] = 7 - v
            else:
                d[k] = data["scores"][k]
        except KeyError:
                d[k] = 7 - v
    return d

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    message_content = message.content
    message_author = message.author
    message_channel = message.channel

    if str(message_author) == "Wordle#2092" or str(message_author) == "Wordle#0" or str(message_author) == "Wordle":
        scores = await parse_message(message_content)
        if not scores:
            return
        else:
            global data
            message_date = message.created_at.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
            date = message_date - timedelta(days=1)
            data['date'] = str(date.date())
            data["scores"] = await update_scores(data, scores)
            await update_scoreboard(data, data["scores"])

            # set last updated for user
            for k in data["scores"].keys():
                data["updated"][k] = str(date.date())

            with open('scores.json', 'w') as file:
                json.dump(data, file, indent=4)
            await message_channel.send(await print_scoreboard(data))

@bot.command(name="set")
async def set(ctx, message):
    global data
    try:
        tries = 7 if message == "X" else int(message)
        user_id = str(ctx.author.id)
        date = str(ctx.message.created_at.astimezone(ZoneInfo("Asia/Kuala_Lumpur")).date())

        # check if updated for today
        try:
            if data["updated"][user_id] != date:
                # manually update score
                data['scores'][user_id] = 7 - tries
                data["updated"][user_id] = date
            else:
                await ctx.channel.send("Score update failed for {}. Score has been updated today.".format(ctx.author.mention))
                return
        except KeyError:
            data['scores'][user_id] = 7 - tries
            data["updated"][user_id] = date

        await ctx.channel.send("Score updated for {}".format(ctx.author.mention))
    except Exception:
        await ctx.channel.send("Please enter a number between 1 to 6 for your number of tries, or X if failed.")

@bot.command(name="scoreboard")
async def scoreboard(ctx):
    await ctx.channel.send(await print_scoreboard(data))

@bot.command(name="score")
async def print_score(ctx):
    today_date = str(ctx.message.created_at.astimezone(ZoneInfo("Asia/Kuala_Lumpur")).date())
    await ctx.channel.send(await print_scores(data, "scores", today_date))

@bot.command(name="tries")
async def print_tries(ctx):
    today_date = str(ctx.message.created_at.astimezone(ZoneInfo("Asia/Kuala_Lumpur")).date())
    await ctx.channel.send(await print_scores(data, "tries", today_date))

if __name__ == "__main__":
    # keep_alive()
    bot.run(os.environ['TOKEN'])