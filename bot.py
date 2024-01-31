import websocket
import rel
import requests
import json
import imdb
import time

ia = imdb.Cinemagoer()
username = "cashmeoutside20243546768"
first_play = "U Turn (1997)"
first_play_id = 19918
current_movie = ""
current_year = 0
current_id = 0
gameId = ""
cast = []
filmography = set()
player_number = 0
our_turn = False

# KNOWN ISSUES
# currently are possible errors with adding movies to filmography and no movies end up getting added due to everything having been played (because it is unlikely to happen)
# also does not account for bans yet (because I have not run into it yet so I don't know what the message data/protocol looks like)
# cinemagoer read operation can time-out though is not likely

def on_message(ws: websocket.WebSocketApp, message):
    global ia
    global username
    global first_play
    global current_movie
    global current_year
    global current_id
    global gameId
    global cast
    global filmography
    global player_number
    global our_turn

    # pong to pings
    if message == "2":
        ws.send('3')

    # initiate match
    elif message == "3probe":
        ws.send('5')
        ws.send(f'42["find-match",{{"daycount":33,"username":"{username}","wins":0,"startingMovieInput":"{first_play}","startingMovieId":{first_play_id},"staging":false,"battleStats":{{"todayWins":0,"todayDraws":0,"todayLosses":0,"todayCurrentStreak":0,"todayBestStreak":0,"todayLongestBattle":0,"allTimeBestStreak":0,"allTimeLongestBattle":0,"wins":0,"draws":0,"losses":0,"daycount":22}}}}]')
        
        print(f'Searching for match... First play: {first_play} ID: {first_play_id}')
        with open("log.txt", "a") as log:
            log.write(f'Searching for match... First play: {first_play} ID: {first_play_id}\n')

    # main message handler
    elif message[:2] == "42":
        [protocol, data] = json.loads(message[2:])
        
        # initiate game
        if protocol == "initiate-game":
            gameId = data["gameId"]
            player_number = data["playersData"][username]["playerNumber"]
            our_turn = player_number == data["playerTurn"]
            current_movie = data["films"][0]["title"][:-7]
            current_year = data["films"][0]["title"][-5:-1]
            current_id = data["films"][0]["id"]
            ws.send(f'42["join-game-room",{{"gameId":"{gameId}"}}]')
            time.sleep(1)
            ws.send(f'42["ready-up",{{"gameId":"{gameId}","username":"{username}","bans":["matt damon","tom bower","sophie monk"],"playersData":"{data["playersData"]}"}}]')

            print(f'Game found. Starting movie: {current_movie} ({current_year}) ID: {current_id}')
            print(f'We are player {player_number}. It is{"" if our_turn else " not"} our turn.\n')
            with open("log.txt", "a") as log:
                log.write(f'Game found. Starting movie: {current_movie} ({current_year}) ID: {current_id}\n')
                log.write(f'We are player {player_number}. It is{"" if our_turn else " not"} our turn.\n\n')

        # play first if we need to
        elif protocol == "start-game" and our_turn:
            cur_movie = ia.get_movie(ia.search_movie(f'{current_movie} ({current_year})', results=1)[0].getID())
            cast = cur_movie["cast"]

            print(f'Searching for connection using {cast[0]["name"]}...\n')
            with open("log.txt", "a") as log:
                log.write(f'Searching for connection using {cast[0]["name"]}...\n\n')

            dictFilmography = ia.get_person(cast[0].getID())['filmography']
            for role in dictFilmography:
                for movie in dictFilmography[role]:
                    try:
                        if f'{current_movie} ({current_year})' == f'{movie["title"]} ({movie["year"]})':
                            raise Exception("movie played")
                        filmography.add(movie)
                    except:
                        pass

            next_movie = filmography.pop()

            ws.send(f'42["submit-movie",{{"gameId":"{gameId}","username":"{username}","input":"{next_movie["title"]} ({next_movie["year"]})","currentMovieId":{current_id},"currentMovieTitle":"{current_movie}","currentMovieYear":"{current_year}"}}]')

            print(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}')
            with open("log.txt", "a") as log:
                log.write(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}\n')

        # respond to plays
        elif protocol == "update-game":
            # our last submission was successful
            if data["gameData"]["playerTurn"] != player_number:
                our_turn = False
                print(f'\nSuccessful connection using {data["newMovie"]["title"]}! Actor connections: {", ".join(data["connections"])}\n')
                with open("log.txt", "a") as log:
                    log.write(f'\nSuccessful connection using {data["newMovie"]["title"]}! Actor connections: {", ".join(data["connections"])}\n\n')
            
            # enemy submission was successful
            else:
                print(f'Opponent successful connection using {data["newMovie"]["title"]}! Actor connections: {", ".join(data["connections"])}')
                with open("log.txt", "a") as log:
                    log.write(f'Opponent successful connection using {data["newMovie"]["title"]}! Actor connections: {", ".join(data["connections"])}\n')

                our_turn = True
                filmography.clear()
                current_movie = data["newMovie"]["title"][:-7]
                current_year = data["newMovie"]["title"][-5:-1]
                current_id = data["newMovie"]["id"]

                cur_movie = ia.get_movie(ia.search_movie(f'{current_movie} ({current_year})', results=1)[0].getID())
                cast = cur_movie["cast"]
                person = cast[0]

                # can we do a connection with this person
                while (person["name"].lower() in data["connectionCounts"]) and (int(data["connectionCounts"][person["name"].lower()]) >= 3):
                    cast.pop(0)
                    person = cast[0]
                
                print(f'Searching for connection using {person["name"]}...\n')
                with open("log.txt", "a") as log:
                    log.write(f'Searching for connection using {person["name"]}...\n\n')

                # add valid guessable movies to the pool
                dictFilmography = ia.get_person(person.getID())['filmography']
                for role in dictFilmography:
                    for movie in dictFilmography[role]:
                        try:
                            for film in data["gameData"]["films"]:
                                if film["title"] == f'{movie["title"]} ({movie["year"]})':
                                    raise Exception("movie played")
                            filmography.add(movie)
                        except:
                            pass

                next_movie = filmography.pop()

                ws.send(f'42["submit-movie",{{"gameId":"{gameId}","username":"{username}","input":"{next_movie["title"]} ({next_movie["year"]})","currentMovieId":{current_id},"currentMovieTitle":"{current_movie}","currentMovieYear":"{current_year}"}}]')

                print(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}')
                with open("log.txt", "a") as log:
                    log.write(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}\n')


        # handle errors from us
        elif protocol == "error" and our_turn:
            if data["message"] == "This movie is not in our database" or data["message"] == "No links were found to this movie":
                # more selections from the actor
                if len(filmography) > 0:
                    next_movie = filmography.pop()
                    ws.send(f'42["submit-movie",{{"gameId":"{gameId}","username":"{username}","input":"{next_movie["title"]} ({next_movie["year"]})","currentMovieId":{current_id},"currentMovieTitle":"{current_movie}","currentMovieYear":"{current_year}"}}]')

                    print(f'{"Above movie was not in database, trying new movie" if data["message"] == "This movie is not in our database" else "Above movie has no links to current movie, trying new movie"}')
                    print(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}')
                    with open("log.txt", "a") as log:
                        log.write(f'{"Above movie was not in database, trying new movie" if data["message"] == "This movie is not in our database" else "Above movie has no links to current movie, trying new movie"}\n')
                        log.write(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}\n')

                # no more movies from the actor, get the next actor
                else:
                    cast.pop(0)

                    print(f'Actor movies exhausted, now searching for connection using {cast[0]["name"]}...\n')
                    with open("log.txt", "a") as log:
                        log.write(f'Actor movies exhausted, now searching for connection using {cast[0]["name"]}...\n\n')

                    dictFilmography = ia.get_person(cast[0].getID())['filmography']
                    for role in dictFilmography:
                        for movie in dictFilmography[role]:
                            try:
                                for film in data["gameData"]["films"]:
                                    if film["title"] == f'{movie["title"]} ({movie["year"]})':
                                        raise Exception("movie played")
                                filmography.add(movie)
                            except:
                                pass
                    
                    next_movie = filmography.pop()
                    ws.send(f'42["submit-movie",{{"gameId":"{gameId}","username":"{username}","input":"{next_movie["title"]} ({next_movie["year"]})","currentMovieId":{current_id},"currentMovieTitle":"{current_movie}","currentMovieYear":"{current_year}"}}]')

                    print(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}')
                    with open("log.txt", "a") as log:
                        log.write(f'Submitted {next_movie["title"]} ({next_movie["year"]}) against {current_movie} ({current_year}) ID: {current_id}\n')
            
            # catch all uncaught errors
            else:
                print(f'Uncaught error. Header: {data["header"]} Message: {data["message"]}')
                with open("log.txt", "a") as log:
                    log.write(f'Uncaught error. Header: {data["header"]} Message: {data["message"]}\n')
        
        # errors from our opponent
        elif protocol == "error" and not our_turn:
            if data["message"] == "No links were found to this movie":
                print(f'Opponent failed with guess {data["header"]}')
                with open("log.txt", "a") as log:
                    log.write(f'Opponent failed with guess {data["header"]}\n')

        # opponent casted
        elif protocol == "cast-lifeline-response" and not our_turn:
            print(f'Opponent used CAST lifeline')
            with open("log.txt", "a") as log:
                    log.write(f'Opponent used CAST lifeline\n')

        # opponent used time
        elif protocol == "add-time" and not our_turn:
            print(f'Opponent used TIME lifeline')
            with open("log.txt", "a") as log:
                    log.write(f'Opponent used TIME lifeline\n')

        # game end
        elif protocol == "game-over":
            if int(data["gameData"]["winner"]) == player_number:
                print("Game over, we won!")
                with open("log.txt", "a") as log:
                    log.write("Game over, we won!\n")
            else:
                print("We lost? Investigate.")
                with open("log.txt", "a") as log:
                    log.write("We lost? Investigate.\n")

        # time synced
        elif protocol == "sync-time":
            print(f'Time synced with server')
            with open("log.txt", "a"):
                log.write(f'Time synced with server\n')
        
        # player readied
        elif protocol == "players-ready":
            print(f'We are ready')
            with open("log.txt", "a"):
                log.write(f'We are ready\n')

        # opponent disconnected
        elif protocol == "opponent-disconnected":
            print(f'Opponent disconnected, yay!')
            with open("log.txt", "a"):
                log.write(f'Opponent disconnected, yay!\n')
        
        # catch all uncaught protocols
        else:
            print(f'Uncaught protocol: {protocol} with data: {data}')
            with open("log.txt", "a") as log:
                log.write(f'Uncaught protocol: {protocol} with data: {data}\n')


