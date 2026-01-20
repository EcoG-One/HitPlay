`**HitPlay** is a music knowledge game. Find the song, the performer and if you can the year it was first released!`
```
#Rules of the game
Inspired by the board game Hitster, now we can all play it on our computer, with the songs of our choice.
The game is very simple. It starts by pressing the Start Game button and immediately a song starts playing.
 We must guess the title and the performer of the song, as well as the year of its first release. 
 If we find the title, we get 1 point, for the performer another one, while if we find the year we get 
 two more points. 
 If we do not find the exact year but our guess is up to 2 years away from the correct one, we get 1 point.
 The winner is the player who collects the most points. 
 (Players agree on the number of total points for the game to end, 
 or on a time limit or otherwise when all the available songs have played).
 To check the correctness of the player's answer, click on the song card that appears on the screen. 
 It will turn around and reveal the correct answer. 
```
```
A second way to play is against the clock. Start and press the timer. 
A one-minute countdown will start, and the player has to find as many songs as he can in one minute. 
If he doesn't know the song, he can go to the next one by pressing Next, or go back to a previous song with Previous. 

#Instructions
```
`You will find the HitPlay game in 2 formats: `
```
The first consists of a single webpage, HitPlay.html, which contains all the game code in HTML, CSS and JavaScript. 
But in order for it to work you need to add a folder named *music* 
containing all the songs of the Hitster list on Spotify:
 https://open.spotify.com/playlist/0Mpj1KwRmY2pHzmj7mfbdh
The songs must be in mp3. In a future version, there will be no need for the songs to be added by you, 
they will play directly from Spotify just like in the board game. 
```
```
Perhaps more practical is the second format, as it allows you to use any songs you like. 
Simply create a folder named music and copy the songs you want to this folder. 
Then you run the main.py which scans the music folder, finds all the songs in it, reads their metadata, 
and creates a JSON file with all the correct answers. 
It then displays the game's website, and serves to it the songs and the relevant answer cards. 
Of course, in order for the main.py to run, you must first install the requirements with:
pip install -r requirements.txt 
```
Have fun!
