#!/usr/bin/env python
from BeautifulSoup import BeautifulSoup
import urllib2
import time
import datetime
import sys
import urllib2
import json
import difflib
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import datetime

Base = declarative_base()
engine = create_engine('sqlite:////home/ubuntu/b2s/songs.db')
Base.metadata.create_all(engine)
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

def similar(arg1, arg2):
        ratio = 0.82
        return difflib.SequenceMatcher(None, arg1.lower(), arg2.lower()).ratio() >= ratio

def get_songs():
    '''
#html = urllib2.urlopen('http://api.beatport.com/catalog/3/most-popular?perPage=100')
#songs_dict = json.loads(html.read())
    songs = []
    for song in songs_dict['results']:
        title = song['name']
        full_title = song['title']
        artists = '|'.join([s['name'] for s in song['artists']])
        genre = song['genres'][0]['name']
        rank = song['position']
        date = song['releaseDate']
        sample = song['sampleUrl']
        songs.append({'title':title,'artists':artists,'genre':genre,'rank':rank,'full_title':full_title,'sample':sample,'date':date})
'''
    html = urllib2.urlopen('http://www.beatport.com/top-100').read()
    soup = BeautifulSoup(html,convertEntities=BeautifulSoup.HTML_ENTITIES)
    table = soup('tr')[2:]
    songs = []

    for t in table:
        tds = t('td')
        song = json.loads(tds[1]('span')[0]['data-json'])
        title = song['name']
        full_title = song['title']
        artists = '|'.join([s['name'] for s in song['artists']])
        genre = song['genres'][0]['name']
        rank = song['position']
        date = song['releaseDate']
        sample = song['sampleUrl']
        songs.append({'title':title,'artists':artists,'genre':genre,'rank':rank,'full_title':full_title,'sample':sample,'date':date})
    return songs

def add_songs(songs):
    try:
        for song in songs:
            get_or_create(title=song['title'],artists=song['artists'],genre=song['genre'],rank=song['rank'],full_title=song['full_title'],sample=song['sample'],date=song['date'])
        all_songs = get_existing_songs(True) 
        for song in all_songs:
            get_song(title=song.title,artists=song.artists).rank = ''
        for song in songs:
            get_song(title=song['title'],artists=song['artists']).rank = song['rank']
    except Exception,e:
        print 'add songs error:',e


def search(song):
    titles = []
    titles.append(song.full_title.replace('&','and').replace('feat.','featuring').replace('(Original Mix)','-+Original Mix').replace('Feat.', '-+feat.').replace('Extended Remix','').replace(')','').replace('(','').replace(' ','+'))
    titles.append(song.title.replace(' ','+').replace('&','and').replace('feat.','featuring'))
    artists = song.artists.split('|')
    for title in titles:
        while True:
            try:
                track_search = 'http://ws.spotify.com/search/1/track.json?q=%s' % title
                html = urllib2.urlopen(track_search)
                songs_dict = json.loads(html.read())
                for song_result in songs_dict['tracks']:
                    for artist in artists:
                        if similar(artist,song_result['artists'][0]['name']):
                            title = title.replace('+',' ')
                            #print 'comparing',title,'  AND  ',song_result['name'],'  by  ',artist,' AND ',song_result['artists'][0]['name']
                            if similar(title,song_result['name']) :
                                print 'FOUND!',song_result['href'],song.artists,'title:',song.title
                                return (title,song.artists,song_result['href'],song_result['album']['availability']['territories'])
                            elif title in song_result['name'] and 'original' in song_result['name'].lower():
                                print 'FOUND!',song_result['href'],song.artists,'title:',song.title
                                return (title,song.artists,song_result['href'],song_result['album']['availability']['territories'])
                            elif title in song_result['name'] and 'radio' in song_result['name'].lower():
                                print 'FOUND! (radio)',song_result['href'],song.artists,'title:',song.title
                                return (title,song.artists,song_result['href'],song_result['album']['availability']['territories'])
                            elif title in song_result['name']:
                                print 'FOUND! blind',song_result['href'],song.artists,'title:',song.title
                                return (title,song.artists,song_result['href'],song_result['album']['availability']['territories'])
            except Exception, e:
                print 'error',e,track_search
                if 'HTTP Error 502:' not in e:
                    continue            
                print 'retrying'
            break

