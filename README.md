# auto-genote
Program to automatically check if a new grade has been published using genote, a website my school uses.

# Requirements
[This](genote.py) is a "cog" for [Red](https://github.com/Cog-Creators/Red-DiscordBot). You need to have a working installation of RedBot to use this.

# Installation
* Download [the cog](genote.py) into the `cogs` folder of Red
* Run `[p]load genote`

When fist running the bot, a config file will be created. You need to change the file's content and fill it with your Genote credentials. The bot will use those credentials to see if there's changes in the number of grades you have. Your credentials are safely stored on (and never leave) your own computer to prevent potential leaks.  
Your username should be written between the "double quotes" after `"username":`.  
Similarly, your password should be written between the "double quotes" after `"password":`.

# Configuration
There's 2 configuration commands:
1. `[p]genote channel <channel>` (replace `<channel>` with a mention to the channel of your choice) sets the channel where new grade announcements are posted
2. `[p]genote loop_time <time>` (replace `<time>` with the number of seconds of your choice) sets the number of seconds between each check for new grades

# Usage
The bot does it all for you!

Your users can do `[p]genote notify yes` to receive the announcements in PM. This allows for better notifications for people who don't regularly check the channel you've set.

They can stop receiving those notifications by doing `[p]genote notify no`.
