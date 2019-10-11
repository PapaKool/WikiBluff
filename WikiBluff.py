# |==========================================================================================|
# |                              Random Wikipedia Browser                                    |
# |                                (for no good reason)                                      |
# |                                    By Koolaid                                            |
# |                                                                                          |
# |                     To Do:                                                               |
# |                                                                                          |
# |                1. Search for images more thoroughly                                      |
# |                2. Add paragraph body hyperlinks? (maybe too hard)                        |
# |                3. Clean up imports / Speed up code                                       |
# |                4. Prettify UI                                                            |
# |                5. Explore PySimpleGUI options / Tkinker                                  |
# |                                                                                          |
# | *Python 3.7*                                               *Note: Will not run in Repl*  |
# |==========================================================================================|


import asyncio
import ctypes
import functools
import random
import re
import subprocess
import sys
import time
from subprocess import DEVNULL
from urllib.request import urlopen

import PySimpleGUI as sg
import websockets as ws
from bs4 import BeautifulSoup as bs


class ConnectionData:
  def __init__(self, connections=[], addresses=[], usernames=[], playerids=[], points=[], banned=[]):
    self.connections = connections
    self.addresses = addresses
    self.usernames = usernames
    self.playerids = playerids
    self.points = points
    self.banned = banned


class GameOptions:
  def __init__(self, pubip, hostport, num_players, num_choices, max_points, choose_fact_timer, memorize_timer,
               explain_timer, choosing_winner_timer):
    self.pubip = pubip
    self.hostport = hostport
    self.num_players = num_players
    self.num_choices = num_choices
    self.max_points = max_points
    self.choose_fact_timer = choose_fact_timer
    self.memorize_timer = memorize_timer
    self.explain_timer = explain_timer
    self.choosing_winner_timer = choosing_winner_timer


class GameData:
  def __init__(self, state='waitstart', judge=-1, truther=-1, turn=-1, titles=[], fact=[], article_choice=None,
               proceed=False, endgame=False, midgame=False, round_winner='', tie=False):
    self.state = state
    self.judge = judge
    self.truther = truther
    self.turn = turn
    self.titles = titles
    self.fact = fact
    self.article_choice = article_choice
    self.proceed = proceed
    self.endgame = endgame
    self.midgame = midgame
    self.round_winner = round_winner
    self.tie = tie


def errorhandle(error):
  errorwindow = sg.Window("An error has occurred").Layout([
    [sg.Text("WikiBluff has encoutned the following error and needs to close.")],
    [sg.Text(e)],
    [sg.Exit()],
  ])
  button, junk = errorwindow.Read()
  errorwindow.Close()
  sys.exit(0)


def getfact():  # Gets variables to plug into the main window
  link = "https://en.wikipedia.org/wiki/Special:Random"

  fact = urlopen(link)  # Grab html
  bsfact = bs(fact, 'html.parser')  # Converts to BeautifulSoup object
  title = re.sub(' - Wikipedia', '', bsfact.title.text)  # Variable for "Open Page" button text
  title = re.sub(',', '-', title)

  # --------------------- Grab variable for the main "fact" paragraph ------------------------
  para = str(bsfact.body.find('div', attrs={'mw-parser-output'}))  # "mw-parser-output" is body of page

  return para, title


