<br>
<img src="resources/josm_tagger_120.png" alt="img" width="70" style="vertical-align:middle;">
<h1 style="display:inline-block; margin-left:10px;">
JOSM-What?!?</h1>

I love mapping on OpenStreetMap and my favorite editor is **JOSM**.

Unfortunately, I often need to map etherogeneous elements in the same session: roads, waterways, forests, buildings and their features (entrances, gates, driveways, garages). 

The editor's User Interface is powerful but it slows me down, despite I use v ery much the keyboard shortcuts: every time I have to manually add the tags one by one... it's so frustrating!

I also tried defining presets: that's useful but not very fast: once the preset is created, I still have to look for the one I need and select it from a list. Too slow!

Copy the tags from an existing object and paste them *Shift-Ctrl-V*? Yes, I tried that too, of course, and it's one of my favorite techniques; unfortunately it works just for the copied element. Too limited!

Also repeating the last operation with *Shift-R* is handy, but only works when the new element the same as the last selected one: for instance: click a Gate (*barrier=gate*), then create a new node, select it and hit Shift-R to make an new Gate of it. Too limited, again!

---

## *The idea*

One day I asked myself: "*why can't I use a hotkey, such as Ctrl-0 to activate a window, and "launch" from there some mnemonic command, easy to remember and fast to type, to apply one or more tags to the element(s) I have selected in JOSM?*"

<br>

For this reason, I created **JOSM Tagger**: 

<p align="center">
  <img src="resources/doc/pub/main_form_acp.png" style="box-shadow: 0 0 10px rgba(0,0,0,0.5);">
</p>

Once the program starts, it will stay visible on top of the other windows (you can configure it to partially or totally disappear, however).

You can normally work with JOSM but, when you come across an element which is encoded in JOSM Tagger, here comes the "magic": 

- **Select** that element in JOSM; 
- Click the main program window or just press Ctrl-0 to **recall JOSM Tagger**;
- **Type** the code corresponding to the tag (or group of tags) to be added;
- **Press Enter** to confirm!

JOSM Tagger will do the rest and apply all the tags associated with the recalled group.

The program comes with several tag groups I've defined for my personal needs; you can edit them or create new ones, of course!

...And if you need to know whether a group with the desired tags already exists or not, there's also a tool to Search Tool with filtering capabilities.

---

## *And now... "à vous!" (if you like)*
After working on it for some time, the program has now reached the state where "everything works... on my computer", so now  it's time for sharing; hope it will help you too!

Max

<br>


---


# Disclaimer

This program is distributed "*as-is*". 

JOSM Tagger was originally developed in Windows and all the described features *should* work as described here and in the documentation.

A Linux version is also available: it should work too, but there's some restriction, as the hotkey might not work, depending on the graphic environment:

 - On X11/Xorg: hotkey should work as intended
 - On Wayland: Most probably the hotkey won't work due to environment-dependent restrictions. If this is your case, you can try emulating a X11 session or use Josm Tagger without hotkey.
 
---

## Some nerdy facts :-)

- Josm Tagger is written in Python 3 (3.12-3.14), with some help from several AI engines (mainly Codex by OpenAI); it communicates wiyh JOSM through the native Remote Control interface; Optionally, it can use GUI automation features (only in Windows) to emulate user interaction through the regular controls.

- Developing the core feature (sending specified tags to JOSM) took just a couple of hours in February 2026, thanks to the AI contribution in building up the whole main form layout and transmission/control routines.

- Making everything work as I wanted, with proper logics and without critical glitches, took about four months, thanks to the AI's stupidity... seriously, don't expect miracles from those engines!.   
  
  OK, I worked on this project during my spare time, mainky in the weekends, that's still a huge time respect to the amount I dedicated to the core feature.

- While building JOSM Tagger, I also wanted to know a little more about the IA engines and test some of them (at least in their free version), so now I've learned that...

	- <u>The AI that fixed the most bugs</u> in this project was **Codex**: it has very good code analysis capabilities an can provide a working solution in a reasonable time; This is also the engine I used to implement new features into the app.
	
	- **Gemini** helped too, but it's slower and somehow less efficient; I still think that Codex is working better.  

	- How about **GitHub Copilot**? It participated too, of course! I found it's </u>quite good at creating form layouts</u> starting from mockup pictures, but when it had generate the code behind the controls, it started losing the overall view and increasing the level of Entropy, instead of reducing it.
	
	- <u>The worst AI</u> that participated in this project is **ChatGPT**.  