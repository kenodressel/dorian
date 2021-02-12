#!/usr/bin/env python3
import discord
import re
import logging
import asyncio
from os import environ
from random import randint
import operator
import pickle
import json

logging.basicConfig(level=logging.INFO)

client = discord.Client()
discord.opus.load_opus
roll_command = "!croll"
vote_command = "!cvote"
stats_command = "!cstats"

FirstConnect = True
LastPlayingIndex = -1
PlayingQuotes = {
    1: "with dice",
    2: "second item"
}

votes = {}
empty_vote = {
    's': 0,
    'f': 0,
    'hs': 0,
    'es': 0,
    'cf': 0,
    'cs': 0,
}

COL_CRIT_SUCCESS = 0xFFFFFF
COL_EXTR_SUCCESS = 0xf1c40f
COL_HARD_SUCCESS = 0x2ecc71
COL_NORM_SUCCESS = 0x2e71cc
COL_NORM_FAILURE = 0xe74c3c
COL_CRIT_FAILURE = 0x992d22


class DiceResult:
    def __init__(self):
        self.title = ""
        self.desc = ""
        self.colour = COL_NORM_SUCCESS
        self.image = ""
        self.short = ""


def roll_die(min=1, max=10):
    result = randint(min, max)
    return result


def roll_the_dice(bonus_die, penalty_die, threshold, author=None):
    if author and author in votes:
        # any above 0?
        sum_votes = sum(votes[author].values())
        if sum_votes == 0:
            return resolve_die(bonus_die, penalty_die, threshold)

        # force next roll
        next_roll = max(votes[author].items(), key=operator.itemgetter(1))[0]
        result = resolve_die(bonus_die, penalty_die, threshold)
        while result.short != next_roll:
            result = resolve_die(bonus_die, penalty_die, threshold)
        votes[author] = empty_vote.copy()
        return result
    return resolve_die(bonus_die, penalty_die, threshold)


def resolve_die(bonus_die, penalty_die, threshold):
    ten_result_pool = [roll_die(0, 9)]

    ten_result = min(ten_result_pool)
    one_result = roll_die()

    if bonus_die > 0 and penalty_die > 0:
        return "Can't chain bonus and penalty dice"

    for i in range(bonus_die):
        ten_result_pool.append(roll_die(0, 9))
        ten_result = min(ten_result_pool)

    for i in range(penalty_die):
        ten_result_pool.append(roll_die(0, 9))
        ten_result = max(ten_result_pool)

    combined_result = (ten_result * 10) + one_result

    if bonus_die > 0 or penalty_die > 0:
        desc = '(' + '|'.join([str(i * 10) for i in ten_result_pool]) + ') ' + str(ten_result * 10) + ' + ' + str(
            one_result) + ' = ' + str(combined_result)
    else:
        desc = str(ten_result * 10) + ' + ' + str(one_result) + ' = ' + str(combined_result)

    if threshold:
        ret = DiceResult()
        if combined_result == 1:
            ret.title = "Critical Success!"
            ret.colour = COL_CRIT_SUCCESS
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779042867138134066/nat20Smaller.png"
            ret.short = "cs"
        elif combined_result <= 5 and threshold > 50:
            ret.title = "Critical Success!"
            ret.colour = COL_CRIT_SUCCESS
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779042867138134066/nat20Smaller.png"
            ret.short = "cs"
        elif combined_result == 100:
            ret.title = "Critical Failure!"
            ret.colour = COL_CRIT_FAILURE
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779042861928022047/nat1smaller.png"
            ret.short = "f"
        elif combined_result > 95 and threshold <= 50:
            ret.title = "Critical Failure!"
            ret.colour = COL_CRIT_FAILURE
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779042861928022047/nat1smaller.png"
            ret.short = "cf"
        elif combined_result <= threshold / 5:
            ret.title = "Extreme Success!"
            ret.colour = COL_EXTR_SUCCESS
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779041383959756860/yaythulhuSmaller.png"
            ret.short = "es"
        elif combined_result <= threshold / 2:
            ret.title = "Hard Success!"
            ret.colour = COL_HARD_SUCCESS
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779041377534869533/babythulhuSmaller.png"
            ret.short = "hs"
        elif combined_result <= threshold:
            ret.title = "Success!"
            ret.colour = COL_NORM_SUCCESS
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779043134020780062/cutethulhuSmaller.png"
            ret.short = "s"
        else:
            ret.title = "Failure"
            ret.colour = COL_NORM_FAILURE
            ret.image = "https://cdn.discordapp.com/attachments/778900221199253505/779043270948421662/deniedSmaller.png"
            ret.short = "f"

        # ret.title = ret.title + str(CombinedResult)
        ret.desc = desc
        return ret
    else:
        ret = desc
        return ret