async def clientthread(websocket, _, conn_data=None, game_data=None, game_opt=None):
  print("running thread...")
  while websocket.open != True:
    await asyncio.sleep(.1)
  addr = websocket.remote_address[0]
  if addr in conn_data.banned:
    websocket.send('error=banned')
    return
  print(str(addr))
  try:
    indx = conn_data.addresses.index(addr)
  except Exception:
    pass
  if addr not in conn_data.addresses and addr != '':
    if len(conn_data.addresses) == game_opt.num_players + 1:
      websocket.send('error=lobbyfull')
      return
    conn_data.addresses.append(addr)
    conn_data.usernames.append('New User')
    conn_data.connections.append(websocket)
    conn_data.points.append(0)
    playerid = str(random.randint(1000000, 9999999))

    while playerid in conn_data.playerids:
      playerid = str(random.randint(1000000, 9999999))
    conn_data.playerids.append(playerid)
    msg = f'playerid={playerid}'
    print(playerid)
  elif addr in conn_data.addresses:
    conn_data.connections[indx] = websocket
    msg = f'playerid={conn_data.playerids[indx]}'
  indx = conn_data.addresses.index(addr)
  await websocket.send(
    f"{msg}&index={indx}&players={conn_data.usernames}&state={game_data.state}&points={conn_data.points}")
  if game_data.midgame:
    loop = asyncio.get_event_loop()
    await asyncio.ensure_future(sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt), loop=loop)
  while True:
    if game_data.endgame:
      return
    try:
      message = await asyncio.wait_for(websocket.recv(), timeout=1)
      if message != '':
        print(message)
        try:
          messagearray = message.split('&')
        except:
          messagearray = [message, "dummy"]
        for msg in messagearray:
          if 'username=' in msg:
            cusername = msg.split('=')
            conn_data.usernames[indx] = cusername[1]
          if 'proceed=' in msg and 'true' in msg:
            cproceed = msg.split('=')
            if 'true' in cproceed[1]:
              game_data.proceed = True
          if 'articlechoice=' in msg:
            cachoice = msg.split('=')
            game_data.article_choice = int(cachoice[1])
          if 'winnerchoice=' in msg:
            cwchoice = msg.split('=')
            game_data.round_winner = int(cwchoice[1])
    except Exception as e:
      if 'closed' in str(e):
        conn_data.usernames[indx] = conn_data.usernames[indx] + ' - Disconnected'
    await websocket.send(f'players={conn_data.usernames}&points={conn_data.points}')
    if websocket.closed:
      return


async def sendgamestate(conn_data=None, game_data=None, game_opt=None, game_winner=None):
  s, j, t = game_data.state, game_data.judge, game_data.truther

  if s == 'choosingfact':
    timer = game_opt.choose_fact_timer
  elif s == 'memorize':
    timer = game_opt.memorize_timer
  elif s == 'explain':
    timer = game_opt.explain_timer
  elif s == 'choosingwinner':
    timer = game_opt.choosing_winner_timer
  elif s == 'endround':
    timer = 5
  else:
    timer = 0

  pgamestate = f"players={conn_data.usernames}&state={s}&points={conn_data.points}&judge={j}&timer={timer}&turn={game_data.turn}"
  jgamestate, tgamestate = pgamestate, pgamestate

  if s == 'endround':
    pgamestate = f"{pgamestate}&truther={t}&winner={game_data.round_winner}"
    jgamestate, tgamestate = pgamestate, pgamestate
  else:
    pgamestate = f"{pgamestate}&truther=-1"
    jgamestate = pgamestate
  if s not in 'endgame endround':
    tgamestate = f'{tgamestate}&truther={t}&winner={game_data.round_winner}'
  if s == 'endgame':
    pgamestate = f"{pgamestate}&tie={game_data.tie}&gamewinner={game_winner}"
    tgamestate, jgamestate = pgamestate, pgamestate

  if s in "memorize explain choosingwinner endround":
    title = game_data.titles[game_data.article_choice]
    pgamestate = f"{pgamestate}&this_game_title={title}"
    tgamestate = f"{tgamestate}&this_game_title={title}"
    jgamestate = f"{jgamestate}&this_game_title={title}"

  if s == 'choosingfact':
    tgamestate = f"{tgamestate}&this_game_options={game_data.titles}"

  if s == 'memorize':
    tgamestate = f"{tgamestate}&this_game_article={game_data.fact[game_data.article_choice]}"

  for indx, conn in enumerate(conn_data.connections):
    if indx != j and indx != t:
      try:
        await conn.send(pgamestate)
      except:
        continue
    elif indx == j:
      try:
        await conn.send(jgamestate)
      except:
        continue
    elif indx == t:
      try:
        await conn.send(tgamestate)
      except:
        continue


