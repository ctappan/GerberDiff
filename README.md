# GerberDiff

A very crude tool to automatically generate diffs of PCB gerber files. Assumes that Gerbers are supplied as two .zip archives each containing a "Gerber" folder. 

This builds on Curta Circuitos' [pcb-tools package](https://github.com/curtacircuitos/pcb-tools). I installed the package from source, it may also be available via PyPi. I had to manually install the cairo image library via homebrew.  This has only been tested on MacOS 10.15.17, but should work on Windows if you install Cairo.

## Future improvements:
- more flexible input format
- optimize the geber rendering 
- packaging/sane installation