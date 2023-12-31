from requests import post, get
from dotenv import load_dotenv
import PySimpleGUI as sg
import os
from typing import Tuple
from time import sleep
from regex_helper import is_valid_type

load_dotenv()

CLIENT_ID = str(os.getenv("CLIENT_ID"))
CLIENT_SECRET = str(os.getenv("CLIENT_SECRET"))
LYRICS_API = str(os.getenv("LYRICS_API"))


ERR_DEFAULT = {"error": "Something Went Wrong With Spotify API"}


def get_token() -> Tuple[bool, str]:
    auth_url = "https://accounts.spotify.com/api/token"
    data = {"grant_type": "client_credentials"}
    result = post(auth_url, data=data, auth=(CLIENT_ID, CLIENT_SECRET))

    if result.status_code != 200:
        return False, "Something Went Wrong while getting access token"

    token = result.json()['access_token']
    return True, token


def get_auth_header(token: str) -> dict:
    return {"authorization": "Bearer " + token}


def print_track_info(track_info) -> None:
    print(f"Track Name: {track_info['name']}")
    print(f"Album: {track_info['album']['name']}")
    print(f"Artist: {track_info['artists'][0]['name']}\n")


def process_track(track_id, token) -> None:
    success, track_info = get_track_info(token, track_id)
    if success:
        print_track_info(track_info)
        fetch_and_write_lyrics(track_id, track_info['name'])
    else:
        message_box("Error Getting Track Info")


def get_track_info(token: str, track_id: str) -> Tuple[bool, dict]:
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    res = get(url, headers=get_auth_header(token))
    if res.status_code != 200:
        return False, ERR_DEFAULT
    track_data = res.json()
    return True, track_data


def get_album_tracks(token: str, album_id: str) -> Tuple[bool, dict]:
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    res = get(url, headers=get_auth_header(token))
    if res.status_code != 200:
        return False, ERR_DEFAULT
    album_data = res.json()
    return True, album_data


def process_album(album_id, token) -> None:
    success, album_info = get_album_tracks(token, album_id)
    if success:
        track_names, track_ids = get_tracks_list(album_info)
        message_box(f"Found Album tracks:\n{track_names}")
        for track_id in track_ids:
            sleep(3)
            process_track(track_id, token)
    else:
        message_box("Error Getting Album Info")


def get_tracks_list(data: dict) -> Tuple[str, list]:
    names, track_ids = [], []
    for item in data["items"]:
        names.append(item["name"])
        track_ids.append(item["id"])
    names = "\n".join(names)
    return names, track_ids


def get_lyrics(track_id: str) -> Tuple[bool, str]:
    url = LYRICS_API + f"{track_id}&format=lrc"
    data = get(url)
    if data.status_code != 200:
        return False, "Something Went Wrong"
    lyrics_data = data.json()
    if lyrics_data['error']:
        return False, "Error"
    lyrics = convert_to_lrc(lyrics_data)
    return True, lyrics


def convert_to_lrc(lyrics_data: dict) -> str:
    lrc_lines = []
    if lyrics_data['syncType'].lower() == 'unsynced':
        for line in lyrics_data['lines']:
            lrc_lines.append(line['words'])
    else:
        for line in lyrics_data['lines']:
            lrc_lines.append(f"[{line['timeTag']}] {line['words']}")

    return '\n'.join(lrc_lines)


def fetch_and_write_lyrics(track_id, track_name) -> None:
    lyrics_available, lyrics = get_lyrics(track_id)
    if lyrics_available:
        write_to_file(lyrics, track_name)
        message_box(msg=f"Successfully Fetched Lyrics for {track_name}")
    else:
        message_box("Error Getting Lyrics")


def write_to_file(lyrics: str, track_name: str) -> None:
    with open(f"{track_name}.lrc", 'w', encoding='utf-8') as lrc_file:
        lrc_file.write(lyrics)


def input_dialog_box() -> Tuple[str, str]:
    sg.theme("Black")
    layout = [[sg.Text('Enter Spotify URL'), sg.InputText()],
              [sg.Button('Ok'), sg.Button('Cancel')]]
    window = sg.Window('Lyrics', layout)

    event, values = window.read()  # type: ignore
    if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
        window.close()
        exit(0)
    url_info = is_valid_type(values[0])
    if url_info['type'] is not None:
        window.close()
        return url_info['type'].lower(), url_info['id']
    sg.popup("Invalid Spotify URL. Please try again.")
    window.close()
    return input_dialog_box()


def message_box(msg: str) -> None:
    window = sg.Window('Lyrics')
    sg.popup(msg)
    window.close()


def main() -> None:
    url_type, id_from_url = input_dialog_box()
    success, token = get_token()
    if not success:
        message_box(msg=token)
        exit(0)
    if url_type == "track":
        process_track(id_from_url, token)
    elif url_type == "album":
        process_album(id_from_url, token)


if __name__ == "__main__":
    main()
