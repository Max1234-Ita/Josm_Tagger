# Running JOSM Tagger on Linux

On Linux, especially in Wayland sessions, the global hotkey may not work reliably; this is an environment limitation, not necessarily a bug in the application.

JOSM Tagger already includes a few supported paths you can try, as-is:

## 1. Use an X11 session

This is the most reliable option for global hotkeys.

At the login screen, choose an X11/Xorg session instead of Wayland, then start JOSM Tagger normally.

You can verify the session type with:

```bash
echo $XDG_SESSION_TYPE
```

The expected value is:

```bash
x11
```

## 2. Run JOSM Tagger inside Xephyr on Wayland

If you want to stay in Wayland but still use an X11 environment for the app, you can run it inside Xephyr.

This is already supported by the launcher script:

```bash
sudo apt install xserver-xephyr
JOSM_TAGGER_USE_XEPHYR=1 ./josmtagger.sh
```

The script also supports a manual Xephyr flow:

```bash
Xephyr :99 -screen 1280x800 -ac -br -reset
DISPLAY=:99 /home/ubu/PycharmProjects/Josm_Tagger/.venv/bin/python /home/ubu/PycharmProjects/Josm_Tagger/main.py
```

## 3. Use the restore helper in a Wayland session

The launcher supports restoring an already running instance through `--restore`.

This is implemented by the existing Linux instance-restore helper, so you can bind a desktop shortcut to:

```bash
/home/ubu/PycharmProjects/Josm_Tagger/josmtagger.sh --restore
```

If JOSM Tagger is already running, that command asks the existing instance to restore/focus itself. If no instance is running, it simply exits.


<br>

---


# Recommended configuration  
#### To use if the hotkey is not working

In case the hotkey doesn't work, you may want to avoid that JOSM Tagger gets minimzed into the System Tray; here's some option to set to prevent this:

1. Run Josm Tagger;

2. Open menu ***`Edit/Preferences`***;

3. In the ***Behaviour*** section, set as follows:

| Option | Set value |
| --- | --- |
| On focus loss | *`Do nothing`*  /  *`Fade out`* |
| On Apply | *`Keep form visible`* |
| On close | *`Exit app`* |
 
