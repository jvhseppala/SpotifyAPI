#import the required libraries
import json
import requests
import datetime
import base64
from urllib.parse import urlencode
import pandas as pd

#insert client id & client secret for the Spotify API

client_id = '[]'
client_secret = '[]'

#import the artist list

path = '.../artistList.xlsx'
artist_df = pd.read_excel(path)
artist_list = artist_df['Artist_name'].tolist()

#create a class for the API

class SpotifyAPI(object):
    access_token = None
    access_token_expires = datetime.datetime.now()
    access_token_did_expire = True
    client_id = None
    client_secret = None
    token_url = 'https://accounts.spotify.com/api/token'
    
    def __init__(self, client_id, client_secret, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.client_id = client_id
        self.client_secret = client_secret
    
    def get_client_credentials(self):
        '''
        Returns a base64 encoded string
        '''
        client_id = self.client_id
        client_secret = self.client_secret
        if client_secret == None or client_id == None:
            raise Exception('You must set client_id and client_secret')
        client_creds = f'{client_id}:{client_secret}'
        client_creds_b64 = base64.b64encode(client_creds.encode())
        return client_creds_b64.decode()
    
    def get_token_headers(self):
        client_creds_b64 = self.get_client_credentials()
        return {
            'Authorization': f'Basic {client_creds_b64}' #<base64 encoded client_id:client_secret>
        }
    
    def get_token_data(self):
        return {
            'grant_type': 'client_credentials'
        }
    
    def perform_auth(self):
        token_url = self.token_url
        token_data = self.get_token_data()
        token_headers = self.get_token_headers()
        r = requests.post(token_url, data = token_data, headers = token_headers)
        if r.status_code not in range(200, 299):
            raise Exception('Could not authenticate client.')
        data = r.json()
        now = datetime.datetime.now()
        access_token = data['access_token']
        expires_in = data['expires_in']
        expires = now + datetime.timedelta(seconds=expires_in)
        self.access_token = access_token
        self.access_token_expires = expires
        self.access_token_did_expire = expires < now
        return True
    
    def get_access_token(self):
        token = self.access_token
        expires = self.access_token_expires
        now = datetime.datetime.now()
        if expires < now:
            self.perform_auth()
            return self.get_access_token()
        elif token == None:
            self.perform_auth()
            return self.get_access_token()
        return token
    
    def get_resource_header(self):
        access_token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        return headers
    
    def get_resource(self, lookup_id, resource_type = 'albums', version = 'v1'):
        endpoint = f'https://api.spotify.com/{version}/{resource_type}/{lookup_id}'
        headers = self.get_resource_header()
        r = requests.get(endpoint, headers = headers)
        if r.status_code not in range(200, 299):
            return{}
        return r.json()
    
    def get_album(self, _id):
        return self.get_resource(_id, resource_type = 'albums')
    
    def get_artist(self, _id):
        return self.get_resource(_id, resource_type = 'artists')
    
    def base_search(self, query_params):
        headers = self.get_resource_header()
        endpoint = 'https://api.spotify.com/v1/search'
        lookup_url = f'{endpoint}?{query_params}'
        r = requests.get(lookup_url, headers = headers)
        if r.status_code not in range(200, 299):
            return {}
        return r.json()
    
    def search(self, query=None, operator=None, operator_query=None, search_type = 'artist'):
        if query == None:
            raise Exception('A query is required')
        if isinstance(query, dict):
            query = ' '.join([f'{k}:{v}' for k,v in query.items()])
        if operator != None and operator_query != None:
            if operator.lower() == 'or' or operator.lower() == 'not':
                operator = operator.upper()
                if isinstance(operator_query, str):
                    query = f'{query} {operator} {operator_query}'
        query_params = urlencode({'q': query, 'type': search_type.lower()})
        #print(query_params)
        return self.base_search(query_params)


def artistLookup(artistsList):
    '''
    Get the top result of the search query 
    '''
    spotify = SpotifyAPI(client_id, client_secret)
    spotify.perform_auth()

    artistGenresList = []

    checkName = 'name' #make sure that name is in returned list of keys

    for artist in artistsList:
        resultArtists = spotify.search(query = artist, search_type = 'artist')

        try:
            if checkName in resultArtists['artists']['items'][0].keys():
                if resultArtists['artists']['items'][0]['name'] == artist:
                    artistGenresList.append(resultArtists['artists']['items'][0]['genres'])
                else:
                    artistGenresList.append('Query not exact match or top match')
            else:
                artistGenresList.append('Artist not found')
        except:
            artistGenresList.append('Unknown error') #Couldn't figure out why the script came to a halt, but this except clause allowed the script run completely
    
    return artistGenresList

def main():
    artist_df['spotifyGenres'] = artistLookup(artist_df)
    artist_df.to_excel('refinedArtistList.xlsx')

if __name__ == "__main__":
    main()
