import json
import math
import os
import redis
import requests
import schedule
import time
import tweepy

'''
Environment Variables: USER_ID, LEAGUE_ID, REDIS_PASS, CONSUMER_KEY, CONSUMER_SECRET, KEY, 
                        SECRET, NORTHEAST, SOUTHEAST, MIDWEST, WEST
'''
########## OS Environment Variables ###########

# Sleeper.app Credentials
user = os.getenv("USER_ID")
league = os.getenv("NOTHEAST")

# Twitter Developer Account Credentials
consumer_key = os.getenv("CONSUMER_KEY")
consumer_secret = os.getenv("CONSUMER_SECRET")
key = os.getenv("KEY")
secret = os.getenv("SECRET")

########## Global Variables ###########

# Twitter Developer Account Settings
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(key, secret)
auth.secure = True
api = tweepy.API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

# Set the year since the season will span across multiple years
# I am not using this but this is for if I do decide to later on
year = str(time.ctime())[-4:]

# URL endpoints for sleeper.app
BASE_URL = "https://api.sleeper.app"

USER = f"{BASE_URL}/v1/user/{user}"

ALL_LEAGUES = f"{BASE_URL}/v1/user/{user}/leagues/nfl/{year}"

SPECIFIC_LEAGUE = f"{BASE_URL}/v1/league/{league}"

LEAGUE_ROSTERS = f"{BASE_URL}/v1/league/{league}/rosters"

ROSTER = f"{BASE_URL}/v1/league/{league}/rosters"

USER_IN_LEAGUE = f"{BASE_URL}/v1/league/{league}/users"

HEADERS = {'USER:': user, 'LEAGUE': league}


########## Main Functions ###########


def weekly_scores():
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    # Let's try to get the matchups and then see who won/lost each matchup
    num_matchups, active_rosters = set_matchups(client)
    # print(active_rosters)
    get_matchups(client, active_rosters)
    tweet_scores(client, num_matchups)


def set_standings():
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    USERS_LIST = set_user_list()

    # I think I want to use a dictionary here with the user and their wins
    standings_dict = {}
    most_wins = 0
    leaders = 0
    for user in USERS_LIST:
        wins = client.hget(str(user), 'wins')
        if wins:
            standings_dict[user] = int(wins)
            if int(wins) > most_wins:
                most_wins = int(wins)
                leaders = 1
            elif int(wins) == most_wins:
                most_wins = int(wins)
                leaders += 1
    # Now that I have a dictionary with each user: wins => let's order the dictionary with lambda expression
    standings_dict = {k: v for k, v in sorted(
        standings_dict.items(), key=lambda item: item[1], reverse=True)}
    # Initialize combined status var
    combined_status = ""
    i = 0
    repeat = 1
    last = 0
    for key, value in standings_dict.items():
        team_name = get_team_name(key)
        losses = int(client.hget(key, "losses"))
        i += 1
        if i <= leaders and leaders == 1:
            status = f"1st: {team_name}:     {value}-{losses}"
        elif i <= leaders and leaders > 1:
            status = f"1st: {team_name}:     {value}-{losses}"
        elif (i - 2) % 10 == 0 and last > int(value):
            status = f"2nd: {team_name}:     {value}-{losses}"
        elif (i - 2) % 10 == 0 and last > int(value):
            status = f"2nd: {team_name}:     {value}-{losses}"
        elif (i - 3) % 10 == 0 and last > int(value):
            status = f"3rd: {team_name}:     {value}-{losses}"
        elif (i - 3) % 10 == 0 and last == int(value):
            status = f"3rd: {team_name}:     {value}-{losses}"
        elif last > int(value):
            status = f"{i}th: {team_name}:     {value}-{losses}"
            repeat = 1
        else:
            status = f"{i - repeat}th: {team_name}     {value}-{losses}"
            repeat += 1
        last = int(value)
        combined_status = combined_status + status + "\n"
    week = get_week()
    beginning = f"NorthEast - week {week} standings: \n\n"
    combined_status = beginning + combined_status + "\n#BOTS2020"
    num_tweets = math.ceil(len(combined_status) / 274)
    send_tweet(combined_status, 1, num_tweets)


