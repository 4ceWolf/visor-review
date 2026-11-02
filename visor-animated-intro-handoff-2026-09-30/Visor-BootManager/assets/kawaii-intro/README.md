# Personal review media

The user's `Kawaii GIF.gif` is copied unchanged as `kawaii.gif`. Original author
and redistribution rights are unverified. Do not treat the code's BSD license
as a license for the character artwork. Replace with rights-cleared media before
publishing. The source-only patch excludes these assets.

`kawaii-mjpeg.mp4` is a decoder fixture converted using:

```sh
ffmpeg -threads 1 -i kawaii.gif -an -c:v mjpeg -threads 1 -q:v 3 \
  -pix_fmt yuvj420p -movflags +faststart kawaii-mjpeg.mp4
```