def on_error(ws, error):
    print(error)

def on_close(ws, close_status_code, close_msg):
    print(f"### closed ### {close_status_code}, {close_msg}")

def on_open(ws: websocket.WebSocketApp):
    print("Opened connection")
    ws.send('2probe')


if __name__ == "__main__":
    # websocket.enableTrace(True)
    with open("log.txt", "w") as log:
        pass

    # get session id
    r = requests.get("https://www.cinenerdle2.app/socket.io/?EIO=4&transport=polling&t=OpILxx1")
    sid = json.loads(r.text[1:])["sid"]

    # necessary for verification?
    requests.post(f"https://www.cinenerdle2.app/socket.io/?EIO=4&transport=polling&t=OpILxxi&sid={sid}", "40").text
    requests.get(f"https://www.cinenerdle2.app/socket.io/?EIO=4&transport=polling&t=OpILxxj&sid={sid}").text
    
    # open and run websocket
    ws = websocket.WebSocketApp(f"wss://www.cinenerdle2.app/socket.io/?EIO=4&transport=websocket&sid={sid}",
                              on_open=on_open,
                              on_message=on_message,
                              on_error=on_error,
                              on_close=on_close)

    ws.run_forever(dispatcher=rel, reconnect=5)

    # idk
    requests.get(f"https://www.cinenerdle2.app/socket.io/?EIO=4&transport=polling&t=OpILxyL&sid={sid}").text

    rel.signal(2, rel.abort)
    rel.dispatch()