def set_point_leaders():
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    USERS_LIST = set_user_list()

    # I think I want to use a dictionary here with the user and their wins
    standings_dict = {}
    most_wins = 0
    leaders = 0
    for user in USERS_LIST:
        wins = client.hget(str(user), 'fpts')
        if wins:
            standings_dict[user] = int(wins)
            if int(wins) > most_wins:
                most_wins = int(wins)
                leaders = 1
            elif int(wins) == most_wins:
                most_wins = int(wins)
                leaders += 1
    # Now that I have a dictionary with each user: wins ,,, let's order the dictionary
    standings_dict = {k: v for k, v in sorted(
        standings_dict.items(), key=lambda item: item[1], reverse=True)}
    combined_status = ""
    i = 0
    repeat = 1
    last = 0
    teams = []
    for key, value in standings_dict.items():
        team_name = get_team_name(key)
        if team_name in teams:
            continue
        teams.append(team_name)
        i += 1
        if i <= leaders and leaders == 1:
            status = f"1st: {team_name}:     {value}"
        elif i <= leaders and leaders > 1:
            status = f"1st: {team_name}:     {value}"
        elif (i - 2) % 10 == 0 and last > int(value):
            status = f"2nd: {team_name}:     {value}"
        elif (i - 2) % 10 == 0 and last > int(value):
            status = f"2nd: {team_name}:     {value}"
        elif (i - 3) % 10 == 0 and last > int(value):
            status = f"3rd: {team_name}:     {value}"
        elif (i - 3) % 10 == 0 and last == int(value):
            status = f"3rd: {team_name}:     {value}"
        elif last > int(value):
            status = f"{i}th: {team_name}:     {value}"
            repeat = 1
        else:
            status = f"{i - repeat}th: {team_name}     {value}"
            repeat += 1
        last = int(value)
        combined_status = combined_status + status + "\n"
    week = get_week()
    beginning = f"NorthEast - total points through week {week}: \n\n"
    combined_status = beginning + combined_status + "\n#BOTS2020"
    num_tweets = math.ceil(len(combined_status) / 274)
    send_tweet(combined_status, 1, num_tweets)


########## Sleeper API Functions ###########


def get_user():
    r = requests.get(USER)
    return json.loads(r.content)


'''
{
    "username": "sleeperuser",
    "user_id": "12345678",
    "display_name": "SleeperUser",
    "avatar": "cc12ec49965eb7856f84d71cf85306af"
}
'''


def get_specific_league():
    r = requests.get(SPECIFIC_LEAGUE)
    return json.loads(r.content)


'''
{
  "total_rosters": 12,
  "status": "in_season",
  "sport": "nfl",
  "settings": { settings object },
  "season_type": "regular",
  "season": "2018",
  "scoring_settings": { scoring_settings object },
  "roster_positions": [ roster positions array ],
  "previous_league_id": "198946952535085056",
  "name": "Sleeperbot Dynasty",
  "league_id": "289646328504385536",
  "draft_id": "289646328508579840",
  "avatar": "efaefa889ae24046a53265a3c71b8b64"
}
'''


def get_league_rosters():
    r = requests.get(LEAGUE_ROSTERS)
    return json.loads(r.content)


'''
[
    {
        "starters": ["2307", "2257", "4034", "147", "642", "4039", "515", "4149", "DET"],
        "settings": {
            "wins": 5,
            "waiver_position": 7,
            "waiver_budget_used": 0,
            "total_moves": 0,
            "ties": 0,
            "losses": 9,
            "fpts_decimal": 78,
            "fpts_against_decimal": 32,
            "fpts_against": 1670,
            "fpts": 1617
        },
        "roster_id": 1,
        "reserve": [],
        "players": ["1046", "138", "147", "2257", "DET"],
        "owner_id": "188815879448829952",
        "league_id": "206827432160788480"
    },
    ...
]
'''


def get_user_in_league():
    r = requests.get(USER_IN_LEAGUE)
    return json.loads(r.content)


'''
[
    {
        "user_id": "<user_id>",
        "username": "<username>",
        "display_name": "<display_name>",
        "avatar": "1233456789",
        "metadata": {
            "team_name": "Dezpacito"
        },
        "is_owner": true // is commissioner(there can be multiple commissioners)
    },
    ...
]
'''


def get_league_matchups():
    LEAGUE_MATCHUPS = f"{BASE_URL}/v1/league/{league}/matchups/" + \
        str(get_week())
    r = requests.get(LEAGUE_MATCHUPS)
    return json.loads(r.content)


'''
[
  {
    "starters": ["421", "4035", "3242", "2133", "2449", "4531", "2257", "788", "PHI"],
    "roster_id": 1,
    "players": ["1352", "1387", "2118", "2133", "2182", "223", "2319", "2449", "3208", "4035", "421", "4881", "4892", "788", "CLE"],
    "matchup_id": 2
  },
  ...
]
'''

########## Redis Functions ###########


def get_week():
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    # client.set('fantasy_week', '3')
    return int(client.get('fantasy_week'))


def update_week():
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    client.incr("fantasy_week")
    week = int(client.get('fantasy_week'))
    print(f"We are now on week {week} for fantasy football.")


def set_matchups(client):
    matchups = get_league_matchups()  # Return a list of dictionaries
    num_matchups = 0
    roster = ""
    active_rosters = []

    for matchup in matchups:
        for key, value in matchup.items():
            if key == 'roster_id':
                roster = "roster_" + str(value)
                active_rosters.append(roster)
            elif key == 'points':
                if not value:
                    value = "0"
                client.hset(roster, "points", str(int(value)))
            elif key == 'matchup_id':
                if value > num_matchups:
                    num_matchups = value
                client.hset(roster, "matchup", value)
                match = "matchup_" + str(value)
                client.sadd(match, roster)
        #
    print(f"There are {num_matchups} different matchups this week.")
    # Now I have the matchups saved within redis database
    return num_matchups, active_rosters


