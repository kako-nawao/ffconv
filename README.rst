ffconv
======

Process media files to match defined profiles using ffmpeg

Why?
----

I needed to convert tons of media files to allow Direct Play with my Roku+Plex setup.
Why Direct Play? Because the box I use as media server has a pitiful CPU (Atom), so I does not do very well with
transcoding on the fly.
Why not upgrade the box instead? Not all of us are rich, you know... and I can't just throw it away, can I?
Couldn't I use ffmpeg directly instead? Of course, I know my way around ffmpeg, but analyzing streams to know if you
have to convert anything is a pain in the ass... now multiply that by hundreds of videos and audio files... No way.

What?
-----

It is just a wrapper around FFmpeg tools (ie, ``ffmpeg`` and ``ffprobe``) built in Python.
All it does is probe the input file and check the profile to determine what streams need to be converted.
Then it converts them and merges everything back into a single file, very much like the original
one (by default replacing it).

How?
----

Install it from this repository::

    pip install git+https://github.com/kako-nawao/ffconv.git

Then process your file with the profile you want::

    ffconv Titanic.mkv roku

You can also specify the output file name if you want to keep the original one::

    ffconv Titanic.mkv roku --output Titanic-notranscode.mkv

If everything works you will get no output whatsoever. Cool, right? If you don't like that
you can enable **debug** mode and you'll get a ton of info::

    ffconv Titanic.mkv roku -d

To Do
-----

There are a few things pending:

- Option to add profiles, as right now there's only *roku*
- Option to *append* converted streams, instead of replacing the original ones