async def startpage(loop):
  ipsite = "https://ident.me"
  ipurl = urlopen(ipsite)
  ipurlbs = bs(ipurl, 'html.parser')
  pubip = ipurlbs.text
  print(pubip)
  sg.ChangeLookAndFeel('SystemDefault')
  start_window = sg.Window('WikiBluff').Layout([
    [sg.Text("Start game on:"),
     sg.InputText(pubip, text_color='#FF0000', disabled=True, justification='center', size=(15, 1), key=0),
     sg.Text(":", justification='left', pad=(0, 3)), sg.InputText('443', size=(6, 1), justification='left', key=1)],
    [sg.Text('Number of players:'), sg.InputText('4', size=(2, 1), justification='left', pad=((51, 30), 1), key=2)],
    [sg.Text('Number of article choices:'),
     sg.InputText('6', size=(2, 1), justification='left', pad=((9, 30), 1), key=3)],
    [sg.Text('Points needed to win:'), sg.InputText('5', size=(2, 1), justification='left', pad=((35, 30), 1), key=4)],
    [sg.Text('Time to choose an article:'),
     sg.InputText('10', size=(2, 1), justification='left', pad=((10, 30), 1), key=5)],
    [sg.Text('Time to memorize article:'),
     sg.InputText('20', size=(2, 1), justification='left', pad=((13, 30), 1), key=6)],
    [sg.Text('Time to explain article:'),
     sg.InputText('30', size=(2, 1), justification='left', pad=((29, 30), 1), key=7)],
    [sg.Text('TIme to pick winner:'), sg.InputText('0', size=(2, 1), justification='left', pad=((44, 30), 1), key=8)],
    [sg.Button('Host Game'), sg.Button('Exit')]
  ])

  # Value keys for this window:
  #
  #   0 = pubip
  #   1 = hostport
  #   2 = num_players
  #   3 = num_choices
  #   4 = max_points
  #   5 = choose_fact_timer
  #   6 = memorize_timer
  #   7 = explain_timer
  #   8 = choosing_winner_timer

  button = '__TIMEOUT__'
  while button == '__TIMEOUT__':
    button, dict_vals = start_window.Read(timeout=100)
    await asyncio.sleep(.1)

  if button == 'Exit' or button is None:
    start_window.Close()
    return
  elif button == 'Host Game':
    start_window.Close()
    vals = []
    print(dict_vals)
    for key, val in dict_vals.items():
      if key == 0:
        vals.append(val)
      else:
        vals.append(int(val))

    game_opt = GameOptions(*vals[:2], (vals[2] - 1), (vals[3] - 1), *vals[4:])
    conn_data = ConnectionData()
    game_data = GameData()
    addRule(game_opt.hostport)
    bound_client_thread = functools.partial(clientthread, conn_data=conn_data, game_data=game_data, game_opt=game_opt)
    wsserver = ws.serve(bound_client_thread, None, game_opt.hostport)
    server = await asyncio.ensure_future(wsserver, loop=loop)
    await asyncio.ensure_future(lobbyloop(server=server, conn_data=conn_data, game_data=game_data, game_opt=game_opt),
                                loop=loop)
    server.close()
    await server.wait_closed()
  return