class Song(Base):
    __tablename__ = 'songs'
    id = Column(Integer, primary_key=True)
    title = Column(String(250), nullable=False)
    artists = Column(String(250), nullable=False)
    genre = Column(String(250), nullable=False)
    rank = Column(Integer, nullable=True)
    highest_rank = Column(Integer, nullable=True)
    full_title = Column(String(250), nullable=False)
    link = Column(String(250), nullable=True)
    region = Column(String(500), nullable=True)
    sample = Column(String(250), nullable=True)
    date = Column(String(80), nullable=True)
    found_date = Column(String(80),nullable=True)
    def __str__(self):
        date = '-'.join(self.date.split('-')[1:]) + '-' +self.date.split('-')[0]
        class_top = 'class="'
        if self.rank != '':
            if int(self.highest_rank) > 40:
                class_top += 'not_top_40'
        if self.link:
            css = ''
            if self.found_date:
                margin = datetime.timedelta(days = 7)
                two_day_margin = datetime.timedelta(days = 2)
                today = datetime.date.today()
                dates = self.found_date.split('-')
                if today - two_day_margin <= datetime.date(int(dates[2]),int(dates[0]),int(dates[1])):
                    css = 'STYLE="background-color: rgb(134,228,150)"'
                elif today - margin <= datetime.date(int(dates[2]),int(dates[0]),int(dates[1])):
                    css = 'STYLE="background-color: rgb(255,255,0)"'
            return '<tr ' + class_top + '" ' + css + '><td>' + str(self.rank) +'</td> <td><a href=' +self.link + '>'+self.title + '</a></td><td>'+self.artists.replace('|',', ') + '</td><td>'+self.genre + '</td><td>'+str(self.highest_rank) + '</td><td>'+str(date) + '</td></tr>' 
        return '<tr ' +  class_top + ' no_link"><td>'+ str(self.rank) +'</td><td>' +self.full_title + '</td><td>'+self.artists.replace('|',', ') + '</td><td>'+self.genre + '</td><td>'+str(self.highest_rank) + '</td><td>'+str(date) + '</td></tr>\n' 

def drop_table():
    Base.metadata.drop_all(bind=engine)

def get_song(title,artists):
    return session.query(Song).filter(Song.title == title,Song.artists == artists).first()

def get_or_create(title,artists,genre,rank,full_title,sample,date):
    song = session.query(Song).filter(Song.title == title,Song.artists == artists).first()
    if song:
        if song.highest_rank > rank:
            song.rank = rank
            #print 'updating rank'
            song.highest_rank = rank
            session.commit()
        return song
    print 'new song:',title
    song = Song(title=title,artists=artists,genre=genre,rank=rank,highest_rank=rank,full_title=full_title,sample=sample,date=date)
    session.add(song)
    session.commit()
    return song 

def update_link(title,artists,link,region):
    song = session.query(Song).filter(Song.title == title,Song.artists == artists).first()
    print 'found link for',title
    song.link = link
    song.region = region
    song.found_date = '-'.join(str(datetime.date.today()).split('-')[1:]) + '-' + str(datetime.date.today()).split('-')[0]
    session.commit()

def get_ranked():
    songs = session.query(Song).all()
    ranked = [s for s in songs if str(s.rank).isdigit()]
    ranked.sort(key=lambda x: x.rank)
    unr = [s for s in songs if not str(s.rank).isdigit()]
    return ranked+unr

def get_existing_songs(all=False):
    if all:
        songs = session.query(Song).all()
        return songs
    songs = session.query(Song).filter(Song.link == None).all()
    return songs

def create_page():
    unordered_songs = get_existing_songs(True)
    print 'total songs:',len(unordered_songs)
    ranked = filter(lambda song: song.rank,unordered_songs)
    unranked = filter(lambda song: not song.rank,unordered_songs)
    ranked.sort(key = lambda x: int(x.rank))
    unranked.sort(key = lambda x: x.date)
    songs = ranked + unranked
    table = "<table class='tablesorter' id='myTable'><thead><b><th></th><th><a href='#'>title</a></th><th><a href='#'>artists</a></th><th><a href='#'>genre</a></th><th><a href='#'>highest rank</a></th><th style='width:100px'><a href='#'>date</a></th></thead></b><tbody>"
    for s in songs:
        table += str(s)
    table += '</tbody></table>'

    html = open('/var/www/templates/template_index.html').read()
    html = html.replace('{{ table }}',table)
    open('/var/www/templates/index.html',mode='w').write(html)
    print 'wrote page'

def main():
    print 'started at:',datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')
    if len(sys.argv) > 1:
        create_page()        
        exit()
    songs = get_songs() # get current top 100
    print 'got top100 songs'
    add_songs(songs) # add new songs or update
    songs_without_links = get_existing_songs()
    print 'searching'
    for song in songs_without_links: # search for links
        link = search(song)
        if link:
            update_link(region=link[3],link=link[2],title=song.title,artists=song.artists)
    create_page()        
    print 'finished.\n'

if __name__ == '__main__':
    main()