def parse_roll(dice_string, author=None):
    fail = """
Unable to parse dice command. Usage:
```
!croll [[die type][number=1]]...[[threshold][score]]

Die Types:
    b: Bonus dice (can't be chained with Penalty)
    p: Penalty dice (can't be chained with Bonus)
    t: threshold to determine success/fail. Score is required if a threshold is set.

Examples:
    !croll
    36

    !croll t60
    Hard Success: 24

    !croll b
    70/30 + 5 = 35

    !croll t70p2
    Failure: 0/50/70 + 4 = 74
```
"""

    # check for the case where ppl forget to write t
    # handle case where there is no bpt
    if dice_string.isnumeric():
        return roll_the_dice(0, 0, int(dice_string), author)

    dice = [x for x in re.split('([bpt](?:\d+)?)', dice_string) if x]

    if len(dice) > 1 and 'b' in dice_string and 'p' in dice_string:
        return "Can't chain bonus and penalty dice"

    bonus_die = 0
    penalty_die = 0
    threshold = False

    for die in dice:

        default_num = False
        # match string
        die_string = re.search('([bpt])(\d+)?', die)
        # for b and p, add dice number 1
        if not die_string:
            default_num = True
            die = die + "1"

        # try to match it again
        die_string = re.search('([bpt])(\d+)?', die)
        # still didn't work
        if not die_string:
            return fail

        # get the matched groups
        die_groups = die_string.groups()
        # too many ?
        if len(die_groups) != 2:
            return fail

        # parse number of dice
        try:
            num = int(die_groups[1])
        except:
            default_num = True
            num = 1

        # get die code (b p t)
        die_code = die_groups[0]

        # too long of a dice code?
        if len(die_code) > 1:
            return fail

        if die_code == 'b':
            bonus_die = num

        if die_code == 'p':
            penalty_die = num

        if die_code == 't':
            if default_num:
                return "threshold requires a value!"
            else:
                threshold = num

    return roll_the_dice(bonus_die, penalty_die, threshold, author)


def parse_vote(vote_string):
    fail = "Use !cvote user cs|es|hs|s|f|cf"

    vote_regex = re.search('^(\w+#\d+)\s(\w+)$', vote_string)
    if not vote_regex:
        return fail

    vote_groups = vote_regex.groups()
    if not vote_groups:
        return fail

    user = vote_groups[0]
    vote = vote_groups[1]
    if user not in votes:
        votes[user] = empty_vote.copy()

    if vote not in votes[user]:
        return fail

    votes[user][vote] += 1
    return "vote accepted"


async def cycle_playing():
    global LastPlayingIndex
    playing = PlayingQuotes[randint(1, len(PlayingQuotes))]
    while playing == LastPlayingIndex:
        playing = PlayingQuotes[randint(1, len(PlayingQuotes))]
    LastPlayingIndex = playing
    # await client.change_presence(game=discord.Game(name=playing))
    await asyncio.sleep(randint(60, 600))


def update_stats(result, user):
    try:
        with open('data/stats_' + user.replace('#', '_') + '.json', 'r') as json_file:
            user_stats = json.load(json_file)
    except FileNotFoundError:
        user_stats = empty_vote.copy()

    user_stats[result.short] += 1

    with open('data/stats_' + user.replace('#', '_') + '.json', 'w') as outfile:
        json.dump(user_stats, outfile)


def get_stats(user=None):
    try:
        with open('data/stats_' + user.replace('#', '_') + '.json', 'r') as json_file:
            user_stats = json.load(json_file)
    except FileNotFoundError:
        user_stats = empty_vote.copy()

    return json.dumps(user_stats, indent=4)


@client.event
async def on_ready():
    global FirstConnect
    print("Dorian connected")
    if FirstConnect:
        FirstConnect = False
        # while True:
        # await asyncio.ensure_future(cyclePlaying())


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if environ['CHANNEL_NAME'] and message.guild and message.channel.name != environ['CHANNEL_NAME']:
        return

    author = str(message.author).replace(' ', '')

    if message.content.startswith(roll_command):
        result = parse_roll(message.content[len(roll_command) + 1:], author)
        if isinstance(result, str):
            await message.channel.send(result)
        else:
            em = discord.Embed(title=result.title, description=result.desc, colour=result.colour)
            em.set_footer(text=result.desc)
            em.set_image(url=result.image)
            em.description = None
            update_stats(result, author)
            await message.channel.send(message.author.mention, embed=em)

    if message.content.startswith(stats_command):
        result = get_stats(author)
        await message.channel.send(result)

    if message.content.startswith(vote_command) and not message.guild:
        result = parse_vote(message.content[len(vote_command) + 1:])
        if isinstance(result, str):
            await message.channel.send(result)


token = environ['DORIAN_TOKEN']
client.run(token)