async def lobbyloop(server=None, conn_data=None, game_data=None, game_opt=None):
  lobby_window = sg.Window('WikiBluff - Lobby').Layout([
    [sg.Text('Listening on:'),
     sg.InputText(f'{game_opt.pubip}:{game_opt.hostport}', disabled=True, size=(21, 1), justification='center')],
    [],
    [sg.Text("Connected players:")],
    [sg.Listbox(conn_data.usernames, size=(30, 4), key='players_element')],
    [sg.Button('Start Game'), sg.Button('Exit')]
  ])
  button = '__TIMEOUT__'
  while button == '__TIMEOUT__':
    button, selectedusers = lobby_window.Read(timeout=100)
    lobby_window.Element('players_element').Update(conn_data.usernames)
    await asyncio.sleep(.1)

  if button == 'Exit' or button is None:
    delRule()
    server.close()
    await server.wait_closed()
    game_data.endgame = True
    lobby_window.Close()
    return

  if button == 'Start Game':
    await asyncio.ensure_future(
      gameloop(conn_data=conn_data, game_data=game_data, game_opt=game_opt, lobby_window=lobby_window), loop=loop)
    lobby_window.Close()
    return


async def gameloop(conn_data=None, game_data=None, game_opt=None, lobby_window=None):
  game_data.midgame = True
  game_opt.num_players = len(conn_data.playerids) - 1
  game_data.judge = random.randint(0, game_opt.num_players)

  while True:

    game_data.judge = (game_data.judge + 1) % game_opt.num_players
    game_data.truther = random.randint(0, game_opt.num_players)
    while game_data.judge == game_data.truther:
      game_data.truther = random.randint(0, game_opt.num_players)

    game_data.fact = []
    game_data.titles = []
    for i in range(game_opt.num_choices + 1):
      f, t = getfact()
      game_data.fact.append(f)
      game_data.titles.append(t)

    if game_opt.num_choices > 1:
      game_data.state = "choosingfact"
      await asyncio.ensure_future(sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt), loop=loop)
      timed = time.time() + game_opt.choose_fact_timer
      game_data.proceed = False
      while not game_data.proceed and timed > int(time.time()):
        await asyncio.sleep(.1)
        if updateLobbyWindow(lobby_window):
          return
      if not game_data.proceed:
        game_data.article_choice = random.randint(0, game_opt.num_choices)
    else:
      game_data.article_choice = 0
    game_data.fact[game_data.article_choice] = re.sub('//upload.', 'https://upload.',
                                                      game_data.fact[game_data.article_choice])
    game_data.fact[game_data.article_choice] = re.sub('a href=', 'a style=\"pointer-events: none\" href=',
                                                      game_data.fact[game_data.article_choice])
    game_data.fact[game_data.article_choice] = re.sub('a class=', 'a style=\"pointer-events: none\" class=',
                                                      game_data.fact[game_data.article_choice])
    game_data.state = 'memorize'
    await asyncio.ensure_future(sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt), loop=loop)

    timed = time.time() + game_opt.memorize_timer
    game_data.proceed = False
    while not game_data.proceed and timed > time.time():
      await asyncio.sleep(.1)
      if updateLobbyWindow(lobby_window):
        return

    game_data.state = 'explain'
    for player_index in range(len(conn_data.playerids)):
      reindexed = player_index + game_data.judge
      reindexed = reindexed % len(conn_data.playerids)
      game_data.turn = reindexed
      if reindexed != game_data.judge:
        await asyncio.ensure_future(sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt),
                                    loop=loop)
        timed = time.time() + game_opt.explain_timer
        game_data.proceed = False
        while game_data.proceed == False and timed > time.time():
          await asyncio.sleep(.1)
          if updateLobbyWindow(lobby_window, conn_data):
            return

    game_data.state = 'choosingwinner'
    game_data.turn = -1
    game_data.proceed = False
    await asyncio.ensure_future(sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt), loop=loop)
    timed = time.time() + game_opt.choosing_winner_timer

    while not game_data.proceed:
      while timed > time.time() and game_opt.choosing_winner_timer != 0:
        await asyncio.sleep(1)
        timed += 1
      if not game_data.proceed and game_opt.choosing_winner_timer != 0:
        game_data.round_winner = -1
        break
      await asyncio.sleep(.1)
      if updateLobbyWindow(lobby_window, conn_data):
        return

    game_data.state = 'endround'
    if game_data.round_winner != -1:
      conn_data.points[game_data.round_winner] += 1
      if game_data.round_winner == game_data.truther:
        conn_data.points[game_data.judge] += 1
      await asyncio.ensure_future(sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt), loop=loop)
    else:
      game_data.state = 'skipround'

    game_winner = ''
    for indx, points in enumerate(conn_data.points):
      if points >= game_opt.max_points:
        game_data.state = 'endgame'
        if game_winner == '':
          game_winner = conn_data.usernames[indx]
        else:
          game_data.tie = True
          game_winner = f'{game_winner}+{conn_data.usernames[indx]}'
        timed = time.time() + 6
        while timed > time.time():
          await asyncio.sleep(.1)
          if updateLobbyWindow(lobby_window, conn_data):
            return
        await asyncio.ensure_future(
          sendgamestate(conn_data=conn_data, game_data=game_data, game_opt=game_opt, game_winner=game_winner),
          loop=loop)
        lobby_window.Close()
        end_window = sg.Window('Game over!').Layout([
          [sg.Text(game_winner + ' won the game!')],
          [sg.Text('Thank you for playing. The game will now close.')],
          [sg.Ok]
        ])
        _ = end_window.Read()
        end_window.Close()
        return


