# Tweetify

- Tweetify is a social media platform similar to tweetor.

## Get started

To set up tweetify on your local machine, you need to first get python and pip on your system.

On most GNU+Linux distros python is presintalled. If not then you can do this:
```
Arch-based: pacman -S python3 python3-pip
Debian-based: apt install python3 python3-pip
Void: xbps-install python3 python3-pip (i think)
Gentoo: emerge python3 python3-pip (i think this is how you install on gentoo, but if you don't have python then your package manager won't work anyway lmao)
OpenBSD: pkg_add python3 python3-pip
FreeBSD: You can use pkg package manager
```

Then clone this repo with `git clone https://github.com/tweetoruser/Tweetify.git``
cd into the repo directory and then start virtual environment with `python3 -m venv venv`

Activate the virtual environment with `source venv/bin/activate` on GNU+Linux and on FreeBSD/OpenBSD you can do `. venv/bin/activate`

Then install the required PIP packages:
`pip install flask flask_limiter captcha`

run `python3 database_setup.py && python3 app.py` to generate the database and start the web server.
The default listening port is 5000 so visit http://127.0.0.1:5000/ in your web browser.

# TODO:

- Create communities (not done)
- Create DM feature (done but i need to add engaged_dms feature like tweetor)
- Create bio feature (done)
- Add image captcha (done)
- Improve security (not done)
- Add change password feature (done)
- Add IP logging (done but i plan to remove IP logging in the future tbh)
- Add image feature (not done)