def set_roster_data():
    '''
    Within this function I want to be able to update each settings redis variable; 
    points_scored, points_allowed, wins, losses
    '''
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    USERS_LIST = set_user_list()
    rosters = get_league_rosters()

    for user in USERS_LIST:
        fpts = 0
        wins = 0
        losses = 0
        for roster in rosters:
            for key, value in roster.items():
                if key == "settings":
                    for name, val in value.items():
                        if name == "fpts":
                            fpts = val
                        elif name == "wins":
                            wins = val
                        elif name == "losses":
                            losses = val
                elif key == "owner_id" and value == user:
                    client.hset(user, 'fpts', fpts)
                    client.hset(user, 'wins', wins)
                    client.hset(user, 'losses', losses)


def clear_vars():
    client = redis.Redis(host="10.10.10.1", port=6379, db=5,
                         password=os.getenv("REDIS_PASS"))
    league = get_specific_league()
    total_rosters = league["total_rosters"]
    i = 1
    for i in range(total_rosters):
        roster = "roster_" + str(i)
        match = "matchup_" + str(i)
        try:
            client.delete(match)
        except Exception as e:
            print(e)
        try:
            client.hdel(roster, 'points')
        except Exception as e:
            print(e)


########## Helper Functions ###########


def set_user_list():
    users = get_user_in_league()
    users_list = []
    for user in users:
        # print(user)
        for key, value in user.items():
            if key == 'user_id':
                users_list.append(value)
    # print(users_list)
    return users_list


def get_matchups(client, active_rosters):
    league = get_specific_league()
    total_rosters = 0
    total_rosters = league["total_rosters"]

    # if key == 'total_rosters':
    #     total_rosters = value
    i = 1
    for i in range(total_rosters+1):
        roster_id = "roster_" + str(i)
        i += 1
        if roster_id in active_rosters:
            roster_data = client.hgetall(roster_id)
            for key, value in roster_data.items():
                if key.decode("utf-8") == 'matchup':
                    match = "matchup_" + str(value)
                    client.sadd(match, roster_id)


def get_owner_id(roster_id):
    roster_id = roster_id[7:]
    rosters = get_league_rosters()

    flag = False
    for roster in rosters:
        for key, value in roster.items():
            if key == 'roster_id':
                if int(value) == int(roster_id):
                    flag = True
            if flag == True and key == 'owner_id':
                return value


def get_team_name(id):
    team_name = "unknown"
    flag = False
    users = get_user_in_league()
    for user in users:
        for key, value in user.items():
            if key == 'user_id':
                if value == id:
                    flag = True
            elif flag == True and key == 'metadata':
                for name, val in value.items():
                    if name == 'team_name':
                        return val
    return team_name  # If we get here just return the unknown team name


def tweet_scores(client, num_matchups):
    match = 0
    full_tweet = ""
    i = 0
    for match in range(num_matchups):
        match += 1
        matchup = 'matchup_' + str(match)
        members = client.smembers(matchup)
        tweet = ""
        for member in members:
            i += 1
            id = get_owner_id(member.decode("utf-8"))
            team_name = get_team_name(id)
            points = client.hget(member, 'points').decode("utf-8")
            if i % 2 != 0:
                first = team_name
                first_points = points
            else:
                second = team_name
                second_points = points
                if int(first_points) > int(second_points):
                    tweet = first + " def. " + second + ": " + \
                        first_points + " - " + second_points + "\n\n"
                elif int(first_points) < int(second_points):
                    tweet = second + " def. " + first + ": " + \
                        second_points + " - " + first_points + "\n\n"
                else:
                    tweet = first + " & " + second + " tied: " + \
                        first_points + " - " + second_points + "\n\n"
        full_tweet = full_tweet + tweet
    week = get_week()
    beginning = f"NorthEast - week {week} results: \n\n"
    full_tweet = beginning + full_tweet + "\n#BOTS2020"
    num_tweets = math.ceil(len(full_tweet) / 274)
    send_tweet(full_tweet, 1, num_tweets)


########## Twitter API Functions ###########


def send_tweet(message, num, total):
    try:
        message_length = len(message)
        if message_length > 274:
            new_message = message[:274]
            i = 274
            while new_message[-1] != "\n":
                i -= 1
                new_message = message[:i]
            send_tweet(new_message, num, total)
            message_length = message_length - i
            num += 1
            send_tweet(message[-message_length:], num, total)
            api.update_status(str(message))
        else:
            if total > 1:
                message = f"({num}/{total})\n" + message
            api.update_status(message)
    except tweepy.TweepError as e:
            print(e.reason)


########## Scheduler ###########

print(time.ctime())

schedule.every().monday.at("02:01").do(update_week)
schedule.every().tuesday.at("08:01").do(weekly_scores)
schedule.every().monday.at("05:01").do(clear_vars)
schedule.every().tuesday.at("06:01").do(set_roster_data)
schedule.every().tuesday.at("12:01").do(set_standings)


while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except Exception as identifier:
        print(identifier)
        time.sleep(1)