def updateLobbyWindow(lobby_window,conn_data):
  button, selected = lobby_window.Read(timeout=100)
  lobby_window.Element('players_element').Update(conn_data.usernames)
  if button == 'Ban':
    for user in selected:
      conn_data.banned.append(conn_data.addresses[conn_data.usernames.index(user)])
      conn_data.connections[conn_data.usernames.index(user)].close()
  if button == 'Exit':
    return True
  else:
    return False


def makeAdmin():
  if not chkAdmin():
    make_admin_window = sg.Window('Run as Admin?').Layout([
      [sg.Text("In order to create a Windows Firewall exception automatically,", justification='center')],
      [sg.Text("you must allow this game to run with administrator privledges.", justification='center')],
      [],
      [sg.Text('If you prefer to make a firewall exception manually (or if you', justification='center')],
      [sg.Text('use a different firewall than Windows Firewall), just click \'No\'.', justification='center')],
      [],
      [sg.Text('Would you like to automatically make a Windows Firewall exception?', justification='center')],
      [sg.Button('Yes'), sg.Button('No')]
    ])

    button, _ = make_admin_window.Read()
    make_admin_window.Close()
    if button == 'Yes':
      try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
        print('yes')
        sys.exit(0)
      except Exception as e:
        print(e)


def chkAdmin():
  try:
    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
  except AttributeError:
    return False
  else:
    return is_admin


def addRule(port):
  try:
    subprocess.run(
      [
        'netsh', 'advfirewall', 'firewall', 'add', 'rule', f'name=WikiBluff',
        'dir=in', 'action=allow', f'program={__file__}', 'enable=yes',
        f'localport={port}', 'protocol=tcp', 'interfacetype=any', 'edge=yes',
      ],
      check=True,
      stdout=DEVNULL,
      stderr=DEVNULL
    )
    print("Rule \"WikiBluff\" added for ", __file__)
  except Exception as e:
    print("Error adding rule \"WikiBluff\":\n\n", e)


def delRule():
  try:
    subprocess.call(f"netsh advfirewall firewall delete rule name=WikiBluff", shell=True, stdout=DEVNULL,
                    stderr=DEVNULL)
    print(f"Rule \"WikiBluff\" deleted")
  except Exception as e:
    print("Error deleting rule \"WikiBluff\":\n\n", e)


makeAdmin()
loop = asyncio.get_event_loop()
loop.run_until_complete(startpage(loop))
loop.stop()
while loop.is_running():
  continue
loop.close()
sys.exit(0)
