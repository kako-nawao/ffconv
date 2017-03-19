======
ffconv
======

Process media files to match profiles using ffmpeg

Why?
====

I needed to convert tons of media files to allow Direct Play with my Roku+Plex setup.
Why Direct Play? Because the box I use a media server has a pitiful CPU (Atom), so I does not do very well with
transcoding on the fly.

Why not upgrade the box instead? Not all of us are rich, you know... and I can't just throw it away, can I?
Couldn't you use ffmpeg directly instead? Of course, but analyzing streams to know if you have to convert anything is
a pain in the ass... now multiply that by hundreds of movies, then series, then music... you get the picture.

What?
=====

This is just a wrapper around FFmpeg tools, such as ``ffmpeg`` and ``ffprobe``, built in Python.
It's meant to be run in a shell, so you can play with for loops and whatnot. No GUI. Ever.
It did start off as a (somewhat ugly) script, but then I thought, "if this grows it could become
useful..." and decided to clean it up a bit. Just a bit.

How?
====

You could (not yet) set up a *profile* (right now there's only *roku*), which is basically a configuration of target
attributes for each media type (codec, channels, etc), which is used when processing to convert any streams if
needed.
For example, by using *roku*, all audio will be converted to 2-channel AAC and all subtitles to SRT.

Where?
======

It works right now, but some important functionality is missing:

+ Definition of profiles by users, probably as text files (json, yaml)
+ Option to *append* converted streams to original ones instead of replacing them
